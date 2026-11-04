"""Presentation-only margin revision from the saved paired analysis."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=Path(__file__).parent
records=json.loads((p/'analysis.json').read_text())['n20_final']
order=['fixed','rules','scheduled','depth2_pattern','proxy_feedback','uniform_conditioned','allocation_swap']
values=[next(r['mean_vs_uniform_pct'] for r in records if r['method']==m) for m in order]
fig,ax=plt.subplots(figsize=(11,4.8),layout='constrained')
bars=ax.bar(order,values,color=['#527c9d','#58a192','#277b62','#94709b','#c69c42','#87929f','#b15c4c'])
ax.bar_label(bars,fmt='%.2f%%',padding=4,fontsize=10)
ax.axhline(0,color='#26384d',lw=1)
ax.tick_params(axis='x',rotation=20)
ax.set(ylim=(-12.5,6),ylabel='Mean paired allocated-objective difference (%)\nnegative is better',title='N20 / 88 observations: comparison with conditioned uniform')
fig.savefig(p/'conditioned-comparison-readable.png',dpi=160)
