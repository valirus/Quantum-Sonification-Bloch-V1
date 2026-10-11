from pathlib import Path
import argparse
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
p=argparse.ArgumentParser();p.add_argument('--output-dir',default='regenerated_figures');a=p.parse_args()
O=Path(__file__).resolve().parents[1];A=O/'data';OUT=O/a.output_dir
if OUT.exists():raise FileExistsError('Choose a new figure output directory.')
OUT.mkdir(parents=True)
D=pd.read_csv(A/'validation_3000_3099.csv');dev=pd.read_csv(A/'development_1000_1099.csv');curves=pd.read_csv(A/'RQ2.csv');pred=pd.read_csv(A/'validation_predictions.csv');controls=pd.read_csv(A/'control_mechanisms.csv');dist=pd.read_csv(A/'distance_by_layer.csv')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'savefig.bbox':'tight'})
blue='#126E82';orange='#C24C25';gray='#5E6268'
for lang in ['en','es']:
 es=lang=='es'
 def save(fig,name):
  fig.savefig(OUT/f'{name}_{lang}.pdf');fig.savefig(OUT/f'{name}_{lang}.png',dpi=170);plt.close(fig)
 # Algorithmic pipeline; not an interface screenshot.
 fig,ax=plt.subplots(figsize=(7,3.5));ax.set_xlim(0,10);ax.set_ylim(0,6);ax.axis('off')
 boxes=[(3.1,4.85,3.8,.85,'Estado puro por capa\n15 qubits; 100 + 100 semillas' if es else 'Pure state per layer\n15 qubits; 100 + 100 seeds'),(.3,3.0,4.2,1.05,'Reducciones de un qubit\nBloch: frecuencia, amplitud, AM, paneo' if es else 'Single-qubit reductions\nBloch: pitch, amplitude, AM, pan'),(5.2,3,4.4,1.05,'Reducciones de dos qubits\nMI total → bosque de expansión máxima' if es else 'Two-qubit reductions\nTotal MI → maximum spanning forest'),(1.15,1.2,3.1,.85,'BFS: fronteras simultáneas\nPromedio de voces; ataque 20 %' if es else 'BFS: simultaneous frontiers\nVoice averaging; 20 % attack'),(5.5,1.2,3.4,.85,'DFS: voces secuenciales\nPesos por evento; ataque 5 %' if es else 'DFS: sequential voices\nEvent weights; 5 % attack')]
 for x,y,w,h,label in boxes:
  ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.12',facecolor='#F1F5F6',edgecolor=blue,linewidth=1));ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=9)
 for start,end in [((4.2,4.75),(2.4,4.15)),((5.8,4.75),(7.4,4.15)),((2.4,2.9),(2.7,2.15)),((3.8,2.9),(6.7,2.15)),((6.1,2.9),(3.6,2.15)),((7.5,2.9),(7.3,2.15))]:
  ax.add_patch(FancyArrowPatch(start,end,arrowstyle='->',mutation_scale=12,color=gray,linewidth=1.1))
 ax.text(5,.35,'Audio estéreo → descriptores acústicos; evaluación por semilla' if es else 'Stereo audio → acoustic descriptors; evaluation by seed',ha='center',fontsize=9)
 save(fig,'Fig1')
 # Depth trajectories fresh cohort only; pointwise intervals.
 fig,axs=plt.subplots(1,3,figsize=(7,2.8),layout='constrained')
 for ax,mode,feat,label in [(axs[0],'quantum','central_cut_entanglement_entropy_bits','Entropía del corte (bits)' if es else 'Cut entropy (bits)'),(axs[1],'quantum','mean_bloch_radius','Radio medio de Bloch' if es else 'Mean Bloch radius')]:
  t=curves[(curves['mode']==mode)&(curves.feature==feat)].sort_values('layer');ax.plot(t.layer,t['mean'],color=blue,marker='o',ms=3);ax.fill_between(t.layer,t.ci_low,t.ci_high,color=blue,alpha=.16);ax.set_ylabel(label)
 page=(sum(1/k for k in range(257,32769))-127/512)/np.log(2);axs[0].axhline(page,color=gray,ls='--',lw=1,label='Media de Haar' if es else 'Haar mean');axs[0].axhline(7,color=gray,ls=':',lw=1,label='Máximo' if es else 'Maximum');axs[0].legend(loc='lower right');axs[0].set_ylim(-.15,7.3)
 for mode,color,mark in [('bfs',blue,'o'),('dfs',orange,'s')]:
  t=curves[(curves['mode']==mode)&(curves.feature=='spectral_entropy_mean')].sort_values('layer');axs[2].plot(t.layer,t['mean'],color=color,marker=mark,ms=3,label=mode.upper());axs[2].fill_between(t.layer,t.ci_low,t.ci_high,color=color,alpha=.12)
 axs[2].set_ylabel('Entropía espectral (bits)' if es else 'Spectral entropy (bits)');axs[2].legend()
 for i,ax in enumerate(axs):ax.set_xlabel('Capa' if es else 'Layer');ax.set_xticks([0,2,4,6,8,10]);ax.text(-.12,1.03,f'({chr(97+i)})',transform=ax.transAxes,weight='bold')
 save(fig,'Fig2')
 # Primary prediction distributions, no optimistically high global R2 emphasis.
 p=pred[(pred['mode']=='dfs')&(pred.target=='duration_sec')].copy();p['gain']=(p.observed-p.M1)**2-(p.observed-p.M2)**2;v=p.groupby('seed').gain.mean();mses=[np.mean((p.observed-p[m])**2)for m in ['M0','M1','M2']]
 fig,axs=plt.subplots(1,2,figsize=(7,2.8),layout='constrained');axs[0].bar(['M0','M1','M2'],np.sqrt(mses)*1000,color=[gray,blue,orange]);axs[0].set_ylabel('RMSE de duración (ms)' if es else 'Duration RMSE (ms)');axs[0].set_ylim(0,61)
 for j,x in enumerate(np.sqrt(mses)*1000):axs[0].text(j,x+1,f'{x:.2f}',ha='center',fontsize=9)
 axs[1].hist(v.to_numpy()*1000,bins=16,color=blue,alpha=.8);axs[1].axvline(0,color=gray,ls='--');axs[1].set_xlabel('Ganancia MSE por semilla (10⁻³ s²)' if es else 'Per-seed MSE gain (10⁻³ s²)');axs[1].set_ylabel('Semillas' if es else 'Seeds')
 for i,ax in enumerate(axs):ax.text(-.1,1.03,f'({chr(97+i)})',transform=ax.transAxes,weight='bold')
 save(fig,'Fig3')
 # Controls distinct units.
 fig,axs=plt.subplots(1,2,figsize=(7,2.6),layout='constrained')
 for ax,feat,label in [(axs[0],'duration_sec','Cambio de duración BFS (s)' if es else 'BFS duration change (s)'),(axs[1],'bfs_frontier_count','Cambio de número de fronteras' if es else 'Change in frontier count')]:
  for j,(condition,color)in enumerate([('tree_shuffle',blue),('weight_shuffle',orange)]):
   v=controls[(controls.feature==feat)&(controls['mode']=='bfs')&(controls.condition==condition)].iloc[0];ax.errorbar(v.mean_control_minus_original,j,xerr=[[v.mean_control_minus_original-v.ci_low],[v.ci_high-v.mean_control_minus_original]],fmt='o',color=color,capsize=4)
  ax.axvline(0,ls='--',color=gray,lw=1);ax.set_yticks([0,1],['Árbol + pesos' if es else 'Tree + weights','Sólo pesos' if es else 'Weights only']);ax.set_xlabel(label);ax.set_ylim(-.6,1.6)
 for i,ax in enumerate(axs):ax.text(-.12,1.03,f'({chr(97+i)})',transform=ax.transAxes,weight='bold')
 save(fig,'Fig4')
 # Per-layer correlations, secondary; no spurious CI.
 fig,axs=plt.subplots(1,2,figsize=(7,2.7),layout='constrained')
 for ax,target in zip(axs,['Bloch','MI']):
  for mode,color,marker in [('bfs',blue,'o'),('dfs',orange,'s')]:
   t=dist[(dist['mode']==mode)&(dist.target==target)];ax.plot(t.layer,t.spearman_distance_rho,color=color,marker=marker,ms=3,label=mode.upper())
  ax.axhline(0,color=gray,ls='--',lw=1);ax.set_xlabel('Capa' if es else 'Layer');ax.set_ylabel(('ρ de distancias '+target) if es else (target+' distance ρ'));ax.set_ylim(-.15,.65);ax.set_xticks([2,4,6,8,10]);ax.legend()
 for i,ax in enumerate(axs):ax.text(-.12,1.03,f'({chr(97+i)})',transform=ax.transAxes,weight='bold')
 save(fig,'Fig5')
 # Limit family, analytic entropy and coordinate discontinuity.
 fig,axs=plt.subplots(1,2,figsize=(7,2.65),layout='constrained');t=np.linspace(0,1,501);pr=np.sin(np.pi*t/4)**2;h=np.zeros_like(t);ok=(pr>0)&(pr<1);h[ok]=-pr[ok]*np.log2(pr[ok])-(1-pr[ok])*np.log2(1-pr[ok]);axs[0].plot(t,7*h,color=blue,label='S(A)');axs[0].plot(t,np.zeros_like(t),color=orange,ls='--',label='MI por pares' if es else 'Pairwise MI');axs[0].set_xlabel('Parámetro t' if es else 'Parameter t');axs[0].set_ylabel('Bits');axs[0].legend()
 ep=np.logspace(-8,-1,100);axs[1].loglog(ep,np.sin(ep),color=blue,label='Distancia del estado' if es else 'State trace distance');axs[1].loglog(ep,np.sqrt(1-np.sin(ep/2)),ls='--',color=orange,label='Distancia del audio' if es else 'Normalized audio distance');axs[1].set_xlabel('Separación azimutal ±ε (rad)' if es else 'Azimuthal offsets ±ε (rad)');axs[1].set_ylabel('Distancia' if es else 'Distance');axs[1].legend(loc='center right')
 for i,ax in enumerate(axs):ax.text(-.12,1.03,f'({chr(97+i)})',transform=ax.transAxes,weight='bold')
 save(fig,'Fig6')
print('12 bilingual vector figures regenerated from the supplied validation tables.')
