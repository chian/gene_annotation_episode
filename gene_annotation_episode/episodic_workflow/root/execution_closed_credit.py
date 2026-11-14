"""Original closed operational-credit custody for an explicit execution receiver.

No constructor, episode role registration, descriptor or public dispatch lives here.
"""
from __future__ import annotations

import json
import math

from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.communication import plain

_CLOSED_CREDIT = 'execution_closed_operational_credit_v1'
ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')


class ExecutionClosedCredit:
    def _closed_credit_carrier(self, context):
        """Validate closed runtime metadata without reading scientific payloads."""
        from .episode_return_records import EpisodeReturnRecords
        EpisodeReturnRecords(self.store, self.run_id,
            failure_prefix='execution_closed_credit_').authenticate(context)
        row = self.store.db.execute('SELECT state,completion,archive FROM runtime_episodes '
            'WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()
        if (context.role not in ROLES or row is None or row['state'] != 'yielded'
                or row['completion'] is None or row['archive'] is None):
            raise ValueError('execution_closed_credit_carrier_conflict')
        completion, archive = json.loads(row['completion']), json.loads(row['archive'])
        if (type(completion) is not dict or set(completion) != {'actions', 'ended_by'}
                or type(completion['actions']) is not int or completion['actions'] < 0
                or type(completion['ended_by']) is not str or not completion['ended_by']
                or type(archive) is not dict or set(archive) != {'file', 'sha256', 'index_sha256'}
                or type(archive['file']) is not str or len(archive['file']) != 69
                or not archive['file'].endswith('.json')
                or any(character not in '0123456789abcdef' for character in archive['file'][:-5])
                or any(type(archive[key]) is not str or len(archive[key]) != 64
                    or any(character not in '0123456789abcdef' for character in archive[key])
                    for key in ('sha256', 'index_sha256'))):
            raise ValueError('execution_closed_credit_carrier_conflict')
        observations = list(self.store.db.execute('SELECT unit_index,observation FROM runtime_observations '
            'WHERE run_id=? AND episode_id=? ORDER BY unit_index', (self.run_id, context.episode_id)))
        if [row['unit_index'] for row in observations] != list(range(completion['actions'])):
            raise ValueError('execution_closed_credit_history_conflict')
        return {'completion': completion, 'archive': archive,
            'history_sha256': digest([list(row) for row in observations])}

    def _closed_credit_receipts(self, context, *, through=None):
        """Pin the original receipt prefix; later delivery never reprices it."""
        from .episode_receipts import EpisodeReceipts
        from .episode_return_records import _same
        db = self.store.db
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name="
                "'runtime_receipt_inheritance'").fetchone() is None or db.execute(
                'SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?',
                (self.run_id, context.episode_id)).fetchone() is None:
            return None, None, None
        if through is None:
            through = db.execute('SELECT coalesce(max(receipt_index),0) FROM runtime_record_receipts '
                'WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone()[0]
        if type(through) is not int or through < 0:
            raise ValueError('execution_closed_credit_receipt_conflict')
        own_through, current, seen, manifests, rows = through, context.episode_id, set(), [], []
        while current is not None:
            if current in seen:
                raise ValueError('execution_closed_credit_receipt_conflict')
            seen.add(current)
            manifest = EpisodeReceipts.read_manifest(db, self.run_id, current)
            recorded = db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
                (self.run_id, current)).fetchone()
            if recorded is None or not _same(json.loads(recorded['request'])['message'].get(
                    'knowledge_inheritance'), manifest):
                raise ValueError('execution_closed_credit_receipt_conflict')
            manifests.append({'episode_id': current, 'manifest': manifest})
            rows.extend(list(row) for row in db.execute('SELECT receipt_index,episode_id,record_ref,receipt_kind,source_index '
                'FROM runtime_record_receipts WHERE run_id=? AND episode_id=? '
                'AND (? IS NULL OR receipt_index<=?) ORDER BY receipt_index',
                (self.run_id, current, through, through)))
            current, through = manifest['parent_episode_id'], manifest['through_receipt_index']
        known = sorted({row[2] for row in rows})
        initial = sorted({row[2] for row in rows if row[1] != context.episode_id or row[3] == 'initial'})
        return {'through_receipt_index': own_through,
            'sha256': digest({'manifests': manifests, 'rows': rows})}, known, initial

    def _closed_credit_value(self, view):
        if (type(view) is not dict or type(view.get('credit')) not in (int, float)
                or not math.isfinite(view['credit'])):
            raise ValueError('execution_closed_credit_view_conflict')

    def _closed_credit_facts(self, context, completion_snapshot):
        """Capture the already projected view once, inside the closing facts."""
        if completion_snapshot is None:
            return {}
        capture = completion_snapshot.get('operational_credit_snapshot')
        completion = completion_snapshot.get('completion')
        if capture is None or completion is None:
            return {}
        # Existing histories are never upgraded or backfilled by a later read.
        if self.store.db.execute('SELECT 1 FROM runtime_forms WHERE run_id=? AND episode_id=?',
                (self.run_id, context.episode_id)).fetchone() is not None:
            return {}
        if type(capture) is not dict or set(capture) != {'view', 'selection'}:
            raise ValueError('execution_closed_credit_snapshot_conflict')
        capture = json.loads(canonical(plain(capture)))
        carrier = self._closed_credit_carrier(context)
        if (completion.get('ended_by') != carrier['completion']['ended_by']
                or type(completion.get('units_consumed')) is not int
                or completion['units_consumed'] != carrier['completion']['actions']):
            raise ValueError('execution_closed_credit_carrier_conflict')
        selection = self._selection(context, capture['selection'])
        prefix, known, initial = self._closed_credit_receipts(context)
        if prefix is not None and (selection['known_record_refs'] != known
                or selection['initial_known_record_refs'] != initial):
            raise ValueError('execution_closed_credit_receipt_conflict')
        self._closed_credit_value(capture['view'])
        return {_CLOSED_CREDIT: {'version': _CLOSED_CREDIT,
            'context_sha256': digest(context.as_record()), 'binding_sha256': digest(self._credit_binding_record(context)),
            'selection': selection, 'receipt_prefix': prefix,
            'completion_sha256': digest(carrier['completion']), 'archive_sha256': digest(carrier['archive']),
            'history_sha256': carrier['history_sha256'],
            'view': capture['view'], 'view_sha256': digest(capture['view'])}}

    def _closed_operational_credit_view(self, context, receiver_selection):
        """Return only the original closed view, never another projection."""
        from .episode_return_records import _same
        if self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='runtime_forms'").fetchone() is None:
            return None
        row = self.store.db.execute('SELECT facts,form FROM runtime_forms WHERE run_id=? AND episode_id=?',
            (self.run_id, context.episode_id)).fetchone()
        if row is None:
            return None
        facts = json.loads(row['facts'])
        if _CLOSED_CREDIT not in facts:
            return None
        value = facts[_CLOSED_CREDIT]
        fields = {'version', 'context_sha256', 'binding_sha256', 'selection', 'receipt_prefix',
            'completion_sha256', 'archive_sha256', 'history_sha256', 'view', 'view_sha256'}
        if row['form'] is None or type(value) is not dict or set(value) != fields or value['version'] != _CLOSED_CREDIT:
            raise ValueError('execution_closed_credit_snapshot_conflict')
        carrier = self._closed_credit_carrier(context)
        if (value['context_sha256'] != digest(context.as_record()) or value['binding_sha256'] != digest(self._credit_binding_record(context))
                or value['completion_sha256'] != digest(carrier['completion'])
                or value['archive_sha256'] != digest(carrier['archive'])
                or value['history_sha256'] != carrier['history_sha256']):
            raise ValueError('execution_closed_credit_carrier_conflict')
        saved = self._selection(context, value['selection'])
        prefix = value['receipt_prefix']
        if prefix is not None and (type(prefix) is not dict or set(prefix) != {'through_receipt_index', 'sha256'}):
            raise ValueError('execution_closed_credit_receipt_conflict')
        actual, known, initial = self._closed_credit_receipts(context,
            through=None if prefix is None else prefix['through_receipt_index'])
        if not _same(actual, prefix) or prefix is not None and (
                saved['known_record_refs'] != known or saved['initial_known_record_refs'] != initial):
            raise ValueError('execution_closed_credit_receipt_conflict')
        supplied = self._selection(context, receiver_selection)
        if (not set(saved['known_record_refs']) <= set(supplied['known_record_refs'])
                or supplied['initial_known_record_refs'] != saved['initial_known_record_refs']):
            raise ValueError('execution_closed_credit_receipt_conflict')
        if prefix is not None:
            _, current_known, current_initial = self._closed_credit_receipts(context)
            if (set(supplied['known_record_refs']) != set(current_known)
                    or set(supplied['initial_known_record_refs']) != set(current_initial)):
                raise ValueError('execution_closed_credit_receipt_conflict')
        elif supplied['known_record_refs'] != saved['known_record_refs']:
            raise ValueError('execution_closed_credit_receipt_conflict')
        view = json.loads(canonical(value['view']))
        if value['view_sha256'] != digest(view):
            raise ValueError('execution_closed_credit_view_conflict')
        self._closed_credit_value(view)
        if not _same(view['credit'], facts.get('credit')):
            raise ValueError('execution_closed_credit_view_conflict')
        return view

    def _closed_completion_verdict(self, context, proof):
        """Reuse only an endpoint verification actually recorded in history."""
        if self._closed_operational_credit_view(context, None) is None:
            return None
        from .method_loop.identities import UnitRef
        from .episode_return_records import _same
        from .numerical import NumericBand
        from .practical_yield import ESTIMATOR_VERSION
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_request_binding import is_compact_assignment, materialized_assignment
        assignment = (materialized_assignment(self.store, context)
            if is_compact_assignment(plain(context.assignment)) else context.assignment)
        from gene_annotation_episode.episodic_workflow.root.library.lumpy_request_binding import (is_compact_assignment as is_lumpy_assignment,
            materialized_assignment as materialized_lumpy_assignment)
        if is_lumpy_assignment(plain(context.assignment)):
            assignment = materialized_lumpy_assignment(self.store, context)
        matches = 0
        for row in self.store.db.execute('SELECT unit_index,observation FROM runtime_observations '
                'WHERE run_id=? AND episode_id=? ORDER BY unit_index', (self.run_id, context.episode_id)):
            try:
                observed = json.loads(row['observation'])
                supplied = observed['credit']
                if type(supplied) is not dict or not _same(supplied.get('practical_completion'), proof):
                    continue
                index = observed['decision_index']
                unit = UnitRef.from_record(observed['unit_ref'])
                estimate = observed['step']['estimate']
                diagnostics, provenance = estimate['diagnostics'], estimate['provenance']
                if (type(index) is int and index >= 0
                        and type(supplied.get('estimation_action_index')) is int
                        and supplied['estimation_action_index'] == index
                        and unit.episode_id == context.episode_id and unit.unit_index == row['unit_index']
                        and proof['run_id'] == self.run_id and proof['episode_id'] == context.episode_id
                        and proof['assignment_sha256'] == digest(assignment)
                        and proof['operation_key'] == f'{self.run_id}:{context.episode_id}:{index}'
                        and type(estimate['turns']) is int and estimate['turns'] == unit.unit_index + 1
                        and provenance['version'] == ESTIMATOR_VERSION
                        and diagnostics['fitting_scope'] == 'verified_assignment_endpoint'
                        and _same(diagnostics['completion_proof'], proof)
                        and type(diagnostics['completion_action_index']) is int
                        and diagnostics['completion_action_index'] == index
                        and _same(diagnostics['completion_unit_ref'], unit.as_record())
                        and _same(estimate['expected_next_gain'], NumericBand.exact(0).as_record())):
                    matches += 1
            except (ValueError, TypeError, KeyError):
                continue
        return matches == 1

