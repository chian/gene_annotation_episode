"""Pure ArtifactBundle resolution, C extraction and one D calculation.

Every original slot and calculation request survives an acquisition gap. A
reader is selected explicitly and called once per exact artifact/reader; there
is no parser fallback, suffix inference, file access or resource operation.
"""
from copy import deepcopy
import hashlib

from . import bvbrc_genome_alignment_bundle_contracts as c
from .bvbrc_alignment_values import diagnostic, requirement
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_genome_alignment_input_contracts import ROLES
from .bvbrc_genome_alignment_inputs import extract_genome_alignment_inputs
from .bvbrc_genome_alignment_associations import bind_genome_alignment_artifacts
from .bvbrc_genome_alignment_sheet import build_genome_alignment_data, build_genome_alignment_sheet
from .bvbrc_genome_alignment_calculators import calculate_genome_alignment_components
from .bvbrc_genome_alignment_bundle_projection import (
    project_genome_alignment_facts, requested_projection_status, _union_requirements, _union_diagnostics,
)
from .mauve_v4_formats import parse_mauve_v4
from .mauve_v4_format_contracts import scalar as _v4_scalar
from .xmfa_formats import parse_mauve_xmfa
from .mauve_backbone_formats import parse_mauve_backbone, parse_mauve_bbcols


def _artifact(member):
    return {k: member[k] for k in ('raw_artifact_ref', 'source_ref', 'sha256')}


def _key(member):
    return tuple(member[k] for k in ('raw_artifact_ref', 'source_ref', 'sha256'))


def _cause(parameters, slot, code, artifacts):
    code = c.PREFIX + code
    refs = list(dict.fromkeys(a['source_ref'] for a in artifacts))
    if not refs and slot['source_ref'] is not None:
        refs = [slot['source_ref']]
    identity = 'ga_bundle_req:' + hashlib.sha256(c._canonical(
        [parameters['analysis_id'], slot['slot_id'], code, artifacts]).encode()).hexdigest()
    kind = 'output_bytes' if code.rsplit('_', 1)[-1] in ('missing', 'incomplete') or code in (
        c.PREFIX + 'artifact_digest_conflict', c.PREFIX + 'artifact_size_conflict') else 'parser_binding'
    return {'requirements': [requirement(identity, kind=kind, role=slot['role'], source_refs=refs, reason_code=code)],
        'diagnostics': [diagnostic(code, phase='publication', path='/document_slots/' + str(parameters['document_slots'].index(slot)),
                                   evidence_refs=refs)]}


def _declared_matches(member, reader):
    declaration = member['declared_format']
    version = {'mauve_v4': '4', 'mauve1_xmfa': 'Mauve1'}.get(reader['format'])
    # Accepted010: a sidecar dialect is not a native version or execution mode.
    return (declaration['format'] == reader['format'] and declaration['version'] in (None, version)
            and declaration['mode'] is None)


def _transfer_complete(member):
    transfer = member['transfer']
    if not transfer['body_complete'] or transfer['object_complete'] != 'yes':
        return False
    size = member['byte_count']
    if transfer['total_size'] is not None and transfer['total_size'] != size:
        return False
    observed = transfer['observed_range']
    if observed is not None and (observed['start'] != 0 or observed['end_inclusive'] + 1 != size
                                 or observed['total_size'] != size):
        return False
    # requested_range records the request, not the returned representation.
    # A complete HTTP 200 object can ignore it; retain that host qualification.
    return True


def _parse(raw, artifact, reader):
    fmt = reader['format']
    if fmt == 'mauve_v4':
        result = parse_mauve_v4(raw, artifact=artifact, encoding=reader['encoding'])
    elif fmt == 'mauve1_xmfa':
        result = parse_mauve_xmfa(raw, artifact=artifact, dialect='mauve1', alphabet='dna', encoding=reader['encoding'])
    elif fmt == 'mauve_backbone':
        result = parse_mauve_backbone(raw, artifact=artifact, dialect='libmems_signed_coordinate_pairs_v1', encoding=reader['encoding'])
    else:
        result = parse_mauve_bbcols(raw, artifact=artifact, dialect='libmems_interval_columns_members_v1', encoding=reader['encoding'])
    return {'artifact': deepcopy(artifact), 'format': fmt, 'parse_status': result['status'],
            'document': result['value'], 'diagnostics': result['diagnostics']}


def _native_version_conflict(parsed):
    """A retained partial document does not certify a supported version."""
    document = parsed['document']
    if document is None:
        # v4 stops before building a document when its first format marker is
        # unsupported or absent. Preserve that null parse and its exact cause.
        return any(d['code'] in ('mauve_v4_version_unsupported', 'mauve_v4_format_unrecognized')
                   for d in parsed['diagnostics'])
    if parsed['format'] == 'mauve1_xmfa':
        return document['format_version_token'] != 'Mauve1'
    if parsed['format'] == 'mauve_v4':
        return _v4_scalar(document['metadata'], 'format_version') != 4
    return False


