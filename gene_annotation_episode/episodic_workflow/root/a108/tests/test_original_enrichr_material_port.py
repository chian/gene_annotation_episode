"""Offline committed-chain controls over actual private Stores and receipts.

The original harness supplies inert literal protocol operands. No producer,
HTTP client, API invocation, native process or continuation loop is executed.
"""
import ast
from copy import deepcopy
import hashlib
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest


def original_protocol_operands():
    path = Path(__file__).parent / 'fixtures/enrichr_original_protocol/original_harness.txt'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '3d64ea9355b0929c4c53a920eeaf6f019805c2a306cf9c179ebbb9950e493211'
    tree = ast.parse(raw)
    owner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Harness')
    init = next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
    calls = [n for n in ast.walk(init) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == 'APIServiceExecution']
    assert len(calls) == 1
    config = ast.literal_eval(next(k.value for k in calls[0].keywords if k.arg == 'configuration'))['enrichr']
    requests = [n.value for n in init.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Attribute) and t.attr == 'request' for t in n.targets)]
    assert len(requests) == 1
    return ast.literal_eval(requests[0]), config


# a108 carries no private method_loop package; its modules import the shared root package.
METHOD_LOOP_OWNER = {'a101': 'a101.', 'a105': 'a105.', 'a106': 'a106.', 'a108': ''}


