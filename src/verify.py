"""Fast verification of the checked-in model; no data download or training."""
import json, subprocess, io
import numpy as np
from data import ROOT

def main():
    (ROOT/'build').mkdir(exist_ok=True)
    cmd=['gcc','-std=c99','-O2','-Wall','-Wextra','-Werror','-pedantic','-Iembedded',
         'embedded/engine_guard.c','embedded/replay.c','-lm','-o','build/replay']
    subprocess.run(cmd,cwd=ROOT,check=True)
    subprocess.run([str(ROOT/'build/replay'),'--selftest'],check=True)
    a=np.load(ROOT/'models/model.npz'); rng=np.random.default_rng(123)
    # Synthetic physically plausible points; not raw benchmark redistribution.
    u=np.tile([.01,150,105000,10,300,.5],(200,1))
    u[:,0]=rng.uniform(.003,.025,200);u[:,1]=rng.uniform(100,250,200)
    x=np.c_[u,np.vstack([u[0],u[:-1]]),u[:,0]*u[:,4]/u[:,1]]
    z=(x-a['mean'])/a['scale']
    for i in range(3):
        z=z@(a[f'w{i}']*a['scales'][i])+a[f'b{i}']
        if i<2:z=np.maximum(0,z)
    expected=np.clip(z.ravel()*a['ys']+a['ym']+a['physics'][0]*x[:,12]+a['physics'][1],10000,250000)
    s=io.StringIO();np.savetxt(s,np.c_[u,np.ones(200)*50000],fmt='%.9g')
    r=subprocess.run([str(ROOT/'build/replay')],input=s.getvalue(),text=True,capture_output=True,check=True)
    c=np.loadtxt(io.StringIO(r.stdout));mask=c[:,2]==0
    assert mask.sum()>100
    error=float(abs(c[mask,0]-expected[mask]).max());assert error<2.,error
    print(f'Synthetic Python/C parity: {error:.4f} Pa maximum, {mask.sum()} valid vectors')
    return error
if __name__=='__main__':main()
