"""Modified placement only. Official Body/Head, depth and PSD assembly functions."""
import argparse
from contextlib import ExitStack
import gc
import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

import torch
from diffusers import AutoencoderKL
from safetensors.torch import load_file
from transformers import CLIPTextModel
from modules.layerdiffuse import diffusers_kdiffusion_sdxl as layer
from modules.layerdiffuse.layerdiff3d import UNetFrameConditionModel
from modules.layerdiffuse.vae import TransparentVAE
from modules.marigold import MarigoldDepthPipeline
from utils.torch_utils import seed_everything


def peak(label):
    torch.cuda.synchronize()
    print("PEAK", json.dumps(dict(stage=label, allocated=torch.cuda.max_memory_allocated(),
                                  reserved=torch.cuda.max_memory_reserved())), flush=True)
    torch.cuda.reset_peak_memory_stats()


def release():
    gc.collect()
    torch.cuda.empty_cache()


def run_layer(api, args):
    unet = UNetFrameConditionModel.from_pretrained(args.layer, subfolder="unet").to("cpu")
    vae = AutoencoderKL.from_pretrained(args.layer, subfolder="vae").to("cpu", dtype=torch.bfloat16)
    trans = TransparentVAE.from_pretrained(args.layer, subfolder="trans_vae").to("cpu", dtype=torch.bfloat16)
    pipe = layer.KDiffusionStableDiffusionXLPipeline.from_pretrained(
        args.layer, unet=unet, vae=vae, trans_vae=trans, text_encoder=None, text_encoder_2=None, scheduler=None)
    for k, v in load_file(str(args.cache)).items():
        tag, index = k.rsplit(".", 1)
        pipe._cached_prompt_embeds.setdefault(tag, [None, None])[int(index)] = v
    assert len(pipe._cached_prompt_embeds)==24
    encode = layer.vae_encode
    decode = trans.decoder.forward
    pipeline_call = type(pipe).__call__
    current = ["load"]
    def prepare(self, *pos, **kw):
        vae.cpu()
        trans.cpu()
        unet.to("cuda")
        current[0] = "Body" if kw["group_index"]==0 else "Head"
        return pipeline_call(self, *pos, **kw)
    def encode_image(*pos, **kw):
        unet.to("cpu")
        vae.cuda()
        trans.encoder.cuda()
        latent = encode(*pos, **kw)
        vae.cpu()
        trans.encoder.cpu()
        release()
        peak(current[0]+" image encode")
        unet.to("cuda")
        return latent
    decoding = set()
    def decode_image(sd_vae, latent, *pos, **kw):
        if current[0] not in decoding:
            peak(current[0]+" denoise")
            unet.to("cpu")
            vae.cuda()
            trans.decoder.cuda()
            release()
            decoding.add(current[0])
        if kw.get("mask") is not None:
            kw["mask"] = kw["mask"].cuda()
        return decode(sd_vae, latent.cuda(), *pos, **kw)
    with ExitStack() as ctx:
        ctx.enter_context(patch.object(type(pipe),"__call__",prepare))
        ctx.enter_context(patch.object(layer,"vae_encode",encode_image))
        ctx.enter_context(patch.object(trans.decoder,"forward",decode_image))
        unet.to("cuda")
        api.run_layerdiff(pipe,str(args.source),str(args.output),42,30,1024)
    peak("Head decode completed")


def run_depth(api, args):
    unet=UNetFrameConditionModel.from_pretrained(args.depth,subfolder="unet",torch_dtype=torch.bfloat16).to("cpu")
    enc=CLIPTextModel.from_pretrained(args.depth/"text_encoder",dtype="auto",device_map={"":0})
    pipe=MarigoldDepthPipeline.from_pretrained(args.depth,unet=unet,text_encoder=enc,torch_dtype=torch.bfloat16)
    pipe.cache_tag_embeds()
    del enc
    pipe.vae.cuda()
    single=pipe.single_infer
    decode=pipe.decode_depth
    def denoise(*pos,**kw):
        pipe.vae.cpu()
        release()
        peak("depth image encode")
        unet.to("cuda")
        return single(*pos,**kw)
    decoding=False
    def decode_depth(*pos,**kw):
        nonlocal decoding
        if not decoding:
            peak("depth denoise")
            unet.to("cpu")
            pipe.vae.cuda()
            release()
            decoding=True
        return decode(*pos,**kw)
    with patch.object(pipe,"single_infer",denoise), patch.object(pipe,"decode_depth",decode_depth):
        api.run_marigold(pipe,str(args.source),str(args.output),42,768)
    peak("depth decode")


@torch.inference_mode()
def run(args):
    assert torch.cuda.device_count()==1 and "3060 Ti" in torch.cuda.get_device_name()
    print("GPU",torch.cuda.get_device_name(),os.environ["CUDA_VISIBLE_DEVICES"],flush=True)
    entry=Path("inference/scripts/inference_psd_quantized.py")
    spec=importlib.util.spec_from_file_location("official_psd",entry)
    api=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    seed_everything(42)
    run_layer(api,args)
    release()
    run_depth(api,args)
    release()
    api.further_extr(str(args.output/args.source.stem),rotate=False,save_to_psd=True,tblr_split=False)
    print("PSD assembly returned",flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ["layer","depth","source","cache","output"]:
        p.add_argument(key,type=Path)
    run(p.parse_args())
