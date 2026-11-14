"""Selected, Store-free Cobra model inspection and editing; never optimize.

The host authenticates received Files and optional Source references before
dispatch. These records validate shape and native readback, not that custody or
the biological correctness of a caller's proposed reaction. Full captures stay
private; the projector copies one explicitly selected native collection.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.flux_balance_contracts import ISSUE_CODES, _bounds as _native_bounds, _terms, flux_balance_schema
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority.flux_balance_result_contracts import _checked, _props, _shared, fba_result_schema
REQUEST_VERSION = 'flux_balance_model_request_v1'
RESULT_VERSION = 'ordinary_fba_model_result_v1'
VIEW_VERSION = 'flux_balance_model_view_v1'
_TEXT = deepcopy(flux_balance_schema('Reaction')['properties']['id'])
_UINT = {'type': 'integer', 'minimum': 0}
_SOURCE = {'type': 'string', 'pattern': 'source_[a-f0-9]{24,64}'}

def _obj(**fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}

def _arr(item):
    return {'type': 'array', 'items': item}

def _nullable(item):
    return {'anyOf': [item, {'type': 'null'}]}
_REFS = {**_arr(_SOURCE), 'uniqueItems': True}
_BOUND = _obj(kind={'enum': ['finite', 'negative_infinity', 'positive_infinity']}, value=_nullable({'type': 'number'}))
_MET = _obj(id=_TEXT, name={'type': 'string'}, compartment_id=_TEXT, formula=_nullable({'type': 'string'}), charge=_nullable({'type': 'number'}), source_refs=_REFS)
_RXN = _obj(id=_TEXT, name={'type': 'string'}, stoichiometry={**_arr(_obj(metabolite_id=_TEXT, coefficient={'type': 'number'})), 'minItems': 1}, lower=_BOUND, upper=_BOUND, source_refs=_REFS)
_CHANGE = _obj(reaction_id=_TEXT, lower=_BOUND, upper=_BOUND, source_refs=_REFS)
_OBJECTIVE = {'oneOf': [_obj(kind={'const': 'preserve'}), _obj(kind={'const': 'single_reaction'}, reaction_id=_TEXT, direction={'enum': ['preserve', 'min', 'max']}, source_refs=_REFS)]}
_EDITS = _obj(output_format={'enum': ['sbml', 'cobra_json']}, add_metabolites=_arr(_MET), add_reactions=_arr(_RXN), bounds=_arr(_CHANGE), objective=_OBJECTIVE)
_FILE = flux_balance_schema('File')
_FILE["properties"]["format"] = {"enum": ["sbml", "cobra_json"]}
_REQUEST = {'oneOf': [_obj(version={'const': REQUEST_VERSION}, mode={'const': mode}, model_file=_FILE, edits={'type': 'null'} if mode == 'inspect' else _EDITS) for mode in ('inspect', 'edit')]}
_COLLECTIONS = ('model', 'compartments', 'metabolites', 'reactions', 'genes', 'groups', 'stoichiometry', 'objective')
_SELECTOR = _obj(snapshot_phase={'enum': ['loaded_original', 'effective']}, collection={'enum': list(_COLLECTIONS)}, ordinals=_nullable(_arr(_UINT)), row_window=_obj(offset=_UINT, limit={'type': 'integer', 'minimum': 1}))
_DECLARATION = _obj(role={'enum': ['original_model', 'effective_model', 'effective_problem', 'edited_model']}, relative_path=_TEXT, file=flux_balance_schema('File'))
_EDIT_RESULT = _obj(collection={'enum': ['add_metabolites', 'add_reactions', 'bounds', 'objective']}, ordinal=_UINT, state={'enum': ['not_attempted', 'applied', 'rejected', 'unknown']}, issue_code=_nullable({'enum': sorted(ISSUE_CODES)}))
_RESULT = _obj(version={'const': RESULT_VERSION}, request=_REQUEST, models={}, problems={}, edit_results=_arr(_EDIT_RESULT), edit_state={'enum': ['not_requested', 'exact', 'rejected', 'partial', 'unknown']}, edited_model=_nullable(_DECLARATION), files=_arr(_DECLARATION), model_optimize_call_count={'const': 0}, issues=_arr({}))

def _view_values_schema(collection):
    if collection == 'model':
        return _obj(**_props('ModelSnapshot', 'model_id', 'model_name', 'population', 'medium_state', 'medium_basis'))
    kind = {'compartments': 'Compartment', 'metabolites': 'Metabolite', 'reactions': 'Reaction', 'genes': 'Gene', 'groups': 'Group', 'stoichiometry': 'Stoichiometry', 'objective': 'Objective'}[collection]
    schema = _shared(kind)
    omitted = {'source', 'annotation_pointer', 'notes_pointer', 'gpr_source_pointer', 'boundary_source', 'native_expression_pointer', 'flux_expression_pointer'}
    schema['properties'] = {key: value for key, value in schema['properties'].items() if key not in omitted}
    schema['required'] = [key for key in schema['required'] if key not in omitted]
    return schema

def _view_schema():
    feature = _shared('SourceFeature')
    feature['properties'].pop('source')
    feature['required'].remove('source')
    alternatives = []
    for collection in _COLLECTIONS:
        selection = deepcopy(_SELECTOR)
        selection['properties']['collection'] = {'const': collection}
        row = {'oneOf': [_obj(ordinal=_UINT, availability={'const': 'present'}, values=_view_values_schema(collection)), _obj(ordinal=_UINT, availability={'const': 'unavailable'}, values={'type': 'null'})]}
        alternatives.append(_obj(version={'const': VIEW_VERSION}, selector=selection, population=_obj(basis={'const': 'captured_loaded_native_collection'}, expected_count=_nullable(_UINT), retained_count=_UINT, snapshot_available={'type': 'boolean'}), page=_obj(selected_row_count=_UINT, offset=_UINT, returned_row_count=_UINT, has_more={'type': 'boolean'}), rows=_arr(row), edit_state=deepcopy(_RESULT['properties']['edit_state']), source_features=_arr(feature), issues=_arr(fba_result_schema('FBAResultIssue'))))
    return {'oneOf': alternatives}
_VIEW = _view_schema()

def flux_balance_model_schema(kind):
    return deepcopy({'Request': _REQUEST, 'Edits': _EDITS, 'ViewSelector': _SELECTOR, 'Result': _RESULT, 'View': _VIEW}[kind])

def _require(value, code, field=''):
    if not value:
        raise ValueError('fba_model_' + code + (':' + field if field else ''))

def validate_flux_balance_model_view(value):
    """Check source-free scalar/page identities; confer no source authority."""
    value = _checked(value, _VIEW, 'fba_model_view_invalid')
    selected, pop, page, rows = (value['selector'], value['population'], value['page'], value['rows'])
    ordinals = selected['ordinals']
    total = pop['retained_count'] if ordinals is None else len(ordinals)
    offset, limit = (selected['row_window']['offset'], selected['row_window']['limit'])
    _require(page['selected_row_count'] == total and page['offset'] == offset and (page['returned_row_count'] == len(rows) == min(limit, max(0, total - offset))) and (page['has_more'] == (offset + limit < total)), 'view_page_conflict')
    if not pop['snapshot_available']:
        _require(pop['expected_count'] is None and pop['retained_count'] == 0 and all((row['availability'] == 'unavailable' for row in rows)), 'view_population_conflict')
    elif selected['collection'] in {'model', 'objective'}:
        _require(pop['expected_count'] == pop['retained_count'] == 1, 'view_population_conflict')
    if pop['expected_count'] is not None:
        _require(pop['retained_count'] <= pop['expected_count'] and all((index < pop['expected_count'] for index in ([row['ordinal'] for row in rows] if ordinals is None else ordinals))), 'view_population_conflict')
        if selected['collection'] == 'stoichiometry':
            _require(pop['retained_count'] == pop['expected_count'], 'view_population_conflict')
    returned = [row['ordinal'] for row in rows]
    if ordinals is None:
        _require(all((row['availability'] == 'present' for row in rows)) and all((left < right for left, right in zip(returned, returned[1:]))), 'view_ordinal_conflict')
    else:
        _require(returned == ordinals[offset:offset + limit], 'view_ordinal_conflict')
    _require(len({row['ordinal'] for row in rows if row['availability'] == 'present'}) <= pop['retained_count'], 'view_population_conflict')
    seen = {}
    for index, row in enumerate(rows):
        previous = seen.setdefault(row['ordinal'], row)
        _require(canonical(previous) == canonical(row), 'view_ordinal_conflict')
        if row['availability'] == 'unavailable':
            _require(not pop['snapshot_available'] or selected['collection'] not in {'model', 'objective'}, 'view_population_conflict')
            continue
        _require(pop['snapshot_available'] and pop['retained_count'] > 0, 'view_population_conflict')
        values, collection = (row['values'], selected['collection'])
        if collection in {'model', 'objective'}:
            _require(row['ordinal'] == 0, 'view_ordinal_conflict')
        elif collection != 'stoichiometry':
            _require(values['position'] == row['ordinal'], 'view_ordinal_conflict')
        if collection == 'model' and values['population']['completeness'] == 'complete':
            _require(all((values['population'][axis] is not None for axis in ('compartments', 'genes', 'metabolites', 'reactions', 'groups'))), 'view_population_conflict')
        elif collection == 'reactions':
            _native_bounds(values, f'/rows/{index}/values')
        elif collection == 'objective':
            _terms(values, f'/rows/{index}/values')
    return value
