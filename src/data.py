"""Download source recordings without redistributing third-party raw data."""
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://vehsys.gitlab-pages.liu.se/dx_benchmarks/liuice/competition/trainingdata/trainingdata.zip'
TARGET = 'intake_manifold_pressure'
# Inputs exclude the target and its history. Units follow the source recordings.
SIGNALS = ['air_mass_flow', 'engine_speed', 'Intercooler_pressure',
           'throttle_position', 'intercooler_temperature', 'wastegate_position']

def fetch(archive=None):
    (ROOT / 'reports').mkdir(parents=True, exist_ok=True)
    raw = ROOT / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    archive = Path(archive) if archive else raw / 'trainingdata.zip'
    if not archive.exists():
        print('Downloading LiU-ICE archive (~61 MB)...', flush=True)
        with urllib.request.urlopen(URL, timeout=120) as response, archive.open('wb') as out:
            while block := response.read(1024 * 1024):
                out.write(block)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = ROOT / 'reports/data_manifest.json'
    if manifest.exists():
        expected = json.loads(manifest.read_text()).get('sha256')
        if expected and digest != expected:
            raise ValueError('Source archive differs from the recorded experiment hash. Preserve the existing manifest and review the upstream revision before starting a new experiment.')
    with zipfile.ZipFile(archive) as z:
        for member in z.namelist():
            if member.startswith('trainingdata/') and member.endswith(('.csv', '_fault_time.txt')):
                (raw / Path(member).name).write_bytes(z.read(member))
    (ROOT / 'reports/data_manifest.json').write_text(json.dumps({
        'url': URL, 'sha256': digest, 'archive_bytes': archive.stat().st_size,
        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(raw.glob('*.csv'))},
        'split': {'train': 'wltp_NF.csv', 'validation': 'wltp_NF_2.csv',
                  'test': 'ftp75city2_NF.csv', 'fault_test': 'ftp75city2_f_*.csv'},
        'note': 'Public benchmark training archive; project-defined holdout, not hidden competition test.'
    }, indent=2))

def load(name):
    return pd.read_csv(ROOT / 'data/raw' / name)

def physics_feature(d):
    # Speed-density inspired regressor; coefficient fitted on train only.
    return d.air_mass_flow.to_numpy() * d.intercooler_temperature.to_numpy() / np.maximum(d.engine_speed.to_numpy(), 1)

def features(d):
    a = d[SIGNALS].to_numpy()
    # One causal delay, reset to first input at the start of every independent run.
    return np.c_[a, np.vstack([a[0], a[:-1]]), physics_feature(d)]

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--archive'); a=p.parse_args(); fetch(a.archive)
