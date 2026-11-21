"""Run outside the pinned checkout. No backend is forced."""
import functools, json, os, sys, warnings
from pathlib import Path
import torch
import torch.nn.functional as F
OUT=Path(os.environ["NF4_DIAG_DIR"])
MODE=os.environ.get("NF4_PROBE","small")
def write(file,data):
    with (OUT/file).open("a",encoding="utf8") as f: f.write(json.dumps(data,ensure_ascii=False)+"\n")
def info(t):
    return None if t is None else dict(shape=list(t.shape),stride=list(t.stride()),dtype=str(t.dtype),device=str(t.device))
def candidates(q,k,v,mask,drop,causal,gqa):
    backend=torch.backends.cuda
    args=backend.SDPAParams(q,k,v,mask,drop,causal,gqa)
    opts={}
    for name,fn in [("flash",backend.can_use_flash_attention),("efficient",backend.can_use_efficient_attention),("cudnn",backend.can_use_cudnn_attention)]:
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            ok=fn(args,debug=True)
        opts[name]={"eligible":bool(ok),"warnings":[str(w.message) for w in ws],"enabled":getattr(backend,name.replace("efficient","mem_efficient")+"_sdp_enabled")()}
    return opts
def profiled(call):
    # ATen operator dispatch events are exposed even without CUPTI on Windows.
    with torch.profiler.profile(activities=[torch.profiler.ProfilerActivity.CPU]) as prof:
        res=call()
        torch.cuda.synchronize()
    ev=[x.key for x in prof.key_averages() if "attention" in x.key.lower()]
    selected=next((backend for op,backend in [("_scaled_dot_product_flash_attention","flash"),("_scaled_dot_product_efficient_attention","efficient"),("_scaled_dot_product_cudnn_attention","cudnn"),("_scaled_dot_product_attention_math","math")] if any(op in event for event in ev)),None)
    return res,{"events":ev,"selected":selected}
def small():
    import platform,subprocess,importlib.metadata
    gpu=torch.cuda.get_device_name(0)
    assert torch.cuda.device_count()==1 and "3060 Ti" in gpu
    b=torch.backends.cuda
    meta=dict(python=platform.python_version(),torch=str(torch.__version__),cuda=torch.version.cuda,driver=subprocess.check_output(["nvidia-smi","--query-gpu=driver_version","--format=csv,noheader","-i",os.environ["CUDA_VISIBLE_DEVICES"]],text=True).strip(),bitsandbytes=importlib.metadata.version("bitsandbytes"),gpu=gpu,selected_uuid=os.environ["CUDA_VISIBLE_DEVICES"],capability=torch.cuda.get_device_capability(),memory_free_total=torch.cuda.mem_get_info(),native_bf16=torch.cuda.is_bf16_supported(including_emulation=False),flags={n:getattr(b,n+"_sdp_enabled")() for n in ["flash","mem_efficient","cudnn","math"]})
    write("small.jsonl",meta)
    assert meta["native_bf16"]
    q=torch.randn((1,4,64,64),device="cuda",dtype=torch.bfloat16)
    _,events=profiled(lambda:F.scaled_dot_product_attention(q,q,q))
    write("small.jsonl",dict(q=info(q),candidates=candidates(q,q,q,None,0.,False,False),**events))
