# EngineGuard: project text for a resume-writing chat

## Copy-ready context

Project: **EngineGuard — Embedded Machine Learning for Engine Air-Path Development**

Repository: https://github.com/Pavan-amikula/engine-guard

Built a reproducible engine-control development prototype that estimates intake manifold pressure using other engine operating signals. The project uses measured LiU-ICE turbocharged-engine test-bench recordings at approximately 20 Hz, combines a fitted speed-density baseline with a compact residual neural network, exports quantized model parameters to portable C, and evaluates the implementation through host-compiled replay and an interactive dashboard. The purpose is to demonstrate the practical development chain from data and model selection to inspectable embedded inference and model-based integration preparation.

Used entire independent recordings for training, validation and final testing: 36,068 training samples, 36,183 validation samples, and 17,423 nominal test samples, plus 18 independent fault recordings. Excluded manifold-pressure measurements and target history from model inputs. Selected a 13→24→12→1 ReLU network on validation data, using causal current/delayed features and train-only normalization. Compared against a speed-density baseline and ridge regression.

On the final nominal FTP75 test recording, achieved **2.100 kPa RMSE, 1.486 kPa MAE and R²=0.9837**, reducing RMSE by **65.6%** against the **6.109 kPa** speed-density baseline. Exported 612 int16 weights and 37 float32 biases, totaling **1,372 parameter bytes**, a **47.1% reduction** from float32 parameter storage. Quantization changes predictions by at most 3.915 Pa on the nominal test recording; the C implementation differs from the Python quantized reference by at most **0.095 Pa** on valid inputs.

Implemented finite-input checks, physical validity checks, training-envelope checks, baseline fallback, explicit caller-owned state, a filtered pressure residual, and persistence-based disagreement monitoring. Verified invalid-input handling, reset, sustained-bias response and out-of-envelope history recovery. Measured a median of five batch-mean timings of **1.128 μs/call**, each batch containing one million C estimator/monitor calls, on the documented Windows desktop using MinGW GCC 6.3.0 and `-O2`. This is host timing, not ECU WCET. Inference uses floating-point arithmetic with int16 weight storage, not integer-only computation.

Created a 50 ms integration contract, a Simulink C Caller harness-generation script and a TargetLink external-code handoff guide. MATLAB/Simulink execution, TargetLink execution, ECU deployment, PIL/HIL, complete target RAM/flash/stack measurement and closed-loop control are **not verified**. The portfolio demonstrates host software-in-the-loop style numerical replay; avoid implying certified or vendor-tool SIL completion.

Built a local Python/HTML/JavaScript dashboard that runs compiled C over nominal and sensor-fault recordings and supports replay, seek, speed controls and diagnostic-state visualization. Produced a captioned 36-second MP4, animated GIF, validation plots, per-fault metrics, dataset/source SHA-256 manifests and a GitHub Actions reproduction workflow. Related research and dataset attribution remain in the repository.

## Resume bullets

- Developed a physics-guided engine manifold-pressure virtual sensor using real 20 Hz test-bench data; achieved **2.10 kPa held-out RMSE** and **65.6% lower error** than a speed-density baseline using whole-recording validation.
- Exported a **649-parameter residual neural network** to allocation-free C with int16 weight storage, reducing parameter memory by **47.1% to 1.34 KiB** while maintaining **<0.095 Pa Python/C deviation** on valid test inputs.
- Implemented input validation, domain guards, baseline fallback and residual-based monitoring; evaluated **18 independent sensor-fault recordings**, documented detection limits, and delivered an interactive C replay dashboard and video demonstration.
- Prepared **Simulink C Caller and TargetLink external-code integration artifacts**, including a 50 ms scheduling contract, numerical verification, provenance manifests and reproducible CI tooling.

## Relevant keywords

Embedded machine learning; engine control development; control engineering; automotive embedded software; powertrain; model-based development; virtual sensing; system identification; physics-guided residual learning; speed-density estimation; air-path dynamics; transient engine data; Python; NumPy; pandas; scikit-learn; C99; GCC; model deployment; int16 weight quantization; floating-point inference; memory footprint; software-in-the-loop style replay; back-to-back numerical verification; fault injection; EWMA residual monitoring; out-of-distribution detection; fallback strategy; fixed-step execution; Simulink C Caller; TargetLink external-code integration preparation; Git; GitHub Actions; reproducibility; requirement traceability.

## Claims to preserve accurately

This is an independent portfolio prototype based on public research measurements, not employment at Volvo or a completed Volvo thesis. Do not claim production ECU deployment, verified TargetLink/Simulink execution, integer-only inference, AUTOSAR/MISRA/ISO 26262 compliance, closed-loop stability, emissions/fuel savings, comprehensive fault isolation, or official competition results. The conservative monitor misses the −5% manifold fault and has weak sensitivity to some other faults. One-engine generalization is limited. Do not invent a multi-month development history or hardware experience.

## Interview preparation

Be ready to explain why adjacent-row random splits inflate time-series performance; why pressure itself is excluded from features; why a residual model helps a baseline; how per-layer quantization scales are applied; what memory figures omit; why mean desktop timing does not establish real-time deadlines; how faulty estimator inputs can undermine diagnosis; and how to validate an external C component through model, host and target stages. Reproduce the commands and inspect the source before presenting implementation details as personal experience.
