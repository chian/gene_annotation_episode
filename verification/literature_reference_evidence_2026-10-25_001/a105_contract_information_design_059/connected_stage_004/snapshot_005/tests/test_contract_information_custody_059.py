"""Opted-in selected forms over actual synthetic native operations and custody."""
import asyncio
from copy import deepcopy
from functools import partial
import json

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE as PROFILE
from gene_annotation_episode.domain import obj
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_kinetic_storage import kinetic_cells_schema
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.tools import ToolRegistry
from test_contract_information_runtime_059 import PresentedProvider, information, populate
from test_literature_kinetic_storage import setup
from test_literature_kinetic_integration import reason
from test_runtime import FixtureController
from test_runtime_decision_exchanges import select


LITERAL = obj({'numbers': kinetic_cells_schema(),
               'qualification': {'type': 'string', 'enum': ['unknown', 'qualified']}})
COMPACT = obj({'numbers': {'$ref': 'episode-fact:literature_kinetic_cells'},
               'qualification': {'type': 'string', 'enum': ['unknown', 'qualified']}})


def commission(seed, args, form):
    return select({'selection': {'kind': 'episode_child', 'role': 'literature',
        'assignment': {**plain(seed.assignment), 'requested_kinetic_components': ['parameter_ratio']},
        'goal': 'Determine the synthetic source parameter ratio and preserve limitations',
        'scope': plain(seed.scope), 'purpose': 'Return the selected native ratio and bounded qualification',
        'schema_json': json.dumps(form, ensure_ascii=False, indent=1),
        'initial_report_json': json.dumps({'qualification': 'unknown'})}, 'report_update': {}})


def world(path, *, execution_binding=None):
    store, seed, args = setup(path / 'state')
    provider = PresentedProvider([])
    value = Workflow(store, ToolRegistry(store), provider, path / 'run', seed.run_id,
        lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
        ScientificFindingProgress(FindingProgressPolicy(1)),
        initial_known_record_refs=list(seed.received_record_refs),
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
            reference_parent_sources=[args['source_ref']], contract_information_profile=PROFILE),),
        decision_protocol='decision_exchange_v1', execution_binding=execution_binding)
    root = value.build('annotation', 'root', 'Evaluate the supplied synthetic experimental evidence', plain(seed.scope))
    return store, seed, args, provider, value, root


@pytest.mark.parametrize('form', [LITERAL, COMPACT], ids=['literal', 'compact'])
def test_parent_owns_selected_form_and_actual_native_return_with_mixed_interpretation(tmp_path, form):
    store, seed, args, provider, value, root = world(tmp_path)
    selected = commission(seed, args, form)
    action = populate(args)
    action['response']['report_update'] = {'qualification': 'qualified'}
    provider.script = iter([information('episode.return_contract', role='literature', source='literature_kinetic_cells'),
        selected, information('episode.operation_contract', operation='literature.kinetic.populate'), action,
        select(reason(store, args['source_ref']))])
    try:
        result = asyncio.run(root.run_async(value.context))
        assert result.units_consumed == 2
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM literature_kinetic_operations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_kinetic_received').fetchone()[0] == 1
        child_row = store.db.execute("SELECT * FROM runtime_episodes WHERE json_array_length(path)=2").fetchone()
        request = json.loads(child_row['request'])
        assert request['report_contract']['measurements']['schema'] == LITERAL
        declaration = request['message']['report_contract_declaration']
        assert declaration['submitted_schema_json'] == selected['response']['selection']['schema_json']
        assert len(declaration['fact_references']) == (1 if form is COMPACT else 0)
        returned = json.loads(store.db.execute('SELECT form FROM runtime_forms').fetchone()[0])
        assert returned['qualification'] == 'qualified'
        assert [row['component'] for row in returned['numbers']] == ['parameter_ratio']
        assert returned['numbers'][0]['value'] == 4
        assert all(row[side]['uncertainty_values']['delivery_status'] == 'not_requested'
                   for row in returned['numbers'] for side in ('numerator', 'denominator'))
        assert not store.list('observation') and not store.list('assessment')
        # Full parent and child TASK meanings persist across metadata exchanges.
        assert 'Requested operation/return information: literature_kinetic_cells' in provider.rendered[1]
        assert 'Requested operation/return information: literature.kinetic.populate' in provider.rendered[3]
    finally:
        store.close()


