"""Actual private constructors/Store/readers; controlled ordinary visibility.

Malformed stored source records test negative qualification. No stored source
is claimed as an authentic native receipt. The original generic result reader
is wrapped only to count actual calls; its validation and failures are retained.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources

VERSIONS = (
    'native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1',
    'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1',
    'native_infernal_bundle_v1', 'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1',
    'native_protein_structure_bundle_v1', 'native_rna_structure_bundle_v1',
)
PREFIXES = ('', 'scientific_process/', 'hpc_work_planning/',
    'hpc_work_planning/hpc_allocation_execution/', 'scientific_process/hpc_work_planning/',
    'scientific_process/hpc_work_planning/hpc_allocation_execution/')


def forbidden(*args, **kwargs):
    raise AssertionError('native bundle guard probe cannot execute native/provider work')


def caught(callback, plain):
    try:
        return {'status': 'returned', 'value': plain(callback())}
    except Exception as error:
        return {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error)}


def source(store, provider, version):
    artifact = store.artifact('{}', 'application/json')
    return store.put('source', {'provider': provider, 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': artifact,
        'version': version, 'retrieved_at': None}, origin='tool')['id']


def probe(axis, output, *, expected):
    package = 'gene_annotation_episode.episodic_workflow.root.' + axis + '.'
    module = lambda name: importlib.import_module(package + name)
    plain = module('communication').plain
    BindingContext = module('episode_bindings').BindingContext
    EpisodeRef = module('method_loop.identities').EpisodeRef
    output.mkdir(parents=True, exist_ok=False)
    leaves = ('execution_job_submission',
        *(('execution_job_submission/api_job_execution',) if axis == 'a107' else ()),
        'execution_job_submission/local_job_execution', 'execution_job_submission/hpc_job_execution',
        'execution_result_acquisition')
    homes = tuple(prefix + leaf for prefix in PREFIXES for leaf in leaves)
    repository = Path(__file__).resolve().parents[4]
    axis_directory = repository / 'gene_annotation_episode/episodic_workflow/root' / axis
    def source_hashes():
        return {str(path.relative_to(repository)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(axis_directory.rglob('*.py')) if 'tests' not in path.parts}
    report = {'version': 'actual_private_native_bundle_guard_probe_v3', 'axis': axis,
        'expected': expected, 'source_hashes': source_hashes(),
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'owners': {}, 'controlled_ports': ['ordinary source visibility only',
            'controlled typed root objective and request; actual Journal and receipt initialization'],
        'actual_store_records': True, 'actual_private_constructors': True,
        'malformed_negative_sources_not_native_evidence': True,
        'scientific_evidence_authenticated': False, 'native_or_model_operations': 0,
        'full_registry_or_receipt_integration_claimed': False, 'diagnostic_completed': False}
    destination = output / 'guard_probe.json'
    def retain():
        destination.write_text(json.dumps(report, indent=2) + '\n')
    retain()
    with patch('subprocess.Popen', forbidden), patch('socket.socket.connect', forbidden), patch('socket.socket.connect_ex', forbidden):
        with module('state').Store(output / 'store') as store:
            problem = store.create_problem(raw_sequence='ATGGCT', molecule='dna')
            scope = {'subject_refs': problem['subject_refs']}
            run_id = axis + '-original-native-bundle-guards'
            path = (('annotation', 'root'),)
            try:
                episode_id = EpisodeRef(run_id, path).episode_id
                journal = module('episode_journal').Journal(store, run_id)
                receipts = module('episode_receipts').EpisodeReceipts(store, run_id)
                loop = module('method_loop')
                goal = loop.EpisodeGoal.root(objective='Controlled original native bundle guard context',
                    result_contract={'role': 'annotation'})
                message = {'scope': scope, 'initial_report': {}, 'episode_assignment': {},
                    'knowledge_inheritance': receipts.bind(episode_id)}
                request = loop.EpisodeRequest(goal, module('runtime').Record(message))
                request_record = plain(request.as_record())
                canonical = module('method_loop.durable').canonical
                with store.transaction():
                    receipts.receive(episode_id, scope['subject_refs'], kind='initial')
                    journal.save('runtime_episodes', {'episode_id': episode_id,
                        'path': canonical(path), 'request': canonical(request_record),
                        'initial_credit': 0., 'state': 'active', 'completion': None, 'archive': None})
                context = BindingContext(run_id, episode_id, 'annotation', path, scope, {}, request_record)
                records = module('episode_return_records').EpisodeReturnRecords(
                    store, run_id, failure_prefix='native_bundle_guard_probe_')
                assert records.authenticate(context) is context
                report['root_context'] = {'status': 'authenticated', 'request': request_record,
                    'saved_episode': plain(journal.row('runtime_episodes', episode_id)),
                    'receipt_manifest': plain(receipts.manifest(episode_id)),
                    'workflow_build_claimed': False, 'native_return_or_child_attempt_created': False}
                retain()
            except Exception as error:
                import traceback
                report['root_context'] = {'status': 'raised',
                    'type': type(error).__module__ + '.' + type(error).__qualname__,
                    'message': str(error), 'traceback': traceback.format_exc()}
                retain()
                raise
            for home in homes:
                owner = {'bundles': {}}
                report['owners'][home] = owner
                try:
                    cls = module(home.replace('/', '.') + '.episode').ExecutionEpisode
                    services = SimpleNamespace(reference_in_context=lambda *args: True)
                    binding = cls(services, store=store, directory=output / 'bindings' / home,
                        run_id=run_id, resources=resources(), initial_information={}, tool_registry=None,
                        handoff_unit=1., acquired_record_unit=1., log_window_bytes=1024,
                        log_roles=('stdout', 'stderr'))
                    owner['constructor'] = {'status': 'returned', 'descriptor': binding.as_record()}
                except Exception as error:
                    owner['constructor'] = {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__, 'message': str(error)}
                    retain()
                    continue
                for version in (*VERSIONS, 'controlled_generic_negative_result_v1'):
                    reference = source(store, 'episode.execution_result', version)
                    selection = {'run_id': run_id, 'episode_id': context.episode_id,
                        'known_record_refs': [reference], 'initial_known_record_refs': []}
                    calls = []
                    original = binding._read_result
                    def observed_read(*args, **kwargs):
                        calls.append({'reference': args[0], 'scope': plain(args[1])})
                        return original(*args, **kwargs)
                    row = {'reference': reference, 'resolved': []}
                    with patch.object(binding, '_read_result', observed_read):
                        row['received'] = caught(lambda: binding._received(context, selection, _handoff_read=forbidden), plain)
                        row['received_generic_reads'] = list(calls)
                        for namespace in (None, 'source', 'execution_result'):
                            calls.clear()
                            value = caught(lambda: binding.resolve(context, reference, namespace), plain)
                            row['resolved'].append({'namespace': namespace, 'outcome': value, 'generic_reads': list(calls)})
                    owner['bundles'][version] = row
                    retain()
                for label, provider in (('ordinary', 'synthetic.ordinary_source'), ('practical', 'episode.practical_receipt')):
                    reference = source(store, provider, None)
                    owner[label] = caught(lambda: binding.resolve(context, reference, 'source'), plain)
                retain()
    assert source_hashes() == report['source_hashes']
    assert len(report['owners']) == (30 if axis == 'a107' else 24)
    report['diagnostic_completed'] = True
    retain()
    assert all(row['constructor']['status'] == 'returned' for row in report['owners'].values())
    for owner in report['owners'].values():
        assert set(owner['bundles']) == {*VERSIONS, 'controlled_generic_negative_result_v1'}
        generic = owner['bundles']['controlled_generic_negative_result_v1']
        assert len(generic['received_generic_reads']) == 1
        assert owner['ordinary'] == {'status': 'returned', 'value': True}
        if expected == 'restored':
            for version in VERSIONS:
                row = owner['bundles'][version]
                assert row['received']['status'] == 'returned' and not row['received_generic_reads']
                assert row['received']['value'][1:] == [{}, {}]
                assert all(item['outcome'] == {'status': 'returned', 'value': False}
                    and not item['generic_reads'] for item in row['resolved'])
    if expected == 'baseline':
        assert any(owner['bundles'][version]['received_generic_reads']
            or any(item['generic_reads'] for item in owner['bundles'][version]['resolved'])
            for owner in report['owners'].values() for version in VERSIONS)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--axis', choices=('a107', 'a110'), required=True)
    parser.add_argument('--expected', choices=('baseline', 'restored'), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    output = args.output.resolve()
    assert output.is_relative_to(root / 'runs')
    probe(args.axis, output, expected=args.expected)
