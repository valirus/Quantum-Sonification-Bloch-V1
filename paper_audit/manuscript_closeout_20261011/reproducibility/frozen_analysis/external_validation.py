"""Fit frozen OLS specifications on development seeds and evaluate disjoint fresh seeds."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
from dataset_tools import read_dataset,fit_predict,LOCAL,RELATIONAL,TARGETS

def run(args):
    train=read_dataset(args.train);test=read_dataset(args.test)
    if set(train.seed)&set(test.seed):raise ValueError('Development and validation seeds overlap')
    layers=np.sort(train.layer.unique())
    if set(layers)!=set(test.layer.unique()):raise ValueError('Different depth grids; extrapolation is not supported')
    if args.bootstrap<1:raise ValueError('bootstrap must be positive')
    seeds=np.sort(test.seed.unique());n=len(seeds)
    boot=np.random.default_rng(args.random_seed).integers(0,n,(args.bootstrap,n))
    rows=[];records=[]
    for mode in ['bfs','dfs']:
        a=train[train['mode']==mode];b=test[test['mode']==mode].sort_values(['seed','layer'])
        for target in TARGETS:
            y=b[target].to_numpy()
            pred={m:fit_predict(a,b,target,cols,layers) for m,cols in
                  [('M0',[]),('M1',LOCAL),('M2',LOCAL+RELATIONAL)]}
            mse={m:np.mean((y-v)**2) for m,v in pred.items()}
            variance=np.mean((y-y.mean())**2)
            errors=pd.DataFrame({'seed':b.seed.to_numpy(),'M1':(y-pred['M1'])**2,'M2':(y-pred['M2'])**2})
            perseed=errors.groupby('seed').mean().reindex(seeds)
            delta=(perseed.M1-perseed.M2).to_numpy()
            ci=np.quantile(delta[boot].mean(axis=1),[.025,.975])
            rows.append({'mode':mode,'target':target,'n_development_seeds':train.seed.nunique(),
                'n_validation_seeds':n,**{f'{m}_MSE':float(v) for m,v in mse.items()},
                **{f'{m}_R2':float(1-v/variance) if variance>0 else np.nan for m,v in mse.items()},
                'M2_vs_M1_MSE_reduction_pct':float(100*(mse['M1']-mse['M2'])/mse['M1']),
                'mean_seed_MSE_M1_minus_M2':delta.mean(),'fixed_training_CI_low':ci[0],'fixed_training_CI_high':ci[1]})
            for j,r in enumerate(b.itertuples()):
                records.append({'seed':r.seed,'layer':r.layer,'mode':mode,'target':target,'observed':y[j],
                                **{m:v[j] for m,v in pred.items()}})
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(out/'validation_metrics.csv',index=False)
    pd.DataFrame(records).to_csv(out/'validation_predictions.csv',index=False)
    (out/'methods.json').write_text(json.dumps({'status':'External evaluation of frozen models',
        'bootstrap':args.bootstrap,'random_seed':args.random_seed,
        'development_seeds':sorted(train.seed.unique().tolist()),'validation_seeds':seeds.tolist(),
        'caveat':'Intervals resample validation seeds with trained models fixed. They quantify test-sample uncertainty, not training uncertainty. No test labels tune the models. No multiplicity-adjusted confirmatory claim is automatic.'},indent=2))
    print(pd.DataFrame(rows).to_string(index=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--train',required=True);p.add_argument('--test',required=True)
    p.add_argument('--output-dir',required=True);p.add_argument('--bootstrap',type=int,default=5000)
    p.add_argument('--random-seed',type=int,default=20261004)
    run(p.parse_args())
