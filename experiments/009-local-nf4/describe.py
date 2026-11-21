from pathlib import Path
import json
p=Path(__file__).resolve().parent/"run-nf4-preflight"
def lines(name):
    f=p/name
    return [json.loads(i) for i in f.read_text(encoding="utf8").splitlines() if i.strip()] if f.exists() else []
real=lines("real.jsonl");small=lines("small.jsonl")
actual=sorted({e["selected"] for e in real if e.get("selected")})
ineligible=[e for e in real if e.get("event")=="eligibility" and not any(v["eligible"] and v["enabled"] for v in e["candidates"].values())]
summary={"small_dispatch":next((r["selected"] for r in small if "selected" in r),None),
         "real_dispatches":actual,"unclassified_dispatches":sum(e.get("event")=="dispatch" and e["selected"] is None for e in real),
         "real_distinct_calls_profiled":sum(e.get("event")=="dispatch" for e in real),
         "rejected_shapes":ineligible,"real_shapes_seen":sum(e.get("event")=="before" for e in real)}
(p/"attention-summary.json").write_text(json.dumps(summary,indent=2),encoding="utf8")
print(json.dumps({k:v for k,v in summary.items() if k!="rejected_shapes"}),"rejected",len(ineligible))
