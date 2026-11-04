"""Explicit finding-unit projection over information known to an episode.

This is a callable component, not an installed case policy. Its caller must
provide the known assessment references and numerical unit. It neither infers
receipt from all shared records nor changes the numerical yield estimator.
"""
import math
import json
import sqlite3
from dataclasses import dataclass

from .domain import canonical
from .scientific_findings import FindingIdentity, IDENTITY_VERSION
from .finding_validity import FindingValidity, VALIDITY_VERSION, target_eligible
from .episode_receipts import RECEIPT_VERSION


@dataclass(frozen=True)
class FindingProgressPolicy:
    finding_unit: float

    def __post_init__(self):
        if (type(self.finding_unit) not in (int, float)
                or not math.isfinite(self.finding_unit) or self.finding_unit <= 0):
            raise ValueError('explicit_positive_finding_unit_required')

    def as_record(self):
        return {'version': 'known_retained_scientific_findings_v1',
            'finding_unit': self.finding_unit, 'identity_version': IDENTITY_VERSION,
            'finding_validity_version': VALIDITY_VERSION,
            'eligible_information': 'distinct_current_retained_typed_target_findings',
            'receipt': 'caller_supplies_actual_known_assessment_references',
            'negative_information': 'retained_without_applicability_or_opinion_weight',
            'annotation_support': 'separately_bound_not_this_score',
            'activity_credit': False}


@dataclass(frozen=True)
class ScientificFindingProgress:
    """Runtime adapter requiring actual episode receipt information."""
    policy: FindingProgressPolicy
    loss_preview_size: int = 24
    requires_episode_receipts = True

    def __post_init__(self):
        if not isinstance(self.policy, FindingProgressPolicy):
            raise TypeError('explicit_finding_progress_policy_required')
        if type(self.loss_preview_size) is not int or self.loss_preview_size < 0:
            raise ValueError('nonnegative_loss_preview_size_required')

    def as_record(self):
        return {'kind': 'received_scientific_finding_progress',
            'policy': self.policy.as_record(), 'receipt_version': RECEIPT_VERSION,
            'loss_preview_size': self.loss_preview_size,
            'baseline': 'frozen_inherited_parent_information',
            'parent_projection': 'received_meanings_not_sum_of_child_scores'}

    def __call__(self, store, scope, *, known_assessment_refs, assignment=None,
                 episode_id=None, run_id=None):
        return self.read_details(store, scope, known_assessment_refs=known_assessment_refs,
            assignment=assignment, episode_id=episode_id, run_id=run_id,
            details_limit=self.loss_preview_size, details_offset=0)

    def read_details(self, store, scope, *, known_assessment_refs, details_limit,
                     details_offset, assignment=None, episode_id=None, run_id=None):
        if assignment is not None and store.validate_scope(assignment['scope']) != store.validate_scope(scope):
            raise ValueError('scientific_credit_scope_differs_from_original_commission')
        return project_finding_progress(store, scope, self.policy,
            known_assessment_refs=known_assessment_refs, details_limit=details_limit,
            details_offset=details_offset)


def project_finding_progress(store, scope, policy, *, known_assessment_refs,
                             details_limit=0, details_offset=0):
    """One explicit unit per distinct retained finding, never per operation.

    Current corrections retire exact earlier findings. Inherited information
    and actual form/own-read receipt must be supplied by the runtime integration;
    this function deliberately does not discover a parent's known set globally.
    It projects the currently valid portion of that known information, not a
    frozen belief state: an authoritative correction can retire an old known
    finding before its replacement has been received. The replacement earns
    nothing until known; loss provenance remains explicit in detailed output.
    """
    if not isinstance(policy, FindingProgressPolicy):
        raise TypeError('explicit_finding_progress_policy_required')
    if (type(details_limit) is not int or details_limit < 0
            or type(details_offset) is not int or details_offset < 0):
        raise ValueError('finding_detail_page_requires_nonnegative_integers')
    if isinstance(known_assessment_refs, (str, bytes)):
        raise TypeError('explicit_known_assessment_references_required')
    known = sorted(set(known_assessment_refs))
    with store.read_snapshot():
        scope = store.validate_scope(scope)
        return _project_snapshot(store, scope, policy, known, details_limit, details_offset)


