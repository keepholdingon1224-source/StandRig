"""External measurement driver; the pinned inference and StandRig runner stay untouched."""
import csv,datetime,hashlib,json,os,subprocess,sys,time,threading
from pathlib import Path
import psutil
P=Path(__file__).resolve().parent
OUT=P/"run-nf4-preflight";GPU="GPU-cf2220a2-aaf6-affa-ea59-8951594faf5e"
REPO=P/"StandRig";OFF=P/"see-through";SOURCE=REPO/"source_007/original.png"
def git(*args):return subprocess.check_output(["git","-C",str(OFF),*args],text=True).strip()
def sampled(cmd,phase,env,log):
    with log.open("wb") as stream,(OUT/(phase+"-samples.csv")).open("w",newline="") as fp:
        proc=subprocess.Popen(cmd,cwd=OFF,stdout=stream,stderr=subprocess.STDOUT,env=env)
        target=psutil.Process(proc.pid);w=csv.writer(fp)
        w.writerow(["utc","tree_rss_bytes","system_used_bytes","system_available_bytes","gpu_used_mib","gpu_free_mib"])
        while True:
            try: members=[target,*target.children(recursive=True)]
            except psutil.NoSuchProcess: members=[]
            rss=0
            for m in members:
                try:rss+=m.memory_info().rss
                except psutil.NoSuchProcess:pass
            mem=psutil.virtual_memory()
            gpu=subprocess.check_output(["nvidia-smi","-i",GPU,"--query-gpu=memory.used,memory.free","--format=csv,noheader,nounits"],text=True).strip().split(",")
            w.writerow([datetime.datetime.now(datetime.timezone.utc).isoformat(),rss,mem.total-mem.available,mem.available,*[v.strip() for v in gpu]]);fp.flush()
            if proc.poll() is not None:return proc.returncode
            time.sleep(1)
def main():
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=GPU,HF_HOME=str(P/"hf"),HF_HUB_OFFLINE="1",OMP_NUM_THREADS="8",MKL_NUM_THREADS="8",OPENBLAS_NUM_THREADS="8",PYTHONUTF8="1",PYTHONUNBUFFERED="1",NF4_DIAG_DIR=str(OUT),PYTHONPATH=str(P/"diagnostics"))
    pins=json.loads((OUT/"revisions-nf4.json").read_text(encoding="utf-8-sig"))
    snapshots=[P/"hf/hub"/("models--"+repo.replace("/","--"))/"snapshots"/pin for repo,pin in sorted(pins.items(),key=lambda pair:0 if "layerdiff3d" in pair[0] else 1)]
    report={"mode":"nf4","resolution":1024,"depth_resolution":768,"seed":42,"steps":30,"group_offload":True,"source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),"official_commit":git("rev-parse","HEAD"),"gpu_uuid":GPU,"models":pins,"diagnostic_pass":False,"smoke":"not_started"}
    try:
        assert report["official_commit"]=="fc4440db7c076518e313f378e28b1504e9886a95" and not git("status","--porcelain","--untracked-files=no")
        hashes=json.loads((OUT/"verified-files.json").read_text());assert all(hashes[k]["revision"]==v for k,v in pins.items())
        subprocess.run([sys.executable,"-m","pip","freeze"],stdout=(OUT/"pip-freeze.txt").open("w"),check=True)
        rc=sampled([sys.executable,str(P/"diagnostics/attention_probe.py")],"small",env,OUT/"diagnostic-1.txt")
        report["small_exit"]=rc
        if rc:raise RuntimeError("small diagnostic failed")
        env["NF4_PROBE"]="probe"
        cmd=[sys.executable,"inference/scripts/inference_psd_quantized.py","--srcp",str(SOURCE),"--save_dir",str(P/"probe-images"),"--save_to_psd","--seed","42","--resolution","1024","--resolution_depth","768","--num_inference_steps","30","--repo_id_layerdiff",str(snapshots[0]),"--repo_id_depth",str(snapshots[1])]
        rc=sampled(cmd,"real",env,OUT/"diagnostic-2-3.txt");report["real_exit"]=rc
        if rc!=42 or not (OUT/"memory.jsonl").exists() or '"probe_completed"' not in (OUT/"memory.jsonl").read_text():
            raise RuntimeError("real-input preflight stopped; inspect diagnostic-2-3.txt and real.jsonl")
        report["diagnostic_pass"]=True;env["NF4_PROBE"]="measure"
        full=P/"run-nf4-1024";assert not full.exists()
        cmd=[sys.executable,str(REPO/"experiments/009-run-seethrough.py"),str(OFF),str(SOURCE),str(full),str(OUT/"revisions-nf4.json"),"--mode","nf4","--resolution","1024"]
        report["smoke"]="started";rc=sampled(cmd,"full",env,OUT/"runner.txt");report["full_exit"]=rc
        report["smoke"]=json.loads((full/"run.json").read_text())["status"]
        if rc:raise RuntimeError("official runner returned failure")
    except Exception as err:
        report["error"]=str(err)
        if report["smoke"]=="not_started":(OUT/"inference.txt").write_text("Full inference not started: "+str(err)+"\n")
        raise
    finally:(OUT/"run.json").write_text(json.dumps(report,indent=2))
if __name__=="__main__":main()


