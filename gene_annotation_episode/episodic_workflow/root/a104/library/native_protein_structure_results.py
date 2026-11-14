"""Selected protein result acquisition, qualification and requested publication.

The results episode owns the selection. This host reuses the capture and bounded
result worker; it neither performs a native analysis nor chooses another job.
Receipt proof owns durable action state and historical authority. Scientific
bytes are opened only during selected work or an explicitly requested check.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
from typing import get_args
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a104.library.native_protein_structure_acquisition import decode_protein_structure_json, retained_protein_structure_file
from gene_annotation_episode.episodic_workflow.root.a104.library.native_protein_structure_returns import FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE, SEQUENCE_SOURCE
from gene_annotation_episode.episodic_workflow.root.a104.library.protein_structure_authority import ProteinFactGroups, ProteinResultAuthorityRecord, ProteinStructureOperandError
from gene_annotation_episode.episodic_workflow.root.a104.library.protein_structure_contracts import IssueCode, ResultCustody, issue, same
from gene_annotation_episode.episodic_workflow.root.a104.library.protein_structure_result_receipts import ProteinResultReceipts
from gene_annotation_episode.episodic_workflow.root.a104.library.protein_structure_result_views import validate_protein_structure_failure_return, validate_protein_structure_projection_rows
_CODES = frozenset(get_args(IssueCode))

def _require(condition, code='original_commission_mismatch'):
    if not condition:
        raise ProteinStructureOperandError(issue(code, stage='authority', field='receipt'))

def _problem(error, *, stage='input', field='file_identity', role=None):
    if isinstance(error, ProteinStructureOperandError):
        return deepcopy(error.issue)
    code = str(error) if str(error) in _CODES else 'retained_artifact_missing' if isinstance(error, OSError) else 'invalid_schema'
    return issue(code, stage=stage, field=field, artifact_role=role)

def _unique(rows):
    result, seen = ([], set())
    for row in rows:
        key = canonical(row)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(row))
    return result

def _empty_facts() -> ProteinFactGroups:
    return {name: [] for name in FACT_SOURCES}

class NativeProteinStructureResults:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.receipts = ProteinResultReceipts(owner)

    def applies(self, context) -> bool:
        assignment = plain(context.assignment)
        return context.role == 'results' and isinstance(assignment, dict) and isinstance(assignment.get('selector'), dict) and (assignment['selector'].get('version') == 'protein_structure_result_selector_v1')

    def _bytes(self, identity, *, role=None):
        try:
            raw = retained_protein_structure_file(self.store, identity).read_bytes()
            if len(raw) != identity['byte_length'] or hashlib.sha256(raw).hexdigest() != identity['sha256']:
                raise ValueError('input_digest_mismatch')
            return raw
        except (ValueError, OSError) as error:
            raise ProteinStructureOperandError(_problem(error, role=role)) from error

    def _json(self, identity, *, role=None):
        try:
            return decode_protein_structure_json(self._bytes(identity, role=role), canonical_bytes=True)
        except ValueError as error:
            raise ProteinStructureOperandError(_problem(error, role=role)) from error

    def read_result_authority(self, custody: ResultCustody, *, scope: dict) -> ProteinResultAuthorityRecord:
        try:
            validate_protein_structure_failure_return({'version': 'protein_structure_failure_return_v1', 'custody': custody, 'projection_id': None, 'issue': issue('original_commission_mismatch', stage='authority', field='receipt')})
            _require(custody is not None and custody['run_id'] == self.owner.run_id)
            receipt = self.receipts.read_completed(episode_id=custody['result_episode_id'], operation_key=custody['result_operation_key'], scope=plain(scope))
            _require(same(custody, receipt['publication']['custody']))
        except (ValueError, TypeError, KeyError) as error:
            raise ProteinStructureOperandError(_problem(error, stage='authority', field='receipt')) from error
        body = receipt['body']
        job = body['bundle']['requested_job']['native_protein_structure']
        return deepcopy({'custody': custody, 'selector': body['intent']['assignment']['selector'], 'request': job['request'], 'software': job['software'], **body['qualified_files'], 'facts': receipt['publication']['facts']})

    def _verify_artifacts(self, receipt):
        body, publication = (receipt['body'], receipt['publication'])
        files = body['qualified_files']
        for projection in publication['facts'][PROJECTION_SOURCE]:
            names = ('sheet_file', 'components_file') if projection['calculation'] is not None else ('native_file',)
            for name in names:
                _require(files[name] is not None)
                self._bytes(files[name], role='native_result' if name == 'native_file' else None)
            if projection['delivery']['kind'] == 'artifact':
                table = self._json(projection['delivery']['table_file'])
                _require(type(table) is dict and set(table) == {'version', 'rows'} and (table['version'] == 'protein_structure_projection_table_v1'), 'invalid_schema')
                envelope = {name: deepcopy(projection[name]) for name in ('projection_id', 'family', 'selection', 'coordinate_set', 'requested_count', 'matched_count', 'returned_count', 'omitted_count', 'state', 'issues', 'qualifications')}
                envelope.update(version='protein_structure_projection_rows_v1', rows=table['rows'], calculation_id=None if projection['calculation'] is None else projection['calculation']['calculation_id'])
                validate_protein_structure_projection_rows(envelope)
        for descriptor in publication['facts'][SAVED_SOURCE]:
            self._bytes(descriptor['sheet_file'])
            self._bytes(descriptor['original_components_file'])
        descriptors = list(publication['facts'][SEQUENCE_SOURCE])
        for projection in publication['facts'][PROJECTION_SOURCE]:
            if projection['delivery']['kind'] == 'values':
                descriptors.extend((field['value'] for row in projection['delivery']['rows'] for field in row['values'] if field['field'] == 'descriptor' and field['value'] is not None))
        for descriptor in _unique(descriptors):
            _require(files['native_file'] is not None)
            self._bytes(files['native_file'], role='native_result')
            for name, role in (('sequence_file', 'sequence'), ('residue_map_file', 'residue_map'), ('structure_file', 'single_structure')):
                self._bytes(descriptor[name], role=role)

    def own_fact_groups(self, context, *, verify_artifacts: bool) -> ProteinFactGroups:
        _require(type(verify_artifacts) is bool)
        facts = _empty_facts()
        for receipt in self.receipts.completed_receipts(context):
            if verify_artifacts:
                self._verify_artifacts(receipt)
            for source in FACT_SOURCES:
                facts[source].extend(receipt['publication']['facts'][source])
        return {source: _unique(rows) for source, rows in facts.items()}

    def owns_reference(self, reference: str) -> bool:
        return self.receipts.owns_reference(reference)
