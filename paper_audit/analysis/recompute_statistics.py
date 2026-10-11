"""Independent audit of archived CSV. Does not import the supplied analysis kit."""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
from scipy import stats, linalg, optimize
import openpyxl
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--output-dir',required=True)
args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(args.output_dir)
if OUT.exists() and any(OUT.iterdir()):raise FileExistsError('Choose a new output directory')
OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'input_archive'
d=pd.read_csv(BASE/'01_dataset/analysis_dataset.csv')
q=pd.read_csv(BASE/'03_raw_context/layer_metrics.csv')
a=pd.read_csv(BASE/'03_raw_context/audio_features.csv')
b=pd.read_csv(BASE/'03_raw_context/bloch_descriptors.csv')
g=pd.read_csv(BASE/'03_raw_context/gate_manifest.csv')
seeds=np.sort(d.seed.unique());layers=np.sort(d.layer.unique())
qc={'dataset_shape':list(d.shape),'seeds':seeds.tolist(),'missing':int(d.isna().sum().sum()),'duplicate_keys':int(d.duplicated(['seed','layer','mode']).sum())}
merged=a.merge(q,on=['seed','layer'],validate='many_to_one')
qc['merge_max_absolute_error']=float(np.max(np.abs(merged[d.select_dtypes('number').columns].to_numpy()-d[d.select_dtypes('number').columns].to_numpy())))
qc['merge_strings_identical']=bool((merged[d.select_dtypes(exclude='number').columns].to_numpy()==d[d.select_dtypes(exclude='number').columns].to_numpy()).all())
qc['r_cartesian_max_error']=float(np.max(np.abs(np.sqrt(b.x**2+b.y**2+b.z**2)-b.r)))
qc['normalized_linear_entropy_max_error']=float(np.max(np.abs(1-b.r**2-b.linear_entropy)))
qc['rms_joint_identity_max_error']=float(np.max(np.abs(np.sqrt((a.rms_left**2+a.rms_right**2)/2)-a.rms_joint)))
qc['stereo_balance_identity_max_error']=float(np.max(np.abs((a.rms_right-a.rms_left)/(a.rms_right+a.rms_left)-a.stereo_balance)))
qc['initial_state_n_unique_descriptors']=int(q[q.layer==0].drop(columns='seed').drop_duplicates().shape[0])
qc['unique_full_gate_histories']=int(g.groupby('seed').apply(lambda s:hashlib.sha256(s.to_csv(index=False).encode()).hexdigest(),include_groups=False).nunique())
qc['peak_amplitude_max']=float(a.peak_absolute_amplitude.max())
# Workbook checks: compare archived numeric tables, not fit their formulas.
xlsx=[]
wb=openpyxl.load_workbook(ROOT/'input_f1/Analisis Estadístico Sonificación.xlsx',data_only=True,read_only=True)
rows=list(wb['analysis_dataset'].values)[2:]
vals=np.asarray([[r[j] for j in range(42)] for r in rows if isinstance(r[0],(float,int))],dtype=object)
for j,col in enumerate(d.columns):
 if pd.api.types.is_numeric_dtype(d[col]):
  err=float(np.max(np.abs(vals[:,j].astype(float)-d[col].to_numpy())))
  xlsx.append({'workbook':'Analisis Estadístico Sonificación.xlsx','sheet':'analysis_dataset','column':col,'N':len(vals),'max_abs_error':err})
for fname,col in [('RQ4_Anchodebandaespectral.xlsx','spectral_bandwidth_mean_hz'),('RQ4_Entropia.xlsx','spectral_entropy_mean'),('RQ4_Flujoespectral.xlsx','spectral_flux_mean')]:
 w=openpyxl.load_workbook(ROOT/'input_f2'/fname,data_only=True,read_only=True)
 rr=[r for r in list(w.worksheets[0].values)[4:] if isinstance(r[0],(float,int))]
 for j,mode in enumerate(['bfs','dfs']):
  expect=d[d['mode']==mode].sort_values(['seed','layer'])[col].to_numpy()
  v=np.array([r[j] for r in rr if isinstance(r[j],(float,int))])
  xlsx.append({'workbook':fname,'sheet':w.worksheets[0].title,'column':mode,'N':len(v),'max_abs_error':float(np.max(np.abs(v-expect)))})
