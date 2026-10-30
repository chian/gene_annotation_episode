"""Offline design rendering/schema capture only; no episode, model or source IO.

All writes stay under this new077 directory. Existing implementation imports
are read-only; PYTHONDONTWRITEBYTECODE must be set by the invoking shell.
"""
raise SystemExit("Historical note-governed artifact generator retired.")

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE, CONTRACT_ARGUMENT_TRANSPORT
from gene_annotation_episode.decision_context import INSTRUCTIONS
from gene_annotation_episode.domain import obj
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_experimental_prompt import _task
from gene_annotation_episode.literature_reference_parent_prompt import _task as parent_task, REFERENCE_PARENT_TASK
from gene_annotation_episode.literature_ratio_source_storage import ratio_source_population_schema, ratio_source_cells_schema, COMPONENTS

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def write(name, value):
    target = OUT / name
    if target.exists():
        raise RuntimeError('Design generation must not overwrite ' + str(target))
    target.write_text(value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


RATIO_TASK = '''Determine what the reported signal comparison establishes about the studied molecule and the experiment you were assigned. Identify the actual organism, recipient genotype, assayed molecule, preparation, tested construct, reference construct and condition before interpreting a ratio. Establish whether the proteins replace one another or coexist. A WT label may mean tagged plasmid complementation rather than an unmodified organism or endogenous protein. Separate the intended experimental change from expression, loading and other differences that could explain the measured result.

Identify the endpoint and printed signal meaning, its numerator and reference, normalization and signal use. A band or antibody signal can qualify expression comparability without measuring active protein amount, catalysis or the functional endpoint. Growth recovery and survival are different endpoints. Do not borrow a mutant panel, repetition count, loading control, exposure or calibration from another experiment. Preserve meaningful source definitions, including numeric construct names, boundaries and conditions, as definitions rather than broad copied source prose.

Choose the source reads, neighboring context, table investigation or native image view useful for your question. For a printed figure value, examine the actual native image view received by your own episode. Identify its frame and the complete numerator and reference regions. Nominate a printed normalized ratio, percentage or pair of printed signals according to what the source reports. Retain the complete literal, including percent signs and inequalities. Band darkness is not a printed number; this route does not perform densitometry, OCR or calibration.

Record each visual reading as exact, ambiguous, unreadable or conflicting according to the evidence. Preserve distinct joint numerator/reference alternatives and unreadable fragments/regions. A pair requires a supported common signal scale; different exposures do not automatically share a scale. A known different scale is different, not contradictory source evidence. Do not invent a value, positive reference, calibration or detection threshold. Printed zero is a reported signal value, not proof of zero molecules. ND or n.d. alone supplies no numerical limit.

Decide whether each selected prose statement or figure describes the same single reported signal quantity, a different quantity, an unknown association or a conflicting association. Separately establish physical measurement and reference identity from source witnesses. Equal values, repeated displays and a common paper prove neither physical identity nor independence. Preserve linked disagreements, all selected unreadable/ambiguous alternatives and distinct experimental quantities. Do not average, choose a favorable representation, discard an unresolved alternative or treat separate experiments as a representation conflict.

Identify source meanings, exact locations and literal candidates. Deterministic readers authenticate custody and parse the literals; separate calculators perform division and transforms. Ratio, difference and positive log ratio describe one comparison and are not independent evidence credits. A reported-estimate censor domain is not a sampling confidence interval. Keep actual uncertainty meanings and unknowns. Numeric uncertainty reading, calibrated amount, functional-response conversion and observation-model calculations remain unimplemented in this route; that capability limit is not a finding that the source lacks such information.

Return only the parent's requested numerical components and their declared experimental qualifications through its original typed form. Unknown, censored, contradictory and valid partial outcomes remain useful. Source access does not give a parent unrequested numerical knowledge or private image context. Do not calculate target correspondence, annotation probability or combined annotation credit; do not add a report-composition model call, new episode type, fixed reading itinerary or synthetic observation. Choose iteratively from actual outcomes. The shared method loop and configured controller retain continuation authority.'''

DESCRIPTION = ('Read the selected source-reported relative signal from exact JATS percentage syntax or literal nominations in this episode\'s own native image views. Preserve actual subject, constructs, organism, conditions, arrangement, endpoint, normalization, joint numerator/reference alternatives, source association and physical identity. Pair division requires a supported common scale. Candidates, censor domains and unresolved selected representations remain explicit; ratio/difference/log are dependent descriptions. Numeric uncertainty, calibrated amount, functional-response and observation-model readers remain unimplemented here, not paper-level absence findings. No OCR, densitometry, target transfer or annotation credit.')

baseline = LiteratureEpisodes(None, rate_population=True)
old_ops = _population_catalog()
old_facts = baseline._rate_fact_sources()
assert len(old_ops) == 19 and len(old_facts) == 18
request = ratio_source_population_schema()
returned = ratio_source_cells_schema()
write('REQUEST_SCHEMA_001.json', request)
write('RETURN_SCHEMA_001.json', returned)
write('BASELINE_DEFAULT_CONTRACTS_001.json', {
    'scope': 'Readonly current default19/18 declarations; capture only, no scientific execution',
    'population_catalog': old_ops, 'fact_sources': old_facts,
    'assignment_schemas': {role: baseline.assignment_schema(role) for role in baseline.roles}})
assignment = baseline.assignment_schema('literature')
assignment['properties']['requested_ratio_source_components'] = {
    'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPONENTS)}}
write('ENABLED_LITERATURE_ASSIGNMENT_SCHEMA_001.json', assignment)
label_role_schema = obj({
    'role': {'type': 'string', 'enum': ['subject','variant','reference','organism','genotype',
        'construct_variant','construct_reference','preparation_variant','preparation_reference',
        'experiment','condition','endpoint','normalization']},
    'status': {'type': 'string', 'enum': ['known','unknown','conflicting']},
    'label': {'type': ['string','null']},
    'display_status': {'type': 'string', 'enum': ['supplied_definition',
        'retained_for_scoped_access','unresolved_source_meaning']}})
label_projection_schema = obj({
    'version': {'type': 'string', 'const': 'ratio_source_prompt_meanings_v1'},
    'sheets': {'type': 'array', 'items': obj({'sheet_ref': {'type': 'string'},
        'roles': {'type': 'array', 'items': label_role_schema}})}})
write('API_CONTRACT_001.json', {
    'status': 'Proposed for root review; no production integration',
    'constructor_new_keywords': {'ratio_source_population': {'type': 'boolean', 'default': False,
        'requires_when_true': {'rate_population': True}},
        'ratio_source_evidence_origin': {'type': 'string', 'enum': ['reported_source', 'synthetic_fixture'],
            'default': 'reported_source', 'owner': 'caller only', 'nondefault_requires_opt_in': True}},
    'operation': {'name': 'literature.ratio.source.populate', 'description': DESCRIPTION,
        'schema_file': 'REQUEST_SCHEMA_001.json', 'argument_transport_when_profile': CONTRACT_ARGUMENT_TRANSPORT},
    'assignment_field': 'requested_ratio_source_components', 'components': list(COMPONENTS),
    'namespace': 'literature_ratio_source_cells', 'return_schema_file': 'RETURN_SCHEMA_001.json',
    'provider': 'literature.experimental.relative_signal_source',
    'source_record_version': 'literature_relative_signal_source_record_v3',
    'source_request_version': 'relative_signal_source_selection_v2',
    'extraction_version': 'relative_signal_source_extraction_v3',
    'sheet_version': 'relative_signal_sheet_v2', 'calculation_version': 'relative_signal_calculation_v2',
    'service': 'WorkflowServices.literature_ratio_source_repository(*, evidence_origin="reported_source")',
    'repository': 'LiteratureRatioSourceRepository(store,run_id,*,evidence_origin="reported_source")',
    'descriptor': {'binding_id': 'literature', 'version': 'literature_episode_binding_v1',
        'enabled_configuration_addition': {'ratio_source_population': True, 'ratio_source_evidence_origin': 'reported_source'},
        'disabled_additional_configuration_keys': []},
    'new_prompt_marker': {'literature_ratio_source_work': {'version': 'literature_ratio_source_task_v1'}},
    'additional_production_file_proposed': 'gene_annotation_episode/literature_reference_parent_prompt.py',
    'internal_label_projection': label_projection_schema})

tools = [dict(row, argument_transport=CONTRACT_ARGUMENT_TRANSPORT) for row in old_ops]
tools.append({'name': 'literature.ratio.source.populate', 'description': DESCRIPTION,
    'input_schema': request, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT})
child_state = {
    'contract_information_profile': CONTRACT_INFORMATION_PROFILE,
    'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'},
    'goal': {'objective': 'Determine what the supplied constructed protein-signal comparison establishes about expression comparability in separate replacement arms.',
        'task_context': {'constraints': 'Use supplied engineering text and image only. Return the requested source comparison; preserve unresolved scientific meanings.'}},
    'scope': {'subject_refs': ['input_supplied_protein']},
    'literature_assignment': {'version': 'literature_assignment_v1', 'source_refs': ['source_supplied_engineering_text','source_supplied_engineering_image'],
        'question_context_refs': []},
    'working_state': {}, 'tools': tools,
    'child_options': 'Existing literature_strategy investigation is available when useful; source operations can also be chosen directly. No child sequence is prescribed.',
    'requested_report_purpose': 'Return only reported_ratio and its declared source qualifications for deciding experimental comparability.',
    'requested_form': obj({'requested_signal': returned}),
    'available_report_facts': {'literature_ratio_source_cells': {'meaning': DESCRIPTION}},
    'report_lifecycle': 'Interpretations retain their actual reasoning basis. Saved numerical facts populate the original requested field at closure.'}
child = _task(child_state, INSTRUCTIONS + '\n' + baseline.instructions(SimpleNamespace(role='literature')))
child = child.replace('TASK\n\n', 'TASK\n\n' + RATIO_TASK + '\n\n', 1)
child += '\n\nRequested source-ratio components\n\n| Component |\n| --- |\n| reported_ratio |\n'
write('DRAFT_SOURCE_RATIO_TASK_INSERT_001.txt', RATIO_TASK + '\n')
write('DRAFT_CHILD_TASK_001.txt', child + '\n')

parent_state = {key: deepcopy(value) for key, value in child_state.items() if key not in ('literature_assignment','tools')}
parent_state['goal'] = {'objective': 'Evaluate what the supplied constructed reference experiments establish about possible function, keeping expression comparability distinct from isolated molecular activity.',
    'task_context': {'constraints': 'Use supplied engineering sources. Preserve reference identity and partial results. Do not calculate target correspondence or W05 credit.'}}
parent_state['tools'] = []
parent_state['child_options'] = 'A literature investigation can examine a scoped source question. The child owns its iterative choices within the supplied scope and original typed return.'
descriptor = {'version': 'reference_evidence_parent_v1', 'source_refs': ['source_supplied_engineering_text','source_supplied_engineering_image'],
    'source_custody': [], 'child_population_operations': [{'name': row['name'], 'description': row['description']} for row in tools]}
parent = parent_task(parent_state, INSTRUCTIONS, descriptor)
assert parent.count(REFERENCE_PARENT_TASK) == 1 and RATIO_TASK not in parent
write('DRAFT_PARENT_TASK_001.txt', parent + '\n')

write('DRAFT_PARENT_STEERING_001.txt', '''STEERING

Own action yields

| Category | Completed | Total signed yield | Expected next yield | Uncertainty |
| --- | --- | --- | --- | --- |
| child/literature | 1 | 0 | unavailable | fixture estimator unbound |

Admitted requested source signal

| Component | Value | Unit | Status | Origin | Candidates | Reported-estimate domain |
| --- | --- | --- | --- | --- | --- | --- |
| reported_ratio | 0.64 | fraction | populated | synthetic | 0.64 | [0.6399999999999999, 0.64] |

Source comparison meaning

| Subject / variant | Reference / arrangement | Constructs | Organism / genotype | Condition | Endpoint / normalization | Signal use |
| --- | --- | --- | --- | --- | --- | --- |
| SyntheticProtein / K426A | tagged WT complementation / replacement | His-tagged protein residues 1–253; tagged WT counterpart | Engineering bacterium / ΔgeneX::kan | 37 °C; pH 7.4 | immunoblot protein-band signal / same-blot tagged WT reference | experimental_comparability |

Admitted qualifications

| Meaning | State |
| --- | --- |
| Subject, variant, reference, organism, genotype, constructs, condition, endpoint, normalization | known |
| Preparations, experiment identity | unknown |
| Selected roster resolved / point candidates complete / known source conflict | true / true / false |
| Selected association / common signal scale | supported / supported |
| Physical measurement / reference identity | unknown / unknown |
| Independent preparations | unknown |
| Uncertainty | unknown; numeric uncertainty reader unimplemented |
| Basis / conditions | selected received source representations; source comparison interpretation; nominated printed signal pair |
| Numerical meaning | reported signal comparison; stored domain includes finite outward rounding, not a sampling interval |
''')

full = [
    'AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md',
    'docs/TOOL_KNOWLEDGE.md','docs/TASK_AND_STEERING.md','docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
    'docs/PRACTICAL_EXECUTION.md','docs/PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md',
    'research/experimental_scoring_review_2026-10-23/AGENTS.md',
    'gene_annotation_episode/literature_episodes.py','gene_annotation_episode/episode_services.py',
    'gene_annotation_episode/literature_experimental_prompt.py','gene_annotation_episode/literature_reference_parent_prompt.py',
    'gene_annotation_episode/literature_rate_storage.py','gene_annotation_episode/literature_ratio_storage.py',
    'gene_annotation_episode/literature_ratio_source_inputs.py','gene_annotation_episode/literature_ratio_source_validation.py',
    'gene_annotation_episode/literature_ratio_source_calculations.py','gene_annotation_episode/literature_ratio_source_storage.py',
    'gene_annotation_episode/episode_composition.py','gene_annotation_episode/episode_commissions.py',
    'gene_annotation_episode/episode_admission.py','gene_annotation_episode/episode_completion.py',
    'gene_annotation_episode/independent_execution.py','method_loop/runtime.py','method_loop/durable_worker.py',
    'tests/test_literature_ratio_source_inputs.py','tests/test_literature_ratio_source_calculations.py',
    'tests/test_literature_ratio_source_validation.py','tests/test_literature_ratio_source_storage.py',
    'tests/test_literature_ratio_source_readonly.py','tests/test_literature_rate_episode_integration.py',
    'tests/test_literature_cell_possession_integration.py','tests/test_literature_binding_interaction_integration.py',
    'tests/test_literature_experimental_prompt_delivery.py','tests/test_literature_reference_parent_prompt.py',
    'tests/test_literature_reference_parent_delivery.py','tests/test_contract_information_worker_059.py',
    'tests/detached_workflow_fixture.py','tests/test_literature_ratio_integration.py']
parents = 'verification/literature_reference_evidence_2026-10-25_001/'
for name in ('EPISODE_INTEGRATION_DESIGN_RELEASE_077.md','INTEGRATION_CONSUMERS_006.md','CONSUMER_READ_RECEIPT_006.json',
    'SOURCE_TEXT_LOCATOR_ADDENDUM_008.md','CALCULATOR_IDENTITY_ADDENDUM_009.md','OPERAND_METADATA_VERIFICATION_ADDENDUM_010.md',
    'PURE_IMPLEMENTATION_RELEASE_070.md','NATIVE_REPOSITORY_RELEASE_071.md'):
    full.append(parents+'visual_signal_parent_review_067/'+name)
for suffix in ('a105_visual_signal_reader_070/HANDOFF_017.md','a105_visual_signal_reader_repair_074/HANDOFF_007.md',
    'a105_visual_signal_repository_071/IMPLEMENTATION_ADDENDUM_006.md','a105_visual_signal_repository_repair_075/IMPLEMENTATION_003.md',
    'pure_reader_parent_review_070/REPAIRED_ROOT_RECEIPT_002.json','native_ratio_source_parent_review_071/REPOSITORY_ROOT_RECEIPT_001.json',
    'a105_visual_signal_design_067/INTERPRETATION_TASK_005.md','a105_visual_signal_design_067/PROPOSAL_AMENDMENT_004.md',
    'a105_visual_signal_design_067/PROPOSAL_AMENDMENT_005.md','a105_visual_signal_design_067/PROPOSAL_AMENDMENT_006.md'):
    full.append(parents+suffix)
def receipt(path, read):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        'bytes': len(data), 'lines': len(data.splitlines()), 'sha256': hashlib.sha256(data).hexdigest(), 'actual_read': read}
records = [receipt(ROOT/name, 'complete source/document read in sequential tool outputs; design-only') for name in full]
for name, ranges in {
    'gene_annotation_episode/runtime.py': [[790,1578],[1808,2239],[2383,2510],[2561,2626],[3189,3329],[3432,3627],[3675,3868]],
    'gene_annotation_episode/tools.py': [[466,696],[1438,1476]],
    'method_loop/episode.py': [[1016,1833]],
}.items():
    records.append(receipt(ROOT/name, {'complete_function_or_class_paths_read_at_line_ranges': ranges,
        'unrelated_file_regions_not_claimed_read': True}))
