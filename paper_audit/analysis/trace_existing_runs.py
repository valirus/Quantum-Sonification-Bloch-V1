"""Observe the frozen renderer from saved MI/Bloch inputs; never write in runs.

Exports exact event sample boundaries and note controls. Optional WAV verification
re-renders with the ORIGINAL module and compares samples; no new quantum state.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json
import networkx as nx
import numpy as np
import pandas as pd
from scipy.io import wavfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_engine(repo):
    path = Path(repo) / 'src/sonification.py'
    spec = importlib.util.spec_from_file_location('observed_frozen_engine', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, path


def forest_from_matrix(matrix, tolerance):
    n = len(matrix)
    if matrix.shape != (n, n) or not np.isfinite(matrix).all():
        raise ValueError('Invalid MI matrix')
    if not np.allclose(matrix, matrix.T, atol=1e-10, rtol=0):
        raise ValueError('Asymmetric MI matrix')
    if not np.allclose(np.diag(matrix), 0, atol=1e-10):
        raise ValueError('Nonzero MI diagonal')
    if matrix.min() < -1e-10 or matrix.max() > 2+1e-10:
        raise ValueError('MI outside [0,2] bits')
    graph = nx.Graph()
    graph.add_nodes_from(range(n))
    for i in range(n):
        for j in range(i+1, n):
            if matrix[i,j] > tolerance:
                graph.add_edge(i, j, weight=float(matrix[i,j]))
    return graph, nx.maximum_spanning_tree(graph, weight='weight')


def trace_layer(engine, forest, bloch, root, cfg):
    """Call original traversal helpers; reproduce sample rounding, not sound."""
    fs = int(cfg['sample_rate'])
    events, notes = [], []
    for mode in ['bfs', 'dfs']:
        cursor = 0
        groups = (engine.weighted_bfs_frontiers(forest, root) if mode == 'bfs'
                  else [([] if x is None else [x]) for x in engine.weighted_dfs_events(forest, root)])
        for event_id, group in enumerate(groups):
            weights = [float(w) for _, w in group if w > 0]
            weight = float(np.mean(weights)) if weights else 0.0
            duration = (cfg['component_gap_sec'] if not group else
                        cfg['root_duration_sec'] if not weights else
                        engine.mutual_information_to_duration(weight, cfg))
            samples = max(1, int(round(fs*duration)))
            events.append(dict(mode=mode, event_id=event_id, is_gap=not bool(group),
                               start_sample=cursor, end_sample=cursor+samples,
                               start_sec=cursor/fs, end_sec=(cursor+samples)/fs,
                               event_duration_sec=samples/fs, incoming_MI_used=weight,
                               frontier_width=len(group)))
            for node, incoming in group:
                r = float(bloch['r'][node])
                theta, phi = float(bloch['theta'][node]), float(bloch['phi'][node])
                neutral = r <= cfg['bloch_direction_epsilon']
                effective_theta = np.pi/2 if neutral else theta
                effective_phi = np.pi if neutral else phi
                pan = float(np.mod(effective_phi, 2*np.pi)/(2*np.pi))
                g_l, g_r = np.cos(pan*np.pi/2), np.sin(pan*np.pi/2)
                transverse = float(np.hypot(bloch['x'][node], bloch['y'][node]))
                raw_seam_distance = float(min(np.mod(phi,2*np.pi), 2*np.pi-np.mod(phi,2*np.pi)))
                notes.append(dict(mode=mode, event_id=event_id, qubit=int(node),
                    incoming_MI_individual=float(incoming), start_sample=cursor, end_sample=cursor+samples,
                    frontier_width=len(group), mix_divisor=len(group) if mode=='bfs' else 1,
                    x=float(bloch['x'][node]), y=float(bloch['y'][node]), z=float(bloch['z'][node]),
                    r=r, theta_raw=theta, phi_raw=phi, theta_used=effective_theta, phi_used=effective_phi,
                    frequency_hz=engine.theta_to_frequency(effective_theta,cfg),
                    amplitude_before_envelope=cfg['voice_gain']*(cfg['amplitude_floor']+(1-cfg['amplitude_floor'])*r),
                    normalized_linear_entropy=float(bloch['linear_entropy'][node]),
                    AM_depth=cfg['am_depth_max']*float(bloch['linear_entropy'][node]),
                    AM_rate_hz=cfg['am_rate_hz'], gain_left=float(g_l), gain_right=float(g_r),
                    gain_energy_sum=float(g_l*g_l+g_r*g_r),
                    gain_energy_balance_R_minus_L=float(g_r*g_r-g_l*g_l),
                    attack_fraction=cfg['attack_fraction_bfs' if mode=='bfs' else 'attack_fraction_dfs'],
                    neutral_direction=bool(neutral), transverse_radius=transverse,
                    near_pole=bool(transverse<=1e-8), seam_distance_rad=raw_seam_distance,
                    near_seam=bool(raw_seam_distance<=1e-8 and transverse>1e-8)))
            cursor += samples
    return events, notes


def run(args):
    repo, runs, out = map(lambda x:Path(x).resolve(), [args.repo_dir,args.runs_dir,args.output_dir])
    if out == runs or runs in out.parents:
        raise ValueError('Keep trace output outside the original runs directory')
    if out.exists() and any(out.iterdir()):
        raise FileExistsError('Choose a NEW output directory; traces are never overwritten')
    engine, engine_path = load_engine(repo)
    if args.engine_sha256 and sha(engine_path) != args.engine_sha256:
        raise ValueError('Renderer SHA-256 differs from the frozen source')
    paths = sorted(runs.glob('seed_*/metadata.json'))
    if args.seeds is not None:
        selected = set(args.seeds)
        paths = [p for p in paths if int(json.loads(p.read_text())['seed']) in selected]
        if len(paths) != len(selected):
            raise ValueError('Some requested seeds have no metadata.json')
    if args.max_seeds is not None: paths = paths[:args.max_seeds]
    if not paths: raise ValueError('No saved runs found; a summary CSV is insufficient')
    all_events, all_notes, all_edges, summaries, sources = [], [], [], [], []
    seen = set()
    for path in paths:
        meta = json.loads(path.read_text()); seed = int(meta['seed']); run_dir = path.parent
        if seed in seen: raise ValueError('Duplicate seed')
        seen.add(seed); cfg = meta['audio_config']; n = int(meta['num_qubits'])
        if cfg != engine.DEFAULT_CONFIG: raise ValueError('Saved configuration differs from the frozen renderer')
        bpath = run_dir/'bloch_descriptors.csv'; b = pd.read_csv(bpath)
        if b.duplicated(['seed','layer','qubit']).any() or set(b.seed)!={seed}:
            raise ValueError('Invalid Bloch identities')
        sources += [dict(seed=seed,file='metadata.json',sha256=sha(path)),
                    dict(seed=seed,file='bloch_descriptors.csv',sha256=sha(bpath))]
        layers = sorted(set(args.layers)) if args.layers else list(range(int(meta['layers'])+1))
        for layer in layers:
            sub=b[b.layer==layer].sort_values('qubit')
            if sub.qubit.tolist()!=list(range(n)): raise ValueError('Incomplete qubit snapshot')
            bloch={k:sub[k].to_numpy() for k in ['x','y','z','r','theta','phi','linear_entropy']}
            if not np.isfinite(np.column_stack(list(bloch.values()))).all():raise ValueError('Invalid Bloch data')
            mpath=run_dir/'mutual_information_matrices'/f'mi_layer_{layer:02d}.npy'
            matrix=np.load(mpath,allow_pickle=False)
            if matrix.shape!=(n,n):raise ValueError('Wrong MI dimension')
            full,forest=forest_from_matrix(matrix,float(meta['edge_tolerance']))
            sources.append(dict(seed=seed,layer=layer,file=mpath.name,sha256=sha(mpath)))
            events,notes=trace_layer(engine,forest,bloch,int(meta['preferred_root']),cfg)
            all_events += [dict(seed=seed,layer=layer,**r) for r in events]
            all_notes += [dict(seed=seed,layer=layer,**r) for r in notes]
            all_edges += [dict(seed=seed,layer=layer,qubit_a=i,qubit_b=j,MI_bits=float(matrix[i,j]),
                               above_tolerance=bool(matrix[i,j]>meta['edge_tolerance']),in_forest=forest.has_edge(i,j))
                          for i in range(n) for j in range(i+1,n)]
            c=nx.number_connected_components(forest); W=sum(d['weight'] for _,_,d in forest.edges(data=True))
            analytic=c*cfg['root_duration_sec']+(n-c)*cfg['event_duration_max_sec']-(cfg['event_duration_max_sec']-cfg['event_duration_min_sec'])*W/2+(c-1)*cfg['component_gap_sec']
            lengths={mode:max(r['end_sample'] for r in events if r['mode']==mode) for mode in ['bfs','dfs']}
            residual=lengths['dfs']/cfg['sample_rate']-analytic
            if abs(residual)>(n+c)/(2*cfg['sample_rate'])+1e-12:raise AssertionError('DFS timing identity failed')
            row=dict(seed=seed,layer=layer,forest_components=c,forest_edges=forest.number_of_edges(),
                     full_graph_edges=full.number_of_edges(),forest_weight_sum=W,
                     DFS_duration_analytic_sec=analytic,DFS_rounding_residual_sec=residual,
                     BFS_duration_trace_sec=lengths['bfs']/cfg['sample_rate'],
                     DFS_duration_trace_sec=lengths['dfs']/cfg['sample_rate'],wav_checked=False)
            if args.verify_wav:
                audio=engine.render_layer_audio(forest,bloch,int(meta['preferred_root']),cfg)
                for mode in ['bfs','dfs']:
                    wpath=run_dir/'audio'/mode/f'layer_{layer:02d}.wav'
                    fs,stored=wavfile.read(wpath)
                    if fs!=cfg['sample_rate'] or stored.shape!=audio[mode].shape:raise AssertionError('WAV timing/shape mismatch')
                    delta=float(np.max(np.abs(stored.astype(float)-audio[mode].astype(float))))
                    row[mode+'_WAV_max_abs_error']=delta
                    if delta>args.wave_tolerance:raise AssertionError(f'WAV replay mismatch {seed}/{layer}/{mode}: {delta}')
                    sources.append(dict(seed=seed,layer=layer,file=str(wpath.relative_to(run_dir)),sha256=sha(wpath)))
                row['wav_checked']=True
            summaries.append(row)
        print(f'Traced seed {seed}',flush=True)
    out.mkdir(parents=True,exist_ok=True)
    for name,rows in [('events',all_events),('notes',all_notes),('edges',all_edges),('summary',summaries)]:
        pd.DataFrame(rows).to_csv(out/(name+'.csv'),index=False)
    (out/'provenance.json').write_text(json.dumps(dict(engine_sha256=sha(engine_path),
        seeds=sorted(seen),source_hashes=sources,verify_wav=args.verify_wav,wave_tolerance=args.wave_tolerance,
        near_pole_and_seam_threshold=1e-8,notes=['Observer calls original traversal helpers and renderer.',
        'No original file or engine source was modified.','Event times are samples within one layer WAV.',
        'Pole/seam flags are diagnostic thresholds, not exclusions.','Notes list synth controls, not perceived loudness.']),indent=2))
    print(json.dumps(dict(seeds=len(seen),snapshots=len(summaries),output_dir=str(out))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo-dir',required=True);p.add_argument('--runs-dir',required=True)
    p.add_argument('--output-dir',required=True);p.add_argument('--seeds',type=int,nargs='+');p.add_argument('--max-seeds',type=int)
    p.add_argument('--layers',type=int,nargs='+');p.add_argument('--engine-sha256')
    p.add_argument('--verify-wav',action='store_true');p.add_argument('--wave-tolerance',type=float,default=1e-7)
    a=p.parse_args()
    if a.max_seeds is not None and a.max_seeds<1:raise ValueError('max-seeds must be positive')
    if a.wave_tolerance<0:raise ValueError('wave-tolerance must be nonnegative')
    run(a)
