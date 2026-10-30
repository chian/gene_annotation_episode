# Selected transport response: fixed interface before fresh coding

Adopted GOAL_VERBATIM.txt controls; ten axes, no A101/target transfer/W05.
Prior turn is progress: native BtsT HTML extraction and a pure common-curve
response calculator passed250 joined checks and actual controlled typed/reopen
verification. This increment connects that existing calculator to selected work.
No new primary paper or packet is opened; this applies the already reviewed
BtsT distinctions and previously printed numerical example.

## Scientific task and numerical meaning, printed before implementation

Determine whether the selected source supports using one Michaelis-Menten
kinetic curve for the test/reference substrate concentrations and reported Km.
Identify the actual molecule/construct, analyte, preparation, system, endpoint
and fitted-curve context. A shared paper/name or equal number is insufficient.
Assign exact source spans for concentrations and a received committed Km sheet.
State unknown or different curve relationships; do not repair them by assigning
both systems a common label. Preserve reported untyped ±, actual covariance
owners and conditional response-model meaning. Correcting e/h is later assay
arithmetic; h is not annotation reliability or an additional credit multiplier.

Paired cells already defined by TRANSPORT_INTERFACES001–004 remain unchanged.
For the explicitly hypothetical common curve St10,Sr40,Km16.5uM, h=113/212=
.5330188679245284. The actual whole-cell versus vesicle contexts differ, so h
is null/different_kinetic_curves. No covariance follows from Km±6.4. Native
concentrations and supported single-arm saturation survive missing comparisons.

## Exact selected operation schema

Name literature.transport.response.populate. Arguments exact:
{source_ref,source_kind,primitives:{substrate_test,substrate_reference},
 km_sheet_ref,curve_contexts:{substrate_test,substrate_reference,km},
 covariance_source_ref,variance_status,observation_model,model_witnesses}.

source_kind primary_source|retained_extraction|graph_extraction|synthetic_fixture.
primitives each null or existing assay measurement schema:
{witness,number_start,number_end,unit_start,unit_end}. Witness exact
{source_ref,representation:original|text,start,end,quote}; byte offsets for
source witness, Unicode offsets inside quote. Reuse existing _Sources.witness
and .measurement(role=E) so concentrations convert to uM with full token/unit
and censor/approximation checks. Preserve scientific role separately.

km_sheet_ref source|null. Only an actually received selected
LiteratureQuantityRepository output with extraction.quantity=apparent_km and
unit=uM is accepted; no provider-label forgery or caller-supplied Km number.
Native quantity uncertainties remain their exact kind. Saved source numbers
can be consumed without rereading original paper bytes. Root source and every
actually read direct source require scope/receipt; original sheet provenance
requires scoped identities, not hidden original-source reacquisition.

Each curve_contexts entry is null or exact fields
{molecule,analyte,preparation,experimental_system,endpoint,curve}; each nullable
witness, but curve itself must be nonnull for a present context. These are
explicit episode source interpretations, not proof from matching quotations.
The exact same canonical context gives the same full SHA256 kinetic curve key;
different source contexts give different keys. Unknown context=null gives null
key. Do not use paper identity alone as the key. Context identity uses each
field's source_ref,artifact_ref,start,end,quote (not representation alias);
literal contents and source proof remain saved. Equal values in distinct
anchors do not establish curve identity; unresolved aliases stay unknown.

variance_status known|estimated|unknown;
observation_model michaelis_menten|unknown. Selected model or non-unknown
variance status requires >=1 actual model witness. Missing model/covariance is
scientific partial work, not failed execution or a stop condition.

covariance_source_ref null or received original UTF8 JSON with exact keys:
version=a105_transport_covariance_v1,
primitive_order=[substrate_test,substrate_reference,km],
primitive_measurement_keys=[...all3 exact keys...],
primitive_units=[uM,uM,uM],covariance=3x3,origin=reported|derived|synthetic.
All covariance entries are ALREADY canonical uM²; validate owner/order/units,
duplicate JSON keys/nonfinite/underflow. No extra unit conversion or zero
independence is invented. PSD/symmetry/alias validation belongs to calculator.
Supplied covariance requires all3 existing observations/keys.

## Pure reader workload (fresh worker1 owns only these files)

gene_annotation_episode/literature_transport_inputs.py and
tests/test_literature_transport_inputs.py.

Exports transport_response_population_schema(),
read_transport_inputs(arguments,*,read_source,read_quantity).
read_source(ref,representation)->{artifact_ref,content:bytes} already authorized;
read_quantity(ref)->exact
{sheet_ref,input_source_ref,value,unit,origin,reported_uncertainty_kind,
 measurement_key,reported_subject_ref,analyte_ref} already validated authoritative
quantity. This callback performs no numeric inference/source reading.

