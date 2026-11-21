"""Run one inference-only probe. The caller sets CUDA_VISIBLE_DEVICES before startup."""
import argparse
import json
import os
from pathlib import Path

import bitsandbytes as bnb
import torch
from safetensors import safe_open


def emit(**values):
    print(json.dumps(values), flush=True)


def memory(event):
    free, total = torch.cuda.mem_get_info()
    emit(event=event, free=free, total=total, allocated=torch.cuda.memory_allocated(),
         reserved=torch.cuda.memory_reserved())


@torch.inference_mode()
def probe(case, model):
    gpu = torch.cuda.get_device_name()
    emit(pid=os.getpid(), gpu=gpu, visible=os.environ["CUDA_VISIBLE_DEVICES"],
         torch=torch.__version__, bnb=bnb.__version__, dll=Path(bnb.cextension.lib._lib._name).name)
    assert torch.cuda.device_count() == 1 and "3060 Ti" in gpu
    torch.manual_seed(42)
    dtype = torch.bfloat16
    shape = (2, 8, 64) if case == "small" else (13, 77, 768)
    width = shape[-1]
    memory("before_setup")
    x = torch.randn(shape, dtype=dtype, device="cuda")
    if case == "control":
        layer = torch.nn.Linear(width, width, dtype=dtype).cuda()
    else:
        layer = bnb.nn.Linear4bit(width, width, compute_dtype=dtype, quant_type="nf4",
                                  compress_statistics=False).to(dtype=dtype)
        if case == "clip":
            prefix = "text_model.encoder.layers.0.self_attn.q_proj"
            with safe_open(model, framework="pt", device="cpu") as weights:
                key = prefix + ".weight"
                stats = {k: weights.get_tensor(k) for k in weights.keys() if k.startswith(key + ".")}
                layer.weight = bnb.nn.Params4bit.from_prequantized(
                    weights.get_tensor(key), stats, device="cuda", module=layer)
                layer.bias = torch.nn.Parameter(weights.get_tensor(prefix + ".bias").cuda())
        else:
            layer = layer.cuda()
    emit(case=case, input=list(x.shape), input_dtype=str(x.dtype), logical_weight=[width, width],
         weight=list(layer.weight.shape), weight_dtype=str(layer.weight.dtype))
    torch.cuda.synchronize()
    memory("before_forward")
    y = layer(x)
    torch.cuda.synchronize()
    assert y.shape == x.shape and y.dtype == dtype and torch.isfinite(y).all().item()
    emit(result="pass", output_dtype=str(y.dtype), rms=y.float().square().mean().sqrt().item())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=["control", "small", "clip"])
    parser.add_argument("--model")
    args = parser.parse_args()
    probe(args.case, args.model)
