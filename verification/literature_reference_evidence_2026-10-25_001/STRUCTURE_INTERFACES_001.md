# A111 reference structural components: fixed first executable interface

Adopted full literature goal governs. Previous goal turn was progress. Root
independently reviewed all147 IscR BioC passages, original Table1 and figures1/2/3/6,
verified35 worker-packet files, and reproduced coordinates using installed
Bio.PDB.MMCIF2Dict. Root obtained associated original wwPDB4HF1 validation XML.
Root then reread the COMPLETE authority set, current A111sheet027/crosswalk and
latest scope LAST (ISCR_STRUCTURE_PARENT_RESET001). No new paper is required.

Scientific example printed before coding: 4HF1 IscR3CA/hya, four Glu43 group
distances2.814260471,3.504470573,2.648124053,3.056920182Å. Six selected residue
RSCCs .911,.903,.963,.944,.960,.939. Proposed D=min(max(0,RSCC)^2)=.815409,
Gplus=3/4=.75,Gminus=0/4=0 with positive[0,3.5]Å,incompatible[4.5,infinity).
Conditional source product D*Gplus=.61155675, D*Gminus=0, signed difference
.61155675. Cutoffs/transforms are explicit proposals. No coordinate uncertainty,
H-bond energy, physical occupancy, holo contact or target credit is inferred.
The same apo structure/density supports these factors; they are not independent.

The experiment uses3CA proteins, not native cluster-occupied WT. Single selected
deposited model/assignment defines conditional q=C=I=1 only for its geometry
statement, as proposal027 permits. This is NOT a default for missing population
occupancy, causal comparison or chemical assignment evidence. No T or target
operands/aggregation are implemented. General model alternatives, symmetry,
other structural modalities, nuisance contrasts/isolating bounds and calibrated
nondetection remain required unfinished work.

## File ownership

Fresh worker1 owns ONLY gene_annotation_episode/literature_structure_calculations.py
and tests/test_literature_structure_calculations.py. Pure deterministic arithmetic,
synthetic fixtures only; no source, network, state or model work.

Fresh worker2 owns ONLY gene_annotation_episode/literature_structure_inputs.py
and tests/test_literature_structure_inputs.py. Pure selected coordinate/validation
reader, synthetic fixtures only; no research-paper interpretation or network/state.

Fresh worker3 owns ONLY gene_annotation_episode/literature_structure_storage.py
and tests/test_literature_structure_storage.py under the exact repository
contract appended below. Root has not created those files.

Root owns existing LiteratureEpisodes/Services,
typed return/projection, recurring aspect TASK, integration/examples/replay and
progress. Do not edit any other session's tool graders or original live pin/case.

## Source reader operation arguments, exact closed fields

```
source_ref,coordinate_source_ref,validation_source_ref,source_kind,
model_number,literals,geometry_panel,local_panel,evaluation_scope
```

source_refs are received source IDs; validation_source_ref nullable. source_kind
primary_source|retained_extraction|graph_extraction|synthetic_fixture (same existing
SOURCE_KINDS). model_number positive int, never bool. evaluation_scope is exactly
conditional_deposited_model_geometry. Do not accept an unconditional population
or causal task under this operation. Exact literals map molecule,construct,
experimental_system,condition,partner,experiment to nullable _Sources byte witnesses.

geometry_panel is a list (possibly empty; calculator reports invalid denominator),
each exact {endpoint_a,endpoint_b,positive_max_A,incompatible_min_A}. Endpoints:
{auth_chain,auth_seq_id,insertion_code,comp_id,atom_names,alt_id}. auth_chain,
auth_seq_id,comp_id,alt_id are nonempty strings. insertion_code is string, ''
means no insertion. atom_names is nonempty unique list of nonempty strings.
alt_id='.' means no alternate; an explicit named alternate is allowed and must
match every selected atom. No automatic best/highest-occupancy alternate.
Positive cutoff finite >=0; incompatible cutoff finite >positive cutoff. These
are proposed predicate parameters, not fabricated measurements. Coordinates Å.
Group observable is min of all Euclidean atom-pair distances between the TWO
explicit complete groups. If any requested endpoint atom is unavailable or
ambiguous, preserve known rows but the group's distance remains unavailable.
No symmetry/assembly transform or implicit chain/atom remapping is performed.

local_panel is list (possibly empty), each exact
{auth_chain,auth_seq_id,insertion_code,comp_id,alt_id}. One RESIDUE-granularity
validation selection per member; no atom-level RSCC claim. Duplicate geometry
members/identical reversed groups or duplicate local selectors are invalid
denominator/duplicate selection errors; ordering/renaming atoms cannot make a
second physical constraint. Unique physical residue selectors retain fixed panel.

Reader exports structure_population_schema(),read_structure_inputs(arguments,*,read_source).
Callback read_source(ref,representation)->{artifact_ref,content:bytes}; use existing
_Sources for witnesses and callback custody. No model numeric point arguments.
Use installed Bio.PDB.MMCIF2Dict over exact decoded original bytes; no worker's
research parser/import (it mutates historical outputs). Reject malformed structure
syntax, unequal atom columns, nonfinite/lexically underflowed coordinates/RSCC,
invalid scalar units/identity/model fields. '?' and '.' are missing scientific
numeric data, not zero. Return useful partial native observations for absent
atoms/residues/RSCC. Strict XML rejects DOCTYPE/ENTITY; preserve source attributes.

