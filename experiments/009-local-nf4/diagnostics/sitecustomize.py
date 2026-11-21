import os,sys
from pathlib import Path
if Path(sys.argv[0]).name=="inference_psd_quantized.py" and os.environ.get("NF4_PROBE") in ("probe","measure"):
    try:
        from attention_probe import install
        install()
    except BaseException:
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(86)
