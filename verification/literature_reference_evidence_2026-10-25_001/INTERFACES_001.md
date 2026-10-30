# First A105 source-rate population increment

The current controlling goal is preserved verbatim in GOAL_VERBATIM.txt.
It supersedes the previous all-axis literature scope. There are ten axes in
the larger system; no A101/A102/A103/A104 grader or target-transfer calculation
belongs in this increment. W05 credit remains separate.

## Case and scientific meaning

The retained CsiD preparation oxygen-rate example supplies two graph-derived
means, SDs and counts. A no-inhibitor reference is not a no-enzyme blank.
Three measurements are not automatically three independent preparations.
The source endpoint is oxygen consumption; this alone does not populate an
isolated chemical product-formation rate or an annotation confidence.

The paired fields below preserve this source distinction. A rate difference
and retained fraction describe one comparison, not two independent proofs.
Source statistical evidence can be calculated only under an explicit supported
observation model. No alignment or target-correspondence input is accepted.

## Closed handoff for the first implementable route

All objects below are finite JSON, with exact keys and explicit nulls.
Public contracts/calculators reject booleans as numbers and nonfinite operands.

`SourceTable` supplied to a deterministic reader:

- `source_ref`, `artifact_ref`: retained source and representation identity.
- `text`: the exact already acquired UTF-8 table representation. Acquisition is
  separate selected episode work. The reader performs no network/source fetch.
- `representation`: `primary_table|retained_extraction|synthetic_fixture`.
- `delimiter`: a single declared tab/comma separator; no autodetection.
- Columns have the exact headers `subject`, `experiment`, `arm`, `condition`,
  `endpoint`, `normalization`, `value`, `unit`, `uncertainty_kind`,
  `uncertainty_magnitude`, `count`, `sampling_basis`, `origin`.

`read_rate_table(table, *, expected_subject, expected_experiment)` returns
`{version: a105_rate_extraction_v1, subject, experiment, rows}`.
Exact source subject/experiment tokens must match the requested ones; no
mapping by equal numbers or a best-hit choice. Repeated arm rows with equal
values remain duplicate representations only if their source identities match;
different conflicting rows are not averaged. Unknown values use empty tokens.

Each row has exactly:

- `arm`, `condition`, `endpoint`, `normalization` (nonempty source tokens).
- `value`: finite number|null; `unit`: one supported rate unit.
- `status`: `observed|unavailable|censored|conflicting`.
- `bound`: `none|lt|le|gt|ge`; `approximate`: bool.
- `uncertainty`: `{kind: sd|sem|unspecified|unreported,
  magnitude: number|null, count: integer|null,
  sampling_basis: biological_preparations|technical_measurements|unspecified}`.
- `origin`: `reported|graph_derived|synthetic`.
- `source`: `{source_ref,artifact_ref,representation,row_number,
  header,raw_row}`; exact header/row text retained for validation/reconstruction.

`validate_rate_extraction(extraction)` returns a detached normalized record.
Unknown counts/bases remain unknown; SD and SEM remain distinct. A censoring
threshold is retained with its inequality, never used as an exact operand.

`populate_rate_contrast(extraction, *, reference_arm, test_arm,
                       dependence='unknown')` returns a source sheet:

- Same actual subject and experiment; distinct, uniquely identified arms;
  same endpoint and normalization. Units convert through an explicit finite
  conversion table, never from amount/time to concentration/time without volume.
- Cells: `reference_rate`, `test_rate`, `rate_difference` (reference-test),
  `retained_fraction` (test/reference), `fractional_decrease` (1-fraction).
- Error cells: reported mean standard errors when SD/count or SEM identifies
  them, and difference SE only with explicit `independent` dependence or a
  separately supported covariance route. Unknown dependence stays unavailable.
- Each cell includes value/null, unit, status, formula, input row identities,
  origin, and constrained unavailable reason. Source/native uncertainty remains
  alongside calculated uncertainty; no CI is invented.
- `scope=source_preparation_endpoint`; `annotation_credit=null`;
  `molecule_specific_product_rate=null` for this un-attributed rate route.
- No target relationship or combination with other axes.

These initial functions do not pretend to cover binding, transport, product
identification, general figures, unknown-denominator panels or all A105 models.
They provide a source-boundary foundation that contrasting cases can revise.

## Ownership before parallel coding

- Coordinator: this plan, shared `literature_experimental_contracts.py`,
  integration trace and later LiteratureEpisodes/typed-return wiring.
- Fresh table-reader worker: only `literature_rate_reader.py` and
  `tests/test_literature_rate_reader.py`.
- Fresh calculator worker: only `literature_rate_calculations.py` and
  `tests/test_literature_rate_calculations.py`.
- No worker changes tools.py, domain.py, state.py, runtime.py, communication.py,
  source publications, tool graders or another worker's files.

Shared contract implementation precedes coding delegation. Workers consume its
exact signature. Runtime integration remains coordinator-owned until all affected
consumers and durability paths are traced; helper tests do not establish it.

## Verification requirements

Check wrong subject, experiment, arm, condition identity, endpoint,
normalization and unit; malformed headers and tokens; SD versus SEM;
unknown count/replication/dependence; censoring; conflicting rows; original-source
identity and duplicate representations; zero denominator; finite arithmetic;
retention through serialization. Label source-reconstruction fixtures honestly.
No biological validation, original trace acquisition, model-backed execution,
annotation credit or complete LiteratureEpisodes integration is claimed here.
