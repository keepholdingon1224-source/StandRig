"""Fresh-process CLIP placement intervention. Never dispatch a mixed-device state."""
import argparse
from types import SimpleNamespace
from pathlib import Path

import integration as clip
import torch


def tensors(q):
    result = {k: v for k, v in vars(q).items() if isinstance(v, torch.Tensor)}
    if q.state2 is not None:
        result.update({"state2." + k: v for k, v in tensors(q.state2).items()})
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("model", type=Path)
    p.add_argument("condition", choices=["control", "fix", "reference"])
    args = p.parse_args()
    original = clip.bnb.matmul_4bit
    memory = clip.memory

    def measured(event):
        memory(event)
        clip.log("peak", boundary=event, allocated=torch.cuda.max_memory_allocated(),
                 reserved=torch.cuda.max_memory_reserved())

    def checked(x, w, *pos, **kw):
        q = kw["quant_state"]
        before = tensors(q)
        packed = clip.digest(w)
        wrong = [v for v in before.values() if v.device != w.device]
        repair = bool(wrong and args.condition == "fix")
        if repair:
            assert w.is_cuda and all(v.device.type == "cpu" for v in wrong)
            q.to(w.device)
        after = tensors(q)
        after_hash = clip.digest(w)
        clip.log("placement", condition=args.condition, input=clip.tensor(x), weight=clip.tensor(w),
                 before={k:clip.tensor(v) for k,v in before.items()},
                 after={k:clip.tensor(v) for k,v in after.items()}, nested=q.nested,
                 moved_bytes=sum(v.numel()*v.element_size() for v in wrong) if repair else 0,
                 packed_before=packed, packed_after=after_hash)
        assert packed == after_hash
        if x.device != w.device or any(v.device != w.device for v in after.values()):
            measured("placement_rejected")
            raise ValueError("Placement check rejected mixed devices before kernel dispatch")
        torch.cuda.synchronize()
        return original(x, w, *pos, **kw)

    clip.memory = measured
    clip.bnb.matmul_4bit = checked
    clip.run(SimpleNamespace(model=args.model, case="A3" if args.condition=="reference" else "A2", trace=True))


if __name__ == "__main__":
    main()
