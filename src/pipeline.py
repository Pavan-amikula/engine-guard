"""Train on one recording, select on another, evaluate on untouched FTP75 runs."""
import json, platform, subprocess, shutil, time, sys, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.neural_network import MLPRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from data import ROOT, SIGNALS, TARGET, features, physics_feature, load

REPORT=ROOT/'reports'; MODEL=ROOT/'models'; BUILD=ROOT/'build'
def metrics(y,p):
    return {'mae_kpa':float(mean_absolute_error(y,p)/1000),
            'rmse_kpa':float(np.sqrt(mean_squared_error(y,p))/1000),
            'p95_abs_error_kpa':float(np.quantile(abs(y-p),.95)/1000),'r2':float(r2_score(y,p))}

def array(name,x,ctype='float'):
    x=np.asarray(x).ravel()
    vals=','.join(str(int(v)) if ctype=='int16_t' else f'{float(v):.9e}f' for v in x)
    return f'static const {ctype} {name}[{len(x)}]={{'+vals+'};\n'

def export(model,scaler,ym,ys,pa,pb,lo,hi,threshold):
    weights=[]; scales=[]
    for w in model.coefs_:
        scale=max(abs(w).max()/32767,1e-12)
        weights.append(np.rint(w/scale).astype(np.int16));scales.append(scale)
    h1,h2=model.hidden_layer_sizes
    text='#ifndef MODEL_DATA_H\n#define MODEL_DATA_H\n#include <stdint.h>\n'
    text+=f'#define EG_H1 {h1}\n#define EG_H2 {h2}\n'
    for key,val in dict(YM=ym,YS=ys,PHYS_A=pa,PHYS_B=pb,ALARM_THRESHOLD=threshold,
                        S1=scales[0],S2=scales[1],S3=scales[2]).items():
        text+=f'#define {key} ({float(val):.9e}f)\n'
    for key,val in [('XM',scaler.mean_),('XS',scaler.scale_),('LO',lo),('HI',hi)]:text+=array(key,val)
    for i in range(3):text+=array(f'W{i+1}',weights[i],'int16_t')+array(f'B{i+1}',model.intercepts_[i])
    text+='#endif\n';(ROOT/'embedded/model_data.h').write_text(text)
    np.savez(MODEL/'model.npz',**{f'w{i}':weights[i] for i in range(3)},
             **{f'b{i}':model.intercepts_[i] for i in range(3)},scales=scales,
             mean=scaler.mean_,scale=scaler.scale_,ym=ym,ys=ys,physics=[pa,pb],lo=lo,hi=hi,
             threshold=threshold)
    def predict(x):
        a=scaler.transform(x)
        for i in range(3):
            a=a@(weights[i]*scales[i])+model.intercepts_[i]
            if i<2:a=np.maximum(a,0)
        return a.ravel()*ys+ym+pa*x[:,12]+pb
    return predict, sum(w.nbytes for w in weights)+sum(b.size*4 for b in model.intercepts_),sum(w.size*4 for w in weights)+sum(b.size*4 for b in model.intercepts_)

def run_c(name):
    d=load(name); inp=np.c_[d[SIGNALS].to_numpy(),d[TARGET].to_numpy()]
    import io
    text=io.StringIO();np.savetxt(text,inp,fmt='%.9g')
    r=subprocess.run([str(BUILD/'replay')],input=text.getvalue(),text=True,capture_output=True,check=True)
    return d,np.loadtxt(io.StringIO(r.stdout),ndmin=2)

def fault_times():
    out={}
    for p in (ROOT/'data/raw').glob('*_fault_time.txt'):
        for line in p.read_text().splitlines()[1:]:
            name,t=line.split();out[name.replace('fiml','f_iml')+'.csv']=float(t)
    return out

