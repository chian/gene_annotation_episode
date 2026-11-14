"""Original supplied endpoint witness and return-row projection."""
from copy import deepcopy
from gene_annotation_episode.domain import ContractError
from .literature_endpoint_signal_metadata import SCOPE
from .literature_endpoint_signal_contracts import ENDPOINT_SIGNAL_CELLS_SCHEMA_V1

def _witnesses(value):
    if isinstance(value, dict):
        if {'source_ref', 'representation', 'start', 'end', 'quote'} <= value.keys():
            yield value
        else:
            for child in value.values():
                yield from _witnesses(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _witnesses(child)


def _direct(args):
    selected = args['selection']
    refs = [selected['source_ref']]
    if selected['image'] is not None:
        refs.append(selected['image']['source_ref'])
    refs.extend(w['source_ref'] for w in _witnesses(selected))
    if selected['covariance_source_ref'] is not None:
        refs.append(selected['covariance_source_ref'])
    return list(dict.fromkeys(refs))


def _location(witness):
    return {name: witness[name] for name in
        ('source_ref', 'artifact_ref', 'representation', 'start', 'end')}


def _context_projection(args, extraction):
    result = {}
    for name, windows in args['return_context'].items():
        selected, actual = args['selection']['context'][name], extraction['context'][name]
        fragments = []
        if windows and selected is None:
            raise ContractError('endpoint_context_without_source_witness')
        for window in windows:
            a, b = window['start'], window['end']
            if not selected['start'] <= a < b <= selected['end']:
                raise ContractError('endpoint_context_outside_role_witness')
            correction_entry = extraction['context']['correction_discussion']
            correction = correction_entry['witness'] if correction_entry is not None else None
            if (actual is not None and correction is not None
                    and actual['witness']['artifact_ref'] == correction['artifact_ref']
                    and a < correction['end'] and correction['start'] < b):
                raise ContractError('endpoint_context_overlaps_private_correction_result')
            covariance = extraction['covariance']
            if (actual is not None and covariance is not None and covariance['artifact_ref'] is not None
                    and actual['witness']['artifact_ref'] == covariance['artifact_ref']):
                raise ContractError('endpoint_context_from_covariance_packet')
            raw = selected['quote'].encode('utf-8')
            try:
                text = raw[a-selected['start']:b-selected['start']].decode('utf-8')
            except UnicodeError as error:
                raise ContractError('endpoint_context_utf8_boundary_required') from error
            if not text:
                raise ContractError('endpoint_context_empty_fragment')
            if actual is not None:
                fragments.append({'text': text, 'location': {
                    **_location(actual['witness']), 'start': a, 'end': b}})
        result[name] = {'status': 'not_selected' if not windows else
            'source_unavailable' if actual is None else 'selected', 'fragments': fragments}
    return result


def _project_once(args, extraction, sheet, source_refs, read_sizes):
    context = _context_projection(args, extraction)
    locations = []
    for w in _witnesses(extraction):
        if 'artifact_ref' in w and _location(w) not in locations:
            locations.append(_location(w))
    covariance = extraction['covariance']
    model = covariance['model'] if covariance and covariance['error'] is None else None
    if model is not None:
        # The covariance wire retains its authenticated selectors without the
        # reader's enriched artifact_ref. Bind those exact support spans using
        # its actual successful source receipts, including off-page aliases.
        artifacts = {(item['source_ref'], item['representation']): item['artifact_ref']
            for item in extraction['source_artifacts'] if item['error'] is None}
        for witness in _witnesses(model):
            artifact = artifacts.get((witness['source_ref'], witness['representation']))
            if artifact is not None:
                location = {**{key: witness[key] for key in ('source_ref', 'representation', 'start', 'end')},
                    'artifact_ref': artifact}
                if location not in locations:
                    locations.append(location)
    if covariance and covariance['artifact_ref'] is not None:
        size = read_sizes.get((covariance['source_ref'], 'original'), 0)
        if size:
            locations.append({'source_ref': covariance['source_ref'],
                'artifact_ref': covariance['artifact_ref'], 'representation': 'original', 'start': 0, 'end': size})
    uncertainty = {'availability': 'unreported' if covariance is None else 'unavailable' if model is None
        else 'unknown' if model['variance_status'] == 'unknown' else 'available',
        'source_ref': covariance['source_ref'] if covariance else None,
        'basis': model['basis'] if model else None,
        'variance_status': model['variance_status'] if model else None,
        'origin': model['origin'] if model else None,
        'coordinate_units_status': model['coordinate_units_status'] if model else None,
        'physical_uncertainty': 'supplied_physical_estimate_model' if model and
            model['basis'] == 'joint_physical_ordinate_estimates' else 'unreported',
        'published_ratio_uncertainty': 'not_extracted'}
    image = extraction['image']
    common = {'row_version': 'endpoint_signal_return_v1', 'evidence_source_ref': extraction['source_ref'],
        'image_source_ref': image['source_ref'] if image else None, 'evaluation_scope': SCOPE,
        'source_kind': extraction['source_kind'], 'source_context': context,
        'relationships': {name: {'value': item['interpretation']['value'] if item['interpretation'] else 'unknown',
            'status': 'authenticated_interpretation' if item['interpretation'] else 'source_unavailable'}
            for name, item in extraction['relationships'].items()},
        'sampling_window': extraction['context']['sampling_window']['value']
            if extraction['context']['sampling_window'] else None,
        'uncertainty': uncertainty, 'physical_preparation_count': None,
        'physical_preparation_count_status': 'not_extracted',
        'molecular_attribution': 'not_established_by_signal_decomposition',
        'functional_relevance': 'not_scored_by_endpoint_section',
        'dependency_meanings': deepcopy(ENDPOINT_SIGNAL_CELLS_SCHEMA_V1['items']['properties']['dependency_meanings']['const']),
        'source_scope': list(source_refs), 'withheld_locations': locations,
        'withheld_image_source_refs': [image['source_ref']] if image else []}
    return [{**deepcopy(common), **deepcopy(cell)} for cell in sheet['cells']]