Return exact
{version:a105_transport_inputs_v1,source_ref,source_kind,primitive_order,
 values,curve_keys,measurement_keys,primitive_observations,curve_contexts,
 covariance,covariance_origin,variance_status,observation_model,model_witnesses,
 source_refs,km_quantity}.
values/keys correspond to existing pure calculator order. Each literal
primitive observation is existing _Sources.measurement result with role reset
to actual transport role. Km observation is callback result (or null).
Native Km original spread kind stays in km_quantity; source_refs contains
actual directly read root/witness/covariance refs plus km_sheet_ref, not its raw
provenance. Quantity key generated by repository, not reader/model.
Use full SHA256 compact sorted canonical JSON ensure_ascii=False/allow_nan=False
for curve identity, prefix transport_curve_. No state/network/prompt writes,
paper reads, private loops or tool-grader edits. Synthetic tests only.

## Repository workload (fresh worker2 owns only these files)

gene_annotation_episode/literature_transport_storage.py and
tests/test_literature_transport_storage.py.

LiteratureTransportRepository(LiteratureRateRepository), provider
literature.experimental.transport_response,
recordversion=literature_transport_response_record_v1,
tables literature_transport_operations/literature_transport_received.
Exports COMPONENTS from pure transport calculator, PROVIDER,
transport_response_cells_schema(), transport_response_population_schema
(reexport from inputs).

Repository validates selected operation/run/key/schema, direct source receipts
and scoped original provenance, invokes reader then existing calculator once,
saves immutable request/payload and original outcome transactionally. Saved
replay rechecks custody/scoped provenance without original source reads,
parsing or arithmetic. read() validates actual selected output,run,version,
source parents and original saved Km source bindings as needed.

read_quantity callback reads actual selected quantity output. Generate full
SHA256 key prefix transport_quantity_ over compact sorted JSON ensure_ascii=False
of {source_ref:extraction.source.source_ref,artifact_ref:...,
section_id,paragraph_id,expression_start,expression_end,quantity,analyte}.
These are immutable quantity-operand anchors, not numerical value or new action
identity; repeated selected representations of the same original quantity
retain one key. Raw sheet numbers/reported_subject_ref/analyte_ref copied.

Payload includes input_source_ref,args root; input_source_refs all directly
read sources plus saved quantity provenance; direct_input_source_refs exact
custody; input_artifact_ref; extraction; sheet; saved km_payload|null;
experimental_bindings; km_sheet_ref,covariance_source_ref. Record refs include
new source,source parents and actual bound references; changed_record_refs only
actual newly created source/reference records. No numerical scientific credit.

Bindings fields: reported_subject_ref,analyte_ref (copied from Km or null),
test_curve_ref,reference_curve_ref,km_curve_ref (new scoped assay references for
present interpreted contexts; null for unknown). Same canonical context gives
same reference and curve_key. Unknown literals remain in saved extraction.

Each typed row exact:
sheet_ref,evidence_source_ref,km_sheet_ref,covariance_source_ref,
all5 bindings,component,value,unit,status,formula_code,origin,
unavailable_reason,conditional_on,variance_status,observation_model,
operand_source_kind,covariance_origin,reported_km_uncertainty_kind,
evaluated_scope=interpreted_source_kinetic_response.
Formula code transport_<component>_v1 only (no freehand formula string).
Unit enum uM|dimensionless|dimensionless_squared; status populated|unavailable;
origin reported|derived|graph_derived|synthetic; uncertainty kind
unspecified|unreported|not_supplied (new quantity types retain explicit mapping).
No raw curve/measurement hashes, full covariance, witnesses or source dumps in
typed return/prompt. Schema constrained strings/enums and actual saved values
validated; exactly requested subsets and forwarding only admitted cells.

Use existing numerical reasons from calculator (inspect every path) and source
metadata. Payload input_source_refs includes original quantity source as scoped
provenance, but direct receipts require Km sheet only. Fake selected Km sheet,
wrong quantity, cross-run, unreceived root/witness/model/quantity, wrong page
lineage, forged values, invalid covariance or operation reuse return structured
failure without half-published output. Scope/page root is source_ref.
Synthetic repository fixtures only; primary examples belong to root.

## Root integration ownership

WorkflowServices lazy repository; existing LiteratureEpisodes profile includes
one new selected operation and fact route, requested_transport_components.
Descriptor hashes new modules and calculator. Full recurring transport TASK
asks actual biological/curve questions, no sheet dump. Selected result STEERING
shows only requested component meanings and necessary model/uncertainty/status.
Root owns shared glue, new prompt, actual Workflow/primary fixtures, fresh-process
replay and assembled verification. No method_loop/controller/credit change,
new episode, hidden loop, source reacquisition or original case/live pin edit.
