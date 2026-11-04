"""Saved GenomeAlignment data and numerical sheets, without acquisition.

The data record keeps the original task, parsed native values and supplied C
relationships. The sheet keeps that data alongside separately calculated full
components. Building or validating either record never recalculates science.
"""
from copy import deepcopy

from . import bvbrc_genome_alignment_calculation_contracts as c
from .bvbrc_genome_alignment_input_contracts import (
    validate_genome_alignment_inputs, validate_genome_alignment_associations)
from .bvbrc_appservice_contracts import validate_contract
from .mauve_v4_format_contracts import validate_mauve_v4_document
from .mauve_backbone_contracts import validate_mauve_backbone_document, validate_mauve_bbcols_document
from .xmfa_format_contracts import validate_xmfa_document, _artifact

DOCUMENT_VALIDATORS = {'mauve_v4': validate_mauve_v4_document,
    'mauve_backbone': validate_mauve_backbone_document,
    'mauve_bbcols': validate_mauve_bbcols_document,
    'mauve1_xmfa': validate_xmfa_document}


def _parsed(rows):
    c._array(rows); artifacts, documents = {}, {}
    for row in rows:
        c._shape(row, ('artifact', 'format', 'parse_status', 'document', 'diagnostics'))
        _artifact(row['artifact']); c._enum(row['format'], DOCUMENT_VALIDATORS)
        c._enum(row['parse_status'], ('ok', 'partial', 'invalid'))
        c._reports({'requirements': [], 'diagnostics': row['diagnostics']})
        key = c._key(row['artifact'])
        c._require(key not in artifacts, 'artifact_identity_conflict')
        artifacts[key] = row
        if row['document'] is None:
            c._require(row['parse_status'] == 'invalid', 'document_identity_conflict')
        else:
            c._require(row['parse_status'] != 'invalid', 'document_identity_conflict')
            doc = DOCUMENT_VALIDATORS[row['format']](row['document'])
            c._require(doc['artifact'] == row['artifact'], 'artifact_identity_conflict')
            c._require(doc['document_id'] not in documents, 'document_identity_conflict')
            documents[doc['document_id']] = row
    return artifacts, documents


def _reader_matches(slot, parsed):
    if slot['reader']['format'] != parsed['format']:
        return False
    doc = parsed['document']
    return doc is not None and all(doc[k] == v for k, v in slot['reader'].items() if k != 'format')


def _resolutions(value, slots, artifacts, documents):
    c._array(value['slot_resolutions'])
    c._require(len(value['slot_resolutions']) == len(slots), 'slot_resolution_conflict')
    selected_readers = {}
    for (sid, slot), row in zip(slots.items(), value['slot_resolutions']):
        c._shape(row, ('slot_id', 'state', 'artifact', 'document_id', 'candidate_artifacts', 'requirements', 'diagnostics'))
        c._require(row['slot_id'] == sid, 'slot_resolution_conflict')
        c._enum(row['state'], ('resolved', 'missing', 'ambiguous', 'incompatible'))
        c._text(row['document_id'], nullable=True); c._array(row['candidate_artifacts']); c._reports(row)
        candidates = []
        for candidate in row['candidate_artifacts']:
            _artifact(candidate); key = c._key(candidate)
            c._require(key not in candidates, 'artifact_identity_conflict'); candidates.append(key)
            c._require(all(slot[k] is None or slot[k] == candidate[k] for k in ('raw_artifact_ref', 'source_ref')),
                       'artifact_identity_conflict')
        if row['artifact'] is not None:
            _artifact(row['artifact']); key = c._key(row['artifact'])
            c._require(key in candidates, 'artifact_identity_conflict')
            c._require(key not in selected_readers or selected_readers[key] == slot['reader'], 'slot_reader_conflict')
            selected_readers[key] = slot['reader']
        else:
            key = None
        if row['state'] == 'resolved':
            c._require(len(candidates) == 1 and key is not None and row['document_id'] in documents,
                       'slot_resolution_conflict')
            parsed = documents[row['document_id']]
            c._require(parsed['artifact'] == row['artifact'], 'artifact_identity_conflict')
            c._require(_reader_matches(slot, parsed), 'slot_reader_conflict')
        elif row['state'] == 'ambiguous':
            c._require(len(candidates) > 1 and row['artifact'] is None and row['document_id'] is None,
                       'slot_resolution_conflict')
        else:
            # A uniquely selected transfer can still be missing complete bytes.
            c._require(len(candidates) <= 1 and row['document_id'] is None, 'slot_resolution_conflict')
            c._require(not candidates or key is not None, 'slot_resolution_conflict')
        if key in artifacts and artifacts[key]['document'] is not None:
            c._require(_reader_matches(slot, artifacts[key]), 'slot_reader_conflict')