pd.DataFrame(xlsx).to_csv(OUT/'workbook_numeric_verification.csv',index=False)
qc['workbook_max_error']=float(max(z['max_abs_error'] for z in xlsx))
(OUT/'data_integrity.json').write_text(json.dumps(qc,indent=2))
# Conventional pooled regression reproductions, descriptive only.
pooled=[]
for scope,sub in [('all',d),('exclude_0',d[d.layer>0]),('late_4_10',d[d.layer>=4])]:
 for x,y in [('mean_bloch_radius','rms_joint'),('mean_theta_radius_weighted','spectral_centroid_mean_hz')]:
  fit=stats.linregress(sub[x],sub[y]);pooled.append({'scope':scope,'x':x,'y':y,'N_rows':len(sub),'intercept':fit.intercept,'slope':fit.slope,'R2':fit.rvalue**2})
pd.DataFrame(pooled).to_csv(OUT/'pooled_regressions_descriptive.csv',index=False)
# Independent within-depth residual correlations, whole-seed exchangeability.
rng=np.random.default_rng(20261004)
perms=np.array([rng.permutation(100) for _ in range(5000)])
boots=rng.integers(0,100,size=(5000,100))
def center(v):
 out=v-v.mean(axis=0)
 out[:,np.std(v,axis=0)<1e-12]=0
 return out
def r(v,w):return float(np.dot(v.ravel(),w.ravel())/np.sqrt(np.dot(v.ravel(),v.ravel())*np.dot(w.ravel(),w.ravel())))
rq1=[];rq1layers=[]
for mode in ['bfs','dfs']:
 sub=d[d['mode']==mode]
 for x,y in [('mean_bloch_radius','rms_joint'),('mean_theta_radius_weighted','spectral_centroid_mean_hz')]:
  X=sub.pivot(index='seed',columns='layer',values=x).to_numpy();Y=sub.pivot(index='seed',columns='layer',values=y).to_numpy()
  Xc,Yc=center(X),center(Y);obs=r(Xc,Yc);den=np.sqrt(np.sum(Xc**2)*np.sum(Yc**2))
  # elementwise trajectory pairs, equivalent statistic but independently assembled
  null=np.sum(Xc[None,:,:]*Yc[perms],axis=(1,2))/den
  pp=(1+np.count_nonzero(np.abs(null)>=abs(obs)))/5001
  bootvals=np.array([r(center(X[ix]),center(Y[ix])) for ix in boots]);lo,hi=np.quantile(bootvals,[.025,.975])
  rq1.append({'mode':mode,'x':x,'y':y,'r_depth_adjusted':obs,'ci_lo':lo,'ci_hi':hi,'p_seed_permutation':pp,'r_late_4_10_centered':r(Xc[:,4:],Yc[:,4:])})
  for j,layer in enumerate(layers):
   rq1layers.append({'mode':mode,'x':x,'y':y,'layer':int(layer),'r':stats.pearsonr(X[:,j],Y[:,j]).statistic if np.std(X[:,j])>1e-12 and np.std(Y[:,j])>1e-12 else np.nan,'X_within_variance_share':float(np.sum(Xc[:,j]**2)/np.sum(Xc**2)),'Y_within_variance_share':float(np.sum(Yc[:,j]**2)/np.sum(Yc**2)),'cross_product_share':float(np.sum(Xc[:,j]*Yc[:,j])/np.sum(Xc*Yc))})
