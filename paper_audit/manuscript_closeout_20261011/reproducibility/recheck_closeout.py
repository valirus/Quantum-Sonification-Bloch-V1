from pathlib import Path
import json,hashlib,sys
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist,squareform
from scipy.stats import rankdata,false_discovery_control
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reproduction_results/closeout';R.mkdir(parents=True,exist_ok=True);E=ROOT/'reproducibility/reproduction_inputs';C=E/'outputs/paper_audit/closeout_3000_3099'
receipt=json.loads((C/'closeout_receipt.json').read_text()); bad=[]
for name,digest in receipt['file_sha256'].items():
 if hashlib.sha256((E/name).read_bytes()).hexdigest()!=digest:bad.append(name)
assert not bad,bad
src=E/'src'
expected={'simulations.py': '92fac14aa95d286fb305198675881d8209a76c2074cd00bae582a8410c517361', 'sonification.py': '23e747dfe61ff50cc149f7395588fca86488e77f3a18e11fdfa8f87590630ad5', 'gates.py': '12246113afa6f5df414f99643061c5d274c3a44108829cf8c1e5c888f14fa903', 'circuit.py': 'c74bbb63917e56ac6bd09dcea42301bfd6673ae55fdda592d203c5254580eeb5', 'rqc_sonification.py': '67d5ca44bf86e69d7da477059a4fbf91a863075a0fb10991fa0dc02b0fa82ba1'}
assert all(hashlib.sha256((src/name).read_bytes()).hexdigest()==h for name,h in expected.items())
D=pd.read_csv(E/'outputs/paper_audit/validation_3000_3099_tables/analysis_dataset.csv')
T=pd.read_csv(E/'paper_audit/next_steps_kit/input_current_100/analysis_dataset.csv')
B=pd.read_csv(E/'outputs/paper_audit/validation_3000_3099_tables/bloch_descriptors.csv')
assert D.shape==(2200,42) and len(B)==16500 and not D.duplicated(['seed','layer','mode']).any()
assert set(D.seed)==set(range(3000,3100)) and not (set(D.seed)&set(T.seed))
# Full RQ1--4 independently recomputed by recheck_secondary.py.
errors={'separate_script':'recheck_secondary.py'}
# Control summary independently calculated from features, not recorded difference columns.
f=pd.read_csv(C/'topology/control_features.csv');d=pd.read_csv(C/'topology/control_differences.csv')
assert len(f)==32800 and len(d)==32000
base=f[f.condition=='original'].set_index(['seed','layer','mode']);cf=f[f.condition!='original'].copy()
keys=pd.MultiIndex.from_frame(cf[['seed','layer','mode']]);boot=np.random.default_rng(20261004).integers(0,100,(5000,100));summary=[]
features=['duration_sec','rms_joint','spectral_centroid_mean_hz','spectral_bandwidth_mean_hz','spectral_entropy_mean','spectral_flux_mean','stereo_correlation','bfs_frontier_count','bfs_max_frontier_width']
for feat in features:
 cf['delta']=cf[feat].to_numpy()-base.loc[keys,feat].to_numpy()
 for (cond,mode),g in cf.groupby(['condition','mode']):
  vals=g.groupby(['seed','layer']).delta.mean().groupby('seed').mean().sort_index().to_numpy()
  ci=np.quantile(vals[boot].mean(axis=1),[.025,.975]);summary.append([cond,mode,feat,float(vals.mean()),*ci])
s=pd.DataFrame(summary,columns=['condition','mode','feature','mean_control_minus_original','ci_low','ci_high']);s.to_csv(R/'controls_independent.csv',index=False)
stored=pd.read_csv(C/'topology/control_seed_summary.csv');joined=stored.merge(s,on=['condition','mode','feature'],suffixes=('_stored','_independent'),validate='one_to_one');control_error=max(np.max(abs(joined[f'{x}_stored']-joined[f'{x}_independent'])) for x in ['mean_control_minus_original','ci_low','ci_high']);assert control_error<1e-11
assert (d.loc[d['mode']=='dfs','difference_duration_sec']==0).all()
changed=pd.read_csv(C/'topology/fraction_topology_changed.csv');assert len(changed)==400 and (changed.topology_changed==1).all()
for invariant in ['backbone_components','backbone_edges','forest_weight_sum']:
 assert np.max(abs(cf[invariant].to_numpy()-base.loc[keys,invariant].to_numpy()))<1e-12