def _association_links(value, artifacts, documents):
    associations = value['associations']
    if associations is None:
        return
    c._require(c._same(associations['original_task'], value['original_task']), 'original_task_conflict')
    associated = {}
    for row in associations['artifacts']:
        key = c._key(row['artifact']); associated[key] = row
        did = row['document_id']
        if did is not None:
            c._require(did in documents and c._key(documents[did]['artifact']) == key
                       and row['observed_format'] == documents[did]['format'], 'artifact_identity_conflict')
        if key in artifacts and row['observed_format'] is not None:
            c._require(row['observed_format'] == artifacts[key]['format'], 'artifact_identity_conflict')
    for slot, resolution in zip(value['document_slots'], value['slot_resolutions']):
        if resolution['artifact'] is not None:
            row = associated.get(c._key(resolution['artifact']))
            if row is not None and row['state'] == 'bound':
                c._require(row['role'] == slot['role'], 'artifact_identity_conflict')
    for join in associations['bbcols_interval_joins']:
        if join['state'] != 'bound':
            continue
        c._require(join['bbcols_document_id'] in documents and join['xmfa_document_id'] in documents,
                   'saved_reference_conflict')
        side = documents[join['bbcols_document_id']]['document']
        primary = documents[join['xmfa_document_id']]['document']
        c._require(any(c.bc._available(r['native_interval_index_0based'], 0)
            and r['native_interval_index_0based']['value'] == join['native_interval_index_0based'] for r in side['rows'])
            and join['xmfa_block_index'] < len(primary['blocks']), 'saved_reference_conflict')
    for join in associations['native_member_joins']:
        if join['state'] != 'bound':
            continue
        key = c._key(join['artifact']); parsed = artifacts.get(key)
        c._require(parsed is not None and parsed['document'] is not None, 'saved_reference_conflict')
        doc = parsed['document']; index = join['member']['index']
        if parsed['format'] == 'mauve1_xmfa':
            known = c._native_members(doc)
        elif parsed['format'] == 'mauve_v4':
            count = c.v4f.scalar(doc['metadata'], 'sequence_count')
            known = range(count) if count is not None else {i for interval in doc['intervals']
                for segment in interval['segments'] for i in range(len(segment['native_starts']))}
        elif parsed['format'] == 'mauve_backbone':
            known = {r['member_index_token']['value'] for r in doc['columns'] if c.bc._available(r['member_index_token'], 0)}
        else:
            # BBCols tokens are not an exhaustive member census. A C mapping
            # may name an invocation member absent from these particular rows.
            known = None
        c._require(known is None or index in known, 'saved_reference_conflict')
        # C output can survive a separately missing C extraction value. When
        # present, an explicitly bound input-member reference must resolve.
        if value['inputs'] is not None:
            c._require(any(m['member'] == join['input_member'] and m['state'] == 'bound'
                for m in value['inputs']['member_bindings']), 'saved_reference_conflict')


def _data_groups(value):
    return [r for r in (value['inputs'], value['associations']) if r is not None] + [
        {'requirements': [], 'diagnostics': p['diagnostics']} for p in value['parsed_artifacts']] + value['slot_resolutions']


