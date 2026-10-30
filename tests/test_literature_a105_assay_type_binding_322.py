"""A105 delivery of existing numerical reports; synthetic engineering fixtures."""
from dataclasses import replace
import json

from gene_annotation_episode.communication import plain, validate_form, validate_closed_schema, ReportBoundaryError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_contract_information import expand_fact_form
from gene_annotation_episode.literature_a105_worksheet import (
    VERSION, a105_worksheet_template, validate_a105_worksheet_links,
)
from gene_annotation_episode.literature_a105_worksheet_render import render_a105_worksheet
from gene_annotation_episode.literature_completion_time_storage import (
    LiteratureCompletionTimeRepository, completion_time_cells_schema,
)
from gene_annotation_episode.literature_product_partition_storage import (
    LiteratureProductPartitionRepository, product_partition_cells_schema,
)
from gene_annotation_episode.state import Store
from test_a105_partition_time_joined_149 import synthetic_inputs, RAW_NUMBERS


def test_endpoint_duration_and_product_distribution_reach_same_a105_form(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        source, _, times, partition = synthetic_inputs(store)
        context = BindingContext("binding322", "reader", "literature", (("literature", "reader"),),
            store.validate_scope(), {"version": "literature_assignment_v1", "question_context_refs": [],
                "source_refs": [source]}, {}, [source])
        time_repo = LiteratureCompletionTimeRepository(store, context.run_id)
        part_repo = LiteratureProductPartitionRepository(store, context.run_id)
        time_result = time_repo.populate(context, times, "time")
        partition_result = part_repo.populate(context, partition, "partition")
        requests = [
            {"field": "duration", "source": "literature_completion_time_cells", "components": ["completion_time_ratio"]},
            {"field": "composition", "source": "literature_product_partition_cells", "components": ["selected_fraction_sum"]},
        ]
        template = a105_worksheet_template(requests)
        facts = {
            "literature_completion_time_cells": {"type": "array", "meaning": "Requested endpoint durations.",
                "report_schema": completion_time_cells_schema()},
            "literature_product_partition_cells": {"type": "array", "meaning": "Requested product distribution.",
                "report_schema": product_partition_cells_schema()},
        }
        schema = expand_fact_form(json.dumps(template["submitted_form"]), child_role="literature",
            facts_by_role={"literature": facts}, permitted_child_roles=["literature"])["expanded_schema"]
        refs = [source, *time_result["record_refs"], *partition_result["record_refs"]]
        form = {
            "duration": time_repo.project_cells(time_result["record_refs"], permitted_record_refs=refs,
                components=["completion_time_ratio"]),
            "composition": part_repo.project_cells(partition_result["record_refs"], permitted_record_refs=refs,
                components=["selected_fraction_sum"]),
            "assessment_context": {"version": VERSION, "assertion_refs": [], "quantity_links": [], "assertion_links": []},
        }
        validate_form(form, schema, lambda *_: True)
        validate_a105_worksheet_links(form, schema, template["assignment_rosters"], read_public_record=store.get)
        assert form["duration"][0]["status"] == "bounded"
        assert form["composition"][0]["value"] == 1
        records = {row["id"]: row for row in store.list("reference")}
        parts = []
        def table(headers, rows):
            return "\n".join(" | ".join(map(str, row)) for row in [headers, *list(rows)])
        render_a105_worksheet(parts, form, section=lambda out, title, body: out.extend([title, body]),
            table=table, public_records=records)
        rendered = "\n".join(parts)
        assert "Requested preparation completion-time components" in rendered
        assert "Requested product partition components" in rendered
        assert "not independent mass balance" in rendered
        assert "intrinsic rate" in rendered
        assert all(number not in rendered for number in RAW_NUMBERS)

from copy import deepcopy
from functools import partial
from types import SimpleNamespace
import asyncio
import pytest

from gene_annotation_episode.domain import ContractError, obj, validate_schema
from gene_annotation_episode.literature_assay_grading import COMPONENTS, CRITERIA_BY_TYPE, ROLES
from gene_annotation_episode.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository, assay_grading_cells_schema, REQUESTED, NAMESPACE,
)
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController


