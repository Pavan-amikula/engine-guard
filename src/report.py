import json,hashlib
import numpy as np
from data import ROOT
root=ROOT
m=json.loads((root/'reports/metrics.json').read_text())
m['source_sha256']={str(p.relative_to(root)).replace(chr(92),'/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'embedded/engine_guard.c',root/'embedded/engine_guard.h',root/'embedded/model_data.h',root/'models/model.npz']}
(root/'reports/metrics.json').write_text(json.dumps(m,indent=2))
rm=m['test']['deployed_guarded_c']['rmse_kpa'];base=m['test']['speed_density']['rmse_kpa'];reduction=(1-rm/base)*100
bench=np.median([r['mean_us'] for r in m['deployment']['benchmark_runs']])
object_bytes=int((root/'reports/object_size.txt').read_text().splitlines()[1].split()[0])
report=f'''# Measured evaluation

Project-defined whole-recording holdout, evaluated on 21 October 2026. This is not the competition hidden test set.

| Model | Test MAE (kPa) | Test RMSE (kPa) | R² |
|---|---:|---:|---:|
'''
for k,v in m['test'].items():report+=f"| {k} | {v['mae_kpa']:.3f} | {v['rmse_kpa']:.3f} | {v['r2']:.4f} |\n"
report+=f'''
The guarded C estimator reduces RMSE by **{reduction:.1f}%** against the speed-density baseline on this recording. All {m['rows']['test']:,} nominal test samples were within the training-derived envelope. No post-startup alarms occurred on this nominal test recording (samples after 10 s). This does not imply a zero population false-alarm rate.

Training: {m['rows']['train']:,} samples from `wltp_NF.csv`. Validation: {m['rows']['validation']:,} from `wltp_NF_2.csv`. Test: {m['rows']['test']:,} from `ftp75city2_NF.csv`. No target pressure or target history enters the estimator. Candidate architectures were 13→16→8→1, 13→24→12→1, and 13→32→16→1, selected solely on validation RMSE. All candidates used a fixed 180-epoch optimization budget and reported convergence warnings; optimal convergence is not claimed. No architecture or alarm threshold was changed after observing the final holdout.

## Deployment evidence

- Selected 13→24→12→1 residual ReLU network: 612 stored weights, 37 biases; 649 parameters total.
- Parameters: 1,372 bytes with int16 weights + float32 biases versus 2,596 bytes with float32 weights + biases (**47.1% lower parameter storage**).
- Normalization + envelope arrays: another 152 bytes; scales/physical baseline/monitor scalar constants and executable code are additional.
- Host compiled object: {object_bytes:,} bytes text/read-only section; no static mutable data/BSS in that object. This is not a linked target flash figure.
- Caller state: 36 bytes on the host ABI. Activation arrays use 144 nominal bytes; compiler per-function static stack estimates are in `stack_usage.txt`. These estimates are not a measured stack high-water mark or complete nested-call/target stack budget.
- Five batches of 1,000,000 C estimator + monitor calls: median batch mean **{bench:.3f} μs/call** on {m['deployment']['host']}, {m['deployment']['processor']}, {m['deployment']['compiler']}, `-O2`. The published Windows run used a 32-bit executable. Timing excludes CSV I/O. This is neither per-call p99 nor WCET, and does not establish ECU schedulability.
- C versus Python quantized inference: maximum absolute difference **{m['deployment']['c_python_max_abs_diff_pa_in_domain']:.4f} Pa** over valid nominal test inputs.
- Quantized versus original float inference: maximum absolute difference **{m['deployment']['quantization_max_abs_diff_pa']:.3f} Pa**. Inference arithmetic remains floating point.
- C edge checks cover NaN inputs, zero speed, missing pressure, out-of-envelope fallback, one-step OOD-history recovery, sustained bias, and explicit reset. Synthetic 200-vector parity also passes below 2 Pa.

## Complete independent fault replay

Monitor: residual = measured − estimated pressure; EWMA α=0.05; alarm threshold {m['deployment']['alarm_threshold_pa']/1000:.3f} kPa derived from nominal validation 99.5th percentile absolute filtered residual after startup; 10 consecutive samples above threshold. Alarm clears as soon as the condition clears. Approximate filter time constant is 0.975 s at 20 Hz. This conservative global threshold favors few nuisance alarms over small-bias sensitivity.

The delay is to the first alarm after the documented fault time. Alarm fraction is the fraction of all post-fault samples flagged, not classification accuracy. A brief first alarm does not imply sustained detection. Pre-fault fractions exclude the first 10 s. These residuals do not isolate root cause.

| Independent recording | First alarm delay (s) | Post-fault alarm fraction | Pre-fault alarm fraction |
|---|---:|---:|---:|
'''
for r in m['fault_runs']:
    delay='No alarm' if r['first_alarm_delay_s'] is None else f"{r['first_alarm_delay_s']:.2f}"
    report+=f"| {r['file']} | {delay} | {r['post_fault_alarm_fraction']:.2%} | {r['pre_fault_alarm_fraction']:.2%} |\n"
report+='''
For the +15% manifold-pressure fault, the virtual estimate has 1.396 kPa MAE relative to the bias-corrected pressure reference, versus 5.165 kPa for the biased sensor. This reference assumes the benchmark's multiplicative fault law and the documented onset time; it is not a second independent hardware sensor. The first alarm is delayed by 21.21 s and only 14.89% of post-fault samples exceed the conservative criterion. The −5% manifold fault is missed and +5% sensitivity is weak. Airflow faults are particularly difficult because airflow is also an estimator input. These are open engineering limitations, not grounds to claim an operational fault-tolerant controller.

## Reproduction and limits

Run `python src/verify.py` for the existing-model C checks. Run the complete pipeline for data-based evidence. Source archive checksums and file-level split details are in `data_manifest.json`; model/source hashes are in `metrics.json`. The provider may revise the archive, so compare hashes before comparing experiments. Raw data and generated replay CSV are excluded from Git; charts summarize recorded evidence.

Acceptance budgets checked by the pipeline: nominal C RMSE <3 kPa, improvement over the baseline, parameters <2 KiB, and valid-input C/Python parity <2 Pa. These budgets are portfolio targets, not Volvo requirements. Model quality and timing may vary with software and hardware. Simulink execution, TargetLink execution, target flash/RAM/stack and PIL/HIL remain unverified. The engine data is spark-ignition research data and cannot establish transfer to a Volvo heavy-duty diesel platform. No emissions, fuel-efficiency or closed-loop stability improvement is measured.
'''
(root/'reports/RESULTS.md').write_text(report,encoding='utf8')
print('Final measured RMSE',rm,'reduction',reduction,'median host us',bench)