def main():
    for p in [REPORT,MODEL,BUILD,ROOT/'media']:p.mkdir(exist_ok=True,parents=True)
    train,val=load('wltp_NF.csv'),load('wltp_NF_2.csv')
    x,xv=features(train),features(val);y=train[TARGET].to_numpy();yv=val[TARGET].to_numpy()
    pa,pb=np.linalg.lstsq(np.c_[x[:,12],np.ones(len(x))],y,rcond=None)[0]
    residual=y-pa*x[:,12]-pb;ym=residual.mean();ys=residual.std()
    scaler=StandardScaler().fit(x);xt=scaler.transform(x);xvt=scaler.transform(xv)
    candidates=[];best=None
    for hidden in [(16,8),(24,12),(32,16)]:
        print('Training',hidden,flush=True)
        model=MLPRegressor(hidden_layer_sizes=hidden,activation='relu',max_iter=180,
                           learning_rate_init=.001,batch_size=256,alpha=.01,random_state=42,
                           early_stopping=False,n_iter_no_change=25,tol=1e-5)
        model.fit(xt,(residual-ym)/ys)
        p=model.predict(xvt)*ys+ym+pa*xv[:,12]+pb
        score=metrics(yv,p);candidates.append({'hidden':list(hidden),'iterations':model.n_iter_,**score})
        if best is None or score['rmse_kpa']<best[0]:best=(score['rmse_kpa'],model)
    model=best[1]
    # Envelope is train min/max plus 25% span; no test-derived bounds.
    a=train[SIGNALS].to_numpy();span=np.maximum(np.ptp(a,axis=0),1e-6)
    lo=a.min(axis=0)-.25*span;hi=a.max(axis=0)+.25*span
    # Freeze a validation-derived two-sided threshold for the deployed EWMA detector.
    fp=model.predict(xvt)*ys+ym+pa*xv[:,12]+pb
    smooth=pd.Series(yv-fp).ewm(alpha=.05,adjust=False).mean().to_numpy()
    threshold=max(2500.,float(np.quantile(abs(smooth[200:]),.995)))
    quant,stored,fpbytes=export(model,scaler,ym,ys,pa,pb,lo,hi,threshold)
    compiler=shutil.which('gcc')
    if not compiler:raise RuntimeError('Install GCC and put it on PATH.')
    command=[compiler,'-std=c99','-O2','-Wall','-Wextra','-Werror','-pedantic',
             '-fstack-usage','-Iembedded','embedded/engine_guard.c','embedded/replay.c','-lm','-o','build/replay']
    subprocess.run(command,cwd=ROOT,check=True)
    subprocess.run([compiler,'-std=c99','-O2','-Iembedded','-c','embedded/engine_guard.c','-o','build/engine_guard.o'],cwd=ROOT,check=True)
    # Final test is evaluated only after architecture and threshold are frozen.
    test=load('ftp75city2_NF.csv');xx=features(test);yy=test[TARGET].to_numpy()
    ridge=Ridge(alpha=1.).fit(xt,y)
    pred=model.predict(scaler.transform(xx))*ys+ym+pa*xx[:,12]+pb
    quantp=quant(xx)
    d,c=run_c('ftp75city2_NF.csv')
    in_domain=c[:,2]==0
    maxdiff=float(abs(c[in_domain,0]-np.clip(quantp[in_domain],10000,250000)).max())
    assert maxdiff<2.,f'C/Python parity exceeded 2 Pa: {maxdiff}'
    # Fault magnitude ground truth provides an approximate sensor-unbiased reference;
    # actual faulty control behaviour is present, so do not score against nominal replay.
    faults=[];times=fault_times();demo=None
    for p in sorted((ROOT/'data/raw').glob('ftp75city2_f_*.csv')):
        df,cc=run_c(p.name);tt=df.time.to_numpy();onset=times[p.name]
        after=tt>=onset;before=(tt>=10)&(tt<onset);events=np.where(after&(cc[:,3]>0))[0]
        rec={'file':p.name,'fault_onset_s':onset,'post_fault_alarm_fraction':float(np.mean(cc[after,3])),
             'pre_fault_alarm_fraction':float(np.mean(cc[before,3])),
             'first_alarm_delay_s':float(tt[events[0]]-onset) if len(events) else None,
             'ood_fraction':float(np.mean(cc[:,2]==1))}
        if '_f_pim_' in p.name:
            factor=int(p.stem.split('_')[-1])/100
            reference=df[TARGET].to_numpy().copy();reference[after]/=factor
            rec['corrected_reference_mae_kpa']=float(np.mean(abs(reference[after]-cc[after,0]))/1000)
            rec['sensor_bias_mae_kpa']=float(np.mean(abs(reference[after]-df[TARGET].to_numpy()[after]))/1000)
        faults.append(rec)
        if p.name=='ftp75city2_f_pim_115.csv':demo=(df,cc,onset)
    # Deterministic tests of defensive behaviour, reset and sustained bias detection.
    nominal=np.array([.01,150,105000,10,300,.5])
    def rows_run(rows):
        import io
        s=io.StringIO();np.savetxt(s,rows)
        r=subprocess.run([str(BUILD/'replay')],input=s.getvalue(),capture_output=True,text=True,check=True)
        return np.loadtxt(io.StringIO(r.stdout),ndmin=2)
    estimate=rows_run([np.r_[nominal,50000]])[0,0]
    rr=rows_run([np.r_[nominal,estimate]]*250+[np.r_[nominal,estimate+20000]]*250)
    assert rr[:250,3].sum()==0 and rr[-1,3]==1
    assert rows_run([[.01,0,105000,10,300,.5,50000]])[0,2]==2
    assert rows_run([[1,150,105000,10,300,.5,50000]])[0,2]==1
    subprocess.run([str(BUILD/'replay'),'--selftest'],check=True)
    bench=[json.loads(subprocess.check_output([str(BUILD/'replay'),'--benchmark'],text=True)) for _ in range(5)]
    size=subprocess.check_output(['size','build/engine_guard.o'],cwd=ROOT,text=True)
    (REPORT/'object_size.txt').write_text(size)
    stack='\n'.join(p.read_text() for p in BUILD.glob('*.su'))
    (REPORT/'stack_usage.txt').write_text(stack or 'This host compiler did not emit stack-usage files. Target stack measurement remains pending.\n')
    result={'dataset':'LiU-ICE public training archive; project-defined whole-recording split',
            'rows':{'train':len(train),'validation':len(val),'test':len(test)},
            'seed':42,'selected_hidden':list(model.hidden_layer_sizes),'candidates_validation':candidates,
            'test':{'speed_density':metrics(yy,pa*xx[:,12]+pb),'ridge':metrics(yy,ridge.predict(scaler.transform(xx))),
                    'float_mlp':metrics(yy,pred),'int16_storage_mlp':metrics(yy,quantp),
                    'deployed_guarded_c':metrics(yy,c[:,0])},
            'deployment':{'parameter_bytes_int16':stored,'parameter_bytes_float32':fpbytes,
                          'normalization_bounds_bytes':(13*2+6*2)*4,
                          'c_python_max_abs_diff_pa_in_domain':maxdiff,
                          'quantization_max_abs_diff_pa':float(abs(quantp-pred).max()),
                          'nominal_ood_fraction':float(np.mean(c[:,2]==1)),
                          'nominal_alarm_fraction_after_10s':float(np.mean(c[d.time.to_numpy()>=10,3])),
                          'alarm_threshold_pa':threshold,'benchmark_runs':bench,
                          'benchmark_note':'Host clock() batch mean including monitor; not WCET or ECU timing.',
                          'compiler':subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],
                          'host':platform.platform(),'processor':platform.processor(),'python':sys.version.split()[0]},
            'checks':{'c_python_parity':True,'sustained_bias_alarm':True,'nominal_no_alarm_unit_case':True,
                      'nan_input_rejected':True,'zero_speed_rejected':True,'ood_fallback':True,'nan_sensor_rejected':True},
            'fault_runs':faults}
    assert result['test']['deployed_guarded_c']['rmse_kpa']<3.0
    assert result['test']['deployed_guarded_c']['rmse_kpa']<result['test']['speed_density']['rmse_kpa']
    assert stored<2048
    (REPORT/'metrics.json').write_text(json.dumps(result,indent=2))
    df,cc,onset=demo
    pd.DataFrame({'time_s':df.time,'measured_kpa':df[TARGET]/1000,'virtual_kpa':cc[:,0]/1000,
                  'residual_kpa':cc[:,1]/1000,'status':cc[:,2].astype(int),'alarm':cc[:,3].astype(int)}).to_csv(REPORT/'demo_replay.csv',index=False)
    plot(result,test,c,demo)
    subprocess.run([sys.executable,str(ROOT/'src/report.py')],cwd=ROOT,check=True)
    print(json.dumps({k:v for k,v in result.items() if k in ['selected_hidden','test','checks']},indent=2))