def grading_fixture(store, assay_type='endpoint_conversion'):
    quantity_kind = dict(activity_rate='rate_ratio', endpoint_conversion='conversion_fraction',
        product_distribution='product_fraction', reaction_coupling='productive_fraction')[assay_type]
    unit = 'dimensionless' if assay_type == 'activity_rate' else 'fraction'
    lines = [
        'Experiment A: synthetic assay for one reference molecule. Scientific applicability and a known normal fixed-prediction model are explicitly stipulated for this synthetic fixture.',
        f'effect 0.8 {unit}; variance 0.04 {unit}_squared;',
        'recovery 0.9 fraction; attributed 0.6 fraction; total 0.8 fraction;',
        'condition test 0.8 fraction; condition reference 1 fraction;',
        f'assertion prediction 1 {unit}; alternative prediction 0 {unit}.',
        f'Experiment B: effect 0.2 {unit}; variance 0.09 {unit}_squared.',
    ]
    text = '\n'.join(lines)
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_assay_grading_322', 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': None, 'retrieved_at': None}, origin='caller')['id']
    quote = lines[0]
    support = store.put('reference', {'reference_type': 'assay', 'source_ref': source,
        'accession': 'synthetic_assay_322', 'label': 'Experiment A', 'sequence_ref': None,
        'molecule': None, 'length': None, 'term_refs': [], 'context_refs': [],
        'anchor': {'source_ref': source, 'artifact_ref': artifact, 'start': 0,
            'end': len(quote), 'quote': quote}}, origin='caller')['id']
    reaction = store.put('term', {'namespace': 'synthetic', 'accession': 'reaction322',
        'label': 'Synthetic reaction', 'term_type': 'reaction', 'source_ref': source,
        'anchor': None}, origin='caller')['id']
    assertion = store.put('hypothesis', {'subject_refs': [support], 'predicate': 'catalyzes',
        'value': {'type': 'term_ref', 'ref': reaction}, 'context_refs': []}, origin='reasoning')['id']
    def witness(quote, start=0):
        offset = text.index(quote, start)
        return {'source_ref': source, 'representation': 'original', 'start': offset,
            'end': offset + len(quote), 'quote': quote}
    def number(label, token, native_unit):
        fragment = label + ' ' + token + ' ' + native_unit
        start = text.index(fragment)
        return {'kind': 'source_number', 'number': {'witness': witness(fragment),
            'number_start': len(label) + 1, 'number_end': len(label) + 1 + len(token)},
            'unit': witness(native_unit, start + len(label) + 1 + len(token) + 1), 'origin': 'synthetic'}
    args = {'source_ref': source, 'source_kind': 'synthetic_fixture', 'assay_type': assay_type,
        'assertion_ref': assertion, 'experiment_ref': support, 'quantity_kind': quantity_kind,
        'interpretations': {name: {'status': 'supported', 'support_refs': [support]}
            for name in CRITERIA_BY_TYPE[assay_type]},
        'prediction_model': {'kind': 'fixed_predictions_known_normal', 'variance_interpretation': 'known',
            'support_refs': [support]},
        'quantities': {
            'effect': number('effect', '0.8', unit),
            'effect_variance': number('variance', '0.04', unit + '_squared'),
            'recovery': number('recovery', '0.9', 'fraction'),
            'attributed_signal': number('attributed', '0.6', 'fraction'),
            'total_signal': number('total', '0.8', 'fraction'),
            'condition_test': number('condition test', '0.8', 'fraction'),
            'condition_reference': number('condition reference', '1', 'fraction'),
            'assertion_prediction': number('assertion prediction', '1', unit),
            'alternative_prediction': number('alternative prediction', '0', unit),
        }}
    refs = [source, support, assertion]
    context = BindingContext('grading322', 'child', 'literature', (('literature', 'child'),),
        store.validate_scope(), {'version': 'literature_assignment_v1', 'question_context_refs': [support, assertion],
            'source_refs': [source], REQUESTED: list(COMPONENTS)}, {}, refs)
    return context, args, artifact