def _resolve(bundle, parameters, artifact_bytes):
    selected, readers = [], {}
    for slot in parameters['document_slots']:
        candidates = [a for a in bundle['artifacts'] if a['role'] == slot['role'] and
            all(slot[k] is None or slot[k] == a[k] for k in ('source_ref', 'raw_artifact_ref'))]
        if len(candidates) == 1:
            key = _key(candidates[0])
            if key in readers and readers[key] != slot['reader']:
                raise ValueError('bvbrc_genome_alignment_provider_slot_reader_conflict')
            readers[key] = slot['reader']
        selected.append((slot, candidates))
    resolutions, parsed, cache = [], [], {}
    for slot, members in selected:
        artifacts = [_artifact(a) for a in members]
        row = dict(slot_id=slot['slot_id'], state='missing', artifact=artifacts[0] if len(artifacts) == 1 else None,
            document_id=None, candidate_artifacts=artifacts, requirements=[], diagnostics=[])
        if not members:
            row.update(_cause(parameters, slot, 'artifact_bytes_missing', artifacts))
        elif len(members) > 1:
            row['state'] = 'ambiguous'
            row.update(_cause(parameters, slot, 'artifact_selection_ambiguous', artifacts))
        else:
            member, reader = members[0], slot['reader']
            raw = artifact_bytes.get(member['raw_artifact_ref'])
            reasons = []
            if not _declared_matches(member, reader):
                reasons.append('artifact_format_conflict')
            if not _transfer_complete(member):
                reasons.append('artifact_transfer_incomplete')
            if raw is None:
                reasons.append('artifact_bytes_missing')
            else:
                if len(raw) != member['byte_count']:
                    reasons.append('artifact_size_conflict')
                if hashlib.sha256(raw).hexdigest() != member['sha256']:
                    reasons.append('artifact_digest_conflict')
            if reasons:
                row['state'] = 'incompatible' if any(r.endswith('conflict') for r in reasons) else 'missing'
                causes = [_cause(parameters, slot, reason, artifacts) for reason in reasons]
                row['requirements'] = _union_requirements(*(r['requirements'] for r in causes))
                row['diagnostics'] = _union_diagnostics(*(r['diagnostics'] for r in causes))
            else:
                key = _key(member)
                if key not in cache:
                    cache[key] = _parse(raw, artifacts[0], reader)
                    parsed.append(cache[key])
                native = cache[key]
                row['state'] = 'resolved' if native['document'] is not None else 'incompatible'
                row['document_id'] = None if native['document'] is None else native['document']['document_id']
                row['diagnostics'] = deepcopy(native['diagnostics'])
                if _native_version_conflict(native):
                    cause = _cause(parameters, slot, 'artifact_format_conflict', artifacts)
                    row.update(state='incompatible', document_id=None, requirements=cause['requirements'],
                               diagnostics=_union_diagnostics(row['diagnostics'], cause['diagnostics']))
        resolutions.append(row)
    return parsed, resolutions


def consume_bundle(bundle: dict, *, artifact_bytes: dict[str, bytes], supplied_values: list[dict],
    retained_records: tuple[dict, ...], requested_form: dict, parameters: dict) -> dict:
    c._require(type(artifact_bytes) is dict and all(type(k) is str and k and type(v) is bytes for k, v in artifact_bytes.items())
               and type(supplied_values) is list and type(retained_records) is tuple, 'argument_invalid')
    bundle = validate_contract('ArtifactBundle', bundle)
    parameters = c.validate_parameters(parameters)
    form = c.validate_requested_form(requested_form)
    c._validate_selections(parameters, form)
    keys = [_key(a) for a in bundle['artifacts']]
    c._require(len(keys) == len(set(keys)), 'argument_invalid')
    task = bundle['original_task']
    valid_task = task['required_application_id'] == task['native_application_id'] == 'GenomeAlignment'
    genomes = task['submitted_parameters'].get('genome_ids')
    valid_task = valid_task and type(genomes) is list and bool(genomes) and all(type(g) is str and g for g in genomes)
    parsed, resolutions = _resolve(bundle, parameters, artifact_bytes) if valid_task else ([], [])
    extraction = extract_genome_alignment_inputs(task, supplied_values=tuple(supplied_values),
        supplied_bytes=artifact_bytes, retained_records=retained_records)
    associations = bind_genome_alignment_artifacts(task,
        artifacts=tuple(a for a in bundle['artifacts'] if a['role'] in ROLES), parsed_artifacts=tuple(parsed),
        supplied_values=tuple(supplied_values), inputs=extraction['value'], supplied_bytes=artifact_bytes,
        retained_records=retained_records)
    requirements = _union_requirements(bundle['missing_requirements'], extraction['requirements'], associations['requirements'])
    diagnostics = _union_diagnostics(bundle['diagnostics'], extraction['diagnostics'], associations['diagnostics'],
                                    *(p['diagnostics'] for p in parsed))
    result = dict(adapter_id='bvbrc_genome_alignment', adapter_version='1', status='invalid', facts={},
                  sheet=None, components=None, missing_requirements=requirements, diagnostics=diagnostics)
    if not valid_task:
        return result
    data = build_genome_alignment_data(analysis_id=parameters['analysis_id'], original_task=task,
        document_slots=tuple(parameters['document_slots']), inputs=extraction['value'], associations=associations['value'],
        parsed_artifacts=tuple(parsed), slot_resolutions=tuple(resolutions), requirements=tuple(requirements), diagnostics=tuple(diagnostics))
    components = calculate_genome_alignment_components(data, calculation_plan=parameters['calculation_plan'])
    sheet = build_genome_alignment_sheet(data=data, components=components)
    projection = project_genome_alignment_facts(sheet=sheet, components=components,
        missing_requirements=tuple(sheet['requirements']), diagnostics=tuple(sheet['diagnostics']), requested_form=form, parameters=parameters)
    status = requested_projection_status(projection['facts'], sheet=sheet, components=components,
        missing_requirements=tuple(projection['missing_requirements']), diagnostics=tuple(projection['diagnostics']), requested_form=form, parameters=parameters)
    result.update(projection, sheet=sheet, components=components, status=status)
    return result


__all__ = ['consume_bundle']
