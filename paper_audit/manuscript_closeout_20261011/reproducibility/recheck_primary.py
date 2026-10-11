"""Independent recomputation of the uploaded frozen validation evidence."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'reproducibility/reproduction_inputs'
OUT = ROOT / 'reproduction_results/primary'
OUT.mkdir(parents=True, exist_ok=True)
train_path = INPUT / 'paper_audit/next_steps_kit/input_current_100/analysis_dataset.csv'
test_path = INPUT / 'outputs/paper_audit/validation_3000_3099_tables/analysis_dataset.csv'
folder = INPUT / 'outputs/paper_audit/external_validation_3000_3099'
train = pd.read_csv(train_path).sort_values(['seed','layer','mode']).reset_index(drop=True)
test = pd.read_csv(test_path).sort_values(['seed','layer','mode']).reset_index(drop=True)
predictions = pd.read_csv(folder / 'validation_predictions.csv')
stored = pd.read_csv(folder / 'validation_metrics.csv')
manifest = pd.read_csv(INPUT / 'outputs/validation_3000_3099/dataset_manifest.csv')
methods = json.loads((folder / 'methods.json').read_text())
local = ['mean_bloch_radius','mean_linear_entropy','mean_theta_radius_weighted',
         'phi_circular_variance_radius_weighted']
relational = ['log1p_total_mutual_information','edge_weight_entropy']
report = {}
for name, data, start in [('development',train,1000),('validation',test,3000)]:
    assert len(data) == 2200 and data.shape[1] == 42
    assert set(data.seed) == set(range(start,start+100))
    assert set(data.layer) == set(range(11)) and set(data['mode']) == {'bfs','dfs'}
    assert not data.duplicated(['seed','layer','mode']).any()
    assert data.groupby(['seed','layer']).size().eq(2).all()
    assert data.groupby(['seed','mode']).size().eq(11).all()
    numeric = data.select_dtypes(include='number')
    assert np.isfinite(numeric.to_numpy()).all()
    assert data.isna().sum().sum() == 0
    for c,v in [('num_qubits',15),('sample_rate_hz',22050),('stft_nperseg',2048),('stft_noverlap',1536)]:
        assert data[c].eq(v).all()
    quantum = local + ['total_mutual_information','edge_weight_entropy',
                       'central_cut_entanglement_entropy_bits','backbone_components','backbone_edges']
    assert data.groupby(['seed','layer'])[quantum].nunique().eq(1).all().all()
    assert data.central_cut_entanglement_entropy_bits.between(-1e-10,7+1e-10).all()
    data['log1p_total_mutual_information'] = np.log1p(data.total_mutual_information)
    report[name] = {'rows':len(data),'seeds':data.seed.nunique(),'missing_values':0,'duplicate_keys':0}
assert set(train.seed).isdisjoint(test.seed)
assert len(manifest)==100 and set(manifest.seed)==set(test.seed)
assert manifest.status.eq('passed').all() and manifest.error.fillna('').eq('').all()
assert methods['bootstrap']==5000 and methods['random_seed']==20261004
assert methods['development_seeds']==list(range(1000,1100))
assert methods['validation_seeds']==list(range(3000,3100))
assert len(predictions)==4400 and not predictions.duplicated(['seed','layer','mode','target']).any()
assert len(stored)==4 and not stored.duplicated(['mode','target']).any()

report['historical_development_max_numeric_error'] = 'Verified in original audit receipt; archive not duplicated here.'

bootstrap = np.random.default_rng(20261004).integers(0,100,(5000,100))
results=[]; max_prediction_error=0.; max_metric_error=0.
for mode in ['bfs','dfs']:
    a=train[train['mode']==mode].sort_values(['seed','layer'])
    b=test[test['mode']==mode].sort_values(['seed','layer'])
    for target in ['duration_sec','spectral_flux_mean']:
        p=predictions[(predictions['mode']==mode)&(predictions.target==target)].sort_values(['seed','layer'])
        assert len(p)==1100
        assert np.array_equal(p[['seed','layer']].to_numpy(),b[['seed','layer']].to_numpy())
        y=b[target].to_numpy()
        assert np.max(np.abs(y-p.observed.to_numpy())) < 1e-12
        fitted={}
        for model,columns in [('M0',[]),('M1',local),('M2',local+relational)]:
            def depth(data):
                return np.column_stack([np.ones(len(data))]+[(data.layer.to_numpy()==i).astype(float) for i in range(1,11)])
            xtrain=depth(a); xtest=depth(b)
            if columns:
                raw=a[columns].to_numpy(); mu=raw.mean(axis=0); sigma=raw.std(axis=0)
                sigma=np.where(sigma>1e-12,sigma,1.)
                xtrain=np.column_stack([xtrain,(raw-mu)/sigma])
                xtest=np.column_stack([xtest,(b[columns].to_numpy()-mu)/sigma])
            coef=np.linalg.lstsq(xtrain,a[target].to_numpy(),rcond=None)[0]
            fitted[model]=xtest@coef
            error=float(np.max(np.abs(fitted[model]-p[model].to_numpy())))
            max_prediction_error=max(max_prediction_error,error)
            assert error<1e-11
        mse={m:float(np.mean((y-v)**2)) for m,v in fitted.items()}
        variance=float(np.mean((y-y.mean())**2))
        delta=pd.DataFrame({'seed':b.seed.to_numpy(),
               'difference':(y-fitted['M1'])**2-(y-fitted['M2'])**2}).groupby('seed').difference.mean().to_numpy()
        ci=np.quantile(delta[bootstrap].mean(axis=1),[.025,.975])
        calculated={**{m+'_MSE':v for m,v in mse.items()},
                    **{m+'_R2':1-v/variance for m,v in mse.items()},
                    'M2_vs_M1_MSE_reduction_pct':100*(mse['M1']-mse['M2'])/mse['M1'],
                    'mean_seed_MSE_M1_minus_M2':float(delta.mean()),
                    'fixed_training_CI_low':float(ci[0]),'fixed_training_CI_high':float(ci[1])}
        expected=stored[(stored['mode']==mode)&(stored.target==target)].iloc[0]
        for key,value in calculated.items():
            error=abs(value-float(expected[key]));max_metric_error=max(max_metric_error,error)
            assert error<1e-10
        results.append({'mode':mode,'target':target,**calculated,
                        **{m+'_RMSE':float(np.sqrt(v)) for m,v in mse.items()}})
report['manifest_passed_seeds']=100
report['model_predictions_recomputed']=13200
report['prediction_max_absolute_error']=max_prediction_error
report['reported_metrics_max_absolute_error']=max_metric_error
report['primary_criterion_met']=bool(next(r for r in results if r['mode']=='dfs' and r['target']=='duration_sec')['fixed_training_CI_low']>0)
report['scope']='Audit of supplied CSVs and protocol; does not independently inspect WSL engine files or regenerate WAV/statevectors.'
report['input_sha256']={str(p.relative_to(INPUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUT.rglob('*') if p.is_file()}
pd.DataFrame(results).to_csv(OUT / 'RQ5_independent_recomputation.csv',index=False)
(OUT / 'primary_audit_receipt.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
print(pd.DataFrame(results).to_string(index=False))
