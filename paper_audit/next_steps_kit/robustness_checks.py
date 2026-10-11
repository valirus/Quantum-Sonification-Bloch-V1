"""Descriptive robustness diagnostics; repeated folds are not new independent samples."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
from dataset_tools import read_dataset,fit_predict,LOCAL,RELATIONAL,TARGETS,ACOUSTIC

def run(args):
    data=read_dataset(args.dataset);out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    seeds=np.sort(data.seed.unique());layers=np.sort(data.layer.unique());n=len(seeds)
    if args.repeats<1 or not 2<=args.folds<=n:raise ValueError('Invalid repeat/fold counts')
    if args.bootstrap<1:raise ValueError('bootstrap must be positive')
    # RQ4: complete trajectories are resampled, never individual layer rows.
    rng=np.random.default_rng(args.random_seed)
    boot=rng.integers(0,n,(args.bootstrap,n));contrasts=[]
    scopes={'all_layers':layers,'exclude_layer_0':layers[layers!=0],
            'layers_4_and_later':layers[layers>=4]}
    for name,selected in scopes.items():
        if not len(selected):continue
        sub=data[data.layer.isin(selected)]
        for feature in ACOUSTIC:
            pairs=sub.pivot(index=['seed','layer'],columns='mode',values=feature)
            delta=(pairs.bfs-pairs.dfs).groupby('seed').mean().reindex(seeds).to_numpy()
            ci=np.quantile(delta[boot].mean(axis=1),[.025,.975])
            contrasts.append({'scope':name,'feature':feature,'n_seeds':n,'mean_BFS_minus_DFS':delta.mean(),
                              'ci_low':ci[0],'ci_high':ci[1]})
    pd.DataFrame(contrasts).to_csv(out/'RQ4_scope_sensitivity.csv',index=False)
    by_layer=data.groupby(['layer','mode'])[ACOUSTIC].mean()
    by_layer.to_csv(out/'RQ4_means_by_layer.csv')
    # RQ5: identical seed folds for all models and modes within each repeat.
    rows=[]
    for scope,selected in scopes.items():
        if not len(selected):continue
        scoped=data[data.layer.isin(selected)]
        for repeat in range(args.repeats):
            order=np.random.default_rng(args.random_seed+repeat).permutation(seeds)
            folds=np.array_split(order,args.folds)
            for mode in ['bfs','dfs']:
                sub=scoped[scoped['mode']==mode].sort_values(['seed','layer']).reset_index(drop=True)
                for target in TARGETS:
                    y=sub[target].to_numpy();pred={m:np.empty(len(sub)) for m in ['M0','M1','M2']}
                    for group in folds:
                        test=sub.seed.isin(group)
                        train=~test
                        for model,cols in [('M0',[]),('M1',LOCAL),('M2',LOCAL+RELATIONAL)]:
                            pred[model][test]=fit_predict(sub[train],sub[test],target,cols,selected)
                    mse={m:np.mean((y-v)**2) for m,v in pred.items()}
                    variance=np.mean((y-y.mean())**2)
                    row={'scope':scope,'repeat':repeat,'mode':mode,'target':target,'n_seeds':n,
                         **{f'{m}_MSE':float(v) for m,v in mse.items()},
                         **{f'{m}_R2':float(1-v/variance) if variance>0 else np.nan for m,v in mse.items()},
                         'M2_vs_M1_MSE_reduction_pct':float(100*(mse['M1']-mse['M2'])/mse['M1']),
                         'M2_vs_M0_MSE_reduction_pct':float(100*(mse['M0']-mse['M2'])/mse['M0'])}
                    rows.append(row)
    result=pd.DataFrame(rows);result.to_csv(out/'RQ5_repeated_group_CV.csv',index=False)
    summary=result.groupby(['scope','mode','target']).M2_vs_M1_MSE_reduction_pct.agg(['min','median','max'])
    summary.to_csv(out/'RQ5_split_sensitivity_summary.csv')
    (out/'methods.json').write_text(json.dumps({'status':'Exploratory sensitivity diagnostics',
      'n_seeds':n,'repeats':args.repeats,'folds':args.folds,'bootstrap':args.bootstrap,
      'random_seed':args.random_seed,'warnings':[
       'Repeated folds do not increase sample size and are not independent experimental replicates.',
       'Sensitivity intervals are pointwise and descriptive, not a new confirmatory test family.',
       'All models are OLS. Depth is categorical. Scaling is fitted on training rows only.',
       'MSE improvements are conditional on the chosen predictors and circuit ensemble.']},indent=2))
    print(summary.to_string())

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--dataset',required=True);p.add_argument('--output-dir',required=True)
    p.add_argument('--repeats',type=int,default=10);p.add_argument('--folds',type=int,default=5)
    p.add_argument('--bootstrap',type=int,default=5000);p.add_argument('--random-seed',type=int,default=20261004)
    run(p.parse_args())
