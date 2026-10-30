# A110 native report reader129 — engineering proposal, pending root review

This artifact proposes implementation under the unchanged fixed chat goal. It
adds no goal, governing amendment, scoring axis, episode, controller, assay or
annotation-credit policy. The primary-paper packet is deliberately withheld.

The same `literature.reaction.populate` operation and its exact five arguments
remain. Existing prepared v1/v2 datasets follow their original path. A retained
`a110_source_reaction_selection_v1` recipe under `data_source_ref` supplies
source selectors for observed numbers rather than prepared numerical values.
The pure helper normalizes that recipe into the existing v2 numerical/meaning
contract and saves its separate exact native trace. The existing calculator and
all fifteen component meanings remain unchanged.

The finite reader supports reported ratio points, an author's exact `a:b`
expression, independently identified ratio observations, summary SD/SEM/unknown
spread and reported counts, and simple resource quantity/unit selectors. It
keeps reported technical or unknown counts separate from independent n. It
rejects explicit SD/SEM label conflicts, clipped numbers, unsupported limits,
unsupported approximate operands and clipped or incompatible units. A molar
ratio requires an interpreted molar measurement basis; spectral integral
signals are not automatically molar product quantities. Experimental/calibration
interpretation remains the scientist's responsibility. No generic spectrum
reader, curve fit, arbitrary table recognizer or quantitative calibration fit
is claimed. Confidence intervals need their separate endpoint contract and are
not converted to sample SD by this reader.

Predictions, coefficients and demand have distinct parameter records. Reported
parameter numbers use source selectors. Inferred or conditional parameters
remain explicitly declared assumptions with source evidence where available;
the reader does not relabel them as experimental observations. Source-reported
resource concentrations/amounts/rates retain their actual dimension and are
converted only by explicit finite unit scales. Supply is not consumption or
native usable capacity merely because it is reported in a Methods section.

The private native trace does not enter aggregate-only typed returns. A separate
`literature_reaction_native_observations` fact source is selected through
`requested_reaction_native_positions` (nonnegative positions, or `['all']`).
Its public identity is `observation_position`, never a scoring `component`.
Rows retain source/canonical values and units, point versus normalized-pair
representation, ratio kind and measurement/calibration basis, exact scientific
source-number/meaning references, reported uncertainty/count kind and
independent n. Resource rows link to the existing125 resource definitions.
Native rows are supporting operands, not extra assays or numerical scores.

The projection uses the existing semantic sheet and selected operation, plus
its own exact admitted subset and receipt table. Narrow explicit hooks handle
fact discovery, typed validation, admission, forwarding and rendering. The
receipt proof follows126's existing native-observation pattern with the A110
namespace and observation-position identity. No generic communication grammar
or generic scoring route is changed. Scope/received-source authorization runs
before each newly discovered selector's bytes are read. Saved projection and
operation replay use only original saved result/request artifacts and source
metadata, without scientific source bytes, parsing, recalculation or acquisition.

## Proposed ownership and exact patch

`EXISTING_PRODUCTION_PROPOSAL_001.patch` contains only these existing-file hunks:

- `literature_reaction_inputs.py`: native version detection, normalization,
  saved trace and synthetic-fixture origin preservation.
- `literature_reaction_storage.py`: actual direct source roster, native
  publication and metadata-only source-identity checks; native view accessor.
- `literature_episodes.py`: descriptor fingerprint, optional position selector,
  separately typed fact source and narrow admission/forwarding hooks.
- `literature_experimental_prompt.py`: requested-position presentation and
  explicit native observation display branches, preserving128 covariance code.
- `literature_reaction_prompt.py`: correct the old prepared-dataset-only claim;
  retain complete scientific distinctions and add native-reader limitations.

`PATCH_BASE_001.json` pins the exact current-main bases and isolated candidates.
New `literature_reaction_native_inputs.py` and its synthetic unit tests are in
main under129's released ownership. New native storage/render modules remain
only in `candidate_001`. No existing main production edits are authorized or
applied by129. Shared hooks require root review and rebase over126 integration
if that integration lands before this proposal is applied.

## Validation status and limits

Meaningful checks cover existing selected operation, ordinary original typed
child return, separately requested native facts, aggregate-only privacy,
source-before-byte authorization, exact native-position subset custody,
source-free first read-only reconstruction, original receipts, duplicate or
altered rows, and ordinary one-observation-per-completed-action accounting.
An expanded connected invocation and the existing opt-in operation-contract
information profile are being verified; final exact counts and prompt sizes
will be recorded in the terminal report. These are constructed engineering
choices; no new configured-model science or primary biological result is claimed.
