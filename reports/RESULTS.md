# Measured evaluation

Project-defined whole-recording holdout, evaluated on 21 October 2026. This is not the competition hidden test set.

| Model | Test MAE (kPa) | Test RMSE (kPa) | R² |
|---|---:|---:|---:|
| speed_density | 4.937 | 6.109 | 0.8623 |
| ridge | 4.039 | 5.381 | 0.8932 |
| float_mlp | 1.486 | 2.100 | 0.9837 |
| int16_storage_mlp | 1.486 | 2.100 | 0.9837 |
| deployed_guarded_c | 1.486 | 2.100 | 0.9837 |

The guarded C estimator reduces RMSE by **65.6%** against the speed-density baseline on this recording. All 17,423 nominal test samples were within the training-derived envelope. No post-startup alarms occurred on this nominal test recording (samples after 10 s). This does not imply a zero population false-alarm rate.

Training: 36,068 samples from `wltp_NF.csv`. Validation: 36,183 from `wltp_NF_2.csv`. Test: 17,423 from `ftp75city2_NF.csv`. No target pressure or target history enters the estimator. Candidate architectures were 13→16→8→1, 13→24→12→1, and 13→32→16→1, selected solely on validation RMSE. All candidates used a fixed 180-epoch optimization budget and reported convergence warnings; optimal convergence is not claimed. No architecture or alarm threshold was changed after observing the final holdout.

## Deployment evidence

- Selected 13→24→12→1 residual ReLU network: 612 stored weights, 37 biases; 649 parameters total.
- Parameters: 1,372 bytes with int16 weights + float32 biases versus 2,596 bytes with float32 weights + biases (**47.1% lower parameter storage**).
- Normalization + envelope arrays: another 152 bytes; scales/physical baseline/monitor scalar constants and executable code are additional.
- Host compiled object: 3,412 bytes text/read-only section; no static mutable data/BSS in that object. This is not a linked target flash figure.
- Caller state: 36 bytes on the host ABI. Activation arrays use 144 nominal bytes; compiler per-function static stack estimates are in `stack_usage.txt`. These estimates are not a measured stack high-water mark or complete nested-call/target stack budget.
- Five batches of 1,000,000 C estimator + monitor calls: median batch mean **1.128 μs/call** on Windows-11-10.0.26300-SP0, Intel64 Family 6 Model 140 Stepping 1, GenuineIntel, gcc.exe (MinGW.org GCC-6.3.0-1) 6.3.0, `-O2`. The published Windows run used a 32-bit executable. Timing excludes CSV I/O. This is neither per-call p99 nor WCET, and does not establish ECU schedulability.
- C versus Python quantized inference: maximum absolute difference **0.0944 Pa** over valid nominal test inputs.
- Quantized versus original float inference: maximum absolute difference **3.914 Pa**. Inference arithmetic remains floating point.
- C edge checks cover NaN inputs, zero speed, missing pressure, out-of-envelope fallback, one-step OOD-history recovery, sustained bias, and explicit reset. Synthetic 200-vector parity also passes below 2 Pa.

## Complete independent fault replay

Monitor: residual = measured − estimated pressure; EWMA α=0.05; alarm threshold 6.386 kPa derived from nominal validation 99.5th percentile absolute filtered residual after startup; 10 consecutive samples above threshold. Alarm clears as soon as the condition clears. Approximate filter time constant is 0.975 s at 20 Hz. This conservative global threshold favors few nuisance alarms over small-bias sensitivity.

The delay is to the first alarm after the documented fault time. Alarm fraction is the fraction of all post-fault samples flagged, not classification accuracy. A brief first alarm does not imply sustained detection. Pre-fault fractions exclude the first 10 s. These residuals do not isolate root cause.

| Independent recording | First alarm delay (s) | Post-fault alarm fraction | Pre-fault alarm fraction |
|---|---:|---:|---:|
| ftp75city2_f_pic_085.csv | 1.06 | 98.85% | 0.00% |
| ftp75city2_f_pic_090.csv | 1.06 | 93.31% | 0.00% |
| ftp75city2_f_pic_095.csv | 3.91 | 10.38% | 0.00% |
| ftp75city2_f_pic_105.csv | 5.46 | 34.28% | 0.00% |
| ftp75city2_f_pic_110.csv | 25.96 | 57.52% | 0.00% |
| ftp75city2_f_pic_115.csv | 24.06 | 58.49% | 0.00% |
| ftp75city2_f_pim_085.csv | 21.21 | 22.41% | 0.00% |
| ftp75city2_f_pim_090.csv | 23.76 | 7.10% | 0.00% |
| ftp75city2_f_pim_095.csv | No alarm | 0.00% | 0.00% |
| ftp75city2_f_pim_105.csv | 140.81 | 0.06% | 0.00% |
| ftp75city2_f_pim_110.csv | 23.16 | 3.58% | 0.00% |
| ftp75city2_f_pim_115.csv | 21.21 | 14.89% | 0.00% |
| ftp75city2_f_waf_085.csv | 78.11 | 0.51% | 0.18% |
| ftp75city2_f_waf_090.csv | 67.71 | 0.43% | 0.00% |
| ftp75city2_f_waf_095.csv | 143.02 | 0.32% | 0.00% |
| ftp75city2_f_waf_105.csv | 143.27 | 0.05% | 0.00% |
| ftp75city2_f_waf_110.csv | 35.41 | 0.01% | 0.00% |
| ftp75city2_f_waf_115.csv | 35.61 | 0.22% | 0.00% |

For the +15% manifold-pressure fault, the virtual estimate has 1.396 kPa MAE relative to the bias-corrected pressure reference, versus 5.165 kPa for the biased sensor. This reference assumes the benchmark's multiplicative fault law and the documented onset time; it is not a second independent hardware sensor. The first alarm is delayed by 21.21 s and only 14.89% of post-fault samples exceed the conservative criterion. The −5% manifold fault is missed and +5% sensitivity is weak. Airflow faults are particularly difficult because airflow is also an estimator input. These are open engineering limitations, not grounds to claim an operational fault-tolerant controller.

## Reproduction and limits

Run `python src/verify.py` for the existing-model C checks. Run the complete pipeline for data-based evidence. Source archive checksums and file-level split details are in `data_manifest.json`; model/source hashes are in `metrics.json`. The provider may revise the archive, so compare hashes before comparing experiments. Raw data and generated replay CSV are excluded from Git; charts summarize recorded evidence.

Acceptance budgets checked by the pipeline: nominal C RMSE <3 kPa, improvement over the baseline, parameters <2 KiB, and valid-input C/Python parity <2 Pa. These budgets are portfolio targets, not Volvo requirements. Model quality and timing may vary with software and hardware. Simulink execution, TargetLink execution, target flash/RAM/stack and PIL/HIL remain unverified. The engine data is spark-ignition research data and cannot establish transfer to a Volvo heavy-duty diesel platform. No emissions, fuel-efficiency or closed-loop stability improvement is measured.
