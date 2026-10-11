"""Small positive/negative controls on the original engine, not a new engine."""
from pathlib import Path
import argparse, importlib.util, json, sys
import numpy as np
import networkx as nx

def run(repo,output):
    sys.path.insert(0,str(Path(repo).resolve()/'src'))
    import simulations as q
    import sonification as s
    cfg=s.DEFAULT_CONFIG; results={}
    n=3
    plus=np.zeros(2**n,complex);plus[0]=plus[-1]=1/np.sqrt(2)
    minus=plus.copy();minus[-1]*=-1
    b1=q.get_bloch_data_from_statevector(plus,n);b2=q.get_bloch_data_from_statevector(minus,n)
    g1,m1=q.build_mutual_information_graph(plus,n);g2,m2=q.build_mutual_information_graph(minus,n)
    f1=q.build_sonification_backbone(g1);f2=q.build_sonification_backbone(g2)
    a1=s.render_layer_audio(f1,b1,1,cfg);a2=s.render_layer_audio(f2,b2,1,cfg)
    assert np.allclose(m1,m2,atol=1e-12)
    assert all(np.array_equal(a1[k],a2[k]) for k in ['bfs','dfs'])
    results['GHZ_phase_collision']={'n_qubits':n,'state_fidelity':float(abs(np.vdot(plus,minus))**2),
        'MI_max_abs_difference':float(np.max(abs(m1-m2))),'BFS_DFS_identical_samples':True,
        'interpretation':'Orthogonal states can produce exactly the same audio. Full-state inverse is impossible.'}
    signal=np.sin(np.linspace(0,60,4000))
    correlations=[]
    for phi in [.2,np.pi,6.1]:
        a=s.phi_to_equal_power_pan(signal,phi)
        correlations.append(float(np.corrcoef(a.T)[0,1]))
    assert max(abs(x-1) for x in correlations)<1e-12
    results['single_voice_channel_correlation']={'phi':[.2,float(np.pi),6.1],'correlations':correlations,
        'interpretation':'Channel Pearson does not identify pan position.'}
    epsilon=1e-9
    gains1=s.phi_to_equal_power_pan(np.ones(1),epsilon)[0]
    gains2=s.phi_to_equal_power_pan(np.ones(1),2*np.pi-epsilon)[0]
    results['azimuth_seam']={'epsilon_rad':epsilon,'equatorial_Bloch_distance':float(2*np.sin(epsilon)),
        'stereo_gain_distance':float(np.linalg.norm(gains1-gains2))}
    theta=1e-6
    st1=np.array([np.cos(theta/2),np.sin(theta/2)],complex)
    st2=np.array([np.cos(theta/2),-np.sin(theta/2)],complex)
    pole1=q.get_bloch_data_from_statevector(st1,1);pole2=q.get_bloch_data_from_statevector(st2,1)
    results['near_pole']={'theta_rad':theta,'state_fidelity':float(abs(np.vdot(st1,st2))**2),
        'radius':pole1['r'].tolist(),'azimuths_rad':[float(pole1['phi'][0]),float(pole2['phi'][0])],
        'interpretation':'Radius weighting does not suppress azimuth instability at a pure pole.'}
    # Two connected four-node trees, same weights but different adjacency.
    graphs=[]
    for edges in [[(0,1,.1),(1,2,.7),(2,3,1.2)],[(0,1,1.2),(0,2,.1),(0,3,.7)]]:
        g=nx.Graph();g.add_nodes_from(range(4));g.add_weighted_edges_from(edges);graphs.append(g)
    b={'r':np.array([1,.8,.4,.2]),'theta':np.linspace(.2,2.8,4),'phi':np.linspace(.3,5.9,4),
       'linear_entropy':1-np.array([1,.8,.4,.2])**2}
    lengths=[len(s.render_dfs(g,b,0,cfg)) for g in graphs]
    assert lengths[0]==lengths[1]
    analytic=.3+3*.6-.25*2
    assert abs(lengths[0]/cfg['sample_rate']-analytic)<4/(2*cfg['sample_rate'])+1e-12
    results['DFS_weight_multiset_timing_invariance']={'sample_counts':lengths,'analytic_duration_sec':analytic,
        'BFS_sample_counts':[len(s.render_bfs(g,b,0,cfg)) for g in graphs]}
    out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo-dir',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();run(a.repo_dir,a.output)
