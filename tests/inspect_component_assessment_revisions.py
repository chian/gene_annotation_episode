"""Read retained assessment revisions and exercise receipt-limited use envelopes.

This checks deterministic revision custody, with synthetic qualification
envelopes around original runtime assessments. It executes no model or native
job and makes no autonomous-workflow or biological-interpretation claim.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

from gene_annotation_episode.a110_qualification import received
from gene_annotation_episode.component_assessment_dependencies import (
    assessment_dependencies, correction_refs, qualification_assessment_changes)
from gene_annotation_episode.state import Store
from gene_annotation_episode.workflow_budget import active_budget


class ReceivedAssessments:
    def __init__(self, store, known):
        self.store, self.known = store, set(known)

    def get(self, reference):
        assert reference in self.known, 'unreceived_assessment_body_was_read'
        return self.store.get(reference)

    def assessment_key(self, row):
        return self.store.assessment_key(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-directory', required=True, type=Path)
    parser.add_argument('--run-directory', required=True, type=Path)
    args = parser.parse_args()
    directory = args.run_directory.resolve()
    assert directory == Path(active_budget()['run_directory']).resolve()
    # Bind the existing reader methods to a read-only original connection.
    # Do not run Store's schema installation against historical runtime state.
    store = Store.__new__(Store)
    store.path = args.state_directory.resolve()
    store.db = sqlite3.connect((store.path/'state.sqlite3').as_uri()+'?mode=ro', uri=True)
    store.db.row_factory = store._row
    original = 'assessment_0e7eb50bfad99206dfc6c769'
    withdrawal = 'assessment_fed0264b934bf2152c07555f'
    replacement = 'assessment_a698902a7c521674272d2793'
    try:
        before = deepcopy(store.get(original))
        narrow = {original}
        base = assessment_dependencies(ReceivedAssessments(store, narrow), original, narrow)
        assert base['retired'] is False and correction_refs(base) == set()
        known = {original, withdrawal}
        updated = assessment_dependencies(ReceivedAssessments(store, known), original, known)
        assert updated['retired'] is True
        assert updated['superseding_assessment_refs'] == [withdrawal]
        assert updated['replacement_refs'] == []
        assert store.get(withdrawal)['investigation_finding']['replaces_refs'] == []
        explicit_known = {original, replacement}
        explicit = assessment_dependencies(ReceivedAssessments(store, explicit_known), original, explicit_known)
        assert explicit['replacement_refs'] == [replacement]
        assert explicit['retired'] is True
        envelope = {'operation': 'chemistry.reaction_evidence',
            'result': {'source_function_finding': {'assessment_ref': original,
                'assessment_revision_dependency': base}},
            'qualification_dependencies': [original]}
        parent_known = {withdrawal}
        parent_reader = ReceivedAssessments(store, parent_known)
        assert qualification_assessment_changes(parent_reader, envelope, parent_known) == [withdrawal]
        partner = {**deepcopy(envelope), 'operation': 'partner.requirement_evidence',
            'result': deepcopy(envelope['result']['source_function_finding'])}
        assert qualification_assessment_changes(parent_reader, partner, parent_known) == [withdrawal]
        already_updated = deepcopy(envelope)
        already_updated['result']['source_function_finding']['assessment_revision_dependency'] = updated
        already_updated['qualification_dependencies'].append(withdrawal)
        assert qualification_assessment_changes(parent_reader, already_updated, parent_known) == []
        historical = deepcopy(envelope)
        historical['result']['source_function_finding'].pop('assessment_revision_dependency')
        assert qualification_assessment_changes(parent_reader, historical, parent_known) == []
        assert before == store.get(original)
        # Real original qualifications without a molecular finding retain their
        # full original bodies, all fifteen selected descriptors and grading.
        refs = {'source_652a80246d3bb72a39a55c57', 'source_bc1738c092497d0564ce9fc9'}
        bodies = {row['source_ref']: json.loads(row['body']) for row in store.db.execute(
            'SELECT source_ref,body FROM a110_experimental_qualifications') if row['source_ref'] in refs}
        assert set(bodies) == refs
        rows = received(store, refs, next(iter(bodies.values()))['scope'], known=refs)
        assert {row['source_ref'] for row in rows} == refs
        for row in rows:
            body = bodies[row['source_ref']]
            assert all(row[key] == value for key, value in body.items())
            assert row['current'] is True
            assert row.get('source_assessment_change_refs', []) == []
        assert store.db.total_changes == 0
        report = {'kind': 'retained_runtime_assessments_and_synthetic_per_use_envelopes',
            'unreceived_withdrawal_not_consumed': True,
            'ordinary_received_revision_retires_original_use': True,
            'explicit_received_replacement_retained': True,
            'parent_uses_authenticated_original_identity_without_reading_private_assessment': True,
            'a107_and_a110_envelope_routing': True,
            'already_updated_retirement_is_not_falsely_stale': True,
            'historical_unreceived_original_is_not_reconstructed': True,
            'original_assessment_unchanged': True,
            'both_original_experimental_qualification_bodies_unchanged': True,
            'record_mutations': store.db.total_changes,
            'autonomous_workflow_validated': False}
        (directory/'revision-review.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report), flush=True)
    finally:
        store.close()


if __name__ == '__main__':
    main()
