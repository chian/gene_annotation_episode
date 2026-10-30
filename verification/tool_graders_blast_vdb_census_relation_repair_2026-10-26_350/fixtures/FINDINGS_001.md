# Review348: two census-boundary corrections required

This review concerns the pure FunctionSheet → Model → numerical components path
at input SHA256 `78e0491b2d52cfed4bc013b04f2f3487fb86a65691dd3b10a4c97541f6d71b84`
and calculator SHA256 `31d88b0d724ced992c6ca69aab7161632ada3e24d91f2f264387b03d31ef749a`.
Exact inspected copies are in `reviewed_sources/`. The component does **not yet
satisfy the entire accepted338 contract**, because the two supplied-data
counterexamples below pass its actual public input/calculation path.

Root has taken the input census repair.348 changed no production code, prior
test, prior evidence, contract, goal or accounting. This is not a review of347's
separate integration,345's wire lowering, live VDB execution or the308 goal.

## 1. Contradictory observed/census sample identity changes a complete result

The input census join checks the exact address, TargetIdentity and full parent
identity, but omits a comparison with the already qualified sample relation:
`reviewed_sources/blast_vdb_function_inputs.py:795`. The calculator consequently
accepts the census link at `blast_vdb_function_calculators.py:334`, builds its
sample edges from the changed census relation at line241, and uses the changed
partition for correction at line667.

The reproduction starts with344's full three-function bridge example. It changes
only `census_records[0].entities[2].origin_sample_keys` from `["S3"]` to `["S1"]`.
The exact observed entity still belongs to S3 through the source joins below.
The real populator and saved-sheet validator accept this input. The result says
`complete`, census link `available`, `correction_available=true`, with no census
issue. Its observed conditional weights remain one third each, but its corrected
weights change from **(1/7, 2/7, 4/7)** to **(1/5, 2/5, 2/5)**. Actual saved binary64
values are `(0.19999999999999996, 0.39999999999999997, 0.39999999999999997)`.
This is a conflicting relation for the same entity, not an unreported bridge.

The exact original relation to compare is:

| Original sheet path | Retained fact and provenance |
| --- | --- |
| `base_sheet.member_bindings[2]` | MemberKey D2/read/synthetic:m2, `reported_origin`, sample_key S3; source `synthetic:supplied`, pointer `/members/2` |
| `base_sheet.dataset_records[2].sample_links[0]` | sample_key S3, Identity `{namespace:"sample",value:"S3",version:null}`; source `synthetic:supplied`, pointer `/sample` |
| `base_sheet.reference_metadata[5]` | metadata_key sample2, entity D2/S3 and the same sample Identity; source `/sample2`, linkage `/links/sample2`, both `synthetic:supplied` |
| `base_components.sample_groups.groups[2]` | Qualified S3 origin membership for D2/read/synthetic:m2 and original subject ordinal2 |
| `entities[2]` | entity key `entity:16591455967891104a83c37c46d48948a3ace1763bb31b6bfc3dc2348ac5424d`; sample_relation_status available, origin_sample_keys `["S3"]` |
| `census_records[0].entities[2]` | Same exact address and target identity; contradictory `["S1"]`; source remains `synthetic:independent-census`, pointer `/enumeration` |

Both target and parent identity remain nt length8,
SHA256 `34e5c3f4fdedcd486925ac670bb3e895bf692a50183516ac63f0eb07f1b0e7da`.
The identity proof proves those sequence symbols; it does not authorize changing
the originating sample. `_saved_membership_and_samples` at input line1256 already
revalidates the observed joins through the unchanged v1 `_members`/`_samples`
ports. Use that source-qualified exact entity relation, not a global sample name,
taxon, title or matching target digest as the cross-census join.

The relevant requirements are immutable principles6/7/10 (conflicts remain
distinct and associations remain intact),338 sections1/5/6 (exact sourced sample
relations and one consistent population partition), and addendum001's meaningful
saved relationship validation. Unknown data can follow an explicit unknown-data
policy; two available contradictory relations cannot silently select the census
one. The smallest correction is a source-preserving incompatible relation at
the exact observed↔census entity join. For this selected source-block correction,
retain the observed one-third weights and native observations, preserve the
supplied census descriptively, and withhold the entire corrected distribution
with the closed conflict qualification. Do not silently pick S1 or S3, or turn
this contradiction into an assumed independent target.

Complete reproduction:
`run_001/artifacts/census_observed_sample_contradiction.json`.