def plot(result,test,c,demo):
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(2,1,figsize=(12,7),layout='constrained')
    t=test.time.to_numpy();ax[0].plot(t,test[TARGET]/1000,label='Measured',lw=1.1,color='#34495e')
    ax[0].plot(t,c[:,0]/1000,label='Deployed C virtual sensor',lw=.9,color='#008f86')
    ax[0].set(ylabel='Pressure (kPa)',title='Untouched FTP75 city cycle | real engine test bench');ax[0].legend()
    names=['Speed density','Ridge','Float MLP','Int16 storage','Guarded C']
    values=[v['rmse_kpa'] for v in result['test'].values()]
    ax[1].barh(names,values,color=['#a6b5c5','#a6b5c5','#00a99d','#007e77','#116466'])
    ax[1].set(xlabel='RMSE (kPa)',title='Held-out recording | lower is better')
    fig.savefig(ROOT/'media/validation.png',dpi=160);plt.close(fig)
    df,cc,onset=demo;t=df.time.to_numpy();factor=1.15
    reference=df[TARGET].to_numpy().copy();reference[t>=onset]/=factor
    fig,axes=plt.subplots(3,1,figsize=(12,8),sharex=True,layout='constrained')
    axes[0].plot(t,df[TARGET]/1000,label='Pressure sensor (+15% after fault)',color='#f48c42',lw=1)
    axes[0].plot(t,reference/1000,label='Bias-corrected reference',color='#45556b',lw=1)
    axes[0].plot(t,cc[:,0]/1000,label='C virtual sensor',color='#008f86',lw=.8)
    axes[0].set(ylabel='Pressure (kPa)',title='Pressure fault replay | independent FTP75 recording');axes[0].legend(fontsize=9,ncol=3)
    axes[1].plot(t,cc[:,1]/1000,color='#8c57b5',lw=.8);axes[1].set(ylabel='Residual (kPa)')
    axes[2].fill_between(t,0,cc[:,3],color='#df5252',label='Sustained disagreement alarm');axes[2].set(ylabel='Alarm',xlabel='Recording time (s)');axes[2].legend()
    for ax in axes:ax.axvline(onset,color='#df5252',ls='--',lw=1)
    fig.savefig(ROOT/'media/fault_replay.png',dpi=160);plt.close(fig)

if __name__=='__main__': main()
