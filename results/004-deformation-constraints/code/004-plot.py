"""Optional static evidence plots; requires matplotlib, no network or service."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out = Path('results/004-deformation-constraints')
m = json.loads((out / 'metrics.json').read_text())
fig, axes = plt.subplots(4, 2, figsize=(13, 12), sharex=True)
for col, name in enumerate(['hair', 'skirt']):
    for method, color in [('baseline', '#627285'), ('candidate', '#b94719')]:
        part = next(p for p in m[method]['parts'] if p['id'] == name)
        rows = [r for r in part['timeSeries'] if r['t'] <= 8]
        t = [r['t'] for r in rows]
        label = '003' if method == 'baseline' else '004'
        axes[0, col].plot(t, [r['minEdgeRatio'] for r in rows], color=color, label=label+' min')
        axes[0, col].plot(t, [r['maxEdgeRatio'] for r in rows], color=color, linestyle='--', label=label+' max')
        axes[1, col].plot(t, [r['centerlineRatio'] for r in rows], color=color, label=label)
        axes[2, col].plot(t, [r['tipX'] for r in rows], color=color, label=label)
        v = [(rows[i+1]['tipX']-rows[i]['tipX'])*60 for i in range(len(rows)-1)]
        axes[3, col].plot(t[:-1], v, color=color, label=label)
    axes[0, col].set_title(name + ' | identical input, fixed camera')
    axes[0, col].axhline(.9, color='green', linewidth=.8)
    axes[0, col].axhline(1.1, color='green', linewidth=.8)
    if name == 'hair':
        axes[1, col].axhline(.97, color='green', linewidth=.8)
        axes[1, col].axhline(1.03, color='green', linewidth=.8)
    for row, ylabel in enumerate(['all-edge min/max ratio', 'centerline length ratio', 'tip local x (px)', 'tip horizontal velocity (px/s)']):
        axes[row, col].set_ylabel(ylabel)
        axes[row, col].legend(fontsize=8)
        axes[row, col].grid(alpha=.2)
    axes[3, col].set_xlabel('time (s)')
fig.suptitle('004 deformation constraints: full 60Hz samples, no average-only masking')
fig.tight_layout()
fig.savefig(out / 'timeseries.png', dpi=140)
fig.savefig(out / 'timeseries.svg')

# Normalize generated SVG whitespace for repository checks.
p = out / "timeseries.svg"
p.write_text("\n".join(line.rstrip() for line in p.read_text().splitlines()) + "\n")