rq1=pd.DataFrame(rq1);rq1['q_4']=stats.false_discovery_control(rq1.p_seed_permutation);rq1.to_csv(OUT/'RQ1_independent.csv',index=False)
pd.DataFrame(rq1layers).to_csv(OUT/'RQ1_layer_sensitivity.csv',index=False)
# Quantum curves once per state. entropy-vs-spectrum after depth control.
q.groupby('layer').agg({c:['mean','std','min','max'] for c in ['mean_bloch_radius','central_cut_entanglement_entropy_bits','total_mutual_information','positive_edge_density']}).to_csv(OUT/'quantum_trajectories.csv')
signatures=[]
for mode in ['bfs','dfs']:
 sub=d[d['mode']==mode];xc=sub.central_cut_entanglement_entropy_bits-sub.groupby('layer').central_cut_entanglement_entropy_bits.transform('mean');yc=sub.spectral_entropy_mean-sub.groupby('layer').spectral_entropy_mean.transform('mean')
 signatures.append({'mode':mode,'raw_r':stats.pearsonr(sub.central_cut_entanglement_entropy_bits,sub.spectral_entropy_mean).statistic,'depth_centered_r':stats.pearsonr(xc,yc).statistic})
pd.DataFrame(signatures).to_csv(OUT/'entanglement_signature_depth_confound.csv',index=False)
# RQ3 exact Spearman and independent Monte Carlo seed-label permutations.
srng=np.random.default_rng(20261004)
sp=np.array([srng.permutation(100) for _ in range(100000)])
rq3=[]
for mode in ['bfs','dfs']:
 for layer in range(1,11):
  sub=d[(d['mode']==mode)&(d.layer==layer)].sort_values('seed')
  X=stats.rankdata(sub.phi_circular_variance_radius_weighted);Y=stats.rankdata(sub.stereo_correlation);X-=X.mean();Y-=Y.mean();obs=r(X,Y)
  den=np.sqrt(np.sum(X**2)*np.sum(Y**2));nn=Y[sp]@X/den
  pp=(1+np.count_nonzero(np.abs(nn)>=abs(obs)-1e-12))/100001
  rq3.append({'mode':mode,'layer':layer,'rho':obs,'p_100k_seed_permutation':pp})
rq3=pd.DataFrame(rq3);rq3['q_20']=stats.false_discovery_control(rq3.p_100k_seed_permutation);rq3.to_csv(OUT/'RQ3_independent.csv',index=False)
# RQ4 paired per-seed means and sensitivities, plus absolute statewise changes.
acoustics=['duration_sec','rms_joint','spectral_centroid_mean_hz','spectral_bandwidth_mean_hz','spectral_entropy_mean','spectral_flux_mean']
rq4=[];sens=[]
b4=np.random.default_rng(20261003).integers(0,100,size=(10000,100))
for feature in acoustics:
 piv=d.pivot(index=['seed','layer'],columns='mode',values=feature);delta=piv.bfs-piv.dfs
 ds=delta.groupby('seed').mean().to_numpy();tt=stats.ttest_1samp(ds,0);lo,hi=np.quantile(ds[b4].mean(axis=1),[.025,.975])
 rq4.append({'feature':feature,'bfs_mean':piv.bfs.mean(),'dfs_mean':piv.dfs.mean(),'mean_BFS_minus_DFS':ds.mean(),'ci_lo':lo,'ci_hi':hi,'paired_t_99_df':tt.statistic,'p':tt.pvalue,'mean_abs_state_difference':np.abs(delta).mean()})
 for scope,minlayer in [('all',0),('exclude_0',1),('late_4_10',4)]:
  dl=delta[delta.index.get_level_values('layer')>=minlayer].groupby('seed').mean().to_numpy();lo,hi=np.quantile(dl[b4].mean(axis=1),[.025,.975]);tt=stats.ttest_1samp(dl,0)
  sens.append({'scope':scope,'feature':feature,'mean_diff':dl.mean(),'ci_lo':lo,'ci_hi':hi,'p':tt.pvalue})
