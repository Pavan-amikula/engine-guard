"""Render a narrated-by-captions demonstration from actual C replay output."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio
from data import ROOT

def font(size):
    for name in ['C:/Windows/Fonts/segoeui.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(name).exists():return ImageFont.truetype(name,size)
    return ImageFont.load_default(size=size)

def main():
    m=json.loads((ROOT/'reports/metrics.json').read_text());d=pd.read_csv(ROOT/'reports/demo_replay.csv')
    rec=next(r for r in m['fault_runs'] if r['file']=='ftp75city2_f_pim_115.csv')
    onset=rec['fault_onset_s'];fps=15;seconds=36;frames=[]
    writer=imageio.get_writer(ROOT/'media/demo.mp4',fps=fps,codec='libx264',quality=7,macro_block_size=16)
    try:
        for n in range(fps*seconds):
            pos=n/fps
            # Accelerated view of 80-210 s around actual recorded fault onset.
            t=80+(pos/seconds)*130;idx=int(np.searchsorted(d.time_s,t));idx=min(idx,len(d)-1);r=d.iloc[idx]
            im=Image.new('RGB',(1280,720),'#0b1522');draw=ImageDraw.Draw(im)
            def txt(x,y,text,size=22,color='#e6edf5'):draw.text((x,y),text,font=font(size),fill=color)
            txt(48,28,'EMBEDDED ML  /  REAL ENGINE TEST-BENCH DATA',17,'#49d9bf')
            txt(48,62,'EngineGuard',44);txt(48,122,'Intake manifold pressure virtual sensor | host-compiled C replay',22,'#a5b8cc')
            status='Disagreement alarm' if r.alarm else 'Baseline fallback' if r.status else 'ML estimate valid'
            cols=[('RECORDING TIME',f'{r.time_s:.2f} s'),('PRESSURE SENSOR',f'{r.measured_kpa:.1f} kPa'),('VIRTUAL SENSOR',f'{r.virtual_kpa:.1f} kPa'),('MONITOR',status)]
            for j,(label,value) in enumerate(cols):
                x=48+j*300;draw.rounded_rectangle((x,174,x+280,270),radius=10,fill='#142539')
                txt(x+16,186,label,14,'#9aacc0');txt(x+16,218,value,24 if j<3 else 20,'#ffaf64' if r.alarm and j==3 else '#e6edf5')
            left,right,top,bottom=95,1215,315,540
            for v in range(0,181,30):
                y=bottom-v/180*(bottom-top);draw.line((left,y,right,y),fill='#263c50');txt(48,y-10,str(v),15,'#8da4bc')
            part=d[(d.time_s>=80)&(d.time_s<=t)]
            for key,color in [('measured_kpa','#ffaf64'),('virtual_kpa','#42d6b9')]:
                pts=[(left+(rr.time_s-80)/130*(right-left),bottom-rr[key]/180*(bottom-top)) for _,rr in part.iloc[::2].iterrows()]
                if len(pts)>1:draw.line(pts,fill=color,width=2)
            x=left+(onset-80)/130*(right-left);draw.line((x,top,x,bottom),fill='#d96161',width=2)
            txt(x+7,top+5,'+15% pressure-sensor fault',16,'#ffaf64')
            txt(left,bottom+10,'80 s',15,'#8da4bc');txt(right-48,bottom+10,'210 s',15,'#8da4bc')
            txt(65,575,'Measured',18,'#ffaf64');txt(200,575,'C virtual estimate',18,'#42d6b9')
            caption=('Independent FTP75 recording. Target pressure is excluded from model inputs.' if pos<10 else
                     'A real recorded sensor fault changes the signal and affects engine feedback.' if pos<22 else
                     'Filtered residual + persistence detects disagreement; this does not isolate the fault.' if pos<30 else
                     f"Held-out RMSE {m['test']['deployed_guarded_c']['rmse_kpa']:.2f} kPa | {m['deployment']['parameter_bytes_int16']} parameter bytes | inspect reports/metrics.json")
            txt(48,620,caption,20);txt(48,674,'Accelerated recorded-data replay. Desktop execution; ECU timing and proprietary-tool integration remain unverified.',15,'#849bb3')
            writer.append_data(np.asarray(im))
            if n%15==0:frames.append(im.resize((768,432)))
        frames[0].save(ROOT/'media/demo.gif',save_all=True,append_images=frames[1:],duration=1000,loop=0,optimize=True)
        frames[16].save(ROOT/'media/demo_poster.png')
    finally:writer.close()
    print('Rendered media/demo.mp4 and media/demo.gif from reports/demo_replay.csv')
if __name__=='__main__':main()