attachment = Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
records.insert(0, receipt(attachment, 'complete active attachment read FIRST, before design/code consumers'))
write('READ_PROVENANCE_001.json', {'scope': '077 actual design reads; not inherited parent read claims',
    'files': records, 'paper_or_retained_packet_opened': False,
    'clarification': 'Existing test source referencing primary fixture paths was read as code; no fixture function/test was invoked and no retained scientific source bytes were opened.',
    'early_aggregate_output_truncation': 'Early aggregated authority output truncated. Relevant documents were subsequently read in smaller complete outputs; inherited receipts are not substituted for077 source inspection.',
    'production_or_test_edits': False, 'workflow_or_model_or_hpc_or_acquisition': False,
    'latest_root_feedback': ['No blanket numeric-label suppression; preserve numeric identity/context meanings.',
        'Exact008 has no new evaluation_scope/numeric-location return fields. Show concrete rendering and limitations before code.']})
write('DESIGN_ARTIFACT_CHECK_001.json', {'scope': 'schema capture and offline TASK assembly only',
    'original_operation_count': len(old_ops), 'original_return_namespace_count': len(old_facts),
    'proposed_operation_count': len(tools), 'proposed_return_namespace_count': len(old_facts)+1,
    'parent_task_exact_occurrences': parent.count(REFERENCE_PARENT_TASK),
    'new_child_insert_exact_occurrences': child.count(RATIO_TASK),
    'workflow_actions_executed': 0, 'model_calls': 0, 'controller_observations': 0,
    'production_code_written': False, 'existing_tests_written': False})
