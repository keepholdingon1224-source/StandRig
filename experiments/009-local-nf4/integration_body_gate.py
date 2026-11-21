"""External gate: exit 42 only after the first successful, synchronized UNet forward."""
import os
from pathlib import Path
import runpy
import sys

import torch
from modules.layerdiffuse.diffusers_kdiffusion_sdxl import KDiffusionStableDiffusionXLPipeline
from modules.layerdiffuse.layerdiff3d import UNetFrameConditionModel

assert torch.cuda.device_count() == 1 and "3060 Ti" in torch.cuda.get_device_name()
print("GPU", torch.cuda.get_device_name(), os.environ["CUDA_VISIBLE_DEVICES"], flush=True)
cache = KDiffusionStableDiffusionXLPipeline.cache_tag_embeds
forward = UNetFrameConditionModel.forward


def cache_gate(self, *args, **kwargs):
    torch.cuda.synchronize()
    print("cache_tag_embeds enter; load peak allocated/reserved",
          torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved(), flush=True)
    torch.cuda.reset_peak_memory_stats()
    result = cache(self, *args, **kwargs)
    torch.cuda.synchronize()
    print("cache_tag_embeds success; peak allocated/reserved",
          torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved(), flush=True)
    return result


def body_gate(self, *args, **kwargs):
    print("Body forward enter", flush=True)
    torch.cuda.reset_peak_memory_stats()
    forward(self, *args, **kwargs)
    torch.cuda.synchronize()
    print("Body forward success; peak allocated/reserved",
          torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved(), flush=True)
    os._exit(42)


KDiffusionStableDiffusionXLPipeline.cache_tag_embeds = cache_gate
UNetFrameConditionModel.forward = body_gate
entry = Path("inference/scripts/inference_psd_quantized.py").resolve()
sys.argv[0] = str(entry)
sys.path.insert(0, str(entry.parent))
runpy.run_path(str(entry), run_name="__main__")
