from pathlib import Path
import csv,json
p=Path(__file__).resolve().parent/"run-nf4-preflight"
result={}
for f in p.rglob("*-samples.csv"):
    with f.open(encoding="utf8") as s: rows=list(csv.DictReader(s))
    if rows:
        result[f.relative_to(p).as_posix()]={"samples":len(rows),"max_gpu_used_mib":max(int(r["gpu_used_mib"]) for r in rows),"max_tree_rss_bytes":max(int(r["tree_rss_bytes"]) for r in rows),"min_available_system_ram_bytes":min(int(r["system_available_bytes"]) for r in rows)}
(p/"sample-summary.json").write_text(json.dumps(result,indent=2))
print(result)
