"""Apply the corrected RQ1--RQ4 specifications to a supplied seed cohort.

Defaults match the corrected statistical tests; RQ2 pointwise bootstrap bands
are descriptive additions. Designate development/validation before opening data.
"""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
from scipy import stats
from dataset_tools import read_dataset,ACOUSTIC

QUANTUM=['mean_bloch_radius','mean_linear_entropy','mean_von_neumann_entropy',
         'central_cut_entanglement_entropy_bits','total_mutual_information',
         'positive_edge_density','backbone_edges','backbone_components']

def bh(values):
    p=np.asarray(values);order=np.argsort(p)
    ranked=np.minimum.accumulate((p[order]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1]
    q=np.empty_like(p);q[order]=np.minimum(ranked,1);return q

def centered(a):
    result=a-a.mean(axis=0,keepdims=True);result[:,a.std(axis=0)<1e-12]=0;return result

def correlation(a,b):
    den=np.sqrt(np.sum(a*a)*np.sum(b*b))
    return float(np.sum(a*b)/den) if den>0 else np.nan

def run(args):
    if min(args.bootstrap,args.paired_bootstrap,args.permutations,args.stereo_permutations)<1:
        raise ValueError('Resampling counts must be positive')
    data=read_dataset(args.dataset);seeds=np.sort(data.seed.unique());layers=np.sort(data.layer.unique());n=len(seeds)
    for col in QUANTUM+['stereo_correlation','stereo_balance']:
        if col not in data or not np.isfinite(data[col].to_numpy()).all():raise ValueError(f'Invalid column {col}')
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    def matrix(sub,col):return sub.pivot(index='seed',columns='layer',values=col).reindex(index=seeds,columns=layers).to_numpy()
    rng=np.random.default_rng(args.random_seed)
    permutations=np.array([rng.permutation(n) for _ in range(args.permutations)])
    boot=rng.integers(0,n,(args.bootstrap,n));local=[]
    for mode in ['bfs','dfs']:
        sub=data[data['mode']==mode]
        for x,y in [('mean_bloch_radius','rms_joint'),('mean_theta_radius_weighted','spectral_centroid_mean_hz')]:
            a=matrix(sub,x);b=matrix(sub,y);ac=centered(a);bc=centered(b)
            obs=correlation(ac,bc);den=np.sqrt(np.sum(ac*ac)*np.sum(bc*bc))
            if not np.isfinite(obs):raise ValueError('Undefined primary correlation')
            cross=ac@bc.T;null=cross[np.arange(n)[None,:],permutations].sum(axis=1)/den
            p=(1+np.sum(np.abs(null)>=abs(obs)))/(args.permutations+1)
            values=np.array([correlation(centered(a[ix]),centered(b[ix])) for ix in boot])
            if not np.isfinite(values).all():raise ValueError('Degenerate bootstrap samples')
            ci=np.quantile(values,[.025,.975])
            local.append({'mode':mode,'quantum':x,'audio':y,'n_seeds':n,'pearson_depth_adjusted':obs,
                          'ci_low':ci[0],'ci_high':ci[1],'permutation_p_two_sided':p})
    result=pd.DataFrame(local);result['FDR_q_4_tests']=bh(result.permutation_p_two_sided)
    result.to_csv(out/'RQ1_depth_controlled.csv',index=False)
    curves=[]
    for mode,columns in [('quantum',QUANTUM),('bfs',ACOUSTIC+['stereo_correlation','stereo_balance']),
                         ('dfs',ACOUSTIC+['stereo_correlation','stereo_balance'])]:
        sub=data[data['mode']==('bfs' if mode=='quantum' else mode)]
        for feature in columns:
            a=matrix(sub,feature);ci=np.quantile(a[boot].mean(axis=1),[.025,.975],axis=0)
            for j,layer in enumerate(layers):
                curves.append({'mode':mode,'feature':feature,'layer':layer,'n_seeds':n,
                               'mean':a[:,j].mean(),'ci_low':ci[0,j],'ci_high':ci[1,j]})
    pd.DataFrame(curves).to_csv(out/'RQ2_pointwise_seed_bands.csv',index=False)
    stereo=[]
    for mode in ['bfs','dfs']:
        for layer in layers[layers!=0]:
            sub=data[(data['mode']==mode)&(data.layer==layer)].sort_values('seed')
            x=stats.rankdata(sub.phi_circular_variance_radius_weighted);y=stats.rankdata(sub.stereo_correlation)
            x=x-x.mean();y=y-y.mean();rho=correlation(x,y)
            if not np.isfinite(rho):raise ValueError('Undefined stereo association at nonzero layer')
            den=np.sqrt(np.sum(x*x)*np.sum(y*y));count=0;remaining=args.stereo_permutations
            # Reset RNG: the same seed-label permutations are used for all layer/mode tests.
            srng=np.random.default_rng(args.random_seed)
            while remaining:
                k=min(1000,remaining);ix=np.array([srng.permutation(n) for _ in range(k)])
                null=y[ix]@x/den;count+=np.sum(np.abs(null)>=abs(rho)-1e-12);remaining-=k
            stereo.append({'mode':mode,'layer':layer,'n_seeds':n,'spearman_rho':rho,
                           'permutation_p_two_sided':(1+count)/(args.stereo_permutations+1)})
    result=pd.DataFrame(stereo);result['FDR_q_layer_mode_family']=bh(result.permutation_p_two_sided)
    result.to_csv(out/'RQ3_stereo_by_layer.csv',index=False)
    paired_boot=np.random.default_rng(args.random_seed-1).integers(0,n,(args.paired_bootstrap,n));paired=[]
    for feature in ACOUSTIC:
        pairs=data.pivot(index=['seed','layer'],columns='mode',values=feature)
        delta=(pairs.bfs-pairs.dfs).groupby('seed').mean().reindex(seeds).to_numpy()
        ci=np.quantile(delta[paired_boot].mean(axis=1),[.025,.975]);test=stats.ttest_1samp(delta,0)
        paired.append({'feature':feature,'n_seeds':n,'mean_BFS_minus_DFS':delta.mean(),
                       'ci_low':ci[0],'ci_high':ci[1],'paired_seed_t':test.statistic,'paired_seed_p':test.pvalue})
    result=pd.DataFrame(paired);result['FDR_q_6_tests']=bh(result.paired_seed_p)
    result.to_csv(out/'RQ4_paired_six_features.csv',index=False)
    (out/'methods.json').write_text(json.dumps({'cohort_label':args.cohort_label,'seeds':seeds.tolist(),
        'random_seed':args.random_seed,'bootstrap':args.bootstrap,'paired_bootstrap':args.paired_bootstrap,
        'permutations_RQ1':args.permutations,'permutations_RQ3':args.stereo_permutations,
        'notes':['Whole seeds are the independent resampling unit; layers and modes are repeated measures.',
                 'RQ1 uses per-layer centering, whole-trajectory label permutations and refitted bootstrap centering.',
                 'RQ3 excludes initial layer 0, whose descriptors are constant in the original design.',
                 'RQ4 uses a paired t test on each seed\'s average mode difference.',
                 'FDR is applied within predeclared RQ families, not after selecting significant layers.',
                 'RQ2 intervals are pointwise descriptive, not simultaneous confidence bands.',
                 'The cohort label alone does not make a post-hoc analysis confirmatory.']},indent=2))
    print(json.dumps({'n_seeds':n,'cohort_label':args.cohort_label,'output_dir':str(out)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--output-dir',required=True)
    p.add_argument('--cohort-label',required=True);p.add_argument('--bootstrap',type=int,default=5000)
    p.add_argument('--paired-bootstrap',type=int,default=10000);p.add_argument('--permutations',type=int,default=5000)
    p.add_argument('--stereo-permutations',type=int,default=100000);p.add_argument('--random-seed',type=int,default=20261004)
    run(p.parse_args())