def validate_genome_alignment_data(value: dict) -> dict:
    c._finite(value)
    c._shape(value, ('schema_version', 'analysis_id', 'original_task', 'document_slots', 'inputs',
        'associations', 'parsed_artifacts', 'slot_resolutions', 'requirements', 'diagnostics'))
    c._require(value['schema_version'] == 'bvbrc_genome_alignment_data_v1'); c._text(value['analysis_id'])
    validate_contract('OriginalTask', value['original_task'])
    original = value['original_task']
    c._require(original['required_application_id'] == original['native_application_id'] == 'GenomeAlignment', 'original_task_conflict')
    genomes = original['submitted_parameters'].get('genome_ids')
    c._require(type(genomes) is list and bool(genomes) and all(type(g) is str and g for g in genomes), 'original_task_conflict')
    c._array(value['document_slots']); slots = c._slots(tuple(value['document_slots']))
    c._reports(value)
    if value['inputs'] is not None:
        validate_genome_alignment_inputs(value['inputs'])
        c._require(c._same(value['inputs']['original_task'], original), 'original_task_conflict')
    if value['associations'] is not None:
        validate_genome_alignment_associations(value['associations'])
    artifacts, documents = _parsed(value['parsed_artifacts'])
    _resolutions(value, slots, artifacts, documents)
    _association_links(value, artifacts, documents)
    for field in ('requirements', 'diagnostics'):
        # Outer acquisition reports may precede nested reports. No nested cause
        # may disappear or conflict, even if unselected by any calculation.
        c._require(c._same(value[field], c._union([value, *_data_groups(value)], field)), 'component_identity_conflict')
    c._links(value, {r['requirement_id'] for r in value['requirements']})
    return deepcopy(value)


def build_genome_alignment_data(*, analysis_id: str, original_task: dict,
    document_slots: tuple[dict, ...], inputs: dict | None, associations: dict | None,
    parsed_artifacts: tuple[dict, ...], slot_resolutions: tuple[dict, ...],
    requirements: tuple[dict, ...], diagnostics: tuple[dict, ...]) -> dict:
    for arg in (document_slots, parsed_artifacts, slot_resolutions, requirements, diagnostics):
        c._require(type(arg) is tuple, 'argument_invalid')
    value = {'schema_version': 'bvbrc_genome_alignment_data_v1', 'analysis_id': analysis_id,
        'original_task': deepcopy(original_task), 'document_slots': deepcopy(list(document_slots)),
        'inputs': deepcopy(inputs), 'associations': deepcopy(associations),
        'parsed_artifacts': deepcopy(list(parsed_artifacts)), 'slot_resolutions': deepcopy(list(slot_resolutions)),
        'requirements': deepcopy(list(requirements)), 'diagnostics': deepcopy(list(diagnostics))}
    c._finite(value)
    # Check operand shapes before indexing nested reports. A malformed caller
    # value is a contract error, never an unhandled missing-key accident.
    slots = c._slots(document_slots)
    if inputs is not None:
        validate_genome_alignment_inputs(inputs)
    if associations is not None:
        validate_genome_alignment_associations(associations)
    artifacts, documents = _parsed(value['parsed_artifacts'])
    _resolutions(value, slots, artifacts, documents)
    for item in [value, *_data_groups(value)]:
        c._reports(item)
    for field in ('requirements', 'diagnostics'):
        value[field] = c._union([value, *_data_groups(value)], field)
    return validate_genome_alignment_data(value)


def build_genome_alignment_sheet(*, data: dict, components: dict) -> dict:
    data = validate_genome_alignment_data(data)
    components = c.validate_genome_alignment_components(components, data=data)
    return {'schema_version': 'bvbrc_genome_alignment_sheet_v2', 'analysis_id': data['analysis_id'],
        'data': data, 'components': components, 'requirements': deepcopy(components['requirements']),
        'diagnostics': deepcopy(components['diagnostics'])}


def validate_genome_alignment_sheet(value: dict) -> dict:
    c._finite(value)
    c._shape(value, ('schema_version', 'analysis_id', 'data', 'components', 'requirements', 'diagnostics'))
    c._require(value['schema_version'] == 'bvbrc_genome_alignment_sheet_v2')
    data = validate_genome_alignment_data(value['data'])
    c._require(value['analysis_id'] == data['analysis_id'], 'analysis_id_conflict')
    components = c.validate_genome_alignment_components(value['components'], data=data)
    c._reports(value)
    for field in ('requirements', 'diagnostics'):
        c._require(c._same(value[field], components[field]), 'component_identity_conflict')
    return deepcopy(value)


__all__ = ['build_genome_alignment_data', 'validate_genome_alignment_data',
           'build_genome_alignment_sheet', 'validate_genome_alignment_sheet']