def _project_snapshot(store, scope, policy, known, limit, offset):
    """Disk-backed dependency closure, unique keys, and requested details only."""
    spool = sqlite3.connect('')
    spool.row_factory = sqlite3.Row
    try:
        spool.executescript('''PRAGMA temp_store=FILE; PRAGMA cache_size=-2048;
            CREATE TABLE current_findings(key TEXT,ref TEXT,payload TEXT,PRIMARY KEY(key,ref));
            CREATE TABLE known_findings(key TEXT,ref TEXT,payload TEXT,PRIMARY KEY(key,ref));
            CREATE TABLE inactive(ref TEXT PRIMARY KEY,payload TEXT);
        ''')
        validity = FindingValidity(store, scope, spool=spool)
        normalizer = FindingIdentity(store)
        for row in validity.current_records():
            if row['investigation_finding']['status'] != 'retained' or not target_eligible(store, row, scope):
                continue
            value = normalizer.finding(row)
            spool.execute('INSERT INTO current_findings VALUES(?,?,?)',
                (value['finding_key'], row['id'], canonical(value)))
        for ref in known:
            row = store._require(ref, {'assessment'})
            finding = row.get('investigation_finding')
            reason = ('typed_finding_not_recorded' if finding is None else
                'finding_target_outside_scope' if not target_eligible(store, row, scope) else
                'scientific_finding_withdrawn' if finding['status'] == 'withdrawn' else None)
            if reason is None:
                value = normalizer.finding(row)
                # Known canonical meaning survives a representation/opinion-only
                # revision when some current valid record witnesses that meaning.
                if spool.execute('SELECT 1 FROM current_findings WHERE key=? LIMIT 1',
                                 (value['finding_key'],)).fetchone():
                    spool.execute('INSERT INTO known_findings VALUES(?,?,?)',
                        (value['finding_key'], ref, canonical(value)))
                    continue
                reason = ('finding_replaced' if validity.is_replaced(ref)
                    else 'not_current_assessment_revision')
            item = {'assessment_ref': ref, 'reason': reason}
            if reason == 'scientific_finding_withdrawn':
                item['withdrawal_reason'] = finding['withdrawal_reason']
            elif reason == 'not_current_assessment_revision':
                revision = store.db.execute('SELECT record_ref FROM current_revisions '
                    "WHERE record_type='assessment' AND key_ref=?", (store.assessment_key(row),)).fetchone()
                if revision:
                    item['current_assessment_ref'] = revision[0]
                    replacement = store.get(revision[0]).get('investigation_finding', {})
                    if replacement.get('status') == 'withdrawn':
                        item.update(reason='scientific_finding_withdrawn',
                                    withdrawal_reason=replacement['withdrawal_reason'])
            spool.execute('INSERT INTO inactive VALUES(?,?)', (ref, canonical(item)))
        count = spool.execute('SELECT count(DISTINCT key) FROM known_findings').fetchone()[0]
        total = spool.execute('SELECT count(*) FROM known_findings').fetchone()[0]
        inactive_total = spool.execute('SELECT count(*) FROM inactive').fetchone()[0]
        credit = policy.finding_unit*count
        if not math.isfinite(credit):
            raise ValueError('finite_investigation_progress_required')
        details, inactive = [], []
        for row in spool.execute('SELECT * FROM known_findings ORDER BY key,ref LIMIT ? OFFSET ?', (limit, offset)):
            current = spool.execute('SELECT ref FROM current_findings WHERE key=? ORDER BY ref LIMIT 1',
                                    (row['key'],)).fetchone()[0]
            details.append({**json.loads(row['payload']), 'known_assessment_ref': row['ref'],
                'current_assessment_ref': current, 'credit': policy.finding_unit,
                'credit_unit': 'one_distinct_finding_key_not_each_representation_row'})
        for row in spool.execute('SELECT * FROM inactive ORDER BY ref LIMIT ? OFFSET ?', (limit, offset)):
            item = json.loads(row['payload'])
            if item['reason'] == 'finding_replaced':
                witness = validity.one_witness(row['ref'])
                item['replacement_refs'] = [witness] if witness else []
                item['replacement_provenance'] = 'one_current_correction_witness'
            inactive.append(item)
        return {'credit': credit, 'scope': scope, 'policy': policy.as_record(),
            'interpretation': 'scientific_information_progress_not_annotation_support',
            'retained_finding_count': count, 'source_contributions': details,
            'inactive_dependencies': inactive,
            'detail_pages': {'offset': offset, 'limit': limit, 'source_contributions_total': total,
                'source_contribution_row_unit': 'one_known_representation_and_current_validity_witness',
                'inactive_dependencies_total': inactive_total}}
    finally:
        spool.close()
