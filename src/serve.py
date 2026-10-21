"""Local replay dashboard. Predictions are produced by the compiled C executable."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import json
from pathlib import Path
from pipeline import run_c, ROOT, TARGET

CACHE={}
SCENARIOS={'nominal':'ftp75city2_NF.csv','pressure_bias':'ftp75city2_f_pim_115.csv',
           'airflow_bias':'ftp75city2_f_waf_115.csv','intercooler_bias':'ftp75city2_f_pic_115.csv'}
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kw):super().__init__(*args,directory=str(ROOT/'dashboard'),**kw)
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path=='/api/replay':
            key=parse_qs(parsed.query).get('scenario',['nominal'])[0]
            if key not in SCENARIOS:self.send_error(400);return
            if key not in CACHE:
                d,c=run_c(SCENARIOS[key])
                CACHE[key]={'source':SCENARIOS[key],
                    'frames':[[round(float(t),3),round(float(p)/1000,3),round(float(row[0])/1000,3),
                               int(row[2]),int(row[3])] for t,p,row in zip(d.time,d[TARGET],c)]}
            b=json.dumps(CACHE[key]).encode();self.send_response(200)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)))
            self.end_headers();self.wfile.write(b);return
        if parsed.path=='/api/metrics':
            b=(ROOT/'reports/metrics.json').read_bytes();self.send_response(200)
            self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b);return
        super().do_GET()
if __name__=='__main__':
    print('EngineGuard: http://127.0.0.1:8765 (Ctrl+C to stop)',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