def test_original_c1_c4_compact_form_native_custody_rollback_and_readonly_first_reconstruction(tmp_path, monkeypatch):
    from dataclasses import replace
    from method_loop.archive import JsonArchive
    from method_loop.durable import content_digest
    from gene_annotation_episode.domain import ContractError, canonical
    from gene_annotation_episode.episode_admission import AdmissionError, ReceiverBindingV1, admit_return
    from gene_annotation_episode.episode_journal import Journal
    from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository
    from gene_annotation_episode.runtime import TypedReportContract
    from gene_annotation_episode.state import Store
    from test_contract_information_runtime_059 import run_child
    from test_episode_admission import Value, seal_return
    from test_literature_kinetic_count_integration import forbid_science, make_readonly
    from test_literature_rate_episode_integration import service_binding

    binding_record = {'factory_module': 'fixture', 'factory_name': 'open_commission', 'arguments': {},
        'implementation_sha256': 'a' * 64, 'settings_sha256': 'b' * 64}
    store, seed, args, provider, value, root = world(tmp_path, execution_binding=binding_record)
    selected = commission(seed, args, COMPACT)
    provider.script = iter([information('episode.return_contract', role='literature', source='literature_kinetic_cells'), selected])
    def stopped_dispatch(*_a, **_kw):
        raise OSError('Fixture pauses after actual original C1 publication')
    try:
        with monkeypatch.context() as patch:
            patch.setattr(Workflow, 'dispatch_commission', stopped_dispatch)
            with pytest.raises(OSError, match='after actual original C1'):
                asyncio.run(root.run_async(value.context))
        intent = store.db.execute('SELECT * FROM runtime_commission_intents').fetchone()
        spec = json.loads(intent['spec'])
        original_spec = deepcopy(spec)
        child_record = spec['child']['request']
        declaration = child_record['message']['report_contract_declaration']
        assert declaration['submitted_schema_json'] == selected['response']['selection']['schema_json']
        assert child_record['report_contract']['measurements']['schema'] == LITERAL
        assert json.loads(intent['selection'])['schema_json'] == declaration['submitted_schema_json']
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        # Existing C1 publication/recovery and blocking form reconstruction use
        # the original request before attempting any new reference expansion.
        def forbidden_factory(*_a, **_kw):
            raise AssertionError('Original contract must not reload current factories')
        with monkeypatch.context() as patch:
            patch.setattr(Workflow, 'report_sources', forbidden_factory)
            expanded, replayed_declaration = value.expanded_contract_form(root.source,
                selected['response']['selection'], 0, 'literature')
            assert expanded == LITERAL and replayed_declaration == declaration
            assert value.returned_request(spec).as_record() == child_record
            value.selected(root.source, selected['response']['selection'], 0)
        # Run only the selected child's actual native population using its
        # original frozen parent-owned form; no independent model is launched.
        contract = value.returned_request(spec).report_contract
        child = value.build('literature', 'child_0', child_record['goal']['objective'], plain(seed.scope),
            parent=root.request.goal, parent_path=root.source.path, contract=contract,
            initial=child_record['message']['initial_report'],
            episode_assignment=child_record['message']['episode_assignment'],
            report_contract_declaration=declaration)
        action = populate(args)
        action['response']['report_update'] = {'qualification': 'qualified'}
        provider.script = iter([action])
        result = run_child(child, value)
        assert result.units_consumed == 1
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
        asyncio.run(child.build_result(result))
        saved_form = value.journal.row('runtime_forms', child.source.episode_id)
        form, facts = json.loads(saved_form['form']), json.loads(saved_form['facts'])
        assert form['numbers'][0]['value'] == 4
        archive = JsonArchive(tmp_path / 'return-archive')
        returned = {'version': 'returned_episode_v1', 'handle': spec['handle'], 'return_id': '',
            'commission_sha256': content_digest(spec), 'returned_at': '2026-10-26T12:00:00+00:00',
            'outcome': 'closed', 'completion': {'ended_by': 'yield_stop', 'end_reason': '', 'units_consumed': 1},
            'episode_archive': archive.store({'fixture': 'actual child completed'}).descriptor(),
            'result_archive': archive.store({'form': form}).descriptor(), 'form': form,
            'facts_archive': archive.store(facts).descriptor(), 'pending_handles': [], 'failure': None}
        seal_return(returned)
        specialist = value.episode_bindings.for_role('literature')
        parent_context, child_context = value.binding_context(root.source), value.binding_context(child.source)
        receive_key = value.run_id + ':' + root.source.episode_id + ':0:typed_form'
        def receive(delivered):
            return specialist.received_form_references(parent_context, delivered, LITERAL, receive_key)
        receiver = ReceiverBindingV1(store, value.journal, 0, contract,
            lambda delivered: specialist.validate_report(child_context, delivered, LITERAL), receive,
            lambda: 0, lambda index, credit: Value({'credit': credit, 'estimation_action_index': index}))
        repo = specialist.services.literature_kinetic_repository()
        original_receive = repo.receive_cells
        def interrupted(*a, **kw):
            original_receive(*a, **kw)
            raise OSError('Fixture interrupts original C4 after native receipt')
        with monkeypatch.context() as patch:
            patch.setattr(repo, 'receive_cells', interrupted)
            with pytest.raises(OSError, match='after native receipt'):
                admit_return(spec, returned, receiver)
        assert store.db.execute('SELECT count(*) FROM literature_kinetic_received').fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM sqlite_master WHERE name='runtime_return_admissions'").fetchone()[0] == 0
        forged = deepcopy(spec)
        forged['child']['request']['message']['report_contract_declaration']['submitted_schema_json'] = '{}'
        altered_return = deepcopy(returned)
        altered_return['commission_sha256'] = content_digest(forged)
        seal_return(altered_return)
        with pytest.raises(AdmissionError, match='identity_conflict'):
            admit_return(forged, altered_return, receiver)
        admitted = admit_return(spec, returned, receiver)
        assert admitted['state'] == 'admitted' and admitted['report'] == form
        assert spec == original_spec and json.loads(intent['spec']) == original_spec
        parent_context = replace(parent_context, received_record_refs=tuple(dict.fromkeys([
            *parent_context.received_record_refs, *admitted['received_record_refs']])))
        # Rewriting both a saved numerical cell and its local digest still
        # cannot replace its original native operation/operand identity.
        original_cells = form['numbers']
        forged_cells = deepcopy(original_cells)
        forged_cells[0]['value'] = 999
        store.db.execute('UPDATE literature_kinetic_received SET cells=?', (canonical(forged_cells),))
        store.db.execute('UPDATE literature_kinetic_delivery_bindings SET cells_digest=?', (repo._delivery_digest(forged_cells),))
        with pytest.raises(ContractError, match='delivery_binding_mismatch'):
            repo.received_cells(parent_context)
        store.db.execute('UPDATE literature_kinetic_received SET cells=?', (canonical(original_cells),))
        store.db.execute('UPDATE literature_kinetic_delivery_bindings SET cells_digest=?', (repo._delivery_digest(original_cells),))
        whole_sql = list(store.db.iterdump())
        source_artifact = store.get(args['source_ref'])['artifact_ref']
        store.close()
        forbidden = forbid_science(monkeypatch)
        # The first new received-fact projection occurs only after reopening
        # the actual DB read-only, with source/scientific/receive work forbidden.
        with Store(tmp_path / 'state') as reopened:
            make_readonly(reopened, tmp_path / 'state/state.sqlite3')
            get_artifact = reopened.get_artifact
            monkeypatch.setattr(reopened, 'get_artifact',
                lambda ref: forbidden() if ref == source_artifact else get_artifact(ref))
            _, rebound = service_binding(reopened, child_context)
            assert rebound.received_report_facts(parent_context)['literature_kinetic_cells'] == original_cells
            rebound_receiver = replace(receiver, store=reopened, journal=Journal(reopened, value.run_id),
                validate_semantics=forbidden, receive_references=forbidden,
                project_received_credit=forbidden, make_controller_input=forbidden)
            with reopened.read_snapshot():
                assert admit_return(spec, returned, rebound_receiver) == admitted
            assert list(reopened.db.iterdump()) == whole_sql
            assert reopened.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
    finally:
        store.close()
