"""Selected metadata inputs through real Workflow; only choices/HTTP are synthetic.

The existing MinhashRun is shared by other test families and stays unchanged.
This fixture reuses its transport, run/reopen helpers and selected scientific
construction. Supplied JSON enters through register_material and a real selected
material.parse action; no source or runtime acquisition row is injected.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.tools import ToolRegistry

from bvbrc_minhash_episode_fixture import (
    MinhashRun, PUBLICATION, RESOURCES, ROOT, SOURCE_FORM, child, fact_form,
    handoff_form, request, result_form, selected,
)


METADATA_FIELDS = ('kmer_length', 'query_length', 'reference_length', 'alphabet_size')
FACT_FAMILIES = ('bvbrc_minhash_matches', 'bvbrc_minhash_counts',
                 'bvbrc_minhash_calculations', 'bvbrc_minhash_calculation_diagnostics')
SYNTHETIC_ROWS = [['83333.1', '0.223144', '0.259259', '2/3']]


def pair(row_index=0, genome_id='83333.1', *, kmer_length=1,
         query_length=2, reference_length=2, alphabet_size=2):
    return dict(row_index=row_index, genome_id=genome_id, kmer_length=kmer_length,
        query_length=query_length, reference_length=reference_length, alphabet_size=alphabet_size)


def metadata_result_form(*families):
    value = result_form()
    value['properties'] = {name: node for name, node in value['properties'].items()
        if name in {'completed', 'references', 'yield'}}
    value['properties'].update(fact_form(*(families or FACT_FAMILIES))['properties'])
    value['required'] = list(value['properties'])
    return value


class SelectedInputFeedbackReached(Exception):
    """Stop only this harness after the actual failed selection reaches feedback."""


class PartialMetadataResultReached(Exception):
    """Stop only this harness after a partial selected result was observed."""


class MetadataRun(MinhashRun):
    """Select input custody, MinHash acquisition and explicit result calculations.

    Resource roles use the production practical estimator. The scripted fixture
    continuation applies only to the ordinary scientific roles, whose credit is
    explicitly zero. It supplies no scientific scoring or production stop rule.
    """

    def __init__(self, store, directory, *, mode='genome', stages=None,
                 stage_modes=None, parent_form=None, result_schema=None,
                 scope=None, material_ref=None, partial=False,
                 selector_transform=None, after_first_result=None,
                 expect_feedback=False, redeliver=False):
        self.store, self.directory = store, Path(directory)
        self.run_id = 'bvbrc-minhash-metadata-workflow-fixture'
        self.sequence = ''.join(line.strip() for line in
            (ROOT / 'cases/gene_001/target.faa').read_text().splitlines()
            if not line.startswith('>'))
        self.scope = deepcopy(scope) if scope is not None else {'subject_refs':
            store.create_problem(raw_sequence=self.sequence, molecule='protein')['subject_refs']}
        self.stages = deepcopy(stages if stages is not None else [[pair()]])
        self.stage_modes = list(stage_modes or ['native_result'] * len(self.stages))
        assert self.stages and len(self.stage_modes) == len(self.stages)
        self.input_document = {'meaning': 'explicit_synthetic_pair_inputs_not_remote_sketch_metadata',
            'stages': deepcopy(self.stages)}
        self.input_bytes = json.dumps(self.input_document, ensure_ascii=False,
            sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        if material_ref is None:
            material = store.register_material(data=self.input_bytes,
                name='explicit synthetic MinHash pair inputs', format='opaque', use='evidence')
        else:
            material = store.get(material_ref)
        self.material_ref = material['id']
        self.supplied_source_ref = material['source_ref']
        self.supplied_artifact_ref = store.get(self.supplied_source_ref)['artifact_ref']
        assert store.get_artifact(self.supplied_artifact_ref) == self.input_bytes
        self.metadata_source = None
        self.parent_form = deepcopy(parent_form if parent_form is not None else fact_form(*FACT_FAMILIES))
        self.result_form = deepcopy(result_schema if result_schema is not None else metadata_result_form())
        self.query = request(mode)
        self.selected_tools = [{'name': name, 'resources': 'api'} for name in
            ('api.bvbrc.minhash.' + mode, 'api.bvbrc.minhash.result')]
        self.metadata_tools = [{'name': 'material.parse', 'resources': 'local'}]
        self.api_assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'minhash',
            'service': 'bvbrc_minhash', 'request': self.query, 'endpoint': 'usable_handoff',
            'constraints': {'allowed_resource_ids': ['minhash'], 'allowed_kinds': ['api']}}
        self.launch_assignment = {'version': 'execution_launch_assignment_v1',
            'requests': {'minhash': self.api_assignment}, 'immutable_input_versions': [],
            'constraints': {'allowed_resource_ids': ['minhash'], 'allowed_kinds': ['api']}}
        self.calls, self.contexts, self.selectors = {}, [], []
        self.received_forms, self.result_ids = [], []
        self.scientific_after_result = self.root_after_result = self.received_form = None
        self.metadata_report = self.metadata_episode_id = self.scientific_episode_id = None
        self.partial, self.partial_context, self.partial_episode_id = partial, None, None
        self.selector_transform, self.after_first_result = selector_transform, after_first_result
        self.expect_feedback, self.feedback_context, self.feedback_episode_id = expect_feedback, None, None
        self.redeliver, self.redelivered_form = redeliver, None
        assert not redeliver or len(self.stages) == 1
        self.handoff = None
        tools = ToolRegistry(store)
        factory = ExecutionServiceFactory(RESOURCES, {}, 3, 2, .5)
        application = factory(store, run_id=self.run_id, directory=self.directory,
            tool_registry=tools, tool_catalog=tools.catalog())
        self.descriptor = prepare_scientific_binding(run_directory=self.directory,
            source_directory=PUBLICATION, tool_catalog=tools.catalog(),
            child_roles=('scientific_process', 'launch', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        self.library = ScientificProcessLibrary(self.directory / 'scientific-process-library')

        def controller(path, initial):
            def engineering_estimate(history, parameters, contexts):
                # Ordinary scientific fixture choices only. Every resource
                # endpoint still closes through its real validated proof.
                count = (2 if path[-1][0] == 'annotation' else
                    1 if len(path) == 3 else 3 + len(self.stages))
                return YieldEstimate(len(history), NumericBand.exact(
                    0 if len(history) >= count else 1), parameters,
                    {'fixture': 'engineering_scientific_continuation_only'})
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=engineering_estimate
                if path[-1][0] in {'annotation', 'scientific_process'} else None)

        self.workflow = Workflow(store, tools, self, self.directory, self.run_id,
            controller_factory=controller, project_credit=lambda *_: 0,
            episode_binding_descriptors=(self.descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings,
            job_progress_provider=application.job_progress_provider,
            annotation_child_roles=('scientific_process',),
            episode_record_receipts=True, initial_known_record_refs=[self.material_ref])
        self.episode = self.workflow.build('annotation', 'root',
            'Investigate the supplied protein using selected native measurements', self.scope)

    def commission(self, *, metadata=False):
        assignment = {'selection': {'version': 'scientific_process_selection_v3',
            'evidence_axis': self.library.reference('A101'),
            'thought_pattern': self.library.reference('P01'),
            'child_tool_info': deepcopy(self.metadata_tools if metadata else self.selected_tools)},
            'evidence_refs': [*self.scope['subject_refs'], self.material_ref],
            'constraints': {'preserve_original_query': True},
            'context': {'supplied_sequence': self.sequence, 'molecule': 'protein',
                'complete': True, 'label_is_public_identity': False,
                'metadata_material_ref': self.material_ref,
                'selected_minhash_request': deepcopy(self.query)}}
        return child('scientific_process', assignment, self.scope,
            SOURCE_FORM if metadata else self.parent_form)

    def selector(self, index):
        assert self.metadata_source == self.supplied_source_ref
        supplied = []
        for row_index, native in enumerate(self.stages[index]):
            fields = [{'field': field, 'source_ref': self.metadata_source,
                'artifact_ref': self.supplied_artifact_ref,
                'record_path': f'/stages/{index}/{row_index}/{field}'}
                for field in METADATA_FIELDS if native[field] is not None]
            supplied.append({**deepcopy(native), 'provenance': {
                'kind': 'explicit_retained_pair_inputs', 'query_mode': self.query['mode'],
                'query_operand': self.query['query'], 'native_parameter_equivalence': 'unestablished',
                'fields': fields}})
        saved = None
        if self.stage_modes[index] == 'saved_sheet':
            assert index > 0
            saved = self.result_reference(self.received_forms[index - 1])
        value = {'version': 'bvbrc_minhash_result_selector_v2',
            'mode': self.stage_modes[index], 'saved_result_ref': saved, 'pair_metadata': supplied}
        return value if self.selector_transform is None else self.selector_transform(index, value)

    def result_reference(self, form):
        references = [reference for reference in form['references']
            if self.store.get(reference).get('provider') == 'bvbrc_minhash']
        reference, = references
        return reference

    def results_child(self, index):
        selector = self.selector(index)
        self.selectors.append(deepcopy(selector))
        return child('results', {'version': 'execution_results_assignment_v1',
            'handoff_ref': self.handoff, 'selector': selector}, self.scope, self.result_form)

    async def complete(self, episode_id, role, instructions, current, schema):
        self.calls[episode_id] = self.calls.get(episode_id, 0) + 1
        count = self.calls[episode_id]
        self.contexts.append((episode_id, deepcopy(current)))
        execution = current.get('execution_assignment', {})
        version = execution.get('version')
        if version == 'execution_results_assignment_v1' and count == 2 and self.partial:
            self.partial_context, self.partial_episode_id = deepcopy(current), episode_id
            raise PartialMetadataResultReached
        if current.get('feedback') is not None and self.expect_feedback:
            self.feedback_context, self.feedback_episode_id = deepcopy(current), episode_id
            raise SelectedInputFeedbackReached
        assert current.get('feedback') is None, current.get('feedback')
        if version == 'execution_launch_assignment_v1':
            assert count == 1 and execution == self.launch_assignment
            return child('launch_api', self.api_assignment, self.scope, handoff_form())
        if version == 'api_service_assignment_v1':
            assert count == 1 and execution == self.api_assignment
            return selected('api.bvbrc.minhash.' + self.query['mode'])
        if version == 'execution_results_assignment_v1':
            assert count == 1 and execution['selector'] in self.selectors
            self.result_ids.append(episode_id)
            return selected('api.bvbrc.minhash.result')
        if 'scientific_process' in current:
            if len(self.context(episode_id).path) == 3:
                assert count == 1
                self.metadata_episode_id = episode_id
                return {'selection': {'kind': 'tool', 'tool': 'material.parse',
                    'arguments': {'material_ref': self.material_ref, 'format': 'opaque'}},
                    'report_update': {}}
            self.scientific_episode_id = episode_id
            if self.redeliver and count == 5:
                self.redelivered_form = deepcopy(current['child_reports'][-1])
                self.scientific_after_result = deepcopy(current)
                return self.wait()
            if count == 1:
                assert current['received_minhash_values'] == []
                return self.commission(metadata=True)
            if count == 2:
                self.metadata_report = deepcopy(current['child_reports'][-1])
                sources = [reference for reference in self.metadata_report['references']
                    if self.store.get(reference)['record_type'] == 'source']
                self.metadata_source, = sources
                assert self.metadata_source == self.supplied_source_ref
                return child('launch', self.launch_assignment, self.scope, handoff_form())
            if count == 3:
                returned = current['child_reports'][-1]
                assert returned['completed'] is True
                self.handoff, = returned['references']
                return self.results_child(0)
            previous = count - 4
            assert previous == len(self.received_forms)
            self.received_form = deepcopy(current['child_reports'][-1])
            self.received_forms.append(self.received_form)
            self.scientific_after_result = deepcopy(current)
            if previous == 0 and self.after_first_result is not None:
                self.after_first_result(self)
            if self.redeliver:
                return {'selection': {'kind': 'redeliver_report',
                    'delivery_ref': current['report_deliveries'][-1]['delivery_ref'],
                    'purpose': 'Return only the requested typed native measurements',
                    'schema_json': json.dumps(self.result_form)}, 'report_update': {}}
            if previous + 1 < len(self.stages):
                return self.results_child(previous + 1)
            return self.wait()
        if count == 1:
            return self.commission()
        assert count == 2
        self.root_after_result = deepcopy(current)
        return self.wait()


__all__ = ['MetadataRun', 'METADATA_FIELDS', 'FACT_FAMILIES', 'SYNTHETIC_ROWS',
           'pair', 'metadata_result_form', 'SelectedInputFeedbackReached',
           'PartialMetadataResultReached']