@pytest.mark.parametrize('assay_type', ['activity_rate', 'endpoint_conversion', 'product_distribution', 'reaction_coupling'])
def test_four_assay_types_persist_same_numerical_dimensions_and_partial_inputs(tmp_path, assay_type):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, _ = grading_fixture(store, assay_type)
        repo = LiteratureAssayGradingRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'selected-grading')
        rows = outcome['result']['cells']
        validate_schema(rows, assay_grading_cells_schema())
        by_name = {r['component']: r for r in rows}
        assert by_name['measured_effect']['value'] == .8
        assert by_name['effect_precision']['value'] == 25
        assert by_name['recovery_deviation']['value'] == pytest.approx(-.1)
        assert by_name['attributed_fraction']['value'] == pytest.approx(.75)
        assert by_name['condition_response']['value'] == .8
        assert by_name['source_log_evidence_ratio']['value'] == pytest.approx(7.5)
        assert by_name['source_log_evidence_ratio']['status'] == 'conditional'
        assert by_name['source_log_evidence_ratio']['input_origins'] == ['synthetic']
        assert not store.list('observation') and not store.list('assessment')
        partial = deepcopy(args)
        partial['quantities']['effect_variance'] = None
        partial['interpretations']['attribution_supported'] = {'status': 'unknown', 'support_refs': []}
        result = repo.populate(context, partial, 'selected-partial')
        partial_rows = {r['component']: r for r in result['result']['cells']}
        assert partial_rows['measured_effect']['value'] == .8
        assert partial_rows['source_log_evidence_ratio']['value'] is None
        assert 'attribution_supported_unknown' in partial_rows['source_log_evidence_ratio']['reasons']
        assert partial_rows['attributed_fraction']['value'] is None


