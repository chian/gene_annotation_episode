# MinHash selected metadata and closed replay: verified boundary

The selected pair-metadata calculation and requested-return path now passes
the previously failing closed Workflow replay. This is a bounded result under
the user's original goal, not completion of the BV-BRC R2 group.

## Verification and preserved failures

The original check003 recorded 149 passes, 28 failures and 4 setup errors.
Its classification distinguishes prospective commission ordering, fixture
serialization, incomplete focused-dispatch setup and an obsolete test expecting
root tool access. The root-tool restriction was not removed to satisfy that
obsolete test; no all-green claim is made for check003.

Check004 passed 82 of 98 selected tests, including 19 of 20 complete Workflow
cases and five focused dispatch cases. Its 15 remaining fixture failures were
fixed by serializing the complete plain contract. Its one production failure
was closed replay re-extracting metadata during parent commission reconstruction.

Check005 passed all 47 selected tests in 240.60 seconds: the original failed
Workflow replay, 31 new focused commission/custody cases and those 15 corrected
fixture cases. It did not repeat the 82 already passing check004 cases.
The original handle was collected terminal and quiescent. Source, dependencies,
standard library and executable pins were unchanged; the final audit found no
outside Python imports or unbound executable mappings. The current host,
execution binding, API service/execution, contracts, views, grader and runtime
match the tested snapshot. Existing component evidence remains 427 distinct
passing selected cases across check001/check002; that was not a new 427-case run.

Execution used the existing frozen lifecycle under 20 GiB RAM, 4 GiB scratch,
zero swap and no wall-time cap. These MinHash service responses and scientific
choices are explicit engineering fixtures. No new live BV-BRC request or HPC
execution is established.

## What changed

The existing `bvbrc_minhash_sheet_v1` and `calculate_minhash_components` remain
the numerical authority. A single shared hash-fraction helper supplies the
calculator and the projector's consistency validation. The new selector retains
explicit source-backed metadata, identifies a pair by original row index and
genome ID, and preserves native values independently from recalculated values.
Both genome and FASTA modes retain the original native request operands.

The host authenticates new inputs from actual received or selected records.
During prospective child construction it verifies the exact pending parent
selection and strictly earlier source receipt. Runtime feedback preserves the
affected source/pair/field/pointer so the responsible episode can repair its
selection. Those checks neither acquire data nor choose replacement inputs.

`validate_commission_inputs` now distinguishes a new selection from an original
recorded commission. Exact replay authenticates the original action, normalized
scope, child request and prior custody; it does not rebuild metadata inputs.
The same existing scope normalizer compares the stored original spelling with
the normalized child scope. Recorded scopes and selections are not rewritten.
The original frozen-publication reader still validates retained artifact links
and inputs. A recorded but incomplete child still performs first-publication
validation when it actually executes.

## Concrete verified numbers

The constructed shared/union pair is 2/3, with supplied lengths 2/2 and alphabet
size 2. At selected k=1, the shared calculator and received form contain
distance `0.22314355131420976` and p-value `0.2592592592592592`. An explicitly
selected saved-sheet calculation with source-backed k=2 produces
`0.11157177565710488` and `0.10400000000000001`.

The original native-reported values `0.223144` and `0.259259`, original sheet,
calculation artifacts, earlier action records and observations stay unchanged.
Both calculations retain the same original acquisition identity. Closed replay
forbids provider decisions, metadata extraction, full parsing/calculation and
transport, returns the original forms and preserves complete durable history.

## Explicit remaining work and limits

- MinHash tool-information wording still needs the new calculation choices and
  their limitations. Generic launch/API/results context rendering still needs
  detailed TASK and concise STEERING text; user template feedback is pending.
- Live service results and authentic remote sketch parameters remain unverified.
  Supplied k/length/alphabet values do not establish what the server used;
  `native_parameter_equivalence` remains `unestablished`.
- The existing interrupted-construction boundary can save a child before its
  parent commission. Such an orphan remains a specific
  `commission_action_missing` failure. This narrow replay repair does not add
  orphan recovery or erase the retained child. It does not claim arbitrary
  crash recovery is complete.
- Legacy native-only requests remain valid. Missing numerical inputs remain
  unavailable, rather than forcing another child or fabricating defaults.
- No literature grader, W05 annotation aggregation, prompt, scoring policy or
  continuation policy was changed in this repair.

Root reread the authoritative objective and complete operating principles,
reviewed the exact custody/commission/consumer paths and current contract, and
checked the final receipt/audit before accepting this bounded result.
