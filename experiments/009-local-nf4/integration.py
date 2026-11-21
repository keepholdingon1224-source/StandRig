"""Standalone CLIP pair. Called in a fresh process per condition."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import bitsandbytes as bnb
import torch
from diffusers.hooks import apply_group_offloading
from transformers import CLIPTextModel, CLIPTextModelWithProjection, CLIPTokenizer

TAGS = ["front hair", "back hair", "head", "neck", "neckwear", "topwear", "handwear",
        "bottomwear", "legwear", "footwear", "tail", "wings", "objects"]


def log(event, **values):
    print("TRACE " + json.dumps(dict(event=event, **values)), flush=True)


def memory(event):
    free, total = torch.cuda.mem_get_info()
    log(event, free=free, total=total, allocated=torch.cuda.memory_allocated(),
        reserved=torch.cuda.memory_reserved())


def tensor(x):
    return [str(x.device), str(x.dtype), list(x.shape)]


def digest(x):
    return hashlib.sha256(x.detach().contiguous().cpu().view(torch.uint8).numpy().tobytes()).hexdigest()


def state(weight):
    qs = weight.quant_state
    return dict(weight=tensor(weight), quant_type=qs.quant_type, quant_dtype=str(qs.dtype),
                absmax=tensor(qs.absmax), code=tensor(qs.code))


def observe(encoders):
    for index, encoder in enumerate(encoders):
        for i, layer in enumerate(encoder.text_model.encoder.layers):
            key = f"encoder{index + 1}.layer{i}"
            def enter(mod, args, key=key):
                torch.cuda.synchronize()
                log("enter", layer=key, weight_state=state(mod.self_attn.q_proj.weight))

            def leave(mod, args, result, key=key):
                torch.cuda.synchronize()
                log("completed", layer=key)

            layer.register_forward_pre_hook(enter)
            layer.register_forward_hook(leave)
    original = bnb.matmul_4bit

    def traced(x, w, *args, **kwargs):
        qs = kwargs["quant_state"]
        log("matmul", x=tensor(x), w=tensor(w), absmax=tensor(qs.absmax), code=tensor(qs.code))
        result = original(x, w, *args, **kwargs)
        torch.cuda.synchronize()
        return result

    bnb.matmul_4bit = traced


@torch.inference_mode()
def run(opts):
    log("process", pid=os.getpid(), uuid=os.environ["CUDA_VISIBLE_DEVICES"], gpu=torch.cuda.get_device_name(),
        torch=torch.__version__, bnb=bnb.__version__, case=opts.case, hooks=opts.trace)
    assert torch.cuda.device_count() == 1 and "3060 Ti" in torch.cuda.get_device_name()
    memory("before_load")
    encoders = []
    tokens = []
    for suffix, cls in [("", CLIPTextModel), ("_2", CLIPTextModelWithProjection)]:
        tokenizer = CLIPTokenizer.from_pretrained(opts.model / ("tokenizer" + suffix))
        ids = tokenizer(TAGS, padding="max_length", truncation=True, max_length=tokenizer.model_max_length,
                        return_tensors="pt").input_ids
        assert list(ids.shape) == [13, 77]
        tokens.append(ids)
        log("tokens", encoder=suffix or "1", tags=TAGS, ids=ids.tolist(), tensor=tensor(ids), sha256=digest(ids))
        encoder = cls.from_pretrained(opts.model / ("text_encoder" + suffix), dtype="auto", device_map={"": 0})
        encoders.append(encoder.eval())
        log("loaded", encoder=suffix or "1", layers=len(encoder.text_model.encoder.layers),
            q=state(encoder.text_model.encoder.layers[0].self_attn.q_proj.weight))
    if opts.case == "A2":
        for encoder in encoders:
            apply_group_offloading(encoder, onload_device=torch.device("cuda"), num_blocks_per_group=1)
    if opts.case == "A3":
        for encoder in encoders:
            encoder.to("cpu")
    if opts.trace:
        observe(encoders)
    device = encoders[0].device
    features = []
    memory("before_forward")
    for idx, (encoder, ids) in enumerate(zip(encoders, tokens)):
        if opts.case == "A3":
            encoder.to("cuda")
            device = encoder.device
        result = encoder(ids.to(device), output_hidden_states=True, return_dict=False)
        torch.cuda.synchronize()
        feat = result[-1][-2]
        features.append(feat.cpu())
        log("encoded", index=idx, layers=len(encoder.text_model.encoder.layers), tensor=tensor(feat),
            sha256=digest(feat), finite=bool(feat.isfinite().all()))
        pooled = result[0].cpu()
        if opts.case == "A3":
            encoder.to("cpu")
    for label, x in [("body_tokens", torch.cat(features, dim=-1)), ("pooled", pooled)]:
        assert x.isfinite().all()
        log("embedding", name=label, tensor=tensor(x), sha256=digest(x), finite=True)
    memory("after_forward")
    log("pass")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("model", type=Path)
    p.add_argument("case", choices=["A1", "A2", "A3"])
    p.add_argument("--trace", action="store_true")
    run(p.parse_args())