Validation is wwPDB-validation-information with exactly one Entry. Required join:
same normalized PDB accession (_entry.id vs Entry@pdbid), selected existing model,
coordinate latest _pdbx_audit_revision_history ordinal/date vs Entry revision
number/date. Unique selected ModelledSubgroup keyed model/chain/resnum/icode/
altcode plus matching resname and matching coordinate residue identity. Blank
XML alt/insertion matches '.'/'' respectively. Preserve report creation/schema,
source revision and entry fields. Native rscc must lie[-1,1]. No other local
quality metric substitutes for it. Report binding is metadata-based, not a
cryptographic coordinate digest and not independent map recomputation.

validation_binding enum matching_entry_revision|entry_mismatch|revision_mismatch|
binding_unreported|not_supplied. A mismatched/unreported join prevents D while
preserving useful original geometry and raw reported validation rows. If no
validation, all required local values null, not a fabricated all-zero panel.

Reader returns exact {version:a111_structure_inputs_v1,source_ref,source_kind,
coordinate_source_ref,validation_source_ref,model_number,evaluation_scope,literals,
source_refs,coordinate_metadata,validation_metadata,native_geometry,native_local,
calculation_inputs}. Native records preserve selected rows, IDs/atom coordinates/
occupancy/B, original selectors and source/artifact identities. calculation_inputs
must exactly match calculator contract below; atom rows/parameter occupancy remain
separate from measured physical occupancy. Origins synthetic only when fixture.

## Pure calculator interface

Exports VERSION=a111_source_geometry_v1,COMPONENTS,REASONS,CONDITIONAL_CODES,
populate_source_geometry(inputs). Exact input fields:

```
geometry_members,local_members,validation_binding,origin,evaluation_scope
```

origin reported|synthetic. evaluation_scope fixed conditional_deposited_model_geometry.
Each geometry_members entry exact {endpoint_a,endpoint_b,positive_max_A,
incompatible_min_A,unavailable_reason}. endpoint_a/b are nonempty lists of xyz
triples finite numbers, or null. A null endpoint requires reason
endpoint_unmodeled|ambiguous_atom_selection|endpoint_identity_mismatch|
coordinate_unreported. Known endpoint coordinates never have a reason. Do not
accept Boolean numbers or malformed triples; keep exact range checks.
Each local_members entry exact {rscc,unavailable_reason}; rscc finite[-1,1]|null;
missing reason local_rscc_unreported|local_endpoint_unmodeled|
ambiguous_local_selection|local_identity_mismatch. Known rscc requires null reason.
Empty panels produce unknown rather than perfect results. No dependence/model
weights are inferred from panel size.

Output exact {version,inputs,native_geometry,cells}. native_geometry each
{member_index,distance_A,all_pair_distances_A,unavailable_reason}; preserve each
requested pair, no hidden best-assignment search. Use stable math.dist with
explicit representability checks. An unrepresentable distance has
numerical_model_range; it must not create exact0/infinite evidence.

cells is mapping in COMPONENTS order:
local_fit_index,geometry_support_fraction,geometry_opposition_fraction,
source_geometry_positive,source_geometry_opposing,source_geometry_signed.
Each cell exact {value,lower,upper,unit,status,origin,unavailable_reason,
conditional_on,formula_code}. unit dimensionless, all proposed-origin outputs.
status populated|unavailable. source_geometry_signed domain[-1,1], others[0,1].
formula_code closed structure_<component>_v1. Unknown uncertainty remains
unreported: cell bounds are logical/conditional arithmetic enclosures only.

D=min(max(0,RSCC)^2) over nonempty fixed local panel. Missing selected local
member admits[0,1]; Dpoint unknown unless algebraically identified (known D0
makes it0); bounds[0,min known transformed] (or[0,1]allmissing). Invalid binding
gives Dnull[0,1] even if native rows happen to be present. No source conflict
is reconciled by best value. Gplus=count(d<=positive_max)/J, Gminus=
count(d>=incompatible_min)/J. Missing quantities retain fixed J and [0,1]
predicate domains. Report known fractions only if all predicates identified;
unknown Gplus/Gminus keep lower known_count/J and upper(known_count+missing)/J.
Empty geometry panel unknown[0,1]. Individual pairs obey disjoint predicates;
independent marginal bounds are outer, not jointly attainable claims.

p_ref=D*Gplus,o_ref=D*Gminus,z_ref=p_ref-o_ref. q/C/I are explicit conditional
identities by this restricted scope, not populated physical measurements.
Use underlying joint known G direction to cancel z exactly when all geometry
predicates known and Gplus==Gminus even if Dunknown. Known multiplicative zero
can identify p/o without filling other missing cells. Otherwise unknown factors
propagate. For z, retain shared D: first compute h=Gplus-Gminus from each paired
predicate, missing predicate admits[-1,1], then signed product interval D*h.
Do not independently subtract p/o bounds and invent an unattainable point.
Exact rational counts/RSCC arithmetic then float range checks; underflow is
unavailable/numerical_model_range rather than silently an observed0.

