"""Strict CSV assembly and shared validation for the next sonification study."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd

LOCAL = ['mean_bloch_radius','mean_linear_entropy','mean_theta_radius_weighted',
         'phi_circular_variance_radius_weighted']
RELATIONAL = ['log1p_total_mutual_information','edge_weight_entropy']
TARGETS = ['duration_sec','spectral_flux_mean']
ACOUSTIC = ['duration_sec','rms_joint','spectral_centroid_mean_hz',
            'spectral_bandwidth_mean_hz','spectral_entropy_mean','spectral_flux_mean']

def read_dataset(path):
    data = pd.read_csv(path)
    required = ['seed','layer','mode','num_qubits','sample_rate_hz','stft_nperseg','stft_noverlap',
                'total_mutual_information','edge_weight_entropy']+LOCAL+ACOUSTIC
    missing = sorted(set(required)-set(data))
    if missing: raise ValueError(f'Missing columns: {missing}')
    if data[required].isna().any().any(): raise ValueError('Missing values in required fields')
    if not np.isfinite(data[[c for c in required if c!='mode']].to_numpy(dtype=float)).all():
        raise ValueError('Non-finite numeric data')
    for col in ['seed','layer']:
        if not (data[col].to_numpy(dtype=float)==data[col].to_numpy(dtype=int)).all():
            raise ValueError(f'{col} must contain integers')
        data[col]=data[col].astype(int)
    if data.duplicated(['seed','layer','mode']).any(): raise ValueError('Duplicate keys')
    if set(data['mode']) != {'bfs','dfs'}: raise ValueError('Only the two primary modes are supported')
    for col,value in [('num_qubits',15),('sample_rate_hz',22050),('stft_nperseg',2048),('stft_noverlap',1536)]:
        if not (data[col]==value).all():raise ValueError(f'{col} differs from the frozen study value {value}')
    seeds=np.sort(data.seed.unique()); layers=np.sort(data.layer.unique())
    if len(seeds)<5: raise ValueError('At least five seeds are needed')
    if len(data)!=len(seeds)*len(layers)*2: raise ValueError('Incomplete seed/layer/mode grid')
    for col in LOCAL+['total_mutual_information','edge_weight_entropy']:
        if (data.groupby(['seed','layer'])[col].nunique()>1).any():
            raise ValueError(f'Quantum descriptor differs between modes: {col}')
    if (data.total_mutual_information<0).any(): raise ValueError('MI must be nonnegative')
    data['log1p_total_mutual_information']=np.log1p(data.total_mutual_information)
    return data.sort_values(['seed','layer','mode']).reset_index(drop=True)

def fit_predict(train, test, target, cols, layers):
    """Categorical depth and OLS; all scaling fitted only on the training rows."""
    layers=list(layers)
    def depth(data):
        a=data.layer.to_numpy()
        return np.column_stack([np.ones(len(data))]+[(a==x).astype(float) for x in layers[1:]])
    xtrain=depth(train); xtest=depth(test)
    if cols:
        values=train[cols].to_numpy(); mean=values.mean(axis=0); sd=values.std(axis=0)
        sd=np.where(sd>1e-12,sd,1)
        xtrain=np.column_stack([xtrain,(values-mean)/sd])
        xtest=np.column_stack([xtest,(test[cols].to_numpy()-mean)/sd])
    coef=np.linalg.lstsq(xtrain,train[target].to_numpy(),rcond=None)[0]
    return xtest@coef

def assemble(tables_dir, output):
    tables_dir=Path(tables_dir); output=Path(output)
    quantum=pd.read_csv(tables_dir/'layer_metrics.csv')
    acoustic=pd.read_csv(tables_dir/'audio_features.csv')
    if quantum.duplicated(['seed','layer']).any():raise ValueError('Duplicated quantum rows')
    if acoustic.duplicated(['seed','layer','mode']).any():raise ValueError('Duplicated audio rows')
    overlap=(set(quantum)&set(acoustic))-{'seed','layer'}
    if overlap:raise ValueError(f'Unexpected overlapping columns: {sorted(overlap)}')
    data=acoustic.merge(quantum,on=['seed','layer'],how='outer',validate='many_to_one',indicator=True)
    if not (data['_merge']=='both').all():raise ValueError('Unmatched quantum/audio rows')
    data=data.drop(columns='_merge')
    readback_columns=list(data.columns)
    output.parent.mkdir(parents=True,exist_ok=True)
    # Check before installing the final path; no partial valid-looking dataset on failure.
    temp=output.with_name(output.name+'.tmp.csv')
    try:
        data.to_csv(temp,index=False); checked=read_dataset(temp)
        data=data.sort_values(['seed','layer','mode'])[readback_columns]
        data.to_csv(output,index=False)
    finally:
        temp.unlink(missing_ok=True)
    receipt={'rows':len(checked),'seeds':int(checked.seed.nunique()),
             'layers':sorted(checked.layer.unique().tolist()),'modes':['bfs','dfs']}
    output.with_suffix('.validation.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--tables-dir',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();assemble(a.tables_dir,a.output)
