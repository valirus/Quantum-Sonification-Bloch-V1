#!/usr/bin/env bash
# Run from the project root; writes separate reproduction outputs, never synthesis changes.
set -euo pipefail
export OPENBLAS_NUM_THREADS=1
python - <<'PY'
from pathlib import Path
from zipfile import ZipFile
root=Path('reproducibility/reproduction_inputs')
if root.exists(): raise FileExistsError('Preserve the previous reproduction folder; choose a fresh extraction before rerunning.')
root.mkdir(parents=True)
with ZipFile('reproducibility/input_evidence.zip') as z:
 for name in z.namelist():
  assert (root/name).resolve().is_relative_to(root.resolve()),name
 z.extractall(root)
PY
python reproducibility/recheck_primary.py
python reproducibility/recheck_secondary.py
python reproducibility/recheck_closeout.py
python reproducibility/verify_physical_family.py