An unavailable census sample relation is a different case from this reproduced
available-versus-available contradiction. No exact accepted sentence requires
rejecting the census solely because observed sample information is available
while census sample information is unavailable. Section7 and addendum007 retain
unknown information and apply the selected policy. This review does not propose
silently filling a missing census relation from the observed sheet.

## 2. Unresolved optional census dependence bypasses the selected policy

`_dependency_issues` distinguishes an unresolved relation, including absent
source evidence, at input line651. `_census_issues` then collapses every such
case into `census_membership_unverified` at lines775–777. Calculator line334
initializes correction solely from that unavailable census LinkResult. Its
subsequent selected-policy branch can only set correction false; it cannot
honor `qualify_separate` for this case. Baseline correction also gets disabled,
although the dependence relation is retained but unused under that model.

The reproduction preserves the complete six-member/five-target census from
`whole_t1`. It adds a same_library declaration between two existing exact census
addresses, with a nonempty synthetic native_record and `sources=[]`. No member,
sequence, annotation, snapshot, population filter or count is changed. The only
unknown is provenance for that optional dependence edge. All tested models keep
`enumeration_complete=true`, but give a census link unavailable and corrected
cells null with `blast_vdb_function_census_membership_unverified`.

338 section1 explicitly leaves sample/dependence measurements unused in the
baseline. Section6 and addendum007 apply the explicit unknown dependence policy
to the complete census partition. Their required outcomes for this fixture are:

| Model | Policy | Overall/stratum status | CensusResult status / correction_available | Expected corrected A,B |
| --- | --- | --- | --- | --- |
| target_duplicates_only | qualify_separate | complete | available / true | 1/2, 1/2 |
| target_duplicates_only | withhold_weights | complete | available / true | 1/2, 1/2 |
| known_source_blocks | qualify_separate | partial | available / true | 4/5, 1/5 |
| known_source_blocks | withhold_weights | partial | unavailable / false | null, null; dependency_unknown |

The first, third and fourth rows were executed. The second is the same baseline
contract conclusion; it was not rerun because the policy has no baseline meaning.
In every row the observed conditional A,B distribution remains `(4/5,1/5)`.
All complete enumeration facts and descriptive counts survive. The separate
source-cap result must retain `dependency_unknown` and
`unknown_dependency_separate`; the withholding variant preserves the observed
distribution instead of failing the entire stratum. Its corrected function
cells, including correction-specific census operands, remain unavailable, while
the standalone CensusResult still retains descriptive grouped counts.

Known relations stay usable. The exact a1/a2 sequence duplicate links S0/S1 in
the target partition. Three other A targets have available S0 source relations,
so the source-cap partition has one A block and one B block at S2. Only the
unsubstantiated same_library A/B edge is omitted. Thus baseline N=5 and
N_A,N_B=(4,1), giving rates(1/8,1/8). Source-cap N=2 and N_A,N_B=(1,1), giving
rates(1/2,1/8). The observed HSP masses are1 and1/4 in both cases. No sample edge
is guessed and no HSP is created for an unreturned census entity.

The smallest correction is to keep unresolved optional dependence separate
from census identity/membership failure and apply the selected model/policy to
that issue. Preserve genuine conflicting or missing entity/identity relations
as failures; do not ignore all census issues. Existing closed issue and policy
fields are sufficient for this distinction. Root owns the exact implementation.

Complete executions are `run_001/artifacts/unresolved_census_edge_baseline.json`,
`unresolved_census_edge_separate.json`, and
`unresolved_census_edge_withhold.json`. Each retains full original fixture input,
populated sheet, explicit model and all numerical components.

## Evidence and scope of the new execution

`run_001/receipt.json`: returncode0, service wall0.958623259s,20 GiB RAM,
4 GiB scratch, no wall cap, zero swap and cgroup enforcement verified. Scratch
was monitored with possible overshoot, as the receipt states. The runner was
`.venv/bin/python -B` through `gene_annotation_episode.local_jobs.run_local_job`.
The job reproduced four narrow variants and inspected all20 original complete
example JSON files. It did not run any existing test suite.

The actual shared validator remained enabled during every new saved calculation.
Native parser, metadata reparse, public base calculator and FunctionSheet
population ports were forbidden during calculation; fixture construction used
the real populator beforehand. Input sheet/model canonical bytes were checked
unchanged after each call. Production and prior artifacts were read-only. No
network, API, HPC, install, database BLAST or model grading was used.

The full output/expectation summary is `run_001/artifacts/review_results.json`.
Existing344's180-check receipt is independent earlier evidence, not four new
tests added to a tally or a broad rerun. Neither VDB tool nor the308 goal is
declared complete here.
