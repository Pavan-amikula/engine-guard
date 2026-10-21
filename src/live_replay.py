"""Pace real recorded samples at 20 Hz while executing C inference per sample.

This is a desktop soft real-time replay experiment, not a hard real-time ECU task.
"""
import argparse,subprocess,time,json
from data import ROOT,load,SIGNALS,TARGET

def main():
    p=argparse.ArgumentParser();p.add_argument('--file',default='ftp75city2_f_pim_115.csv')
    p.add_argument('--start',type=float,default=120);p.add_argument('--duration',type=float,default=40)
    a=p.parse_args()
    if a.start<0 or a.duration<=0:p.error('start must be non-negative and duration positive')
    d=load(a.file);process=subprocess.Popen([str(ROOT/'build/replay')],stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,text=True,bufsize=1)
    begin=None;calls=0;roundtrips=[];lateness=[]
    try:
        for _,row in d.iterrows():
            t=float(row.time)
            if t>a.start+a.duration:break
            if t>=a.start:
                if begin is None:begin=time.perf_counter();first_t=t
                deadline=begin+(t-first_t)
                wait=deadline-time.perf_counter()
                if wait>0:time.sleep(wait)
                lateness.append(max(0,time.perf_counter()-deadline))
            started=time.perf_counter()
            process.stdin.write(' '.join(f'{float(row[s]):.9g}' for s in [*SIGNALS,TARGET])+'\n')
            process.stdin.flush();line=process.stdout.readline()
            if not line:raise RuntimeError('C replay process stopped unexpectedly')
            predicted,residual,status,alarm=line.split()
            if t>=a.start:
                calls+=1;roundtrips.append(time.perf_counter()-started)
                if calls%20==1:
                    print(f'{t:7.2f}s | sensor {row[TARGET]/1000:6.1f} kPa | C virtual {float(predicted)/1000:6.1f} kPa | status {status} | alarm {alarm}',flush=True)
    finally:
        process.stdin.close();process.wait(timeout=5);process.stdout.close()
    if process.returncode:raise RuntimeError(f'C process exit {process.returncode}')
    if not calls:raise RuntimeError('No samples in requested recording interval')
    print(json.dumps({'paced_samples':calls,'recording_hz':20,'elapsed_s':time.perf_counter()-begin,
          'max_host_wakeup_lateness_ms':max(lateness)*1000,
          'mean_ipc_and_inference_ms':sum(roundtrips)/calls*1000,
          'note':'Desktop pacing and IPC measurements; not ECU WCET or guaranteed deadlines.'},indent=2))
if __name__=='__main__':main()
