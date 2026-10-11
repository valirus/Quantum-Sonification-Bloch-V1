"""Verify the continuous physical-state certificate without circuit dependencies.
Optional --render uses the unchanged archived renderer and quantum extractor.
"""
from pathlib import Path
from itertools import combinations
import argparse,hashlib,json,sys
import numpy as np
import pandas as pd
p=argparse.ArgumentParser();p.add_argument('--render',action='store_true');p.add_argument('--output-dir',default='reproduction_results/physical_family');a=p.parse_args()
root=Path(__file__).resolve().parents[1];out=root/a.output_dir
if out.exists():raise FileExistsError('Use a new output directory.')
out.mkdir(parents=True)
N=15;ix=np.arange(2**N,dtype=np.uint32);internal=np.zeros((N,N),dtype=np.uint8)
for cycle in [list(range(7)),list(range(7,15))]:
 for i,j in zip(cycle,cycle[1:]+cycle[:1]):internal[i,j]=internal[j,i]=1
witness=[]
for k in [1,2]:
 for keep in combinations(range(N),k):
  for f in range(1,k+1):
   for flip in combinations(keep,f):
    odd=np.bitwise_xor.reduce(internal[list(flip)],axis=0);partners={i+7 if i<7 else i-7 for i in flip if i!=14}
    candidates=[w for w in range(N) if w not in keep and odd[w] and w not in partners]
    assert candidates,(keep,flip)
    witness.append({'keep':';'.join(map(str,keep)),'flip':';'.join(map(str,flip)),'witness_bit':candidates[0]})
assert len(witness)==330
pd.DataFrame(witness).to_csv(out/'cancellation_witnesses.csv',index=False)
def state(phases):
 parity=np.zeros(len(ix),dtype=np.uint32)
 for i,j in zip(*np.triu(internal,1).nonzero()):parity^=((ix>>int(i))&1)&((ix>>int(j))&1)
 phase=sum(v*(((ix>>i)&1)&((ix>>(7+i))&1)) for i,v in enumerate(phases))
 return ((1-2*parity.astype(float))*np.exp(1j*phase))/np.sqrt(2**N)
def rdm(v,keep):
 axes=[N-1-i for i in keep];other=[i for i in range(N)if i not in axes]
 m=v.reshape([2]*N).transpose(axes+other).reshape(2**len(keep),-1);return m@m.conj().T
if a.render:
 sys.path.insert(0,str(root/'reproducibility/frozen_source'))
 import simulations as quantum
 import sonification as audio_engine
cases=[(f'common_t_{t}',np.repeat(np.pi*t,7))for t in [0,.025,.1,.25,.5,.75,.9,.975,1]]
rng=np.random.default_rng(20261005)
cases += [(f'heterogeneous_{i}',rng.uniform(-4*np.pi,4*np.pi,7))for i in range(8)]
rows=[];base=None
for name,phases in cases:
 v=state(phases);one=max(np.max(abs(rdm(v,[i])-np.eye(2)/2))for i in range(15));two=max(np.max(abs(rdm(v,[i,j])-np.eye(4)/4))for i,j in combinations(range(15),2))
 axes=[N-1-i for i in range(7)];other=[i for i in range(N)if i not in axes];sv=np.linalg.svd(v.reshape([2]*N).transpose(axes+other).reshape(128,256),compute_uv=False)**2;sv=sv[sv>0];entropy=float(-np.sum(sv*np.log2(sv)))
 prob=np.sin(phases/4)**2;theory=0.
 for q in [prob,1-prob]:
  q=q[q>0];theory-=float(np.sum(q*np.log2(q)))
 row={'case':name,'single_error':float(one),'pair_error':float(two),'entropy':entropy,'formula':theory,'entropy_error':abs(entropy-theory)}
 assert one<1e-12 and two<1e-12 and abs(entropy-theory)<1e-12
 if a.render:
  descriptors=quantum.get_bloch_data_from_statevector(v,N);graph,mi=quantum.build_mutual_information_graph(v,N);forest=quantum.build_sonification_backbone(graph);waves=audio_engine.render_layer_audio(forest,descriptors,7,audio_engine.DEFAULT_CONFIG)
  if base is None:base=waves
  for mode in ['bfs','dfs','combined']:
   assert np.array_equal(waves[mode],base[mode]);row[mode+'_samples_sha256']=hashlib.sha256(waves[mode].tobytes()).hexdigest()
 rows.append(row)
pd.DataFrame(rows).to_csv(out/'numeric_checks.csv',index=False)
report={'status':'PASS','states':len(rows),'symbolic_cases':330,'max_single_error':max(r['single_error']for r in rows),'max_pair_error':max(r['pair_error']for r in rows),'max_entropy_error':max(r['entropy_error']for r in rows),'renderer_executed':a.render,'scope':'External physical family, final snapshot; not RQC holdout.'}
(out/'receipt.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
