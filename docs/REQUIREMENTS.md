# Requirements and evidence matrix

These are project acceptance criteria derived from the supplied thesis description, not requirements issued by Volvo.

| ID | Requirement | Implementation / evidence | Status |
|---|---|---|---|
| R1 | Concrete embedded engine application | Manifold pressure virtual sensor on real LiU-ICE data | Verified host prototype |
| R2 | Develop and compare ML model | Three residual network candidates; baseline and ridge comparison | Verified |
| R3 | Integrate learned model with physics-based approach | Fitted speed-density predictor plus residual correction | Verified |
| R4 | Measure generalization | Entire FTP75 recording held out; no pressure target/history as inputs | Verified, one engine |
| R5 | Constrain parameter storage <2 KiB | 1,372 parameter bytes; extra constants separately reported | Passed |
| R6 | Nominal test RMSE <3 kPa and below baseline | 2.100 vs 6.109 kPa | Passed |
| R7 | Portable C, no inference heap allocation | Fixed arrays, caller-owned state, GCC strict warnings | Passed on host |
| R8 | Numerical equivalence <2 Pa | Recorded and synthetic Python/C comparisons | Passed |
| R9 | Demonstrate computational performance | Five million-call host batches with compiler/environment | Measured; target timing open |
| R10 | Reject invalid inputs and handle OOD | NaN/zero-speed checks, fallback, delayed-input recovery | Verified |
| R11 | Demonstrate recorded fault handling | Eighteen independent FTP75 fault runs and complete metrics | Verified; limited sensitivity |
| R12 | Fit existing model-based workflow | 50 ms contract, C Caller generation script, golden traces | Prepared; MATLAB execution open |
| R13 | TargetLink compatibility approach | External-code handoff, types, scaling, verification contract | Prepared; licensed tool test open |
| R14 | Maintainability and reproducibility | Model artifact, dependency pins, source/data hashes, CI | Local run verified; remote CI separate |
| R15 | Recruiter-visible results and demo | README, plots, GIF, MP4, local interactive replay | Delivered |

Deployment beyond a host prototype requires a chosen ECU, target compiler and linker map, measured stack/RAM/flash, interrupt-aware cycle timing, PIL/HIL, and a controlled closed-loop validation plan. None of those are inferred from desktop speed. The benchmark engine is not a Volvo production powertrain, and its measurements do not demonstrate heavy-duty diesel transfer.