rq4=pd.DataFrame(rq4);rq4['q_6']=stats.false_discovery_control(rq4.p);rq4.to_csv(OUT/'RQ4_independent.csv',index=False)
pd.DataFrame(sens).to_csv(OUT/'RQ4_scope_sensitivity.csv',index=False)
# RQ5 grouped CV written independently: scipy.linalg least squares with categorical layers.
local=['mean_bloch_radius','mean_linear_entropy','mean_theta_radius_weighted','phi_circular_variance_radius_weighted']
d['log1p_MI']=np.log1p(d.total_mutual_information)
rel=['log1p_MI','edge_weight_entropy']
cv=[];foldrecords=[]
for scope,minlayer in [('all_layers',0),('exclude_layer_0',1),('layers_4_and_later',4)]:
 scoped=d[d.layer>=minlayer]
 for rep in range(10):
  groups=np.array_split(np.random.default_rng(20261004+rep).permutation(seeds),5)
  for mode in ['bfs','dfs']:
   sub=scoped[scoped['mode']==mode].sort_values(['seed','layer']).reset_index(drop=True)
   depth=pd.get_dummies(sub.layer,dtype=float).to_numpy() # full one-hot, no extra intercept
   for target in ['duration_sec','spectral_flux_mean']:
    yy=sub[target].to_numpy();preds={m:np.zeros(len(sub)) for m in ['M0','M1','M2']}
    for fold,testseed in enumerate(groups):
     test=np.isin(sub.seed,testseed);train=~test
     for model,cols in [('M0',[]),('M1',local),('M2',local+rel)]:
      xx=depth
      if cols:
       z=sub[cols].to_numpy();mean=z[train].mean(axis=0);sd=z[train].std(axis=0);sd[sd<1e-12]=1;xx=np.column_stack([depth,(z-mean)/sd])
      coef=linalg.lstsq(xx[train],yy[train],lapack_driver='gelsd')[0];preds[model][test]=xx[test]@coef
      if scope=='all_layers' and rep==0:foldrecords.append({'mode':mode,'target':target,'fold':fold,'model':model,'MSE':np.mean((yy[test]-preds[model][test])**2)})
    ms={m:np.mean((yy-v)**2) for m,v in preds.items()};var=np.var(yy)
    cv.append({'scope':scope,'repeat':rep,'mode':mode,'target':target,**{m+'_MSE':v for m,v in ms.items()},**{m+'_R2':1-v/var for m,v in ms.items()},'M2_vs_M1_MSE_reduction_pct':100*(ms['M1']-ms['M2'])/ms['M1']})
cv=pd.DataFrame(cv);cv.to_csv(OUT/'RQ5_independent_group_cv.csv',index=False);cv.groupby(['scope','mode','target']).M2_vs_M1_MSE_reduction_pct.agg(['min','median','max']).to_csv(OUT/'RQ5_split_sensitivity_summary.csv');pd.DataFrame(foldrecords).to_csv(OUT/'RQ5_fold_metrics.csv',index=False)
# Quantify digital squared amplitude; not physical energy.
energy=a.assign(Q=2*a.duration_sec*a.rms_joint**2).groupby('mode').Q.mean().to_dict()
(OUT/'digital_energy.json').write_text(json.dumps(energy,indent=2))
print('INTEGRITY',qc)
print('RQ1',rq1.to_string(index=False))
print('RQ3',rq3.to_string(index=False))
print('RQ4',rq4.to_string(index=False))
print('RQ5',cv.groupby(['scope','mode','target']).M2_vs_M1_MSE_reduction_pct.agg(['min','median','max']).to_string())
print('SIGNATURE',signatures)
# FDR sensitivity valid under arbitrary dependence (no change to original BH estimands).
for file,pcol in [('RQ1_independent.csv','p_seed_permutation'),('RQ3_independent.csv','p_100k_seed_permutation'),('RQ4_independent.csv','p')]:
    frame=pd.read_csv(OUT/file)
    frame['BY_q']=stats.false_discovery_control(frame[pcol],method='by')
    frame.to_csv(OUT/(file[:-4]+'_BY_sensitivity.csv'),index=False)
