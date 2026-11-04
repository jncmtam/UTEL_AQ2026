# Manual CPU recovery: transport frozen numerical financial coefficients

Date: 2026-11-04. Recorded before a second CPU evaluation. All eight GPU responses
completed normally. First CPU evaluation stopped at strict Hamiltonian equality;
its exception, dispatch and charged reservation remain preserved. No model failure
or financial outcome is inferred. No GPU retry is authorized or needed here.

Local reconstruction still exactly matches the prepared private-input hash. The
failure is consistent with platform-dependent floating-point reduction in R.T@R
or R.T@b, which changes coefficient bits and therefore a cryptographic hash. This
cause must be quantified in the recovery certificate, not merely assumed.

Fix: carry the locally frozen quadratic financial statistics alongside the original
full Hamiltonian. Bind them to the original raw-data FinancialSpec fingerprint.
Independently compare frozen statistics with the remote reconstruction using
rtol1e-12/atol1e-18 and report the maximum differences. Reject larger discrepancies,
wrong shapes/nonfinite values or bad hashes. Execute the exact frozen coefficients;
do not round or silently substitute a newly reconstructed Hamiltonian.

A numerical FinancialSpec adapter inherits the existing financial constraints and
data identity but returns the validated frozen quadratic statistics. Its numerical
certificate is separately hashed and bound in the recovery-input manifest. The
ordinary compiler must then reproduce the original Hamiltonian bit-for-bit. Existing
quantum verifier's exact canonical-compilation check remains unchanged. No tolerance
is introduced for accepting a changed Hamiltonian. Allocation uses the same frozen
statistics and remains independently rescored from those coefficients.

Test small floating-point transport differences, rejected financial changes and
wrong hashes, exact post-bind Hamiltonian reproduction and unchanged financial
fingerprint. Preserve all first-attempt artifacts. Manually deploy the diagnosed
CPU fix, then one separately named CPU evaluation under live_guidance_v1_eval2.
Reuse all eight existing model outputs/requests. No prompt/architecture/seed changes,
model escalation, new inference or automatic paid retries. Same original ten-USD
total reservation envelope, with both failed and recovery CPU reservations counted.

Record current source hashes and new private-input hash before dispatch, maximum
platform discrepancies/canonical identities per case, and outcome/financial audit.
If the frozen statistics fail checks or exact compiler identity still fails, stop
and report. This is engineering recovery, not another chance to improve model scores.