# Validate MI summaries directly and independently construct forests for exact sample-count duration.
mi_errors=[];duration_errors=[];symmetry=0
for seed in range(3000,3100):
 for layer in range(11):
  m=np.load(E/f'outputs/validation_3000_3099/seed_{seed:06d}/mutual_information_matrices/mi_layer_{layer:02d}.npy',allow_pickle=False)
  assert m.shape==(15,15) and np.isfinite(m).all() and m.min()>=-1e-9 and m.max()<=2+1e-9
  symmetry=max(symmetry,float(np.max(abs(m-m.T))));u=m[np.triu_indices(15,1)];w=u[u>1e-10];row=D[(D.seed==seed)&(D.layer==layer)&(D['mode']=='dfs')].iloc[0]
  mi_errors.append(abs(w.sum()-row.total_mutual_information))
  parent=list(range(15))
  def find(i):
   while parent[i]!=i:i=parent[i]
   return i
  forest=[]
  for wt,i,j in sorted([(m[i,j],i,j) for i in range(15) for j in range(i+1,15) if m[i,j]>1e-10],reverse=True):
   a,b=find(i),find(j)
   if a!=b:parent[a]=b;forest.append(float(wt))
  c=15-len(forest);count=c*round(.3*22050)+(c-1)*round(.12*22050)+sum(round((.6-.25*v)*22050)for v in forest)
  duration_errors.append(abs(count/22050-row.duration_sec))
assert max(mi_errors)<1e-10 and max(duration_errors)<1e-10
# Distances: rank centered independent vectors and seed relabeling, training-only scaling.
F=['duration_sec','rms_joint','spectral_centroid_mean_hz','spectral_bandwidth_mean_hz','spectral_entropy_mean','spectral_flux_mean','stereo_balance','stereo_correlation'];upper=np.triu_indices(100,1)
rng=np.random.default_rng(20261005);perm=np.array([rng.permutation(100)for _ in range(5000)])
quantum={}
for layer in range(11):
 xyz=B[B.layer==layer].sort_values(['seed','qubit'])[['x','y','z']].to_numpy().reshape(100,15,3)
 dist=np.mean(np.sqrt(np.sum((xyz[:,None,:,:]-xyz[None,:,:,:])**2,axis=-1)),axis=-1)
 mats=np.array([np.load(E/f'outputs/validation_3000_3099/seed_{seed:06d}/mutual_information_matrices/mi_layer_{layer:02d}.npy')[np.triu_indices(15,1)]for seed in range(3000,3100)])
 quantum[('Bloch',layer)]=dist;quantum[('MI',layer)]=squareform(pdist(mats))
res=[];bylayer=[]
for mode in ['bfs','dfs']:
 train=T[T['mode']==mode][F].to_numpy();mu=train.mean(0);sd=train.std(0);sd[sd<=1e-12]=1
 for target in ['Bloch','MI']:
  obs=[];null=np.zeros(5000);used=[]
  for layer in range(11):
   a=squareform(pdist((D[(D['mode']==mode)&(D.layer==layer)].sort_values('seed')[F].to_numpy()-mu)/sd));q=quantum[(target,layer)]
   if np.ptp(q[upper])<1e-10 or np.ptp(a[upper])<1e-10:continue
   qr=rankdata(q[upper]);qr=(qr-qr.mean())/np.linalg.norm(qr-qr.mean());ar=rankdata(a[upper]);ar=(ar-ar.mean())/np.linalg.norm(ar-ar.mean());ar_full=np.zeros((100,100));ar_full[upper]=ar;ar_full[(upper[1],upper[0])]=ar
   rho=float(qr@ar);obs.append(rho);used.append(layer);bylayer.append([mode,target,layer,rho])
   for k in range(0,5000,100):
    pp=perm[k:k+100];null[k:k+100]+=np.sum(ar_full[pp[:,upper[0]],pp[:,upper[1]]]*qr,axis=1)
  statistic=float(np.mean(obs));null/=len(used);p=(1+np.count_nonzero(abs(null)>=abs(statistic)-1e-12))/5001
  res.append([mode,target,statistic,p])
a=pd.DataFrame(res,columns=['mode','target','mean_layer_distance_rho','two_sided_seed_permutation_p']);a['BH_q_family']=false_discovery_control(a.two_sided_seed_permutation_p);a['BY_q_sensitivity']=false_discovery_control(a.two_sided_seed_permutation_p,method='by');a.to_csv(R/'distances_independent.csv',index=False)
st=pd.read_csv(C/'distances/distance_tests.csv');dist_error=float(np.max(abs(a.iloc[:,2:].to_numpy()-st[a.columns[2:]].to_numpy())));assert dist_error<1e-11
out=dict(status='PASS',file_hashes_verified=len(receipt['file_sha256']),all_src_match_frozen_reference_hashes=True,RQ1_RQ4_max_errors=errors,control_max_error=control_error,control_renders=len(f),control_comparisons=len(d),DFS_duration_control_max_difference_sec=0,all_tree_states_changed=True,MI_summary_max_error=float(max(mi_errors)),MI_max_asymmetry=symmetry,exact_DFS_duration_max_error_sec=float(max(duration_errors)),distance_summary_max_error=dist_error,notes=['Source equality and hashes are byte checks, not a remote git history verification.','Original 3000 WAV/statevector files were not supplied; generation validation is recorded, not independently replayed here.','Distance and control bootstrap calculations recomputed independently from supplied inputs.'])
(R/'audit_receipt.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));print(a.to_string(index=False));print(s[s.feature=='bfs_frontier_count'].to_string(index=False))
