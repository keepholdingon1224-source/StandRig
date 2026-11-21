import os,sys,subprocess,json
from pathlib import Path
from measure import sampled,GPU
p=Path(__file__).resolve().parent;root=p/"run-nf4-preflight";out=root/"blocking-diagnostic";out.mkdir(exist_ok=True)
pins=json.loads((root/"revisions-nf4.json").read_text(encoding="utf-8-sig"))
paths=[p/"hf/hub"/("models--"+k.replace("/","--"))/"snapshots"/pins[k] for k in sorted(pins,key=lambda k:0 if "layerdiff3d" in k else 1)]
env=dict(os.environ,CUDA_VISIBLE_DEVICES=GPU,CUDA_LAUNCH_BLOCKING="1",MPLCONFIGDIR=str(p/"mpl-cache"),HF_HOME=str(p/"hf"),HF_HUB_OFFLINE="1",PYTHONUTF8="1",PYTHONUNBUFFERED="1",PYTHONPATH=str(p/"diagnostics"),NF4_PROBE="probe",NF4_DIAG_DIR=str(out))
cmd=[sys.executable,"inference/scripts/inference_psd_quantized.py","--srcp",str(p/"StandRig/source_007/original.png"),"--save_dir",str(p/"probe-images"),"--save_to_psd","--resolution","1024","--resolution_depth","768","--seed","42","--num_inference_steps","30","--repo_id_layerdiff",str(paths[0]),"--repo_id_depth",str(paths[1])]
rc=sampled(cmd,"blocking-only",env,out/"inference.txt")
(out/"result.json").write_text(json.dumps(dict(exit=rc,launch_blocking=True,purpose="Locate asynchronous error; diagnostic only, not a smoke test.")))
