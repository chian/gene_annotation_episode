"""Opt-in genuine ordinary HOMER publication through the existing episode method.

Scripted choices select supplied test inputs and fields. All native outputs,
Sources, actions, forms and receipts are produced by the ordinary owners. An
audit prefix survives a later failure so recovery observes the same attempt.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import zipfile

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode import homer_motif_measurements as measurements
from gene_annotation_episode import homer_motif_result_contracts as contracts
from gene_annotation_episode import homer_motif_tools as host
from gene_annotation_episode import native_homer_execution as native
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = 'research/slotted_process_library/publications/2026-10-24-001'
RUN_ID = 'ordinary-homer-genuine-public-workflow'
QUESTION = ('For the supplied target BED, background BED and reference FASTA, which known and '
    'de novo motifs does the selected HOMER wrapper report under the supplied parameters? '
    'Return the first two known motif occurrences, captured-series counts, population facts '
    'and their native statistics and qualifications. Preserve the selected de novo series '
    'for a later explicit retained-data selection.')
PARAMETERS = dict(window_bp=200, motif_lengths=[8, 10, 12], num_motifs=10, threads=1,
    strand='both', statistic='binomial', normalization=dict(composition='gc', oligo_length=3,
        max_iterations=160, neutral=False), motif_set='all')
COUNTS = ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls',
    'tool_operations', 'runtime_forms', 'runtime_report_attempts')


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def _pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _json(path):
    return json.loads(Path(path).read_bytes())


def _selected_binding(directory):
    """Build an explicit test binding from selected, already qualified assets."""
    attempt = Path(os.environ['HMMER529_ATTEMPT']).resolve(strict=True)
    assert ROOT == attempt / 'source_snapshot'
    selected = _json(attempt / 'selected_request.json')
    assert selected['policy'] == native.POLICY and selected['swap_bytes'] == 0
    original = Path(os.environ['HMMER_NATIVE_ORACLE_HOMER_DEPLOYMENT']).resolve(strict=True)
    historical = _json(original / 'selection.json')
    deployment_files = []
    for row in _json(original / 'owned_runtime_pins_after.json'):
        assert _pin(row['path']) == row
        path = Path(row['path'])
        assert path.is_relative_to(original) and not path.is_symlink()
        deployment_files.append(dict(relative_path=str(path.relative_to(original)),
            sha256=row['sha256'], size_bytes=row['size_bytes'], mode=stat.S_IMODE(path.stat().st_mode)))
    system = {}
    for row in [*historical['core_programs'].values(),
            *(r['file'] for r in historical['additional_elf_inputs']), *historical['os_data_inputs']]:
        assert _pin(row['path']) == row
        assert row['path'] not in system or system[row['path']] == row
        system[row['path']] = row
    correction = historical['extractor_build']['controls']['build_report.json']
    assert _pin(correction['path']) == correction
    deployment = dict(version='homer_native_deployment_v1', root=str(original),
        files=deployment_files, system_files=list(system.values()), corrections=dict(
            extractor_build_report=correction, svg_repair_record=_pin(original / 'deployment_changes.json')))
    software_files = {}
    for name in ('source', 'dependency', 'stdlib', 'binary', 'native_library'):
        for row in _json(attempt / (name + '_pins_before.json')):
            if name == 'source' and Path(row['path']).suffix not in ('.py', '.so'):
                continue
            assert Path(row['path']).name.lower() not in {'agents.md', 'agent.md', 'goal.md'}
            assert _pin(row['path']) == row
            assert row['path'] not in software_files or software_files[row['path']] == row
            software_files[row['path']] = row
    inventory = directory / 'selected-software-files.json'
    _write(inventory, dict(version='homer_native_software_files_v1', files=list(software_files.values())))
    software = dict(version='homer_native_software_v1', python=_pin(attempt / 'runtime/bin/python'),
        python_home=str(attempt / 'runtime'), python_version=sys.version,
        import_roots=[str(ROOT), str(attempt / 'dependencies')], software_files_file=_pin(inventory))
    binding = dict(version='homer_native_binding_v1', operation=contracts.TOOL, variant=native.VARIANT,
        deployment=deployment, software=software, input_staging=dict(mode='verified_copy', max_total_bytes=1024**2))
    assert native.validate_homer_bindings([binding]) == [binding]
    return binding


def _input_files(store):
    archive = ROOT / 'tests/fixtures/homer_v51_selected_region_inputs.zip'
    assert _pin(archive)['sha256'] == '26b0ff374d31cd3aae34c143d0bd93d36dc6da4e35af8f73ee1a0967af250180'
    inputs, initial = [], []
    with zipfile.ZipFile(archive) as stream:
        assert stream.testzip() is None
        manifest = json.loads(stream.read('manifest.json'))
        for row in manifest['files']:
            raw = stream.read(row['member'])
            assert len(raw) == row['size_bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
            reference = store.artifact(raw, 'application/octet-stream')
            assert reference == 'artifact_' + row['sha256']
            inputs.append(dict(role=row['role'], namespace='artifact', reference=reference))
            initial.append(reference)
    assert [row['role'] for row in inputs] == ['target_bed', 'reference_fasta', 'background_bed']
    return inputs, initial


def _form():
    return obj(dict(motifs=contracts.homer_motif_fact_sources()[contracts.FACT_SOURCE]['report_schema']))


def _controller(path, initial):
    return FixtureController(str(path), initial, 1)


def _credit(*args, **kwargs):
    return 0


class _Choices:
    def __init__(self, library, scope, arguments):
        self.library, self.scope, self.arguments = library, scope, arguments
        self.contexts, self.responses = [], []

    async def complete(self, episode_id, role, instructions, context, schema):
        index = len(self.contexts)
        self.contexts.append(deepcopy(context))
        assert role == 'REASONING' and index < 2 and context['feedback'] is None
        assert context['goal']['objective'] == QUESTION
        if index == 0:
            value = dict(selection=dict(kind='episode_child', role='scientific_process', goal=QUESTION,
                scope=deepcopy(self.scope), purpose='Return the assigned HOMER native measurements and qualifications.',
                schema_json=json.dumps(_form()), initial_report_json='{}', assignment=dict(
                    selection=dict(version='scientific_process_selection_v3',
                        evidence_axis=self.library.reference('A103'), thought_pattern=self.library.reference('P01'),
                        child_tool_info=[dict(name=contracts.TOOL, resources='local')]),
                    evidence_refs=[], constraints={}, context=dict(homer_request=deepcopy(self.arguments)))),
                report_update={})
        else:
            assert context['requested_form'] == _form()
            assert context['scientific_process']['assignment']['context']['homer_request'] == self.arguments
            information, = [row for row in context['tools'] if row['name'] == contracts.TOOL]
            assert information['resources'] == 'local' and information['description'] == host.DESCRIPTION
            value = dict(selection=dict(kind='tool', tool=contracts.TOOL,
                arguments=deepcopy(self.arguments)), report_update={})
        fields = [branch['properties'] for branch in schema['properties']['selection']['anyOf']
            if all(value['selection'][key] in branch['properties'].get(key, {}).get('enum', [])
                for key in ('kind', 'role', 'tool') if key in value['selection'])]
        assert len(fields) == 1
        for key in ('assignment', 'arguments'):
            if key in value['selection'] and fields[0][key].get('type') == 'string':
                value['selection'][key] = json.dumps(value['selection'][key], allow_nan=False)
        if value['selection']['kind'] == 'episode_child':
            for key in fields[0]['scope']['required']:
                if key not in value['selection']['scope']:
                    assert {'type': 'null'} in fields[0]['scope']['properties'][key]['anyOf']
                    value['selection']['scope'][key] = None
        Draft202012Validator(schema).validate(value)
        self.responses.append(deepcopy(value))
        return value

    async def release(self, episode_id):
        pass


def _prefix(store, workflow, proof):
    proof['counts'] = {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in COUNTS}
    for table in ('runtime_episodes', 'runtime_actions', 'tool_operations', 'runtime_forms', 'runtime_report_attempts'):
        proof[table] = [dict(row) for row in store.db.execute('SELECT * FROM ' + table + ' ORDER BY rowid')]
    proof['provider_contexts'] = deepcopy(workflow.provider.contexts)
    proof['provider_responses'] = deepcopy(workflow.provider.responses)
    return proof


def test_genuine_ordinary_homer_reaches_scientific_parent(tmp_path, monkeypatch):
    if os.environ.get('HMMER_NATIVE_ORACLE_HOMER_WORKFLOW') != '1':
        pytest.skip('requires explicit bounded genuine HOMER workflow selection')
    prefix = tmp_path / 'HOMER_WORKFLOW_PREFIX.json'
    proof = dict(version='ordinary_homer_workflow_prefix_v1', run_id=RUN_ID,
        question=QUESTION, store_directory=str(tmp_path / 'store'), workflow_directory=str(tmp_path / 'run'),
        native_publication_verified=False, typed_parent_delivery_verified=False,
        qualification='Engineered supplied inputs and scripted episode choices; actual ordinary native results and custody.')
    _write(prefix, proof)
    try:
        binding = _selected_binding(tmp_path)
        workspace = tmp_path / 'native-workspace'
        workspace.mkdir()
        resources = {'selected-homer': dict(kind='local', workspace=str(workspace), policy=deepcopy(native.POLICY),
            native_homer_motif=[binding])}
        environments = [dict(operation=contracts.TOOL, resource_id='selected-homer', binding_ordinal_0based=0,
            environment=deepcopy(native.ENVIRONMENT_SELECTION))]
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5,
            homer_environments=environments, homer_saved_modes=True)
        proof['factory'] = factory.as_record()
        with Store(tmp_path / 'store') as store:
            subject, = store.create_problem(raw_sequence='ACGT', molecule='dna')['subject_refs']
            inputs, initial = _input_files(store)
            initial.insert(0, subject)
            scope = store.validate_scope()
            arguments = dict(mode='run_native', inputs=inputs, parameters=deepcopy(PARAMETERS),
                selection=dict(series=[dict(role='known_results'), dict(role='denovo_pwm', motif_length=8)], offset=0, limit=2))
            tools = ToolRegistry(store, job_limits=deepcopy(native.POLICY))
            factory.configure_tool_registry(tools)
            contract = tools.catalog()[contracts.TOOL]
            assert contract['instructions'] == host.INSTRUCTIONS
            assert contract['invocation_route'] == dict(kind='direct')
            proof['selected_tool_contract'] = contract
            directory = tmp_path / 'run'
            scientific = prepare_scientific_binding(run_directory=directory, source_directory=ROOT / PUBLICATION,
                tool_catalog=tools.catalog(), child_roles=['scientific_process'])
            library = ScientificProcessLibrary(directory / 'scientific-process-library')
            provider = _Choices(library, scope, arguments)
            application = factory(store, run_id=RUN_ID, directory=directory, tool_registry=tools)
            workflow = Workflow(store, tools, provider, directory, RUN_ID, _controller, _credit,
                project_child_credit=_credit, episode_binding_descriptors=[scientific,
                    *application.episode_binding_descriptors], role_credit_bindings=application.role_credit_bindings,
                job_progress_provider=application.job_progress_provider, episode_record_receipts=True,
                initial_known_record_refs=initial)
            proof.update(subject_ref=subject, scope=scope, arguments=arguments, initial_known_record_refs=initial,
                scientific_binding=scientific, scientific_library=library.as_record())
            root = workflow.build('annotation', 'root', QUESTION, scope)
            _write(prefix, proof)
            try:
                completed = asyncio.run(root.run_async(workflow.context))
            finally:
                _write(prefix, _prefix(store, workflow, proof))
            operation, = list(store.db.execute('SELECT * FROM tool_operations'))
            outcome = json.loads(operation['result'])
            assert outcome['status'] in ('completed', 'partial')
            public = contracts.validate_homer_motif_return(outcome['result'])
            assert outcome['record_refs'] == [public['source_ref']]
            source = store.get(public['source_ref'])
            assert source['origin'] == 'tool' and source['provider'] == contracts.TOOL
            assert source['version'] == contracts.SOURCE_VERSION
            capture = store.get(source['parent_source_refs'][0])
            assert capture['version'] == contracts.CAPTURE_VERSION and capture['accession'] == operation['id']
            custody = json.loads(store.get_artifact(capture['request_ref']))
            execution = native.validate_homer_execution(custody['native_execution'])
            assert execution['terminal'] is execution['quiescent'] is True
            assert execution['execution']['wrapper_returncode'] == 0
            assert execution['plan']['identity']['operation_key'] == operation['operation_key']
            control = json.loads(store.get_artifact(source['request_ref']))
            sheet = json.loads(store.get_artifact(control['sheet_file']['artifact_ref']))
            components = json.loads(store.get_artifact(control['components_file']['artifact_ref']))
            assert canonical(measurements.calculate_homer_components(sheet, selector=public['selector'])) == canonical(components)
            assert measurements.project_homer_return(components, source_ref=source['id']) == public
            assert public['population_facts']['unique_joined_target_members'] == 100
            assert public['population_facts']['unique_joined_background_members'] == 1000
            assert public['population_facts']['observed_sequence_lengths_bp'] == [201]
            assert public['counts'][0]['captured_occurrences'] == 1049
            assert public['counts'][0]['selected_occurrences'] == 2
            assert public['counts'][1]['role'] == 'denovo_pwm'
            assert public['counts'][1]['capture_state'] == 'complete'
            assert public['counts'][1]['captured_occurrences'] > 0
            records = EpisodeReturnRecords(store, RUN_ID, failure_prefix='homer_workflow_')
            rows = list(store.db.execute('SELECT * FROM runtime_episodes ORDER BY json_array_length(path)'))
            assert len(rows) == 2
            parent, child = [records.context(row['episode_id']) for row in rows]
            form = json.loads(store.db.execute('SELECT form FROM runtime_forms WHERE episode_id=?',
                (child.episode_id,)).fetchone()[0])
            assert form == dict(motifs=[public])
            attempt, = list(store.db.execute('SELECT * FROM runtime_report_attempts'))
            assert attempt['failure'] is None and json.loads(attempt['form']) == form
            assert workflow.services.molecular_frozen_facts(child, fact_source=contracts.FACT_SOURCE) == [public]
            assert workflow.services.molecular_received_facts(parent, fact_source=contracts.FACT_SOURCE) == [public]
            private = {source['artifact_ref'], source['request_ref'], *source['auxiliary_artifact_refs'],
                capture['id'], capture['artifact_ref'], capture['request_ref'], *capture['auxiliary_artifact_refs']}
            assert private.isdisjoint(initial)
            for context in (parent, child):
                known = set(workflow.receipts.known(context.episode_id))
                assert set(initial) | {source['id']} <= known and private.isdisjoint(known)
                resolver = workflow.resolver(plain(context.scope), context=context)
                for reference in private:
                    assert resolver(reference, 'source' if reference == capture['id'] else 'artifact') is False
                assert host.read_retained_homer_publication(tools, context,
                    workflow.services.read_received_molecular_input, source['id']) == public
                assert set(workflow.receipts.known(context.episode_id)) == known
            final = plain(asyncio.run(root.build_result(completed)).as_record())
            assert final == dict(credit=0, pending_handles=[])
            assert proof['counts'] == dict(runtime_episodes=2, runtime_actions=2, runtime_observations=2,
                runtime_model_calls=2, tool_operations=1, runtime_forms=1, runtime_report_attempts=1)
            proof.update(native_publication_verified=True, typed_parent_delivery_verified=True,
                source=source, capture_source=capture, native_execution=execution, returned=form,
                final_result=final, saved_calculation_and_closed_replay_verified=False)
    except BaseException as error:
        proof['failure'] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        database = tmp_path / 'store/state.sqlite3'
        if database.is_file():
            proof['database_file'] = _pin(database)
        _write(prefix, proof)
