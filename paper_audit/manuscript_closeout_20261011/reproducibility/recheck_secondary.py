"""Check secondary estimates, FDR and randomization with independent arrays."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import stats

root=Path(__file__).resolve().parents[1]
out=root/'reproduction_results/secondary'
out.mkdir(parents=True,exist_ok=True)
tables=root/'data'
data=pd.read_csv(tables/'validation_3000_3099.csv')
rq1=pd.read_csv(tables/'RQ1.csv')
rq3=pd.read_csv(tables/'RQ3.csv')
rq4=pd.read_csv(tables/'RQ4.csv')
def fdr(p):
    ix=np.argsort(p); q=np.empty(len(p)); sorted_q=np.asarray(p)[ix]*len(p)/np.arange(1,len(p)+1)
    for i in range(len(p)-2,-1,-1):sorted_q[i]=min(sorted_q[i],sorted_q[i+1])
    q[ix]=np.minimum(1,sorted_q);return q
errors={}
for row in rq1.itertuples():
    sub=data[data['mode']==row.mode]
    a=(sub[row.quantum]-sub.groupby('layer')[row.quantum].transform('mean')).to_numpy()
    b=(sub[row.audio]-sub.groupby('layer')[row.audio].transform('mean')).to_numpy()
    rho=np.dot(a,b)/np.sqrt(np.dot(a,a)*np.dot(b,b))
    # Initial descriptors are exactly constant; numerical tiny residuals have no effect.
    errors[f'RQ1_{row.mode}_{row.quantum}']=abs(rho-row.pearson_depth_adjusted)
assert max(errors.values())<1e-12
assert np.max(abs(fdr(rq1.permutation_p_two_sided)-rq1.FDR_q_4_tests))<1e-12

# Recompute all four RQ1 randomization values and refitted-centering intervals.
rng1=np.random.default_rng(20261004)
perms1=np.array([rng1.permutation(100) for _ in range(5000)])
boot1=rng1.integers(0,100,(5000,100))
def demean(z):
    result=z-z.mean(axis=0,keepdims=True)
    result[:,z.std(axis=0)<1e-12]=0
    return result
def corr(x,y):return np.sum(x*y)/np.sqrt(np.sum(x*x)*np.sum(y*y))
for row in rq1.itertuples():
    sub=data[data['mode']==row.mode]
    x=sub.pivot(index='seed',columns='layer',values=row.quantum).sort_index().to_numpy()
    y=sub.pivot(index='seed',columns='layer',values=row.audio).sort_index().to_numpy()
    xc,yc=demean(x),demean(y);den=np.sqrt(np.sum(xc*xc)*np.sum(yc*yc));null=np.array([np.sum(xc*yc[perm])/den for perm in perms1])
    p1=(1+np.count_nonzero(abs(null)>=abs(corr(xc,yc))))/5001
    samples=np.array([corr(demean(x[ix]),demean(y[ix]))for ix in boot1]);ci=np.quantile(samples,[.025,.975])
    assert abs(p1-row.permutation_p_two_sided)<1e-12
    assert max(abs(ci[0]-row.ci_low),abs(ci[1]-row.ci_high))<1e-10

rank_x=[];rank_y=[];observed=[]
for row in rq3.itertuples():
    sub=data[(data['mode']==row.mode)&(data.layer==row.layer)].sort_values('seed')
    rho=stats.spearmanr(sub.phi_circular_variance_radius_weighted,sub.stereo_correlation).statistic
    errors[f'RQ3_{row.mode}_{row.layer}']=abs(rho-row.spearman_rho)
    x=stats.rankdata(sub.phi_circular_variance_radius_weighted);y=stats.rankdata(sub.stereo_correlation)
    x-=x.mean();y-=y.mean()
    rank_x.append(x/np.linalg.norm(x));rank_y.append(y/np.linalg.norm(y));observed.append(rho)
xx=np.column_stack(rank_x); yy=np.column_stack(rank_y);counts=np.zeros(20,dtype=int)
rng=np.random.default_rng(20261004)
for _ in range(100):
    permutations=np.stack([rng.permutation(100) for i in range(1000)])
    null=np.einsum('bjk,jk->bk',yy[permutations],xx)
    counts+=(np.abs(null)>=np.abs(observed)-1e-12).sum(axis=0)
p=(counts+1)/100001
assert np.max(abs(p-rq3.permutation_p_two_sided.to_numpy()))<1e-12
assert np.max(abs(fdr(p)-rq3.FDR_q_layer_mode_family))<1e-12

boot=np.random.default_rng(20261003).integers(0,100,(10000,100))
for row in rq4.itertuples():
    pair=data.pivot(index=['seed','layer'],columns='mode',values=row.feature)
    delta=(pair.bfs-pair.dfs).groupby('seed').mean().to_numpy()
    ci=np.quantile(delta[boot].mean(axis=1),[.025,.975])
    t=stats.ttest_1samp(delta,0)
    errors[f'RQ4_{row.feature}']=max(abs(delta.mean()-row.mean_BFS_minus_DFS),abs(ci[0]-row.ci_low),abs(ci[1]-row.ci_high),abs(t.statistic-row.paired_seed_t),abs(t.pvalue-row.paired_seed_p))
assert max(errors.values())<1e-10
assert np.max(abs(fdr(rq4.paired_seed_p)-rq4.FDR_q_6_tests))<1e-12
rq2=pd.read_csv(tables/'RQ2.csv')
rng=np.random.default_rng(20261004)
for _ in range(5000): rng.permutation(100)
curve_boot=rng.integers(0,100,(5000,100))
curve_error=0.
for (mode,feature),frame in rq2.groupby(['mode','feature']):
    sub=data[data['mode']==('bfs' if mode=='quantum' else mode)]
    a=sub.pivot(index='seed',columns='layer',values=feature).sort_index().to_numpy()
    bounds=np.quantile(a[curve_boot].mean(axis=1),[.025,.975],axis=0)
    frame=frame.sort_values('layer')
    curve_error=max(curve_error,float(np.max(abs(a.mean(axis=0)-frame['mean'].to_numpy()))),
                    float(np.max(abs(bounds[0]-frame.ci_low.to_numpy()))),
                    float(np.max(abs(bounds[1]-frame.ci_high.to_numpy()))))
assert curve_error<1e-10
receipt={'maximum_estimate_check_error':max(errors.values()),
         'RQ2_rows_recomputed':len(rq2),'RQ2_maximum_band_check_error':curve_error,
         'RQ3_all_20_permutation_p_values_recomputed':True,
         'FDR_families_recomputed':[4,20,6],
         'RQ1_all_four_FDR_below_0_05':bool(rq1.FDR_q_4_tests.lt(.05).all()),
         'RQ3_FDR_below_0_05':rq3[rq3.FDR_q_layer_mode_family<.05][['mode','layer','spearman_rho','FDR_q_layer_mode_family']].to_dict('records'),
         'RQ4_flux_caution':'Small positive effect in this cohort, FDR q=0.04652; development cohort did not establish a mean difference. Do not claim uniform null or strong universal separation.',
         'provenance':'Independent array calculations on the supplied validation table; the recorded WSL source is included separately.'}
(out/'secondary_audit_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