@pytest.mark.parametrize('axis', ['a101', 'a105', 'a106', 'a108'])
def test_original_enrichr_material_port_denies_private_controls(tmp_path, axis):
    def module(name):
        return import_module('gene_annotation_episode.episodic_workflow.root.' + axis + '.' + name)
    canonical = module('domain').canonical
    identity = module('domain').identity
    digest = module('execution_contracts').digest
    request, configuration = original_protocol_operands()
    with module('state').Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MAAA', molecule='protein')
        scope = store.validate_scope()
        store.db.execute('CREATE TABLE runtime_episodes(run_id TEXT,episode_id TEXT,path TEXT,request TEXT,PRIMARY KEY(run_id,episode_id))')
        store.db.execute('CREATE TABLE runtime_actions(run_id TEXT,episode_id TEXT,decision_index INTEGER,action TEXT,result TEXT)')
        registry = module('tools').ToolRegistry(store, clients=SimpleNamespace())
        guard = registry.retained_molecular_reference_access
        classifier = module('library.retained_input_authority.enrichr_reference_privacy')
        receipts = module('episode_receipts').EpisodeReceipts(store, 'enrichr-engineered-receipts')
        run = receipts.run_id

        def context(path, assignment, parent=None):
            episode = import_module('gene_annotation_episode.episodic_workflow.root.' + METHOD_LOOP_OWNER[axis] + 'method_loop.identities').EpisodeRef(run, path).episode_id
            inheritance = receipts.bind(episode, None if parent is None else parent.episode_id)
            saved = {'message': {'scope': scope, 'episode_assignment': assignment,
                                 'knowledge_inheritance': inheritance}}
            store.db.execute('INSERT INTO runtime_episodes VALUES(?,?,?,?)',
                             (run, episode, canonical(path), canonical(saved)))
            return module('episode_bindings').BindingContext(run, episode, path[-1][0], path, scope, assignment, saved)

        selector = {'version': 'enrichr_selector_v1', 'offset': 0, 'limit': 3}
        assignment = {'version': 'execution_results_assignment_v1',
                      'handoff_ref': 'engineering-handoff', 'selector': selector}
        publisher = context((('results', 'publication'),), assignment)
        raw = store.artifact('engineered retained Enrichr table', 'application/json')
        upload = store.artifact('engineered retained upload reply', 'application/json')
        wire = {'method': 'GET', 'url': 'https://enrichr.invalid/Enrichr/enrich'}
        bare = {'status': 200, 'representation': 'http_response_bytes'}
        final = {'service': 'enrichr', 'content_ref': raw, 'url': wire['url'],
                 'retrieved_at': '2026-10-30T00:00:00+00:00', 'request': wire, 'transport': bare}
        prepared = {'version': 'enrichr_prepared_protocol_v1', 'operation': 'api.enrichr.query',
                    'request': request, 'configuration': configuration, 'mutates_remote': True, 'cache_original': False}
        protocol = {'version': 'enrichr_protocol_snapshot_v1', 'wire_profile': 'enrichr_direct_http_v1',
                    'prepared': prepared, 'stages': [
                        {'ordinal': 0, 'stage_code': 'add_list', 'snapshot': {'service': 'enrichr', 'content_ref': upload}},
                        {'ordinal': 1, 'stage_code': 'enrich', 'snapshot': final}]}
        transport = {**bare, 'enrichr_protocol': protocol}
        control = store.artifact(canonical({'request': wire, 'transport': transport}), 'application/json')
        source = store.put('source', {'provider': 'enrichr', 'accession': None, 'uri': final['url'],
            'artifact_ref': raw, 'text_ref': None, 'request_ref': control, 'version': None,
            'retrieved_at': final['retrieved_at'], 'auxiliary_artifact_refs': [upload]}, origin='external')
        key = f'{run}:{publisher.episode_id}:0'
        operands = {'arguments': {'request': request, 'selector': selector}, 'request': wire,
                    'transport': transport, 'snapshot_sha256': raw.removeprefix('artifact_')}
        op = identity('operation', {'key': key + ':publication', 'name': 'internal.api_service.enrichr.result', 'arguments': operands})
        outcome = {'status': 'completed', 'operation_ref': op, 'record_refs': [source['id']],
                   'result': {'source_ref': source['id']}, 'feedback': None}
        store.db.execute('INSERT INTO tool_operations VALUES(?,?,?,?,?,?)',
            (key + ':publication', op, 'internal.api_service.enrichr.result', canonical(operands), canonical(scope), canonical(outcome)))
        receipt = {'version': 'api_service_acquisition_v1', 'run_id': run, 'episode_id': publisher.episode_id,
            'operation_key': key, 'name': 'api.enrichr.result', 'arguments': {},
            'assignment_sha256': digest(assignment), 'handoff_ref': assignment['handoff_ref'],
            'selector': selector, 'source_ref': source['id'], 'record_refs': [source['id']],
            'snapshot_sha256': operands['snapshot_sha256']}
        committed = deepcopy(outcome)
        committed['operation_ref'] = identity('api_operation', {'key': key})
        committed['result'].update(acquisition_receipt=receipt, handoff_ref=assignment['handoff_ref'])
        store.db.execute('INSERT INTO runtime_actions VALUES(?,?,?,?,?)',
            (run, publisher.episode_id, 0, canonical({'kind': 'tool', 'tool': 'api.enrichr.result', 'arguments': {}}), canonical(committed)))
        parent = context((('scientific_process', 'receiver'),), {})
        receipts.receive(parent.episode_id, [source['id']], kind='initial')
        child = context((*parent.path, ('literature', 'before-file')), {}, parent)
        before_reads = store.db.total_changes
        for reference, expected in [(source['id'], 'source'), (raw, 'raw'), (control, 'private'), (upload, 'private')]:
            rows = classifier.matching_enrichr_publications(store, reference)
            assert len(rows) == 1
            assert classifier.committed_enrichr_reference_kind(store, rows[0], reference) == expected
        materials = module('materials')
        assert materials.artifact_path(store, raw).read_bytes() == b'engineered retained Enrichr table'
        for private in (control, upload):
            with pytest.raises(module('domain').ContractError, match='enrichr_private_artifact_not_readable'):
                materials.artifact_path(store, private)
        assert guard(child, source['id'], 'source') is None
        assert guard(child, raw, 'artifact') is False
        assert guard(child, control, 'artifact') is False
        assert guard(child, upload, 'artifact') is False
        assert store.db.total_changes == before_reads
        receipts.receive(parent.episode_id, [raw, control, upload], kind='initial')
        later = context((*parent.path, ('literature', 'after-file')), {}, parent)
        before_reads = store.db.total_changes
        assert guard(child, raw, 'artifact') is False
        # A negative classifier defers to original authority after a real grant.
        assert guard(later, raw, 'artifact') is None
        assert guard(later, control, 'artifact') is False
        assert guard(later, upload, 'artifact') is False
        assert store.db.total_changes == before_reads
        changed = deepcopy(committed)
        changed['result']['acquisition_receipt']['assignment_sha256'] = '0' * 64
        store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=?',
                         (canonical(changed), run, publisher.episode_id))
        with pytest.raises(module('communication').ReportBoundaryError, match='enrichr_foreign_publication_conflict'):
            guard(later, raw, 'artifact')
