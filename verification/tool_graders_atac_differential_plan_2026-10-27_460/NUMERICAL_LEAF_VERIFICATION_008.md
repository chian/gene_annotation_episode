# Verified numerical leaf, not a completed ATAC tool

`calculate_atac_interval_scores` now implements contract004 as an ordinary pure
function. It retains native inputs, explicit depth factors, adjusted values,
unrounded likelihoods and their separate native-compatible float32 values.
Source joins, parsing, actual coordinates and region calculations remain
separate responsibilities. No episode, annotation-credit rule or resource
choice was added by this component.

The original bounded math001 job finished terminal/quiescent with exit0:
36 tests passed in0.05s; measured service wall0.960209404s. The unit was
`gene-local-job-74337f374f014925b9da44f98a2f6b43.service`. Original source and
interpreter/runner pins were unchanged, with no checkout drift. Actual policy
was20GiB RAM,4GiB monitored scratch,zero swap,no wall limit; observed scratch
was23,031,808 bytes. The original handle, source snapshot, native numerical
oracle, XML and receipt remain in math001. Scratch observation is not a hard
filesystem quota.

| Explicit synthetic input/measurement | Verified value |
| --- | ---: |
| signal1,background1,signal2,background2 |20,1,2,2|
| Declared depths in million_tags |1,2|
| Pseudocount |0.01|
| Condition1 depth factor |1|
| Condition2 depth factor |0.5|
| Adjusted signal2, addition before scaling |1.005|
| Condition1/background float32 likelihood |17.699888229370117|
| Condition2/background float32 likelihood |0|
| Condition1/condition2 float32 likelihood |17.7408447265625|

Every one of the15 numerical values in the separately captured native
TwoConditionScores arrays matched exactly. This is a native numerical oracle
from the earlier explicit execution, not a claim that the BED files carried
those unrounded values. It is not biological validation.

Other checks verify unequal-depth scaling, raw decimal versus float32 storage,
negative depletion and genuine zero, independently usable components with
missing/invalid inputs, explicit depth/parameter validation, overflow/underflow,
strict finite JSON and changed-pseudocount recalculation with network/subprocess
calls forbidden. The original operands remain unchanged.

Final checked source identities:

- `atac_differential_scores.py`:
  `62701fff00d156a75d4571ffc789a6db1b373f56b6d435dd7cd34c182850cdee`
- `test_atac_differential_scores.py`:
  `ecdbf353141b38d79fead02e5ec27fcd72c1a21eb89272cde19e54dc55727835`
- contract004:
  `e9ba8b58a3e9c71e9d229b94f16e6471d86b770b394da7bb1fbd663b381369da`

The numerical leaf has no direct production caller yet. Native parsers/sheet
assembly are owned by fresh464; actual interval/region functions by fresh463
under005/006. Native launch/result-worker integration, requested projection and
episode-path verification remain unfinished. Counts remain112/308,42local,
196outside; this narrow component does not add a completed grader.
