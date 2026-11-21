"""Gate 3 only: stage CLIP, image encoders, then UNet; stop after first Body forward."""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from diffusers import AutoencoderKL
from safetensors.torch import save_file
from transformers import CLIPTextModel, CLIPTextModelWithProjection

from integration import TAGS, digest
from modules.layerdiffuse import diffusers_kdiffusion_sdxl as layer
from modules.layerdiffuse.layerdiff3d import UNetFrameConditionModel
from modules.layerdiffuse.vae import TransparentVAE
from utils.cv import center_square_pad_resize
from utils.torch_utils import seed_everything
from diagnostics.attention_probe import install


def stage(label):
    torch.cuda.synchronize()
    print("STAGE", json.dumps(dict(label=label, allocated=torch.cuda.memory_allocated(),
          peak_allocated=torch.cuda.max_memory_allocated(), peak_reserved=torch.cuda.max_memory_reserved(),
          free_total=torch.cuda.mem_get_info())), flush=True)
    torch.cuda.reset_peak_memory_stats()


@torch.inference_mode()
def body(model, source, cache):
    assert torch.cuda.device_count() == 1 and "3060 Ti" in torch.cuda.get_device_name()
    print("GPU", torch.cuda.get_device_name(), os.environ["CUDA_VISIBLE_DEVICES"], flush=True)
    seed_everything(42)
    install()
    encoders = {}
    for key, cls in [("text_encoder", CLIPTextModel), ("text_encoder_2", CLIPTextModelWithProjection)]:
        encoders[key] = cls.from_pretrained(model / key, dtype="auto", device_map={"": 0}).eval().to("cpu")
    unet = UNetFrameConditionModel.from_pretrained(model, subfolder="unet").to("cpu")
    trans = TransparentVAE.from_pretrained(model, subfolder="trans_vae").to("cpu", dtype=torch.bfloat16)
    vae = AutoencoderKL.from_pretrained(model, subfolder="vae").to("cpu", dtype=torch.bfloat16)
    pipe = layer.KDiffusionStableDiffusionXLPipeline.from_pretrained(
        model, unet=unet, trans_vae=trans, vae=vae, scheduler=None, **encoders)
    stage("loaded_cpu")
    heads = ["headwear","face","irides","eyebrow","eyewhite","eyelash","eyewear","ears","earwear","nose","mouth"]
    for tags in (TAGS, heads):
        hidden = []
        for tokenizer, encoder in [(pipe.tokenizer,pipe.text_encoder),(pipe.tokenizer_2,pipe.text_encoder_2)]:
            encoder.to("cuda")
            ids = tokenizer(tags,padding="max_length",max_length=tokenizer.model_max_length,
                            truncation=True,return_tensors="pt").input_ids.cuda()
            result = encoder(ids, output_hidden_states=True, return_dict=False)
            hidden.append(result[-1][-2].cpu())
            pooled = result[0].cpu()
            del result, ids
            encoder.to("cpu")
        embeddings = torch.cat(hidden,dim=-1)
        print("CLIP",len(tags),digest(embeddings),digest(pooled),flush=True)
        assert embeddings.isfinite().all() and pooled.isfinite().all()
        for i,tag in enumerate(tags):
            pipe._cached_prompt_embeds[tag]=[embeddings[i:i+1].to(unet.dtype),pooled[i:i+1]]
    save_file({tag+"."+str(i):t.contiguous().clone() for tag, pair in pipe._cached_prompt_embeds.items()
               for i,t in enumerate(pair)},str(cache))
    pipe.text_encoder = pipe.text_encoder_2 = None
    encoders.clear()
    del encoder
    torch.cuda.empty_cache()
    stage("clip_released")
    vae.to("cuda")
    trans.encoder.to("cuda")
    rgba=np.array(Image.open(source).convert("RGBA"))
    image,_,_=center_square_pad_resize(rgba,1024,return_pad_info=True)
    rgb=image[...,:3]
    argb=np.concatenate([np.full_like(rgb[...,:1],255),rgb],axis=2)
    latent=layer.vae_encode(vae,trans.encoder,layer.img2tensor(argb,normalize=True),use_offset=False)
    vae.to("cpu")
    trans.encoder.to("cpu")
    torch.cuda.empty_cache()
    stage("vae_released")
    unet.to("cuda")
    stage("unet_resident")
    pipe(strength=1.0,num_inference_steps=30,batch_size=1,generator=torch.Generator(device="cuda").manual_seed(42),
         guidance_scale=1.0,prompt=TAGS,negative_prompt="",c_concat=latent.to(unet.device,unet.dtype),group_index=0)
    raise RuntimeError("Body probe did not intercept its first forward")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ["model","source","cache"]:
        p.add_argument(key,type=Path)
    args=p.parse_args()
    body(args.model,args.source,args.cache)
