# Root review of the RNA execution component

Accepted the scoped execution component after reading all five production
modules, all four owned test modules, HANDOFF.md, INTERFACES_001.md, original
verification receipts and the native artifacts listed in NATIVE_PATHS.txt.
This accepts execution and retention, not the unfinished complete episode path.

check003 actually passed 268 tests: 101 producer tests plus 167 overlapping
pure-component tests. Its bounded lifecycle receipt reports exit 0 and stable
source pins during execution, with 20 GiB memory, 4 GiB scratch and no wall cap.
The later tool-information wording change from "readers" to "native-output
parsers" is explicitly recorded in HANDOFF.md; the run is not represented as
having tested that later text. No repeated broad test was requested for it.

Root directly inspected the retained actual ViennaRNA 2.7.0 records:

* `GGGAAACCC`, `(((...)))`: prediction and supplied-structure evaluation each
  preserve native energy -1.2000000476837158 kcal/mol in their distinct fields.
* The explicit 25 C, dangles=1, noGU model preserves evaluated energy
  -2.140000104904175 kcal/mol and its actual selected/effective settings.
* The GAC/(.) native evaluation preserves the raw 100000.0 native return in
  diagnostics, reports failed energy rather than treating the sentinel as a
  scientific measurement, and retains the valid supplied topology.
* Effective native parameter bytes are retained: 250833 bytes, SHA-256
  9521527a251d5e68e6149595f8aa72aa72c63e00dc5af41d7164e6ecaa664777.

Root checked original/staged operand separation, software identity, explicit
model parameters, rejected-input byte retention, reserved output paths,
sealed replay and unsealed-attempt behavior. Preparation does not start work;
the selected start uses the shared durable native lifecycle. No separate
decision loop, implicit retry or database search was introduced.

Limits remain explicit: native verification uses the isolated retained test
installation, not a claim of general resource deployment. This lane implements
the agreed single-sequence noncrossing modes. It does not implement native
partition-function uncertainty, structural comparisons, perturbation scans,
new presentation, complete registered episode returns or annotation scoring.
358 and 360 still own their separate results/integration work. The user's new
question-dependent comparison direction is recorded verbatim in
349/USER_DIRECTION_009.md and remains additional unfinished RNA work. Neither
RNA tool is counted complete by this review.
