"""Read-only inventory for saved runs shown in Cursor; stdlib only."""
from pathlib import Path
import argparse, csv, hashlib, json

def run(repo,runs,output):
    repo=Path(repo).resolve();runs=Path(runs).resolve();out=Path(output).resolve()
    if out==runs or runs in out.parents:raise ValueError('Output must be outside original runs')
    if out.exists():raise FileExistsError('Choose a fresh inventory file')
    rows=[]
    for folder in sorted(runs.glob('seed_*')):
        if not folder.is_dir():continue
        metadata=folder/'metadata.json';issues=[];meta={}
        if metadata.is_file():
            try:meta=json.loads(metadata.read_text())
            except Exception as e:issues.append('unreadable metadata: '+str(e))
        else:issues.append('missing metadata.json')
        expected=int(meta.get('layers',10))+1
        if meta:
            for key,value in [('num_qubits',15),('layers',10),('preferred_root',7),('edge_tolerance',1e-10)]:
                if meta.get(key)!=value:issues.append('config mismatch: '+key)
            if folder.name!=f"seed_{int(meta['seed']):06d}":issues.append('folder/metadata seed mismatch')
        counts={}
        for label,pattern in [('states','statevectors/statevector_layer_*.npy'),
                              ('MI','mutual_information_matrices/mi_layer_*.npy'),
                              ('QPY','circuits/circuit_layer_*.qpy'),
                              ('BFS_WAV','audio/bfs/layer_*.wav'),('DFS_WAV','audio/dfs/layer_*.wav')]:
            counts[label]=len(list(folder.glob(pattern)))
            if counts[label]!=expected:issues.append(f'{label}: {counts[label]}/{expected}')
        for name in ['bloch_descriptors.csv','layer_metrics.csv','audio_features.csv','gate_manifest.csv','circuit_metrics.csv']:
            if not (folder/name).is_file():issues.append('missing '+name)
        rows.append(dict(folder=folder.name,seed=meta.get('seed'),**counts,
                         file_inventory_ok=not issues,issues='; '.join(issues)))
    if not rows:raise ValueError('No seed_* directories found')
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    hashes={name:hashlib.sha256((repo/name).read_bytes()).hexdigest() for name in
            ['src/sonification.py','src/simulations.py','src/circuit.py','src/gates.py',
             'analysis/extract_stft_features.py','analysis/run_dataset.py']}
    out.with_suffix('.json').write_text(json.dumps(dict(run_folders=len(rows),
        inventory_ok=sum(r['file_inventory_ok'] for r in rows),engine_source_sha256=hashes,
        caveat='Existence/configuration inventory, not binary, quantum or statistical validation.'),indent=2))
    print(json.dumps(dict(run_folders=len(rows),inventory_ok=sum(r['file_inventory_ok'] for r in rows),output=str(out))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo-dir',required=True);p.add_argument('--runs-dir',required=True)
    p.add_argument('--output',required=True);a=p.parse_args();run(a.repo_dir,a.runs_dir,a.output)