def install():
    assert "3060 Ti" in torch.cuda.get_device_name() and torch.cuda.device_count()==1
    from modules.layerdiffuse.layerdiff3d import UNetFrameConditionModel
    from modules.layerdiffuse.diffusers_kdiffusion_sdxl import KDiffusionStableDiffusionXLPipeline
    from modules.marigold import MarigoldDepthPipeline
    from diffusers import AutoencoderKL
    original=F.scaled_dot_product_attention
    stage={"pipeline":"load","in_unet":False,"seen":set(),"unet_shapes":0,"intervals":[]}
    def mem(event,**extra):
        write("memory.jsonl",dict(event=event,stage=stage["pipeline"],allocated_peak=torch.cuda.max_memory_allocated(),reserved_peak=torch.cuda.max_memory_reserved(),**extra))
    def attn(query,key,value,*args,**kw):
        q,k,v=query,key,value
        if stage["pipeline"] not in ("Body","VAE_encode") or (not stage["in_unet"] and stage["pipeline"]=="Body"):return original(q,k,v,*args,**kw)
        mask=kw.get("attn_mask",args[0] if args else None)
        drop=kw.get("dropout_p",args[1] if len(args)>1 else 0.)
        causal=kw.get("is_causal",args[2] if len(args)>2 else False);gqa=kw.get("enable_gqa",False)
        row=dict(stage=stage["pipeline"],q=info(q),k=info(k),v=info(v),mask=info(mask),causal=causal,dropout=drop,gqa=gqa)
        sig=json.dumps(row)
        if sig in stage["seen"]:return original(q,k,v,*args,**kw)
        stage["seen"].add(sig)
        if stage["in_unet"]:stage["unet_shapes"]+=1
        row["math_score_fp32_bytes"]=q.numel()//q.shape[-1]*k.shape[-2]*4
        row["math_enabled"]=torch.backends.cuda.math_sdp_enabled()
        write("real.jsonl",dict(event="before",**row))
        opts=candidates(q,k,v,mask,drop,causal,gqa)
        write("real.jsonl",dict(event="eligibility",candidates=opts,**row))
        if not any(x["eligible"] and x["enabled"] for x in opts.values()):
            mem("stop_no_efficient_candidate")
            raise RuntimeError("PREFLIGHT_STOP: all memory-efficient candidates ineligible/disabled for recorded shape")
        res,ev=profiled(lambda:original(q,k,v,*args,**kw))
        write("real.jsonl",dict(event="dispatch",**ev,**row));return res
    F.scaled_dot_product_attention=attn
    forward=UNetFrameConditionModel.forward
    @functools.wraps(forward)
    def wrapped_unet(*a,**kw):
        stage["in_unet"]=True
        try: res=forward(*a,**kw)
        finally: stage["in_unet"]=False
        if MODE=="probe" and stage["pipeline"]=="Body":
            if not stage["unet_shapes"]:raise RuntimeError("PREFLIGHT_STOP: no Body SDPA observed")
            mem("probe_completed");raise SystemExit(42)
        return res
    UNetFrameConditionModel.forward=wrapped_unet
    def wrap(cls,method,tag):
        fn=getattr(cls,method)
        @functools.wraps(fn)
        def wrapped(*a,**kw):
            prev=stage["pipeline"]
            name=("Body" if kw.get("group_index",0)==0 else "Head") if tag=="LayerDiff" else tag
            mem("before_"+name)
            def capture():
                for acc in stage["intervals"]:
                    acc[0]=max(acc[0],torch.cuda.max_memory_allocated())
                    acc[1]=max(acc[1],torch.cuda.max_memory_reserved())
            capture();stage["pipeline"]=name
            acc=[0,0];stage["intervals"].append(acc);torch.cuda.reset_peak_memory_stats()
            try:return fn(*a,**kw)
            except torch.OutOfMemoryError:
                mem("oom");raise
            finally:
                capture();mem("exit_"+name,whole_stage_allocated_peak=acc[0],whole_stage_reserved_peak=acc[1])
                stage["intervals"].pop();stage["pipeline"]=prev
        setattr(cls,method,wrapped)
    wrap(KDiffusionStableDiffusionXLPipeline,"__call__","LayerDiff")
    wrap(MarigoldDepthPipeline,"__call__","Marigold")
    wrap(AutoencoderKL,"encode","VAE_encode");wrap(AutoencoderKL,"decode","VAE_decode")
    previous=sys.excepthook
    def report_error(ty,err,tb):
        try:
            mem("uncaught_exception",exception=ty.__name__,message=str(err))
        except Exception as probe_error:
            write("memory.jsonl",dict(event="memory_api_unavailable",reason=str(probe_error)))
        finally:previous(ty,err,tb)
    sys.excepthook=report_error
    mem("instrumentation_ready")
if __name__=="__main__":small()