Reasons include local_panel_empty,geometry_panel_empty,validation_not_joined,
local_rscc_unreported,geometry_inputs_unreported,numerical_model_range and source
reader missing reasons as needed. All cell conditional_on includes
selected_model_assignment,proposed_geometry_predicates,unreported_coordinate_uncertainty;
products additionally conditional_state_unit_occupancy,single_state_no_causal_comparison,
assignment_conditioned_isolation,source_geometry_convention. D also
residue_rscc_squared_minimum. No confidence/probability is supplied.

Calculator caller validates actual source identities. Reader supplies group
points from authoritative retained bytes and matching local panel. Neither
worker edits source sheets, runtime/glue/prompts or handles scientific authority
review. Tests must cover complete/partial/empty, threshold gap/disjointness,
ambiguous/duplicate selection, model/alternate/insertion identities, report
binding, shared-factor cancellation and range failures. Label all tests synthetic.

## Selected storage and typed return contract (worker3)

Export LiteratureStructureRepository,COMPONENTS,PROVIDER,
structure_population_schema (reader re-export),structure_cells_schema.
PROVIDER=literature.experimental.structure, record_version=literature_structure_record_v1,
operations_table=literature_structure_operations,received_table=literature_structure_received.
Extend existing LiteratureRateRepository for ordinary receipt/return persistence;
follow current perturbation/transport repository patterns, not a private workflow.

populate(context,args,operation_key) validates actual received/scope/source-kind
and assigned-page lineage for EVERY directly read source: root, coordinates,
validation and literal witnesses. Source parents are scoped provenance, not
silently delivered knowledge. Actual same-run operation identity/request/scope
signature and immutable payload/outcome are saved transactionally. Failed source
or publication must not half-publish bindings or operation. Replay checks saved
identity and current permitted custody but reads only saved sheet/request bytes;
never rerun parser/calculator or regenerate geometry/measurement identities.

Payload follows perturbation fields version,input_source_ref,input_artifact_ref,
input_source_refs,direct_input_source_refs,extraction,sheet,experimental_bindings;
also coordinate_source_ref and validation_source_ref. Build six witnessed literal
bindings: assayed_subject_ref<-molecule(reference),construct_ref<-construct(reference),
experiment_ref<-experiment(reference),partner_ref<-partner(reference),
experimental_system_ref<-experimental_system(context),condition_ref<-condition(context).
Their content identities include witness original source/artifact/span and field;
exact original quote labels persist. Missing literals produce null bindings,
not invented subjects/conditions. Coordinates and validation stay referenced.

Outcome result: sheet_ref,cells,assay_interpretation=literals plus metadata below.
Native arrays remain in saved extraction; no uncontrolled free-text report and no
full coordinate table or host hashes inserted into decision prompts. Do not
create scientific observations/assessments or any controller/credit record.

project_cells(sheet_refs,*,permitted_record_refs,components=None) returns exactly
one row per requested component in order for each received selected sheet. Exact
fields: sheet_ref,evidence_source_ref,coordinate_source_ref,validation_source_ref,
six experimental bindings,component, all numeric cell fields (including closed
formula_code), plus the following finite metadata:

validation_binding from calculation_inputs; evaluation_scope singleton
conditional_deposited_model_geometry; operand_source_kind from extraction;
bound_kind=conditional_arithmetic_outer; unconditional_uncertainty=unreported;
occupancy_basis=conditioned_selected_model;
comparability_basis=single_state_no_causal_comparison;
isolation_basis=conditioned_atom_assignments.

The six current COMPONENTS are those specified above. Native counts and original
coordinates/RSCC/occupancy remain stored, not scored as publication quality.
Typed schema permits nullable source IDs, bindings constrained to their reference/
context namespaces, finite numeric scalar bounds, declared origin=proposed and
unit=dimensionless, closed component/formula/reason/condition codes. Use existing
obj/reference helpers. Lower/upper are arithmetic/logical outer bounds, never CI.
Preserve all unknown source values in saved extraction with their reasons.

read validates actual selected output authority via base read plus source/root/
coordinate/validation request consistency and root artifact binding. Copied
provider/payload records alone are not authoritative. Validate returned values
against saved exact rows; forward only admitted subset, not all private cells.

Worker3 tests use SYNTHETIC CIF/XML fixtures only and can build helpers distinct
from worker2-owned tests. Test complete/partial/mismatch, selected schema and
custody/page source lineage, same-run authority, forged rows/source copies,
atomic publication, replay with reader/calculator disabled and original bytes
forbidden, exact admitted subsets. Reader/calculator imports may be locally
deferred until those workers' files exist; coordinate only via root. Do not read
primary packet or start scientific work. Root owns existing episode glue,
recurring prompt, shared selected integration and real-source controlled examples.
