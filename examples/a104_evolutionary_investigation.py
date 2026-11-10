"""Fresh A104 scientific decisions over exact, authenticated real HPC evidence.

The host commissions A104 once. The configured model chooses scientific
measurements, descendants, interpretation and further shared-parent work.
Retained execution is labelled; no expected biological answer is supplied.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import uuid

from gene_annotation_episode.workflow_budget import active_budget
from gene_annotation_episode.a104_investigation import A104ServiceFactory, A104Subtree
from gene_annotation_episode.a104_tools import A104ToolRegistry, NAMES
from gene_annotation_episode.a104_publication import received_measurement
from gene_annotation_episode.a104_credit import A104EvolutionaryCredit
from gene_annotation_episode.evidence_root import create_evidence_root_workflow, NativeEvidenceRootCredit
from gene_annotation_episode.providers import load_config
from gene_annotation_episode.serial_model_resources import SerialModelConnection as ModelConnection
from gene_annotation_episode.runtime import controller_from_settings
from gene_annotation_episode.state import Store
from gene_annotation_episode.decision_context import PROTOCOL
from gene_annotation_episode.domain import obj
from gene_annotation_episode.a104_hpc import native_body
from gene_annotation_episode.a104_investigation import parent_generation_schema
from gene_annotation_episode.hpc_monitoring import MonitorCheckpoint
from gene_annotation_episode.hpc_scheduler import register_resume
from datetime import datetime, timezone


class CalendarCheckpoint(Exception):
    def __init__(self, request):
        self.request = request


class CommissionedParent:
    """A single caller-owned commission; subsequent choices use the real model."""
    def __init__(self, connection, store, directory, prepared, evidence):
        self.connection, self.store, self.directory = connection, store, directory
        self.prepared, self.evidence = prepared, evidence

    def has_session(self, episode_id, role):
        return self.connection.has_session(episode_id, role)

    def conversation_key(self, episode_id, role):
        return self.connection.conversation_key(episode_id, role)

    async def release(self, episode_id):
        await self.connection.release(episode_id)

    async def complete(self, episode_id, role, instructions, frame, output_schema):
        actual = self.store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                                       (self.run_id, episode_id)).fetchone()
        episode_role = json.loads(actual[0])[-1][0] if actual is not None else None
        done = self.store.db.execute('SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=? '
            'AND result IS NOT NULL', (self.run_id, episode_id)).fetchone()
        if self.integrated and episode_role == 'hpc':
            # The integration experiment explicitly exercises the predictive
            # sister. Its model choices and grading are real; no useful-history
            # or accuracy claim is supplied by this host commission.
            predicted = self.store.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=? "
                "AND json_extract(action,'$.role')='hpc_prediction'", (self.run_id, episode_id)).fetchone()
            state = frame.get('fields', frame)
            if predicted is None and 'hpc_child_commission' in state:
                return {'response': {'response_type': 'select_action', 'selection': {
                    'kind': 'episode_child', 'role': 'hpc_prediction', 'scope': state['hpc_child_scope'],
                    'goal': 'Inspect compatible historical timing and CPU/RAM measurements for this exact A104 '
                        'portfolio. Refresh shared history and compare the declared workload using the shared '
                        'model. Preserve missing capacity and held-out support as unknown; improve the model '
                        'only with genuine disjoint measured data. Preparation and launch belong to execution.',
                    'purpose': 'Validate the live predictive sister and return its actual shared model before execution.',
                    'schema_json': json.dumps(state['hpc_report_form']), 'initial_report_json': '{}',
                    'assignment': {**state['hpc_child_commission'], 'owner_episode_id': state['hpc_owner_episode_id']}},
                    'report_update': {}}}
        if episode_role == 'scientific_process':
            # Input decoding is deterministic. Give the scientific model the
            # native reader's actual tree inventory before it chooses branches,
            # comparisons or new work. A native Source is already admitted;
            # it must not be mistaken for an unexecuted request or raw receipt.
            known = self.workflow.receipts.known(episode_id)
            native_refs = sorted(ref for ref in known if native_body(self.store, ref) is not None)
            inspected = {row[0] for row in self.store.db.execute("SELECT json_extract(action,'$.arguments.native_ref') "
                "FROM runtime_actions WHERE run_id=? AND episode_id=? AND json_extract(action,'$.tool')='phylogeny.inspect' "
                "AND json_extract(result,'$.status')='completed' "
                "AND json_type(result,'$.result.corresponding_relationships')='array'", (self.run_id, episode_id))}
            unread = [ref for ref in native_refs if ref not in inspected]
            if unread:
                return {'response': {'response_type': 'select_action', 'selection': {'kind': 'tool',
                    'tool': 'phylogeny.inspect', 'arguments': {'native_ref': unread[0]}}, 'report_update': {}}}
            instructions += '\nNative split indices are local to each analysis. Use the native inspection\'s '
            instructions += 'corresponding_relationships identities when testing the same relationship across models. '
            instructions += 'Membership overlap between different compatible edges is not model instability. '
            instructions += 'If an earlier comparison used such edges, measure their corresponding native branches '
            instructions += 'and compare those actual measurements before interpreting robustness.'
        if episode_role == 'annotation':
            known = set(self.workflow.receipts.known(episode_id))
            evidence = sorted(ref for ref in known if native_body(self.store, ref) is not None)
            # An earlier development run could have compared different
            # compatible edges by reusing a split ordinal. The original child
            # stays closed. Its parent commissions one explicit review using
            # received native data and the corrected relationship inventory.
            from gene_annotation_episode.a104_interpretation import compare_placements
            for reference in sorted(known):
                measured = received_measurement(self.store, reference)
                if measured is None or measured['body']['schema'] != 'a104_robustness_v1':
                    continue
                placement_refs = measured['body']['placement_refs']
                if not set(placement_refs) <= known:
                    continue
                try:
                    compare_placements(self.store, placement_refs, known)
                except ValueError as error:
                    if str(error) != 'a104_distinct_compatible_branches_are_not_replicate_tests':
                        continue
                else:
                    continue
                reviewed = self.store.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=? "
                    "AND json_extract(action,'$.assignment.context.correspondence_review_ref')=?",
                    (self.run_id, episode_id, reference)).fetchone()
                if reviewed is None:
                    selection = A104Subtree(self.directory/'workflow').commission(self.store,
                        target_ref=self.prepared['target_ref'], scope=self.prepared['scope'], evidence_refs=evidence,
                        child_tool_info=[{'name': name, 'resources': 'local'} for name in
                                         (*NAMES, 'source.read', 'state.query', 'sequence.inspect')],
                        question='Review the received robustness comparison: its selected splits were different '
                            'compatible edges, so their membership overlap does not establish model instability. '
                            'Use phylogeny.inspect corresponding_relationships to identify the same physical '
                            'target/reference relationship across existing native analyses. Reuse valid received '
                            'placement measurements and measure any missing corresponding native branch. '
                            'Run the actual comparison tool and report its support and attribution limits. '
                            'This review uses existing original native outputs; no new alignment or inference is needed.',
                        context={'correspondence_review_ref': reference,
                            'native_evidence_refs': evidence, 'original_placement_refs': placement_refs,
                            'review_provenance': 'explicit_host_commission_after_legacy_noncorresponding_comparison; '
                                'fresh_model_scientific_choices; retained_original_native_outputs'})
                    return {'response': {'response_type': 'select_action', 'selection': selection, 'report_update': {}}}
            hpc_results = sorted(ref for ref in known if self.store.get(ref).get('provider') == 'episode.hpc_result')
            typed_needs = [ref for ref in known if self.store.get(ref).get('provider') == 'host.a104.analysis_need']
            if self.integrated and not evidence and hpc_results:
                return {'response': {'response_type': 'select_action', 'selection': {'kind': 'tool',
                    'tool': 'phylogeny.import_hpc', 'arguments': {'request_ref': self.prepared['native_request_ref'],
                        'hpc_result_ref': hpc_results[-1]}}, 'report_update': {}}}
            original_hpc = self.store.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=? "
                "AND json_extract(action,'$.role')='hpc'", (self.run_id, episode_id)).fetchone()
            if self.integrated and not evidence and typed_needs and original_hpc is None:
                need = json.loads(self.store.get_artifact(self.store.get(typed_needs[-1])['artifact_ref']))
                hpc_schema = obj({'hpc_result_refs': {'type': 'array', 'items': {'type': 'string',
                    'format': 'reference', 'x-reference-namespace': 'source'}, 'uniqueItems': True,
                    'x-source': 'hpc_result_refs'}})
                return {'response': {'response_type': 'select_action', 'report_update': {}, 'selection': {
                    'kind': 'episode_child', 'role': 'hpc', 'scope': self.prepared['scope'],
                    'goal': self.prepared['hpc_commissions']['a104-native']['objective'],
                    'purpose': 'Fulfil the exact received A104 native-analysis need through the shared execution parent.',
                    'schema_json': json.dumps(hpc_schema), 'initial_report_json': '{}',
                    'assignment': ({'commission_source_ref': need['commission_source_ref']}
                        if need.get('commission_source_ref') else {'commission_id': 'a104-native'})}}}
            previously_commissioned = self.store.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=? AND "
                "episode_id=? AND json_extract(action,'$.assignment.context.native_evidence_refs')=?",
                (self.run_id, episode_id, json.dumps(evidence, separators=(',', ':')))).fetchone()
            measured = any(received_measurement(self.store, ref) is not None for ref in known)
        if episode_role == 'annotation' and (done is None or
                self.integrated and evidence and previously_commissioned is None and not measured):
            subtree = A104Subtree(self.directory/'workflow')
            selection = subtree.commission(self.store, target_ref=self.prepared['target_ref'],
                scope=self.prepared['scope'], evidence_refs=evidence,
                child_tool_info=[{'name': name, 'resources': 'local'} for name in
                    (*NAMES, 'source.read', 'state.query', 'sequence.inspect')],
                question='Investigate the evolutionary history and phylogenetic placement of the anonymous '
                    'supplied protein. Inspect the actual native phylogeny, choose and measure its informative '
                    'target relationships, evaluate the functional composition of those particular groups, and '
                    'calculate a matched comparison with the independent organismal reference where available. '
                    'When supplied native model/seed alternatives or target-region tests are present, measure '
                    'their actual relationships and compare the genuinely different full-length analyses at '
                    'the same member scope. Keep regional results attached to their original region. '
                    'Keep characterization, copy mapping, uncertainty, rooting and historical causes explicit. '
                    'Use the real tools to establish and inspect credit. Request exact missing information '
                    'through shared.*; every scientific descendant remains A104. No candidate function is supplied.',
                context={'native_evidence_refs': evidence, 'exact_native_request_ref': self.prepared['native_request_ref'],
                    'native_input_contract': 'Every native_evidence_ref is already an authenticated native phylogeny Source. '
                        'Use it directly as native_ref in phylogeny.inspect and the measurement tools. '
                        'It is not an hpc_result_ref. No reimport or repeat of the original request is needed. '
                        'For a genuinely different test use prepare_analysis, then request_analysis.',
                    'hpc_commission_id': 'a104-native',
                    'execution_provenance': 'fresh integrated PBS execution' if self.integrated else 'retained original PBS execution; fresh scientific decisions',
                    'native_request_action': 'When no native evidence is received, call phylogeny.request_analysis with '
                        'exact_native_request_ref. Commission the operational hpc child with its returned hpc_assignment '
                        'and an hpc_result_refs fact return. The shared annotation parent also receives the typed need. '
                        'Other biological evidence axes remain separate parent-commissioned investigations.',
                    'available_independent_history': 'Inspect the supplied request and native analyses. Any marker-derived reference is a proxy with explicit sampling and orthology assumptions.'})
            return {'response': {'response_type': 'select_action', 'selection': selection, 'report_update': {}}}
        if episode_role == 'annotation':
            output_schema = parent_generation_schema(frame, output_schema)
            instructions += '\nAn unresolved need is not a running producer. Use actual received evidence or '
            instructions += 'commission a useful investigation; an unassigned sibling will not deliver data by calendar waiting.'
            instructions += '\nWhen commissioning a child, schema_json must explicitly declare '
            instructions += '"type":"object", a properties object and "additionalProperties":false at the top level. '
            instructions += 'Use the child\'s actual return-fact contracts for x-source fields.'
            instructions += 'For a literature question, also request an explicit question outcome and '
            instructions += 'attribution limitations, initially unknown. Lists of basis or changed references '
            instructions += 'alone do not tell the parent whether the requested subject was characterized. '
            instructions += 'These descriptive fields do not create assay or A104 credit.'
            instructions += '\nAfter a child returns, inspect its actual findings and completed operations. '
            instructions += 'A further child needs a specific remaining step, new source or different method; '
            instructions += 'do not repeat the same source-reading task simply because characterization remains unknown.'
        return await self.connection.complete(episode_id, role, instructions, frame, output_schema)


async def run(args):
    active_budget()
    directory = args.case_directory.resolve()
    prepared = json.loads((directory/'PREPARED.json').read_text())
    run_id = 'a104-science-'+directory.parent.name
    with Store(directory/'state') as store:
        exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE name='a104_native_results'").fetchone()
        evidence = [row[0] for row in store.db.execute('SELECT source_ref FROM a104_native_results')] if exists else []
        if not evidence and not args.integrated:
            raise ValueError('a104_scientific_run_requires_explicit_authentic_native_inputs')
        tools = A104ToolRegistry(store, a104_work_directory=directory/'native',
            a104_execution_resources=prepared['execution_resources'],
            job_limits={'memory_bytes': 128*1024**2, 'scratch_bytes': 32*1024**2})
        factory = A104ServiceFactory(prepared['source_directory'],
            {'version': 'scientific_tool_retrieval_v1', 'mode': 'literal_test_v1'},
            prepared['execution_resources'], prepared['hpc_commissions'],
            shared_execution_memory=prepared.get('shared_execution_memory'))
        async with ModelConnection(load_config(args.model_config), directory/'provider'/uuid.uuid4().hex, directory) as connection:
            provider = CommissionedParent(connection, store, directory, prepared, evidence)
            provider.run_id = run_id
            provider.integrated = args.integrated
            workflow = create_evidence_root_workflow(store, tools, provider, directory/'workflow', run_id,
                controller_from_settings({'controller': {'cost': .05, 'window_size': 8,
                    'subsample_size': 4, 'uncertainty_alpha': .05}}),
                initial_known_record_refs=list(dict.fromkeys([*prepared['known_record_refs'], *evidence])),
                episode_service_factory=factory, episode_service_binding=factory.as_record(),
                episode_service_inputs='actual_tool_registry_v1', decision_protocol=PROTOCOL,
                annotation_child_roles=('scientific_process', 'literature', 'hpc'))
            provider.workflow = workflow
            root = workflow.build('annotation', 'root', 'Investigate A104 for the supplied protein. '
                'Receive actual evolutionary measurements and share their specific attribution needs. '
                'A105 is already implemented; experimental characterization is independent evidence. '
                'A published information need does not create a producer or promise a later delivery. '
                'Commission an actual useful sibling investigation when needed; calendar waiting requires '
                'real pending work or an independently established scheduled change. '
                'Do not infer exact chemistry or horizontal transfer from an uncharacterized clade.', prepared['scope'])
            print(json.dumps({'event': 'a104_scientific_episode_started', 'run_id': run_id,
                'native_evidence_refs': evidence}), flush=True)
            try:
                record = await root.run_async(workflow.context)
            except (CalendarCheckpoint, MonitorCheckpoint) as waiting:
                schedule = waiting.request if isinstance(waiting, CalendarCheckpoint) else waiting.schedule
                import sys
                source = Path(__file__).resolve()
                command = ['/usr/bin/env', 'PYTHONPATH='+str(source.parents[1]), sys.executable, '-B', str(source),
                    '--case-directory', str(directory), '--repository-root', str(args.repository_root.resolve())]
                if args.integrated:
                    command.append('--integrated')
                if args.model_config:
                    command.extend(['--model-config', str(args.model_config.resolve())])
                spec = register_resume(directory, args.repository_root, command, schedule)
                print(json.dumps({key: spec[key] for key in ('event', 'resume_at', 'timer', 'controller_run_directory')}), flush=True)
                return
            await root.build_result(record)
            known = set(workflow.receipts.known(root.source.episode_id))
            credit = NativeEvidenceRootCredit().read_details(store, prepared['scope'], known_record_refs=known,
                details_limit=128, details_offset=0)
            measurements = [value for reference in known if (value := received_measurement(store, reference)) is not None]
            reports = [dict(row) for row in store.db.execute('SELECT child_episode_id,form,failure FROM runtime_report_attempts '
                'WHERE run_id=? AND form IS NOT NULL', (run_id,))]
            owner_scores = []
            for row in store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? AND "
                "json_extract(request,'$.message.episode_assignment.selection.evidence_axis.option_id')='A104'", (run_id,)):
                own_known = workflow.receipts.known(row[0])
                owner_scores.append({'episode_id': row[0], 'credit': A104EvolutionaryCredit()(store,
                    prepared['scope'], known_record_refs=own_known)['credit']})
            result = {'decision_mode': 'deterministic_native_reader_intake_then_fresh_configured_model_scientific_decisions',
                'operational_validation': 'explicit_predictive_sister_commission_then_actual_model_decisions'
                    if args.integrated else 'retained_original_execution; no_new_job',
                'native_execution': 'fresh_integrated_PBS' if args.integrated else 'retained_authenticated_original_PBS', 'run_id': run_id,
                'credit': credit, 'measurements': measurements, 'returned_forms': reports,
                'owner_scores': owner_scores, 'unresolved_function_and_history_are_not_negative_progress': True}
            (directory/'RESULTS.json').write_text(json.dumps(result, indent=2)+'\n')
            print(json.dumps({'event': 'a104_scientific_episode_returned', 'axis_components': credit['axis_components'],
                'root_credit': credit['credit'], 'measurement_count': len(measurements), 'owner_scores': owner_scores}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-directory', type=Path, required=True)
    parser.add_argument('--repository-root', type=Path, required=True)
    parser.add_argument('--model-config', type=Path)
    parser.add_argument('--integrated', action='store_true')
    asyncio.run(run(parser.parse_args()))
