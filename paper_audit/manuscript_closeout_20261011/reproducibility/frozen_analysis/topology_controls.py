"""Render synthetic forest controls with the unmodified project engine.

These controls change renderer inputs, not physical quantum states. They keep
each component's node set and edge-weight multiset. No new quantum simulation.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, tempfile
import networkx as nx
import numpy as np
import pandas as pd
from dataset_tools import ACOUSTIC

def load_module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def forest_from_matrix(matrix, tolerance):
    n=len(matrix)
    if matrix.shape!=(n,n) or not np.isfinite(matrix).all():raise ValueError('Invalid MI matrix')
    if not np.allclose(matrix,matrix.T,atol=1e-10,rtol=0):raise ValueError('Asymmetric MI matrix')
    if matrix.min() < -1e-9 or matrix.max()>2+1e-9:raise ValueError('MI outside the two-qubit range')
    graph=nx.Graph();graph.add_nodes_from(range(n))
    for i in range(n):
        for j in range(i+1,n):
            if matrix[i,j]>tolerance:graph.add_edge(i,j,weight=float(matrix[i,j]))
    return nx.maximum_spanning_tree(graph,weight='weight')

def controlled_forest(original, kind, rng):
    graph=nx.Graph();graph.add_nodes_from(original.nodes)
    for component in sorted(nx.connected_components(original),key=min):
        nodes=sorted(component);m=len(nodes)
        edges=sorted((min(a,b),max(a,b)) for a,b in original.subgraph(nodes).edges)
        weights=[original[a][b]['weight'] for a,b in edges]
        if kind=='tree_shuffle' and m>2:
            tree=nx.from_prufer_sequence(rng.integers(0,m,size=m-2).tolist())
            edges=sorted((min(nodes[a],nodes[b]),max(nodes[a],nodes[b])) for a,b in tree.edges)
        elif kind not in ['weight_shuffle','tree_shuffle']:
            raise ValueError(kind)
        shuffled=rng.permutation(weights)
        for (a,b),weight in zip(edges,shuffled):graph.add_edge(a,b,weight=float(weight))
    for component in nx.connected_components(original):
        old=sorted(d['weight'] for _,_,d in original.subgraph(component).edges(data=True))
        new=sorted(d['weight'] for _,_,d in graph.subgraph(component).edges(data=True))
        if old!=new:raise AssertionError('Weight multiset changed')
    if {frozenset(c) for c in nx.connected_components(graph)}!={frozenset(c) for c in nx.connected_components(original)}:
        raise AssertionError('Components changed')
    return graph

def edge_set(graph):return {frozenset((a,b)) for a,b in graph.edges}

def dfs_analytic_duration(graph,config):
    c=nx.number_connected_components(graph);n=len(graph)
    weights=sum(float(d['weight']) for _,_,d in graph.edges(data=True))
    # The physical weights are in [0,2]; this is the unclipped linear rule.
    maximum=config['event_duration_max_sec'];minimum=config['event_duration_min_sec']
    return (c*config['root_duration_sec']+(n-c)*maximum
            -(maximum-minimum)*weights/2+(c-1)*config['component_gap_sec'])

def run(args):
    if args.replicates<1 or args.bootstrap<1:raise ValueError('Positive replicate/bootstrap counts required')
    if args.max_seeds is not None and args.max_seeds<1:raise ValueError('max-seeds must be positive')
    repo=Path(args.repo_dir).resolve();runs=Path(args.runs_dir).resolve()
    engine_path=repo/'src/sonification.py';extractor_path=repo/'analysis/extract_stft_features.py'
    engine=load_module(engine_path,'frozen_sonification');extractor=load_module(extractor_path,'frozen_features')
    metadata_paths=sorted(runs.glob('seed_*/metadata.json'))
    if args.max_seeds is not None:metadata_paths=metadata_paths[:args.max_seeds]
    if not metadata_paths:raise ValueError('No full seed runs found; CSV summaries alone are insufficient')
    selected=sorted(set(args.layers));rows=[];seen=set();source_hashes=[]
    with tempfile.TemporaryDirectory(prefix='sonification_controls_') as tmp:
        wav_path=Path(tmp)/'control.wav'
        for metadata_path in metadata_paths:
            run_dir=metadata_path.parent;meta=json.loads(metadata_path.read_text());seed=int(meta['seed'])
            if seed in seen:raise ValueError('Duplicate seeds');
            seen.add(seed)
            config=meta['audio_config']
            if config!=engine.DEFAULT_CONFIG:raise ValueError('Different audio configuration; run a separate version')
            root=int(meta['preferred_root']);tolerance=float(meta['edge_tolerance']);n=int(meta['num_qubits'])
            source_hashes.append({'seed':seed,'metadata_sha256':hashlib.sha256(metadata_path.read_bytes()).hexdigest()})
            bloch_path=run_dir/'bloch_descriptors.csv';bloch=pd.read_csv(bloch_path)
            source_hashes.append({'seed':seed,'bloch_sha256':hashlib.sha256(bloch_path.read_bytes()).hexdigest()})
            if bloch.duplicated(['seed','layer','qubit']).any() or set(bloch.seed)!={seed}:
                raise ValueError('Invalid Bloch row identities')
            for layer in selected:
                b=bloch[bloch.layer==layer].sort_values('qubit')
                if b.qubit.tolist()!=list(range(n)):raise ValueError(f'Incomplete qubits: seed {seed}, layer {layer}')
                descriptor={k:b[k].to_numpy() for k in ['theta','phi','r','linear_entropy']}
                if not np.isfinite(np.column_stack(list(descriptor.values()))).all():raise ValueError('Invalid Bloch values')
                mi_path=run_dir/'mutual_information_matrices'/f'mi_layer_{layer:02d}.npy'
                matrix=np.load(mi_path,allow_pickle=False)
                if matrix.shape!=(n,n):raise ValueError('Wrong number of qubits in MI matrix')
                original=forest_from_matrix(matrix,tolerance)
                source_hashes.extend([{'seed':seed,'layer':layer,'mi_sha256':hashlib.sha256(mi_path.read_bytes()).hexdigest()}])
                baseline={}
                def render(graph,condition,replicate):
                    frontiers=[f for f in engine.weighted_bfs_frontiers(graph,root) if f]
                    for mode,renderer in [('bfs',engine.render_bfs),('dfs',engine.render_dfs)]:
                        audio=renderer(graph,descriptor,root,config)
                        if not np.isfinite(audio).all() or np.max(np.abs(audio))>=1:raise ValueError('Nonfinite audio or clipping')
                        engine.write_wav(wav_path,audio,int(config['sample_rate']))
                        features=extractor.extract_features(wav_path,nperseg=2048,noverlap=1536)
                        if mode=='dfs':
                            residual=abs(features['duration_sec']-dfs_analytic_duration(graph,config))
                            bound=(len(graph)+nx.number_connected_components(graph)+1)/(2*config['sample_rate'])
                            if residual>bound+1e-12:raise AssertionError('DFS duration formula failed')
                            if condition!='original' and abs(features['duration_sec']-baseline[mode]['duration_sec'])>1/config['sample_rate']:
                                raise AssertionError('DFS duration invariant failed')
                        if condition=='original':baseline[mode]=features
                        rows.append({'seed':seed,'layer':layer,'mode':mode,'condition':condition,'replicate':replicate,
                            'topology_changed':edge_set(graph)!=edge_set(original),
                            'backbone_components':nx.number_connected_components(graph),'backbone_edges':graph.number_of_edges(),
                            'forest_weight_sum':sum(d['weight'] for _,_,d in graph.edges(data=True)),
                            'bfs_frontier_count':len(frontiers),'bfs_max_frontier_width':max(map(len,frontiers)),
                            **{k:features[k] for k in ACOUSTIC+['stereo_correlation']}})
                render(original,'original',0)
                for condition_id,condition in enumerate(['weight_shuffle','tree_shuffle']):
                    for replicate in range(args.replicates):
                        rng=np.random.default_rng(np.random.SeedSequence([args.random_seed,seed,layer,condition_id,replicate]))
                        render(controlled_forest(original,condition,rng),condition,replicate)
            print(f'Completed seed {seed}',flush=True)
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    data=pd.DataFrame(rows);data.to_csv(out/'control_features.csv',index=False)
    keys=['seed','layer','mode'];base=data[data.condition=='original'][keys+ACOUSTIC+['stereo_correlation']]
    pairs=data[data.condition!='original'].merge(base,on=keys,validate='many_to_one',suffixes=('','_original'))
    contrasts=[]
    seeds=np.sort(data.seed.unique());boot=np.random.default_rng(args.random_seed).integers(0,len(seeds),(args.bootstrap,len(seeds)))
    for feature in ACOUSTIC+['stereo_correlation']:
        pairs['difference_'+feature]=pairs[feature]-pairs[feature+'_original']
        for (condition,mode),group in pairs.groupby(['condition','mode']):
            # Average controls within each state, selected layers within each seed, then resample seeds.
            delta=group.groupby(['seed','layer'])['difference_'+feature].mean().groupby('seed').mean().reindex(seeds).to_numpy()
            ci=np.quantile(delta[boot].mean(axis=1),[.025,.975])
            contrasts.append({'condition':condition,'mode':mode,'feature':feature,'n_seeds':len(seeds),
                              'mean_control_minus_original':delta.mean(),'ci_low':ci[0],'ci_high':ci[1]})
    pairs.to_csv(out/'control_differences.csv',index=False)
    pd.DataFrame(contrasts).to_csv(out/'control_seed_summary.csv',index=False)
    changed=data[data.condition=='tree_shuffle'].groupby(['seed','layer']).topology_changed.mean()
    changed.to_csv(out/'fraction_topology_changed.csv')
    (out/'methods.json').write_text(json.dumps({'status':'Synthetic renderer-input controls; not new quantum states',
        'seeds':seeds.tolist(),'layers':selected,'replicates_per_condition':args.replicates,
        'random_seed':args.random_seed,'bootstrap':args.bootstrap,
        'sonification_sha256':hashlib.sha256(engine_path.read_bytes()).hexdigest(),
        'extractor_sha256':hashlib.sha256(extractor_path.read_bytes()).hexdigest(),
        'source_hashes':source_hashes,'notes':[
        'weight_shuffle changes weight placement on the same tree.',
        'tree_shuffle changes labeled adjacency and weight placement; it preserves component node sets and weight multisets.',
        'Controls are not required to be realizable as quantum MI matrices.',
        'Singleton and two-node components cannot change topology; their controls are retained and counted.',
        'Intervals are pointwise descriptive; control replicates do not increase independent sample size.',
        'Only temporary WAVs are generated; full quantum simulation is not rerun.']},indent=2))
    print(json.dumps({'seeds':len(seeds),'renders':len(data),'output_dir':str(out)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo-dir',required=True);p.add_argument('--runs-dir',required=True)
    p.add_argument('--output-dir',required=True);p.add_argument('--layers',type=int,nargs='+',default=[2,3,6,10])
    p.add_argument('--replicates',type=int,default=5);p.add_argument('--max-seeds',type=int)
    p.add_argument('--bootstrap',type=int,default=5000);p.add_argument('--random-seed',type=int,default=20261004)
    run(p.parse_args())
