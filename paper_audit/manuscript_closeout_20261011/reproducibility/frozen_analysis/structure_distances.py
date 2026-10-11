"""Within-depth distance associations. Pairs are NOT independent observations.

Calls no engine. Optional MI directory provides full matrices. Audio is represented
by eight frozen features. This evaluates descriptor distances, NOT perception,
NOT global state fidelity, NOT isometry. Whole-seed trajectory permutations.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from scipy.stats import rankdata, false_discovery_control

FEATURES=['duration_sec','rms_joint','spectral_centroid_mean_hz',
          'spectral_bandwidth_mean_hz','spectral_entropy_mean','spectral_flux_mean',
          'stereo_balance','stereo_correlation']

def local_distance(x):
    # Mean of per-qubit 3D norms, not norm of an averaged Bloch vector.
    return np.mean(np.linalg.norm(x[:,None,:,:]-x[None,:,:,:],axis=-1),axis=-1)

def ranked_matrix(distance,upper):
    vals=distance[upper];r=rankdata(vals);r-=r.mean()
    norm=np.linalg.norm(r)
    if np.ptp(vals)<1e-10 or norm==0:return None
    a=np.zeros_like(distance);a[upper]=r/norm;a[(upper[1],upper[0])]=r/norm
    return a

def run(a):
    if a.permutations<1:raise ValueError('Positive permutation count required')
    output=Path(a.output_dir)
    if output.exists() and any(output.iterdir()):raise FileExistsError('Choose new output directory')
    d=pd.read_csv(a.dataset);b=pd.read_csv(a.bloch)
    if d.duplicated(['seed','layer','mode']).any() or b.duplicated(['seed','layer','qubit']).any():raise ValueError('Duplicate input keys')
    seeds=np.sort(d.seed.unique());layers=np.sort(d.layer.unique());n=len(seeds)
    if n<3 or set(d['mode'])!={'bfs','dfs'}:raise ValueError('Need >=3 seeds and two modes')
    if len(d)!=n*len(layers)*2:raise ValueError('Incomplete audio grid')
    if set(b.seed)!=set(seeds) or not np.isfinite(d[FEATURES].to_numpy()).all():raise ValueError('Invalid seed/features')
    qcount=int(d.num_qubits.iloc[0]);upper=np.triu_indices(n,1)
    distances={};skipped=[];scale_records={}
    for layer in layers:
        snap=[]
        for seed in seeds:
            rows=b[(b.seed==seed)&(b.layer==layer)].sort_values('qubit')
            if rows.qubit.tolist()!=list(range(qcount)):raise ValueError('Incomplete aligned qubits')
            snap.append(rows[['x','y','z']].to_numpy())
        distances[('Bloch',int(layer))]=local_distance(np.array(snap))
        if a.runs_dir:
            matrices=[np.load(Path(a.runs_dir)/f'seed_{seed:06d}'/'mutual_information_matrices'/f'mi_layer_{layer:02d}.npy',allow_pickle=False) for seed in seeds]
            for m in matrices:
                if m.shape!=(qcount,qcount) or not np.isfinite(m).all() or not np.allclose(m,m.T,atol=1e-10):raise ValueError('Invalid MI matrix')
            # Upper triangular Frobenius/Euclidean distance per original protocol.
            vectors=np.array([m[np.triu_indices(qcount,1)] for m in matrices])
            distances[('MI',int(layer))]=squareform(pdist(vectors))
    pairs=[];tests=[]
    rng=np.random.default_rng(a.random_seed)
    perms=np.array([rng.permutation(n) for _ in range(a.permutations)])
    for mode in ['bfs','dfs']:
        sub=d[d['mode']==mode].sort_values(['seed','layer'])
        # Freeze on a supplied DEVELOPMENT reference for prospective validation.
        reference=pd.read_csv(a.scale_from) if a.scale_from else d
        fit=reference[reference['mode']==mode][FEATURES].to_numpy()
        mu=fit.mean(axis=0);sd=fit.std(axis=0);sd=np.where(sd>1e-12,sd,1)
        scale_records[mode]={'mean':mu.tolist(),'sd':sd.tolist()}
        for target in ['Bloch']+(['MI'] if a.runs_dir else []):
            qs=[];as_=[];eligible=[]
            for layer in layers:
                obs=sub[sub.layer==layer].sort_values('seed')
                audio=squareform(pdist((obs[FEATURES].to_numpy()-mu)/sd))
                qm=ranked_matrix(distances[(target,int(layer))],upper);am=ranked_matrix(audio,upper)
                if qm is None or am is None:
                    skipped.append(dict(mode=mode,target=target,layer=int(layer),reason='constant/numerically degenerate distances'))
                    continue
                rho=float(qm[upper]@am[upper]);eligible.append(int(layer));qs.append(qm[upper]);as_.append(am)
                pairs.append(dict(mode=mode,target=target,layer=int(layer),n_seeds=n,n_pairs=n*(n-1)//2,spearman_distance_rho=rho))
            if not eligible:raise ValueError('No nondegenerate distance layers')
            obs=float(np.mean([q@r[upper] for q,r in zip(qs,as_)]))
            null=np.zeros(a.permutations)
            for q,r in zip(qs,as_):
                # Same seed permutation for every depth: trajectory dependence preserved.
                for start in range(0,a.permutations,100):
                    px=perms[start:start+100]
                    null[start:start+100]+=r[px[:,upper[0]],px[:,upper[1]]]@q/len(eligible)
            p=(1+np.sum(np.abs(null)>=abs(obs)-1e-12))/(a.permutations+1)
            tests.append(dict(mode=mode,target=target,n_seeds=n,layers_used=';'.join(map(str,eligible)),
                              mean_layer_distance_rho=obs,two_sided_seed_permutation_p=float(p)))
    output.mkdir(parents=True,exist_ok=True)
    table=pd.DataFrame(tests);table['BH_q_family']=false_discovery_control(table.two_sided_seed_permutation_p.to_numpy())
    table['BY_q_sensitivity']=false_discovery_control(table.two_sided_seed_permutation_p.to_numpy(),method='by')
    table.to_csv(output/'distance_tests.csv',index=False);pd.DataFrame(pairs).to_csv(output/'distance_by_layer.csv',index=False)
    (output/'methods.json').write_text(json.dumps(dict(status=a.cohort_label,seeds=seeds.tolist(),
        acoustic_features=FEATURES,scaling=scale_records,scale_from=a.scale_from,
        permutations=a.permutations,random_seed=a.random_seed,skipped_layers=skipped,
        statistic='Unweighted mean within-layer Spearman of distance matrices; two-sided seed-label permutation.',
        null='Same whole-seed permutation at all layers within each test.',
        family='2 tests without MI, 4 with MI; exploratory unless registered before independent cohort.',
        caveats=['Pair count is not independent sample size.','No perceptual or global-state preservation claim.',
                 'Non-injectivity and coordinate discontinuities remain even with positive association.',
                 'Numerical degeneracy threshold 1e-10 is fixed; report all skipped layers.',
                 'No seed-bootstrap CI is provided; duplicate-node distance bootstraps need dedicated treatment.']),indent=2))
    print(table.to_string(index=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--bloch',required=True)
    p.add_argument('--runs-dir');p.add_argument('--scale-from');p.add_argument('--output-dir',required=True)
    p.add_argument('--cohort-label',required=True);p.add_argument('--permutations',type=int,default=5000)
    p.add_argument('--random-seed',type=int,default=20261005);a=p.parse_args();run(a)
