"""Index the evidence with portable relative paths and cryptographic hashes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path('results/007-character-application')
BASE = '13dc02a48f9ace0e2c657dbb751fd7ae865a9138'
manifest = {
    'experiment': '007-character-application',
    'recordedUtc': datetime.now(timezone.utc).isoformat(),
    'repository': 'keepholdingon1224-source/StandRig',
    'branch': 'experiment/rigging-validation-20261115',
    'baselineCommit': BASE,
    'output': {'size':[1152,2048], 'fps':30, 'periodSeconds':8, 'framesPerPeriod':240},
    'status': 'assisted numeric and GUI checks passed; complete automation failed; visual approval pending',
    'source': json.loads((OUT/'source/input.json').read_text()),
    'protectedBaselineTrackedFiles':len((OUT/'source/007-baseline.sha256').read_text().splitlines()),
    'commands': ['npm ci','npm run build','npm test','python experiments/007-references.py',
                 'python experiments/007-segment.py','python experiments/007-rig.py','node experiments/007-bake.mjs',
                 'node experiments/007-gui.mjs','python experiments/007-verify.py'],
    'executionDirectoryRecordedByGit':subprocess.check_output(['git','rev-parse','--show-prefix'],text=True).strip() or '.',
    'sha256': {
        p.relative_to(OUT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(OUT.rglob('*')) if p.is_file() and p != OUT/'manifest.json'
    }
}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