def test_grading_cold_reconstruction_does_not_read_or_recalculate_science(tmp_path, monkeypatch):
    path = tmp_path / 'store'
    with Store(path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, original_artifact = grading_fixture(store)
        repo = LiteratureAssayGradingRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'selected')
        ref = outcome['result']['sheet_ref']
        selected = repo.project_cells([ref], permitted_record_refs=[ref], components=['source_log_evidence_ratio'])
        parent = replace(context, episode_id='parent', role='annotation', path=(('annotation', 'parent'),),
            assignment={}, received_record_refs=[ref, *context.received_record_refs])
        repo.receive_cells(parent, selected, 'manual_trusted_admission')
    def forbidden(*args, **kwargs):
        raise AssertionError('cold reconstruction must use committed grade, without scientific input or arithmetic')
    monkeypatch.setattr('gene_annotation_episode.literature_assay_grading_storage.read_assay_grading_inputs', forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_assay_grading_storage.grade_assay', forbidden)
    with Store(path) as cold:
        original = cold.get_artifact
        def guarded(reference):
            assert reference != original_artifact
            return original(reference)
        monkeypatch.setattr(cold, 'get_artifact', guarded)
        cold.db.execute('PRAGMA query_only=ON')
        changes = cold.db.total_changes
        repo = LiteratureAssayGradingRepository(cold, context.run_id)
        assert repo.read(ref)['sheet']['cells']['source_log_evidence_ratio']['value'] == pytest.approx(7.5)
        assert repo.populate(context, args, 'selected') == outcome
        assert repo.fact_cells(parent, [ref], components=list(COMPONENTS)) == selected
        assert cold.db.total_changes == changes
        altered = deepcopy(selected); altered[0]['value'] = 100
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_fact_values(parent, altered)
        with pytest.raises(ContractError, match='not_received'):
            repo.populate(replace(context, received_record_refs=()), args, 'selected')


@pytest.mark.parametrize('assay_type', ['activity_rate', 'endpoint_conversion', 'product_distribution', 'reaction_coupling'])
def test_selected_grader_delivers_requested_a105_scores_through_actual_loop(tmp_path, assay_type):
    path = tmp_path / 'store'
    with Store(path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        original_context, args, _ = grading_fixture(store, assay_type)
        selected = ['effect_precision', 'source_log_evidence_ratio']
        template = a105_worksheet_template([{'field': 'experiment', 'source': NAMESPACE, 'components': selected}])
        assessment_context = {'version': VERSION, 'assertion_refs': [args['assertion_ref']],
            'quantity_links': [], 'assertion_links': []}
        assignment = {**plain(original_context.assignment), **template['assignment_rosters']}
        child = {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': assignment,
            'goal': 'Evaluate the selected synthetic reference assay using the reusable protocol type.',
            'scope': store.validate_scope(), 'purpose': 'Return the requested A105 numerical evidence components.',
            'schema_json': json.dumps(template['submitted_form']),
            'initial_report_json': json.dumps({'assessment_context': assessment_context})}, 'report_update': {}}
        action = {'selection': {'kind': 'tool', 'tool': 'literature.assay_grading.populate', 'arguments': args},
            'report_update': {'assessment_context': assessment_context}}
        script = iter([child, action])
        contexts, controllers = [], []
        class ControlledProvider:
            async def complete(self, episode_id, role, instructions, context, output_schema):
                contexts.append(context)
                return deepcopy(next(script))
            async def release(self, episode_id):
                pass
        def controller(path, initial):
            result = FixtureController(str(path), initial, 1)
            controllers.append(result)
            return result
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ControlledProvider(),
            run_dir=tmp_path / 'run', controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(original_context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                assay_grading_population=True, reference_parent_sources=[args['source_ref']]),),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0
        assert len(contexts) == 2 and [c.scores for c in controllers] == [[0], [0]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 2
        operation = store.db.execute('SELECT * FROM literature_assay_grading_operations').fetchone()
        outcome = json.loads(operation['outcome'])
        assert [r['component'] for r in outcome['result']['cells']] == selected
        assert outcome['result']['cells'][1]['value'] == pytest.approx(7.5)
        receipt = store.db.execute('SELECT * FROM literature_assay_grading_received').fetchone()
        assert receipt is not None
        rows = json.loads(receipt['cells'])
        assert rows == outcome['result']['cells']
        assert not store.list('observation') and not store.list('assessment')
        descriptor = json.loads((tmp_path / 'run' / 'run.json').read_text())['episode_bindings'][0]
        assert descriptor['configuration']['assay_grading_population'] is True
        services = WorkflowServices(SimpleNamespace(store=store, run_id=operation['run_id']))
        reconstructed, = compose_episode_bindings(services, store=store,
            journal=SimpleNamespace(store=store, run_id=operation['run_id']), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None,
            role_credit_bindings={}).bindings
        assert reconstructed.as_record() == descriptor
        parent = BindingContext(operation['run_id'], receipt['episode_id'], 'annotation',
            (('annotation', receipt['episode_id']),), store.validate_scope(), {}, {},
            reconstructed._assay_grading_repository().cell_record_refs(rows))
        assert reconstructed._assay_grading_repository().fact_cells(parent,
            outcome['record_refs'], components=list(COMPONENTS)) == rows


def test_measured_only_grade_does_not_expand_other_interpretations_or_change_original_request(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, _ = grading_fixture(store)
        context = replace(context, assignment={**dict(context.assignment), REQUESTED: ['measured_effect']})
        repo = LiteratureAssayGradingRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'selected')
        row, = outcome['result']['cells']
        assert row['component'] == 'measured_effect'
        assert row['interpretations'] == {} and row['prediction_model'] is None
        assert row['source_refs'] == [args['source_ref']]
        with pytest.raises(ContractError, match='operation_key_reused'):
            repo.populate(replace(context, assignment={**dict(context.assignment), REQUESTED: list(COMPONENTS)}),
                args, 'selected')


def test_existing_rate_reader_populates_grade_through_bound_received_cell_path(tmp_path):
    from test_literature_rate_storage import setup_store
    store, rate_context, rate_args = setup_store(tmp_path)
    with store:
        context, args, _ = grading_fixture(store, 'activity_rate')
        combined = replace(context, received_record_refs=[*context.received_record_refs, rate_args['source_ref']],
            assignment={**plain(context.assignment), 'source_refs': [args['source_ref'], rate_args['source_ref']]})
        services = WorkflowServices(SimpleNamespace(store=store, run_id=context.run_id))
        binding = LiteratureEpisodes(services, rate_population=True, assay_grading_population=True)
        rate_repo = services.literature_rate_repository()
        rate_outcome = rate_repo.populate(combined, rate_args, 'existing-rate-reader')
        combined = replace(combined, received_record_refs=[*combined.received_record_refs, *rate_outcome['record_refs']])
        native_ref = rate_outcome['result']['sheet_ref']
        args['quantities'] = dict.fromkeys(ROLES)
        args['quantities']['effect'] = {'kind': 'received_component', 'namespace': 'literature_rate_cells',
            'sheet_ref': native_ref, 'component': 'rate_difference'}
        args['quantity_kind'] = 'rate_difference'
        args['prediction_model'] = None
        args['interpretations'] = {name: {'status': 'unknown', 'support_refs': []}
            for name in CRITERIA_BY_TYPE['activity_rate']}
        repo = binding._assay_grading_repository()
        outcome = repo.populate(combined, args, 'grade-existing-rate')
        values = {row['component']: row for row in outcome['result']['cells']}
        assert values['measured_effect']['value'] == 1
        assert values['measured_effect']['unit'] == 'umol/min'
        assert values['source_log_evidence_ratio']['value'] is None
        saved = repo.read(outcome['result']['sheet_ref'])
        native = rate_repo.fact_cells(combined, [native_ref], components=['rate_difference'])
        assert saved['input_component_rows'] == [{'namespace': 'literature_rate_cells',
            'sheet_ref': native_ref, 'components': ['rate_difference'], 'rows': native}]
        # Mere possession of the full sheet identifier cannot grant another
        # episode native numerical fields that were never delivered to it.
        other = replace(combined, episode_id='other', path=(('literature', 'other'),))
        with pytest.raises(ContractError, match='component_not_received'):
            repo.populate(other, args, 'unreceived-native-component')


def test_grading_contract_requires_exact_registered_top_level_schema():
    schema = obj({'experiment': assay_grading_cells_schema()})
    validate_closed_schema(schema)
    changed = deepcopy(schema)
    changed['properties']['experiment']['items']['properties']['meaning'] = {'type': 'number'}
    with pytest.raises(ReportBoundaryError, match='registered source'):
        validate_closed_schema(changed)
    nested = obj({'wrapper': obj({'experiment': assay_grading_cells_schema()})})
    with pytest.raises(ReportBoundaryError, match='whole top-level fields'):
        validate_closed_schema(nested)


def test_grade_render_uses_context_from_all_delivered_cells_and_no_private_context(tmp_path):
    from gene_annotation_episode.literature_assay_grading import CRITERION_QUESTIONS
    from gene_annotation_episode.literature_assay_grading_render import render_received
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, _ = grading_fixture(store)
        repo = LiteratureAssayGradingRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'render-grade')
        ref = outcome['result']['sheet_ref']
        def rendered(components):
            parts = []
            rows = repo.project_cells([ref], permitted_record_refs=[ref], components=components)
            render_received(parts, rows, section=lambda out, title, body: out.extend((title, body)),
                table=lambda headers, rows: '\n'.join(' | '.join(map(str, row)) for row in [headers, *rows]))
            return '\n'.join(parts)
        combined = rendered(['measured_effect', 'source_log_evidence_ratio'])
        assert CRITERION_QUESTIONS['attribution_supported'] in combined
        assert 'fixed_predictions_known_normal' in combined
        assert '7.5' in combined
        measured = rendered(['measured_effect'])
        assert CRITERION_QUESTIONS['attribution_supported'] not in measured
        assert 'fixed_predictions_known_normal' not in measured
        assert ref not in combined and args['assertion_ref'] not in combined
