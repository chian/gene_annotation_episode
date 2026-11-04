"""Pure selected-byte resolution and provider composition for MSA/MetaCATS.

The caller supplies all bytes and authenticated evidence values. This module
does not open a path, contact a service, submit a job or choose work. Only the
finite declared SlotRef/TreeRef fields are compiled.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from urllib.parse import quote

from . import bvbrc_alignment_bundle_contracts as c
from . import bvbrc_alignment_provider_contracts as common
from .bvbrc_appservice_contracts import _at, _finite_json, _same, validate_contract
from .bvbrc_alignment_values import diagnostic, requirement
from .bvbrc_alignment_associations import extract_alignment_associations
from .bvbrc_metacats_associations import extract_metacats_associations
from . import bvbrc_msa_provider_contracts as msa_contracts
from . import bvbrc_metacats_provider_contracts as meta_contracts
from .bvbrc_msa_inputs import extract_msa_sheet
from .bvbrc_metacats_inputs import extract_metacats_sheet
from .bvbrc_msa_grader import calculate_msa
from .bvbrc_metacats_grader import calculate_metacats
from .bvbrc_msa_xmfa_inputs import verify_xmfa_source_inputs, extract_msa_xmfa_bindings
from . import phylogeny_formats
from . import bvbrc_msa_formats
from . import bvbrc_metacats_formats
from .bvbrc_metacats_input_formats import parse_metacats_input_fasta
from .xmfa_formats import parse_mauve_xmfa


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def _json_evidence(raw, pointer):
    """Check a selected evidence value against supplied bytes when available."""
    def object_pairs(pairs):
        value = {}
        for key, item in pairs:
            c.require(key not in value, 'supplied_evidence_duplicate_json_key')
            value[key] = item
        return value
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=object_pairs)
        _finite_json(value)
        return _at(value, pointer)
    except (UnicodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise ValueError('supplied_evidence_bytes_invalid') from exc


def _unique(rows):
    result = []
    for row in rows:
        if not any(_same(row, prior) for prior in result):
            result.append(deepcopy(row))
    return result


def _merge_requirements(*registries):
    known = {}
    for rows in registries:
        for row in rows:
            validate_contract('AcquisitionRequirement', row)
            identity = row['requirement_id']
            c.require(identity not in known or _same(known[identity], row), 'requirement_identity_conflict')
            known[identity] = deepcopy(row)
    return list(known.values())


def _need(provider, aid, path, reason, *, role=None, kind='scientific_metadata', refs=()):
    identity = 'alignment-bundle/' + '/'.join(quote(s, safe='') for s in (provider, aid, path, reason))
    return requirement(identity, kind=kind, role=role, source_refs=list(dict.fromkeys(refs)), reason_code=reason)


def _artifact(content):
    return {'raw_artifact_ref': content['artifact_ref'], 'source_ref': content['source_ref'], 'sha256': content['sha256']}


def _content(artifact):
    return {'artifact_ref': artifact['raw_artifact_ref'], 'artifact_field': 'artifact_ref',
        'source_ref': artifact['source_ref'], 'sha256': artifact['sha256'], 'byte_count': artifact['byte_count']}


def _representation(artifact):
    return {'task_id': artifact['task_association']['task_id'],
        'object': {k: artifact['workspace_object'][k] for k in ('path', 'uuid', 'type')},
        'sha256': artifact['sha256'], 'byte_count': artifact['byte_count'],
        'observed_range': artifact['transfer']['observed_range'],
        'requested_range': artifact['transfer']['requested_range'],
        'body_complete': artifact['transfer']['body_complete'],
        'object_complete': artifact['transfer']['object_complete'],
        'total_size': artifact['transfer']['total_size']}


def _parse(data, artifact, reader):
    dispatch = {'aligned_fasta': phylogeny_formats.parse_aligned_fasta,
        'metacats_input_fasta': parse_metacats_input_fasta,
        'msa_frequency': bvbrc_msa_formats.parse_msa_frequency_table,
        'metacats_chisq': bvbrc_metacats_formats.parse_metacats_chisq_table,
        'metacats_pair': bvbrc_metacats_formats.parse_metacats_pair_table,
        'metacats_raw_r': bvbrc_metacats_formats.parse_metacats_raw_r_table,
        'metacats_metadata': bvbrc_metacats_formats.parse_metacats_metadata,
        'metacats_adjusted_matrix': bvbrc_metacats_formats.parse_metacats_adjusted_matrix,
        'newick': phylogeny_formats.parse_newick, 'mauve_xmfa_v1': parse_mauve_xmfa}
    return dispatch[reader['reader']](data, artifact=artifact, **{k: v for k, v in reader.items() if k != 'reader'})


class _Unavailable(Exception):
    pass


class _Resolver:
    def __init__(self, bundle, raw, supplied, parameters, provider):
        self.bundle, self.raw, self.supplied, self.parameters, self.provider = bundle, raw, supplied, parameters, provider
        self.plans = {p['analysis']['analysis_id']: p for p in parameters['analyses']}
        self.slots, self.documents, self.reads, self.requirements, self.diagnostics = {}, {}, {}, {}, {}
        self.cache = {}
        self.invalid = set()
        self.bindings = {b['binding_id']: b for b in bundle['input_bindings']}
        for aid in self.plans:
            self.documents[aid], self.reads[aid], self.requirements[aid], self.diagnostics[aid] = [], [], [], []

    def issue(self, aid, reason, path, *, role=None, kind='scientific_metadata', refs=(), severity='qualification', slot=None):
        need = _need(self.provider, aid, path, reason, role=role, kind=kind, refs=refs)
        self.requirements[aid] = _merge_requirements(self.requirements[aid], [need])
        diag = diagnostic(reason, path=path, severity=severity, evidence_refs=list(dict.fromkeys(refs)))
        self.diagnostics[aid] = _unique([*self.diagnostics[aid], diag])
        if slot is not None:
            target = self.slots[(aid, slot)]
            if need['requirement_id'] not in target['requirement_ids']:
                target['requirement_ids'].append(need['requirement_id'])
            target['diagnostics'] = _unique([*target['diagnostics'], diag])
        return need

    def _bytes(self, binding, aid, sid, path):
        raw = self.raw.get(binding['artifact_ref'])
        if raw is None:
            raise _Unavailable()
        if len(raw) != binding['byte_count'] or hashlib.sha256(raw).hexdigest() != binding['sha256']:
            self.slots[(aid, sid)]['state'] = 'invalid'
            self.issue(aid, 'alignment_slot_sha256_conflict', path, role=sid, kind='input_bytes',
                refs=[binding['source_ref']], severity='error', slot=sid)
            self.invalid.add(aid)
            return None
        return raw

    def select(self):
        selected_raw = []
        for index, plan in enumerate(self.parameters['artifact_selection']):
            aid, sid = plan['analysis_id'], plan['slot_id']; path = '/artifact_selection/' + str(index)
            row = {**deepcopy(plan), 'state': 'missing', 'artifacts': [], 'content_bindings': [],
                'acquisition_receipt_refs': [], 'document_ids': [], 'tree_ids': [], 'requirement_ids': [], 'diagnostics': []}
            self.slots[(aid, sid)] = row
            source = plan['source']; data = None; actual_artifact = None
            if source['kind'] == 'acquired_role':
                candidates = [a for a in self.bundle['artifacts'] if a['role'] == source['bundle_role']]
                row['artifacts'] = _unique([{k: a[k] for k in ('raw_artifact_ref', 'source_ref', 'sha256')} for a in candidates])
                row['content_bindings'] = _unique([_content(a) for a in candidates])
                row['acquisition_receipt_refs'] = list(dict.fromkeys(a['transfer']['receipt_ref'] for a in candidates))
                if not candidates:
                    self.issue(aid, 'alignment_slot_missing', path, role=sid, kind='output_bytes', slot=sid); continue
                if len(_unique([_representation(a) for a in candidates])) != 1:
                    row['state'] = 'ambiguous'
                    self.issue(aid, 'alignment_slot_ambiguous', path, role=sid, kind='output_metadata', slot=sid); continue
                valid = True
                for candidate in candidates:
                    try:
                        raw = self._bytes(_content(candidate), aid, sid, path)
                    except _Unavailable:
                        self.issue(aid, 'alignment_slot_missing', path, role=sid, kind='output_bytes', refs=[candidate['source_ref']], slot=sid)
                        valid = False; continue
                    if raw is None:
                        valid = False; continue
                    transfer = candidate['transfer']
                    if not transfer['body_complete'] or transfer['object_complete'] != 'yes':
                        row['state'] = 'incomplete'
                        self.issue(aid, 'alignment_slot_incomplete', path, role=sid, kind='output_bytes', refs=[candidate['source_ref']], slot=sid)
                        valid = False
                    declared, reader = candidate['declared_format'], plan['reader']
                    if reader is not None and (declared['format'] != reader['reader'] or
                            declared['mode'] not in (None, self.plans[aid]['analysis']['mode']) or
                            declared['version'] not in (None, reader.get('dialect'), reader.get('layout'))):
                        row['state'] = 'invalid'; self.invalid.add(aid)
                        self.issue(aid, 'alignment_declared_format_conflict', path, role=sid, kind='parser_binding', refs=[candidate['source_ref']], severity='error', slot=sid)
                        valid = False
                    association = candidate['task_association']
                    for code, condition in (('output_association_unproven', association['kind'] in ('unverified_original_path', 'task_info_folder_member')),
                                            ('output_version_unproven', association['byte_version_status'] != 'producer_bytes_bound')):
                        if condition:
                            d = diagnostic(code, path=path, severity='qualification', evidence_refs=[candidate['source_ref']])
                            row['diagnostics'].append(d); self.diagnostics[aid].append(d)
                if not valid:
                    continue
                # Candidates are already proved equivalent; this order chooses
                # one retained representation only, never competing results.
                candidate = min(candidates, key=lambda a: (a['raw_artifact_ref'], a['source_ref'], a['transfer']['receipt_ref']))
                actual_artifact = {k: candidate[k] for k in ('raw_artifact_ref', 'source_ref', 'sha256')}
                data = self.raw[candidate['raw_artifact_ref']]
                if len(candidates) > 1:
                    d = diagnostic('duplicate_artifact_representation', path=path, severity='qualification', evidence_refs=list(dict.fromkeys(a['source_ref'] for a in candidates)))
                    row['diagnostics'].append(d); self.diagnostics[aid].append(d)
            else:
                binding = source['content']; row['content_bindings'] = [deepcopy(binding)]; row['artifacts'] = [_artifact(binding)]
                if binding not in self.bundle.get('supplied_contents', []):
                    row['state'] = 'invalid'; self.invalid.add(aid)
                    self.issue(aid, 'alignment_supplied_content_unbound', path, role=sid, kind='input_bytes', severity='error', slot=sid); continue
                if source['kind'] == 'original_input' and (source['input_binding_id'] not in self.bindings or
                        not _same(self.bindings[source['input_binding_id']]['content'], binding)):
                    row['state'] = 'invalid'; self.invalid.add(aid)
                    self.issue(aid, 'alignment_supplied_content_unbound', path, role=sid, kind='input_metadata', severity='error', slot=sid); continue
                try:
                    data = self._bytes(binding, aid, sid, path)
                except _Unavailable:
                    self.issue(aid, 'alignment_slot_missing', path, role=sid, kind='input_bytes', refs=[binding['source_ref']], slot=sid); continue
                if data is None:
                    continue
                actual_artifact = _artifact(binding)
            if plan['reader'] is None:
                row['state'] = 'retained_unparsed'
            else:
                selected_raw.append((aid, sid, path, actual_artifact, data, plan['reader']))
        # Category belongs to scientific identity, not the native format. All
        # other reader declarations must agree for the exact same byte string.
        declarations = {}
        for aid, sid, path, artifact, data, reader in selected_raw:
            declarations.setdefault(data, set()).add(_canonical({k: v for k, v in reader.items() if k != 'category_id'}))
        for aid, sid, path, artifact, data, reader in selected_raw:
            row = self.slots[(aid, sid)]
            if len(declarations[data]) > 1:
                row['state'] = 'invalid'; self.invalid.add(aid)
                self.issue(aid, 'alignment_declared_format_conflict', path, role=sid, kind='parser_binding', severity='error', slot=sid); continue
            key = _canonical([artifact, reader])
            if key not in self.cache:
                self.cache[key] = _parse(data, artifact, reader)
            parsed = deepcopy(self.cache[key]); document = None
            if parsed['value'] is not None:
                document = common.validate_parsed_document({'kind': common.READER_KINDS[reader['reader']], 'value': parsed['value']})
                did = common.document_identity(document); row['document_ids'] = [did]
                if document['kind'] == 'tree':
                    row['tree_ids'] = [t['tree_id'] for t in document['value']['trees']]
                previous = [d for d in self.documents[aid] if common.document_identity(d) == did]
                c.require(not previous or previous[0] == document, 'parsed_document_identity_conflict')
                if not previous:
                    self.documents[aid].append(document)
            row['state'] = 'resolved' if document else 'invalid'
            row['diagnostics'] = _unique([*row['diagnostics'], *parsed['diagnostics']])
            read_id = 'alignment-read:' + hashlib.sha256(_canonical([aid, sid, artifact, reader]).encode()).hexdigest()
            self.reads[aid].append({'read_id': read_id, 'slot_id': sid, 'artifact': deepcopy(artifact), 'reader': deepcopy(reader),
                'status': parsed['status'], 'document_ids': list(row['document_ids']), 'diagnostics': deepcopy(parsed['diagnostics'])})
            self.diagnostics[aid] = _unique([*self.diagnostics[aid], *parsed['diagnostics']])
            if document is None:
                self.issue(aid, 'alignment_document_unavailable', path, role=sid, kind='parser_binding', slot=sid)

    def identifier(self, ref, aid, path, *, tree=False, nullable=False):
        if nullable and ref is None:
            return None
        c._check(c.TREE if tree else c.SLOT, ref, 'slot_reference_invalid')
        c.require(ref['analysis_id'] == aid and (aid, ref['slot_id']) in self.slots, 'slot_reference_unknown')
        selected = self.slots[(aid, ref['slot_id'])]
        if not selected['document_ids']:
            self.issue(aid, 'alignment_document_unavailable', path, role=ref['slot_id'])
            raise _Unavailable()
        document = next(d for d in self.documents[aid] if common.document_identity(d) == selected['document_ids'][0])
        if tree:
            c.require(document['kind'] == 'tree', 'tree_document_conflict')
            found = [t['tree_id'] for t in document['value']['trees'] if t['tree_index'] == ref['tree_index']]
            if len(found) != 1:
                self.issue(aid, 'alignment_document_unavailable', path, role=ref['slot_id']); raise _Unavailable()
            return found[0]
        return common.document_identity(document)

    def record(self, row, aid, path, fields):
        result = deepcopy(row)
        for name, tree, nullable in fields:
            result[name] = self.identifier(row[name], aid, path + '/' + name, tree=tree, nullable=nullable)
        return result

    def rows(self, values, aid, path, fields):
        result = []
        for index, row in enumerate(values):
            try:
                result.append(self.record(row, aid, path + '/' + str(index), fields))
            except _Unavailable:
                continue
        return result

    def analysis(self, plan):
        result = deepcopy(plan['analysis']); aid = result['analysis_id']; path = '/analyses/' + str(list(self.plans).index(aid)) + '/analysis'
        fields = ('alignment_id', 'frequency_table_id', 'consensus_alignment_id', 'xmfa_document_id') if self.provider == 'msa' else ('alignment_id', 'metadata_document_id')
        for field in fields + (('tree_id',) if self.provider == 'msa' else ()):
            try:
                result[field] = self.identifier(result[field], aid, path + '/' + field, tree=field == 'tree_id', nullable=True)
            except _Unavailable:
                result[field] = None
        if self.provider == 'msa':
            if result['reference'] is not None:
                try:
                    result['reference'] = self.record(result['reference'], aid, path + '/reference', [('alignment_id', False, False)])
                except _Unavailable:
                    result['reference'] = None
        else:
            for field in ('adjusted_matrix_ids', 'chisq_table_ids', 'pair_table_ids', 'raw_r_table_ids'):
                kept = []
                for index, ref in enumerate(result[field]):
                    try:
                        kept.append(self.identifier(ref, aid, path + '/' + field + '/' + str(index)))
                    except _Unavailable:
                        pass
                result[field] = list(dict.fromkeys(kept))
        return result

    def _evidence(self, value, aid, path):
        """Authenticate every supplied Evidence, without interpreting claims."""
        if type(value) is dict:
            if set(value) == {'content', 'pointer'}:
                validate_contract('SourceEvidence', value)
                c.require(value in self.bundle['supplied_scientific_metadata'], 'nested_evidence_unbound')
                return
            for key, child in value.items():
                self._evidence(child, aid, path + '/' + key.replace('~', '~0').replace('/', '~1'))
        elif type(value) is list:
            for index, child in enumerate(value):
                self._evidence(child, aid, path + '/' + str(index))

    def _common(self, value, aid, path):
        common.shape(value, ('version', 'analysis_id', 'input_sequences', 'row_joins', 'automatic_row_joins', 'transformations', 'correspondences', 'feature_genomes', 'source_records', 'member_entities'))
        result = deepcopy(value); result['input_sequences'] = []
        for index, row in enumerate(value['input_sequences']):
            try:
                result['input_sequences'].append(self.record(row, aid, path + '/input_sequences/' + str(index), [('document', False, False)]) if row['kind'] == 'parsed_document' else deepcopy(row))
            except _Unavailable:
                pass
        result['row_joins'] = self.rows(value['row_joins'], aid, path + '/row_joins', [('alignment_id', False, False)])
        result['automatic_row_joins'] = self.rows(value['automatic_row_joins'], aid, path + '/automatic_row_joins', [('alignment', False, False)])
        result['correspondences'] = self.rows(value['correspondences'], aid, path + '/correspondences', [('alignment_id', False, False)])
        result['transformations'] = []
        for index, row in enumerate(value['transformations']):
            root = path + '/transformations/' + str(index); target = deepcopy(row)
            try:
                for field in ('input_rows', 'output_rows'):
                    target[field] = [self.record(r, aid, root + '/' + field + '/' + str(i), [('alignment_id', False, False)]) for i, r in enumerate(row[field])]
                if row['kind'] == 'native_terminal_dash_to_hash':
                    target['alignment_id'] = self.identifier(row['alignment_id'], aid, root + '/alignment_id')
                result['transformations'].append(target)
            except _Unavailable:
                pass
        known = {t['transformation_id'] for t in result['transformations']}
        for field in ('row_joins', 'automatic_row_joins', 'correspondences'):
            kept = []
            for index, row in enumerate(result[field]):
                required = row.get('transformation_ids', [row['transformation_id']] if row.get('transformation_id') else [])
                if set(required) <= known:
                    kept.append(row)
                else:
                    self.issue(aid, 'alignment_transformation_unproven', path + '/' + field + '/' + str(index), role='common_associations')
            result[field] = kept
        return result

    def _context(self, value, aid, path):
        result = deepcopy(value)
        if self.provider == 'msa':
            common.shape(value, ('version', 'analysis_id', 'segments', 'reference', 'tree_bindings'))
            # A segment's absent alignment is a type-permitted null; preserve
            # segment identity, original coordinates and the other evidence.
            result['segments'] = []
            for index, row in enumerate(value['segments']):
                target = deepcopy(row)
                try:
                    target['alignment_id'] = self.identifier(row['alignment_id'], aid, path + '/segments/' + str(index) + '/alignment_id', nullable=True)
                except _Unavailable:
                    target['alignment_id'] = None; target['state'] = 'missing'
                result['segments'].append(target)
            if value['reference'] is not None:
                try:
                    result['reference'] = self.record(value['reference'], aid, path + '/reference', [('alignment_id', False, False)])
                except _Unavailable:
                    result['reference'] = None
            result['tree_bindings'] = []
            for index, row in enumerate(value['tree_bindings']):
                root = path + '/tree_bindings/' + str(index)
                try:
                    target = self.record(row, aid, root, [('tree_id', True, False)])
                except _Unavailable:
                    continue
                for field, tree in (('source_tree_id', True), ('alignment_id', False)):
                    try:
                        target[field] = self.identifier(row[field], aid, root + '/' + field, tree=tree, nullable=True)
                    except _Unavailable:
                        target[field] = None
                target['tip_rows'] = self.rows(row['tip_rows'], aid, root + '/tip_rows', [('alignment_id', False, False)])
                result['tree_bindings'].append(target)
            return result
        from .bvbrc_metacats_association_contracts import DECL_KEYS
        common.shape(value, DECL_KEYS)
        self._original_groups(value)
        for field, fields in (
                ('metadata_joins', [('metadata', False, False), ('alignment', False, False)]),
                ('explicit_memberships', [('alignment_id', False, False)]),
                ('r_columns', [('adjusted_matrix', False, False)]),
                ('exported_group_joins', [('table_id', False, False)]),
                ('native_test_joins', [('table_id', False, False), ('alignment_id', False, True)])):
            result[field] = self.rows(value[field], aid, path + '/' + field, fields)
        result['categories'] = []
        for index, row in enumerate(value['categories']):
            target = deepcopy(row)
            try:
                target['metadata'] = self.identifier(row['metadata'], aid, path + '/categories/' + str(index) + '/metadata', nullable=True)
            except _Unavailable:
                target.update(metadata=None, metadata_column_index_0based=None, raw_heading_token=None)
            result['categories'].append(target)
        known_meta = {r['category_id'] for r in result['categories'] if r['metadata'] is not None}
        result['biological_group_populations'] = []
        for index, row in enumerate(value['biological_group_populations']):
            if row['kind'] == 'explicit' or row['category_id'] in known_meta:
                result['biological_group_populations'].append(deepcopy(row))
            else:
                self.issue(aid, 'metacats_metadata_join_missing', path + '/biological_group_populations/' + str(index), role='metacats_context')
        return result

    def _original_groups(self, value):
        params = self.bundle['original_task']['submitted_parameters']
        for row in value['auto_group_entries']:
            bid = row['input_binding_id']; c.require(bid in self.bindings, 'original_auto_binding_unknown')
            binding = self.bindings[bid]; original = _at(params, binding['parameter_pointer'])
            c.require(type(original) is list and type(row['entry_index_0based']) is int and 0 <= row['entry_index_0based'] < len(original), 'original_auto_entry_unknown')
            expected_pointer = binding['parameter_pointer'] + '/' + str(row['entry_index_0based'])
            c.require(row['original_parameter_pointer'] == expected_pointer, 'original_auto_pointer_conflict')
            expected = {'id': row['feature_id'], 'grp': row['raw_group_value']}
            c.require(_same(_at(params, row['original_parameter_pointer']), expected), 'original_auto_value_conflict')
        for source in value['group_sources']:
            for row in source['bindings']:
                c.require(row['input_binding_id'] in self.bindings, 'original_group_binding_unknown')
                binding = self.bindings[row['input_binding_id']]; original = _at(params, binding['parameter_pointer'])
                # Original feature-group bindings can select one resource or
                # the original ordered list of resources; no label join.
                c.require(_same(original, row['group_id']) or type(original) is list and row['group_id'] in original, 'original_group_value_conflict')

    def scientific_values(self, plan):
        aid = plan['analysis']['analysis_id']; output = []
        for index, selected in enumerate(plan['scientific_inputs']):
            role = selected['role']; path = '/analyses/' + str(list(self.plans).index(aid)) + '/scientific_inputs/' + str(index)
            try:
                c.require(selected['evidence'] in self.bundle['supplied_scientific_metadata'], 'supplied_evidence_unbound')
                found = [r for r in self.supplied if _same(r['evidence'], selected['evidence'])]
                if not found:
                    self.issue(aid, 'alignment_supplied_evidence_unbound', path, role=role); continue
                c.require(len(found) == 1, 'supplied_evidence_ambiguous')
                value = deepcopy(found[0]['value']); self._evidence(value, aid, path)
                c.require(type(value) is dict, 'supplied_value_invalid')
                if role == 'observed_run':
                    common.validate_run_record(value)
                    c.require(value['original_task_id'] == self.bundle['original_task']['task_id'], 'original_task_conflict')
                    self._requested_settings(value)
                else:
                    c.require(value.get('analysis_id') == aid, 'supplied_analysis_conflict')
                    if role == 'common_associations':
                        value = self._common(value, aid, path)
                    elif role in ('msa_context', 'metacats_context'):
                        value = self._context(value, aid, path)
                    elif role == 'xmfa_sources':
                        common.shape(value, ('version', 'analysis_id', 'items'))
                        c.require(value['version'] == 'bvbrc_msa_xmfa_sources_v1', 'source_version_invalid')
                        value['items'] = self.rows(value['items'], aid, path + '/items', [('document', False, False)])
                        c.require(len({r['document'] for r in value['items']}) == len(value['items']), 'source_document_duplicate')
                        for row in value['items']:
                            common.shape(row, ('document', 'inputs', 'source_readers', 'source_comparison', 'evidence'))
                    elif role == 'function_assignments':
                        common.shape(value, ('version', 'analysis_id', 'assignments', 'equivalences'))
                        c.require(value['version'] == 'bvbrc_alignment_functions_v1', 'source_version_invalid')
                    elif role == 'taxonomy_assignments':
                        common.shape(value, ('version', 'analysis_id', 'assignments'))
                        c.require(value['version'] == 'bvbrc_alignment_taxonomy_v1', 'source_version_invalid')
                output.append({'role': role, 'evidence': deepcopy(selected['evidence']), 'value': value})
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                self.invalid.add(aid)
                code = str(exc)
                reason = ('alignment_supplied_evidence_unbound' if code.endswith(('nested_evidence_unbound', 'supplied_evidence_unbound')) else
                    'alignment_original_task_conflict' if code.endswith(('original_auto_binding_unknown', 'original_auto_entry_unknown',
                        'original_auto_pointer_conflict', 'original_auto_value_conflict', 'original_group_binding_unknown',
                        'original_group_value_conflict', 'original_task_conflict', 'requested_setting_conflict')) else
                    'alignment_supplied_value_invalid')
                self.issue(aid, reason, path, role=role, severity='error')
        return output

    def _requested_settings(self, run):
        params = self.bundle['original_task']['submitted_parameters']
        # Exact source parameter names only. An unsupported requested mapping
        # cannot be manufactured from a source default or observed setting.
        names = {'requested_molecule': ('alphabet',), 'aligner': ('aligner',), 'mafft_strategy': ('strategy',),
            'snp_reference_type': ('ref_type',), 'snp_reference_string': ('ref_string',),
            'export_cutoff': ('p_value', 'pvalue'), 'threads': ('threads',), 'translation_table': ('translation_table',),
            'input_mode': ('input_type',), 'epsilon': ('epsilon',)}
        for setting in run['settings']:
            if setting['origin'] != 'requested':
                continue
            candidates = [params[k] for k in names.get(setting['name'], (setting['name'],)) if k in params]
            if setting['name'] == 'aligner':
                canonical = {'Muscle': 'muscle', 'Mafft': 'mafft', 'progressiveMauve': 'progressive_mauve'}
                candidates = [canonical.get(v, v) if type(v) is str else v for v in candidates]
            c.require(candidates and all(_same(v, setting['value']) for v in candidates), 'requested_setting_conflict')

    def output(self):
        self.select(); analyses = []
        for aid, plan in self.plans.items():
            analysis = self.analysis(plan)
            values = self.scientific_values(plan)
            try:
                self._evidence(plan, aid, '/analyses/' + str(list(self.plans).index(aid)))
            except ValueError:
                self.invalid.add(aid); self.issue(aid, 'alignment_supplied_evidence_unbound', '/analyses/' + str(list(self.plans).index(aid)), severity='error')
            analyses.append({'analysis_id': aid, 'status': 'invalid' if aid in self.invalid else 'partial' if self.requirements[aid] or self.diagnostics[aid] else 'ok',
                'analysis': analysis, 'inputs': deepcopy(self.bundle['input_bindings']), 'documents': deepcopy(self.documents[aid]),
                'read_outcomes': deepcopy(self.reads[aid]), 'scientific_values': values, 'population_plans': deepcopy(plan['population_plans']),
                'calculation_parameters': deepcopy(plan['calculation_parameters']), 'requirements': deepcopy(self.requirements[aid]), 'diagnostics': _unique(self.diagnostics[aid])})
        return {'provider': self.provider, 'parameters': deepcopy(self.parameters), 'selections': list(self.slots.values()), 'analyses': analyses,
            'requirements': _merge_requirements(self.bundle['missing_requirements'], *(a['requirements'] for a in analyses)),
            'diagnostics': _unique([*self.bundle['diagnostics'], *(d for a in analyses for d in a['diagnostics'])])}


def resolve_bundle(bundle: dict, *, artifact_bytes: dict[str, bytes], supplied_values: list[dict], parameters: dict, provider: str) -> dict:
    parameters = c.validate_parameters(parameters, provider=provider)
    bundle = validate_contract('ArtifactBundle', bundle)
    expected = 'MSA' if provider == 'msa' else 'MetaCATS'
    c.require(bundle['original_task']['required_application_id'] == expected and bundle['original_task']['native_application_id'] == expected, 'original_task_conflict')
    allowed = {a['raw_artifact_ref'] for a in bundle['artifacts']} | {v['artifact_ref'] for v in bundle.get('supplied_contents', [])}
    c.require(type(artifact_bytes) is dict and all(type(k) is str and type(v) is bytes for k,v in artifact_bytes.items()) and set(artifact_bytes) <= allowed, 'artifact_bytes_invalid')
    for binding in bundle['input_bindings']:
        expected_value = binding['workspace_path'] if binding['kind'] in ('workspace_object', 'retained_bytes') else binding['inline_value']
        c.require(_same(_at(bundle['original_task']['submitted_parameters'], binding['parameter_pointer']), expected_value), 'original_input_conflict')
    _finite_json(supplied_values); c.require(type(supplied_values) is list, 'supplied_values_invalid')
    seen = []
    for row in supplied_values:
        common.shape(row, ('evidence', 'value')); validate_contract('SourceEvidence', row['evidence'])
        c.require(row['evidence'] in bundle['supplied_scientific_metadata'] and row['evidence'] not in seen, 'supplied_evidence_unbound')
        seen.append(row['evidence'])
    # Evidence values are authenticated by host custody. When their underlying
    # bytes were also explicitly selected, verify those actual bytes as well;
    # do not require an unrequested duplicate content acquisition.
    for content in bundle.get('supplied_contents', []):
        raw = artifact_bytes.get(content['artifact_ref'])
        if raw is not None:
            c.require(len(raw) == content['byte_count'] and hashlib.sha256(raw).hexdigest() == content['sha256'], 'supplied_content_bytes_conflict')
    for row in supplied_values:
        evidence = row['evidence']; content = evidence['content']
        raw = artifact_bytes.get(content['artifact_ref'])
        if raw is not None:
            c.require(len(raw) == content['byte_count'] and hashlib.sha256(raw).hexdigest() == content['sha256'], 'supplied_content_bytes_conflict')
            c.require(_same(_json_evidence(raw, evidence['pointer']), row['value']), 'supplied_evidence_value_conflict')
    return _Resolver(bundle, artifact_bytes, supplied_values, parameters, provider).output()


def _populations(compiler, analysis):
    aid = analysis['analysis_id']; output = {k: [] for k in ('alignments', 'composition', 'taxonomy', 'leaves')}
    documents = {common.document_identity(d): d for d in analysis['documents']}
    for index, plan in enumerate(analysis['population_plans']):
        path = '/analyses/' + str(list(compiler.plans).index(aid)) + '/population_plans/' + str(index)
        kind = plan['kind']
        try:
            if kind in ('composition', 'taxonomy'):
                output[kind].append(deepcopy(plan['population'])); continue
            if kind == 'whole_tree':
                tree_id = compiler.identifier(plan['tree'], aid, path + '/tree', tree=True)
                tree = next(t for d in analysis['documents'] if d['kind'] == 'tree' for t in d['value']['trees'] if t['tree_id'] == tree_id)
                output['leaves'].append({'population_id': plan['population_id'], 'tree_id': tree_id,
                    'node_indices': [n['node_index'] for n in tree['nodes'] if not n['child_indices']], 'completeness': 'complete', 'evidence': []})
                continue
            did = compiler.identifier(plan['alignment'], aid, path + '/alignment')
            c.require(documents[did]['kind'] == 'alignment', 'population_document_conflict')
            alignment = documents[did]['value']; width = alignment['observed_column_count']
            if width is None:
                width = alignment['declared_column_count']
            if width is None:
                width = max((len(r['sequence']) for r in alignment['rows']), default=0)
            row = {'population_id': plan['population_id'], 'alignment_id': did,
                'row_indices': [r['row_index'] for r in alignment['rows']], 'columns_0based': list(range(width)),
                'completeness': alignment['completeness'], 'evidence': []}
            if kind == 'alignment_subset':
                row.update({k: deepcopy(plan[k]) for k in ('row_indices', 'columns_0based', 'completeness', 'evidence')})
                if alignment['completeness'] != 'complete' and row['completeness'] == 'complete':
                    row['completeness'] = alignment['completeness']
            output['alignments'].append(row)
        except _Unavailable:
            pass
    return output


def _calculations(compiler, analysis):
    aid = analysis['analysis_id']; original = analysis['calculation_parameters']; output = {'version': original['version'], 'requests': []}
    omitted = set()
    for index, row in enumerate(original['requests']):
        path = '/analyses/' + str(list(compiler.plans).index(aid)) + '/calculation_parameters/requests/' + str(index)
        target = deepcopy(row)
        try:
            for key in ('alignment_id', 'document_id'):
                if key in row:
                    target[key] = compiler.identifier(row[key], aid, path + '/' + key)
            if 'observed_table_id' in row:
                try:
                    target['observed_table_id'] = compiler.identifier(row['observed_table_id'], aid, path + '/observed_table_id', nullable=True)
                except _Unavailable:
                    target['observed_table_id'] = None
            if row['kind'] == 'msa_reference_differences':
                target['reference'] = compiler.record(row['reference'], aid, path + '/reference', [('alignment_id', False, False)])
            if row['kind'] == 'relationship_comparison':
                for key in ('gene_tree_id', 'organismal_tree_id'):
                    target[key] = compiler.identifier(row[key], aid, path + '/' + key, tree=True)
                target['injective_tip_join'] = [compiler.record(r, aid, path + '/injective_tip_join/' + str(i), [('gene_tree_id', True, False), ('organismal_tree_id', True, False)]) for i, r in enumerate(row['injective_tip_join'])]
            if row['kind'].startswith('xmfa_') and 'selection' in row:
                target['selection']['document_id'] = compiler.identifier(row['selection']['document_id'], aid, path + '/selection/document_id')
            if row['kind'] == 'multiplicity' and row['p_values']['kind'] == 'native_tables':
                target['p_values']['table_ids'] = [compiler.identifier(ref, aid, path + '/p_values/table_ids/' + str(i)) for i, ref in enumerate(row['p_values']['table_ids'])]
            output['requests'].append(target)
        except _Unavailable:
            compiler.issue(aid, 'alignment_calculation_dependency_unavailable', path, role=row['request_id'])
            omitted.add(row['request_id'])
    changed = True
    while changed:
        changed = False
        for row in list(output['requests']):
            if set(c._request_dependencies(row)) & omitted:
                index = next(i for i,r in enumerate(original['requests']) if r['request_id'] == row['request_id'])
                path = '/analyses/' + str(list(compiler.plans).index(aid)) + '/calculation_parameters/requests/' + str(index)
                compiler.issue(aid, 'alignment_calculation_dependency_unavailable', path, role=row['request_id'])
                omitted.add(row['request_id']); output['requests'].remove(row); changed = True
    validator = msa_contracts.validate_msa_parameters if compiler.provider == 'msa' else meta_contracts.validate_metacats_parameters
    return validator(output)


def _empty_common(aid):
    return {'version': 'bvbrc_alignment_associations_v1', 'analysis_id': aid,
        **{k: [] for k in ('input_sequences', 'row_joins', 'automatic_row_joins', 'transformations',
            'correspondences', 'feature_genomes', 'source_records', 'member_entities')}}


def _empty_metacats(aid):
    from .bvbrc_metacats_association_contracts import DECL_KEYS
    return {'version': 'bvbrc_metacats_context_v1', 'analysis_id': aid,
        **{k: [] for k in DECL_KEYS if k not in ('version', 'analysis_id')}}


def _assemble(compiler, resolved):
    aid = resolved['analysis_id']; values = {r['role']: r['value'] for r in resolved['scientific_values']}
    documents = tuple(resolved['documents']); inputs = tuple(resolved['inputs']); analysis = deepcopy(resolved['analysis'])
    declarations = {'common': values.get('common_associations', _empty_common(aid)),
        'functions': values.get('function_assignments'), 'taxonomy': values.get('taxonomy_assignments')}
    associated = extract_alignment_associations(inputs=inputs, documents=documents, declarations=declarations)
    if associated['value'] is None:
        compiler.issue(aid, 'alignment_supplied_value_invalid', '/analyses/' + str(list(compiler.plans).index(aid)) + '/scientific_inputs', role='common_associations', severity='error')
        return None, None, associated['diagnostics']
    associations = associated['value']; populations = _populations(compiler, resolved)
    run = values.get('observed_run', {'original_task_id': compiler.bundle['original_task']['task_id'],
        'settings': [], 'commands': [], 'versions': [], 'conflicts': [], 'completeness': 'unknown'})
    arguments = dict(analysis=analysis, inputs=inputs, documents=documents, read_outcomes=tuple(resolved['read_outcomes']),
        run=run, associations=associations, populations=populations, parameters=compiler.plans[aid]['read_parameters'])
    if compiler.provider == 'msa':
        context = values.get('msa_context')
        if context is not None:
            c.require(context['reference'] == analysis['reference'], 'msa_context_reference_conflict')
            segments, trees = context['segments'], context['tree_bindings']
        else:
            segments, trees = [], []
            if analysis['segment_ids']:
                compiler.issue(aid, 'msa_segment_membership_unresolved', '/analyses/' + str(list(compiler.plans).index(aid)) + '/analysis/segment_ids', role='msa_context')
                analysis['segment_ids'] = []
        bindings = []
        for index, item in enumerate(values.get('xmfa_sources', {}).get('items', [])):
            selected = [s for s in compiler.slots.values() if s['analysis_id'] == aid and s['semantic_role'] == 'xmfa_staged_source' and s['state'] in ('retained_unparsed', 'resolved')]
            contents = _unique([b for s in selected for b in s['content_bindings']])
            raw = {b['artifact_ref']: compiler.raw[b['artifact_ref']] for b in contents if b['artifact_ref'] in compiler.raw}
            document = next((d['value'] for d in documents if d['kind'] == 'xmfa' and d['value']['document_id'] == item['document']), None)
            c.require(document is not None, 'xmfa_source_document_conflict')
            verification = verify_xmfa_source_inputs(item['inputs'], source_readers=tuple(item['source_readers']),
                artifact_bytes=raw, content_bindings=tuple(contents), associations=associations)
            bindings.append(extract_msa_xmfa_bindings(document, verification=verification,
                source_comparison=item['source_comparison'], evidence=tuple(item['evidence'])))
        parsed = extract_msa_sheet(**arguments, segments=tuple(segments), tree_bindings=tuple(trees), xmfa_bindings=tuple(bindings))
    else:
        categories = extract_metacats_associations(analysis=analysis, documents=documents, associations=associations,
            declarations=values.get('metacats_context', _empty_metacats(aid)))
        if categories['value'] is None:
            compiler.issue(aid, 'alignment_supplied_value_invalid', '/analyses/' + str(list(compiler.plans).index(aid)) + '/scientific_inputs', role='metacats_context', severity='error')
            return None, None, categories['diagnostics']
        parsed = extract_metacats_sheet(**arguments, category_associations=categories['value'])
    if parsed['value'] is None:
        compiler.issue(aid, 'alignment_supplied_value_invalid', '/analyses/' + str(list(compiler.plans).index(aid)), role='sheet', severity='error')
        return None, None, parsed['diagnostics']
    try:
        parameters = _calculations(compiler, resolved)
        components = (calculate_msa if compiler.provider == 'msa' else calculate_metacats)(parsed['value'], parameters)
    except ValueError:
        compiler.issue(aid, 'alignment_calculation_invalid', '/analyses/' + str(list(compiler.plans).index(aid)) + '/calculation_parameters', severity='error')
        return parsed['value'], None, parsed['diagnostics']
    return parsed['value'], components, parsed['diagnostics']


def _cross_family(row, *, sheet_set, component_set, parameters, provider):
    """Compile scoped identities and unchanged p cells from named saved outputs.

    Each analysis uses the exact provider's saved-family compilation. The
    adapter combines those scoped populations only after checking all sources;
    no filtered row count becomes an all-tests denominator.
    """
    from .bvbrc_metacats_calculators import adjust_p_values
    from .bvbrc_metacats_calculation_contracts import validate_test_family
    family = row['family']; source = row['p_values']; identity = row['family_request_id']
    sheets = {r['analysis_id']: r['sheet'] for r in sheet_set['analyses']}
    components = {r['analysis_id']: r['components'] for r in component_set['analyses']}
    plans = {r['analysis']['analysis_id']: r for r in parameters['analyses']}
    all_cells, all_ids, needs, diagnostics, ordered_explicit = [], [], [], [], {}
    unavailable_source = False
    selected_analyses = {r['analysis_id'] for r in source['requests' if source['kind'] == 'statistical_results' else 'tables']}
    if selected_analyses != set(family['analysis_ids']):
        return {'family_request_id': identity, 'status': 'partial', 'value': None,
            'requirements': [_need(provider, '@families', identity, 'metacats_test_family_incomplete', role=identity)], 'diagnostics': []}
    selected_scopes = set()
    for aid in family['analysis_ids']:
        sheet, component = sheets.get(aid), components.get(aid)
        if sheet is None or component is None:
            needs.append(_need(provider, '@families', identity + '/' + aid, 'alignment_calculation_dependency_unavailable', role=identity)); continue
        local_family = {k: deepcopy(v) for k,v in family.items()}
        local_family['analysis_ids'] = [aid]
        local_family['category_ids'] = [cat for cat in family['category_ids'] if cat in plans[aid]['analysis']['category_ids']]
        local_family['tests'] = [deepcopy(t['test']) for t in family['tests'] if t['analysis_id'] == aid]
        # The total count and assumptions describe the union, not each shard.
        # Local compilation proves identities/populations; global count is
        # applied exactly once by the unchanged adjustment function below.
        local_family.update(population_state='complete' if family['population_state'] == 'complete' else 'unknown', total_test_count=None, assumption=None)
        outcomes = {r['request_id']: r for r in component['results']}
        if source['kind'] == 'statistical_results':
            targets = [r['request_id'] for r in source['requests'] if r['analysis_id'] == aid]
            pplan = {'kind': 'statistical_results', 'statistics_request_ids': targets, 'field': 'mathematical_p'}
        else:
            targets = [r['request_id'] for r in source['eligibility_statistics_requests'] if r['analysis_id'] == aid]
            tables = []
            for ref in source['tables']:
                if ref['analysis_id'] != aid:
                    continue
                selection = next(s for s in sheet_set['selections'] if s['analysis_id'] == aid and s['slot_id'] == ref['slot_id'])
                if len(selection['document_ids']) != 1:
                    needs.append(_need(provider, '@families', identity + '/' + aid + '/' + ref['slot_id'], 'metacats_test_family_incomplete', role=identity))
                    unavailable_source = True
                    continue
                tables.append(selection['document_ids'][0])
            pplan = {'kind': 'native_tables', 'table_ids': tables, 'eligibility_statistics_request_ids': targets}
        if any(t not in outcomes for t in targets):
            needs.append(_need(provider, '@families', identity + '/' + aid, 'alignment_calculation_dependency_unavailable', role=identity)); continue
        if source['kind'] == 'statistical_results':
            cats = {outcomes[t]['value']['category_id'] for t in targets if outcomes[t]['value'] is not None}
        else:
            cats = {d['value']['category_id'] for d in sheet['documents'] if common.document_identity(d) in pplan['table_ids']}
        local_family['category_ids'] = [cat for cat in local_family['category_ids'] if cat in cats]
        if not local_family['category_ids']:
            needs.append(_need(provider, '@families', identity + '/' + aid, 'metacats_test_family_incomplete', role=identity)); continue
        selected_scopes.update((aid, cat) for cat in local_family['category_ids'])
        request = {'kind': 'multiplicity', 'request_id': identity, 'family': local_family, 'p_values': pplan,
            **{k: deepcopy(row[k]) for k in ('method', 'alpha', 'dependence_assumption')}}
        compiled, cells, extra = meta_contracts.compile_family(sheet, request, outcomes)
        if compiled is None:
            needs += extra; unavailable_source = True; continue
        # Duplicate actual IDs or ambiguous original selectors are conflicts,
        # even if their p values happen to agree.
        c.require(not set(compiled['test_ids']) & set(all_ids), 'cross_family_test_identity_ambiguous')
        if family['selection'] == 'explicit_tests':
            for selector, cell in zip(local_family['tests'], cells):
                ordered_explicit[(aid, _canonical(selector))] = cell
        all_ids += compiled['test_ids']; all_cells += cells; needs += extra
    required_scopes = {(aid, cat) for aid in family['analysis_ids'] for cat in family['category_ids'] if cat in plans[aid]['analysis']['category_ids']}
    if family['selection'] == 'all_eligible' and selected_scopes != required_scopes:
        needs.append(_need(provider, '@families', identity, 'metacats_test_family_incomplete', role=identity))
    if needs and (unavailable_source or family['population_state'] == 'complete' or any(r['reason_code'] == 'alignment_calculation_dependency_unavailable' for r in needs)):
        return {'family_request_id': identity, 'status': 'partial', 'value': None, 'requirements': _merge_requirements(needs), 'diagnostics': diagnostics}
    if family['selection'] == 'explicit_tests':
        all_cells = [ordered_explicit[(item['analysis_id'], _canonical(item['test']))] for item in family['tests']]
        all_ids = [cell['test_id'] for cell in all_cells]
    actual = {k: deepcopy(v) for k,v in family.items() if k not in ('selection', 'tests')}; actual['test_ids'] = all_ids
    if actual['population_state'] == 'complete':
        c.require(actual['total_test_count'] in (None, len(all_ids)), 'cross_family_total_conflict')
        actual['total_test_count'] = len(all_ids)
    validate_test_family(actual)
    value = adjust_p_values(tuple(all_cells), family=actual, **{k: row[k] for k in ('method', 'alpha', 'dependence_assumption')})
    needs = _merge_requirements(needs, value['requirements'])
    return {'family_request_id': identity, 'status': 'partial' if needs and value['status'] == 'ok' else value['status'],
        'value': value, 'requirements': needs, 'diagnostics': _unique([*diagnostics, *value['diagnostics']])}


def _projection_complete(facts, *, requested_form=None, parameters=None):
    """Availability of only requested values; optional failures stay retained."""
    if requested_form is not None:
        plans = {p['analysis']['analysis_id']: {r['request_id']: r for r in p['calculation_parameters']['requests']} for p in parameters['analyses']}
        for field, schema in requested_form['properties'].items():
            selected = schema['x-alignment-fact']; value = facts[field]
            if not _projection_complete(value):
                return False
            if selected['kind'] in ('xmfa_coordinates', 'xmfa_coverage'):
                request = plans[selected['analysis_id']][selected['request_id']]
                if request['use_source_bindings']:
                    if selected['kind'] == 'xmfa_coordinates' and any(row['state'] == 'incompatible' or row['source_state'] in ('missing', 'conflicting') for row in value):
                        return False
                    if selected['kind'] == 'xmfa_coverage' and any(row['source_length'] is None for row in value):
                        return False
            if selected['kind'] == 'xmfa_source_positions' and any(row['state'] == 'unknown' for row in value):
                return False
        return True
    if facts is None:
        return False
    if type(facts) is list:
        return all(_projection_complete(v) for v in facts)
    if type(facts) is not dict:
        return True
    if 'value' in facts and 'state' in facts:
        return facts['state'] == 'available'
    if 'count' in facts and 'state' in facts:
        return facts['state'] == 'available'
    if 'numerical_state' in facts:
        return facts['numerical_state'] != 'unavailable'
    if 'measurement' in facts:
        return _projection_complete(facts['measurement'])
    if 'adjusted_p' in facts:
        return facts['adjusted_p'] is not None
    # Nullable optional original coordinates and unrequested interval arrays
    # are part of valid typed facts, not an unavailable collection dependency.
    if any(key.endswith('_ref') for key in facts) or 'code' in facts:
        return True
    return all(_projection_complete(value) for value in facts.values())


def _scientific_value_usable(value):
    if value is None:
        return False
    if type(value) is list:
        return not value or any(_scientific_value_usable(row) for row in value)
    if type(value) is dict:
        if 'measurement' in value:
            return _scientific_value_usable(value['measurement'])
        if ('value' in value or 'count' in value) and 'state' in value:
            return value['state'] == 'available'
        if 'numerical_state' in value:
            return value['numerical_state'] != 'unavailable'
    return True


def consume_bundle(bundle: dict, *, artifact_bytes: dict[str, bytes], supplied_values: list[dict],
        requested_form: dict, parameters: dict, provider: str) -> dict:
    """Resolve once, save full provider values, copy finite original facts."""
    from .bvbrc_alignment_bundle_projection import project_requested_facts
    parameters = c.validate_parameters(parameters, provider=provider)
    requested_form = c.validate_requested_form(requested_form, provider=provider)
    result = {'adapter_id': 'bvbrc_' + provider, 'adapter_version': '1', 'status': 'invalid',
        'sheet': None, 'components': None, 'facts': {}, 'missing_requirements': [], 'diagnostics': []}
    try:
        resolution = resolve_bundle(bundle, artifact_bytes=artifact_bytes, supplied_values=supplied_values, parameters=parameters, provider=provider)
    except ValueError as exc:
        code = str(exc)
        reason = 'alignment_slot_sha256_conflict' if 'content_bytes_conflict' in code else 'alignment_supplied_evidence_unbound' if 'evidence' in code else 'alignment_original_task_conflict' if 'original' in code or 'application' in code else 'alignment_supplied_value_invalid'
        kind = 'input_bytes' if reason == 'alignment_slot_sha256_conflict' else 'original_task' if reason == 'alignment_original_task_conflict' else 'scientific_metadata'
        need = _need(provider, '@requirements', '/bundle', reason, kind=kind)
        result['missing_requirements'] = [need]
        result['diagnostics'] = [diagnostic(reason, path='/bundle', severity='error')]
        result['facts'] = project_requested_facts(sheet_set=None, component_set=None,
            missing_requirements=tuple(result['missing_requirements']), diagnostics=tuple(result['diagnostics']),
            requested_form=requested_form, parameters=parameters, provider=provider)
        return result
    compiler = _Resolver(bundle, artifact_bytes, supplied_values, parameters, provider)
    compiler.slots = {(s['analysis_id'], s['slot_id']): s for s in resolution['selections']}
    for row in resolution['analyses']:
        compiler.documents[row['analysis_id']] = row['documents']; compiler.reads[row['analysis_id']] = row['read_outcomes']
    sheet_set = {'schema_version': 'bvbrc_alignment_sheet_set_v1', 'tool': 'C-L204-MSA' if provider == 'msa' else 'C-L205-MetaCATS',
        'selections': deepcopy(resolution['selections']), 'analyses': []}
    component_set = {'schema_version': 'bvbrc_alignment_component_set_v1', 'analyses': [], 'multiplicity_families': []}
    for row in resolution['analyses']:
        aid = row['analysis_id']; sheet = components = None; extra_diagnostics = []
        try:
            sheet, components, extra_diagnostics = _assemble(compiler, row)
        except ValueError as exc:
            reason = 'alignment_calculation_invalid' if sheet is not None else 'alignment_supplied_value_invalid'
            compiler.issue(aid, reason, '/analyses/' + str(list(compiler.plans).index(aid)), role='provider', severity='error')
        needs = _merge_requirements(row['requirements'], compiler.requirements[aid], sheet['requirements'] if sheet else [], components['requirements'] if components else [])
        diags = _unique([*row['diagnostics'], *compiler.diagnostics[aid], *extra_diagnostics,
            *(sheet['diagnostics'] if sheet else []), *(components['diagnostics'] if components else [])])
        status = 'invalid' if row['status'] == 'invalid' or sheet is None else 'partial' if needs or diags else 'ok'
        sheet_set['analyses'].append({'analysis_id': aid, 'status': status, 'sheet': sheet, 'requirements': needs, 'diagnostics': diags})
        component_set['analyses'].append({'analysis_id': aid, 'components': components})
    for row in parameters['multiplicity_families']:
        try:
            outcome = _cross_family(row, sheet_set=sheet_set, component_set=component_set, parameters=parameters, provider=provider)
        except ValueError:
            rid = row['family_request_id']
            outcome = {'family_request_id': rid, 'status': 'invalid', 'value': None,
                'requirements': [_need(provider, '@families', rid, 'alignment_calculation_invalid', role=rid)],
                'diagnostics': [diagnostic('alignment_calculation_invalid', path='/multiplicity_families/' + str(parameters['multiplicity_families'].index(row)), severity='error')]}
        component_set['multiplicity_families'].append(outcome)
    needs = _merge_requirements(resolution['requirements'], *(r['requirements'] for r in sheet_set['analyses']),
        *(r['requirements'] for r in component_set['multiplicity_families']))
    diags = _unique([*resolution['diagnostics'], *(d for r in sheet_set['analyses'] for d in r['diagnostics']),
        *(d for r in component_set['multiplicity_families'] for d in r['diagnostics'])])
    facts = project_requested_facts(sheet_set=sheet_set, component_set=component_set,
        missing_requirements=tuple(needs), diagnostics=tuple(diags), requested_form=requested_form, parameters=parameters, provider=provider)
    satisfied = _projection_complete(facts, requested_form=requested_form, parameters=parameters)
    invalid = any(s['state'] == 'invalid' and any(d['code'] in ('alignment_slot_sha256_conflict', 'alignment_declared_format_conflict', 'alignment_supplied_content_unbound') for d in s['diagnostics']) for s in sheet_set['selections'])
    invalid |= not any(r['sheet'] is not None for r in sheet_set['analyses'])
    usable = any(_scientific_value_usable(facts[field]) for field, schema in requested_form['properties'].items()
        if schema['x-alignment-fact']['kind'] not in ('qualifications', 'missing_requirements'))
    status = 'invalid' if invalid else 'ok' if satisfied else 'failed' if bundle['status'] == 'failed' and not usable else 'partial'
    result.update(status=status, sheet=sheet_set, components=component_set, facts=facts, missing_requirements=needs, diagnostics=diags)
    return result


__all__ = ['resolve_bundle', 'consume_bundle']
