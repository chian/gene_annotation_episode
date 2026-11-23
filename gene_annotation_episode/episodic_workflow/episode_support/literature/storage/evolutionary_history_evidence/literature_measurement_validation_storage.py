"""Selected precision/control sections and exactly scoped durable fact custody.

Only fresh population reads source bytes or invokes scientific calculations.
Saved reconstruction authenticates the original request and recorded values.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import ContractError, canonical, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_rate_storage import LiteratureRateRepository
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_calibration_recovery_storage import LiteratureCalibrationRecoveryRepository
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_measurement_validation_inputs import (
    VERSION as INPUT_VERSION, CONTEXT_FIELDS, RELATIONSHIPS, FORMULA_RELATIONS,
    measurement_validation_population_schema, measurement_validation_extraction_schema,
    read_measurement_validation_inputs,
)
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.evolutionary_history_evidence.literature_measurement_validation_calculations import (
    COMPONENTS, PRECISION_COMPONENTS, ZPRIME_COMPONENTS, FORMULAS, QUALIFICATIONS,
    measurement_validation_cell_schema, measurement_validation_sheet_schema,
    populate_measurement_validation,
)

PROVIDER = 'literature.a105.measurement_validation'
VERSION = 'literature_measurement_validation_record'
NAMESPACE = 'literature_measurement_validation_cells'
REQUESTED = 'requested_measurement_validation_components'
VIEW = 'measurement_validation_components'
SCOPE = 'source_measurement_validation'


def _array(schema):
    return {'type': 'array', 'items': deepcopy(schema)}


def _ref(nullable=False, namespace='source'):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference',
            'x-reference-namespace': namespace}


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _meaning_schema():
    return _nullable(obj({'source_ref': _ref(), 'artifact_ref': _ref(namespace='artifact'),
        'representation': {'enum': ['original', 'text']},
        'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1},
        'display_text': {'type': 'string', 'minLength': 1},
        'status': {'enum': ['selected', 'unrequested_numbers_withheld', 'numerical_scope_unresolved']},
        'unavailable_reason': {'enum': ['unrequested_numerical_scope_unresolved', None]}}))


def measurement_validation_cells_schema():
    interpreted = lambda values: obj({'value': {'enum': list(values)}, 'support': _array(_meaning_schema())})
    row = obj({**measurement_validation_cell_schema()['properties'],
        'sheet_ref': _ref(), 'evidence_source_ref': _ref(), 'evaluation_scope': {'const': SCOPE},
        'component': {'enum': list(COMPONENTS)}, 'family': {'enum': ['precision', 'zprime', 'raw_control']},
        'measurement_key': {'type': ['string', 'null'], 'minLength': 1},
        'source_kind': {'enum': ['primary_source', 'retained_extraction', 'synthetic_fixture']},
        'source_meanings': obj({name: _meaning_schema() for name in CONTEXT_FIELDS}),
        'relationships': _nullable(obj({name: interpreted(values) for name, values in RELATIONSHIPS.items()})),
        'formula_relation': _nullable(interpreted(FORMULA_RELATIONS)),
        'basis': {'enum': [*RELATIONSHIPS['basis'], None]},
        'source_scope': _array(_ref()),
        'withheld_locations': _array(obj({'source_ref': _ref(), 'artifact_ref': _ref(namespace='artifact'),
            'representation': {'enum': ['original', 'text']}, 'start': {'type': 'integer', 'minimum': 0},
            'end': {'type': 'integer', 'minimum': 1}})),
        'recovery_operand_scope': {'const': 'possessed_rows_retained_without_unrequested_values_or_invented_source_locations'},
        'qualifications': {'const': list(QUALIFICATIONS)}})
    return {'type': 'array', 'items': row, 'x-source': NAMESPACE}


def _locations(extraction):
    return [{**{name: item['number']['selector']['witness'][name]
                for name in ('source_ref', 'artifact_ref', 'representation')},
             'start': item['number']['number_start_bytes'], 'end': item['number']['number_end_bytes']}
            for family in ('precision', 'zprime') for item in extraction[family]]


def _meaning(witness, locations):
    if witness is None:
        return None
    raw = witness['quote'].encode()
    spans = []
    for location in locations:
        if (location['artifact_ref'] == witness['artifact_ref']
                and witness['start'] < location['end'] and location['start'] < witness['end']):
            spans.append((max(witness['start'], location['start']) - witness['start'],
                          min(witness['end'], location['end']) - witness['start']))
    flags = [False] * len(raw)
    for a, b in spans:
        flags[a:b] = [True] * (b-a)
    chunks, start = [], 0
    while start < len(raw):
        hidden = flags[start]
        end = start+1
        while end < len(raw) and flags[end] == hidden:
            end += 1
        chunks.append('[unrequested numerical operand]' if hidden else raw[start:end].decode())
        start = end
    shown = ''.join(chunks)
    # A broad table/context quotation can contain additional statistics whose
    # source positions are absent from the possessed recovery rows. Do not
    # manufacture those positions by matching equal values. Retain the exact
    # witness in the saved extraction and expose a projection limitation.
    visible = re.sub(r'<[^>]+>', ' ', shown)
    numeric = re.search(r'(?<![A-Za-z0-9_.])[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?![A-Za-z0-9_.])', visible)
    mixed = bool(numeric and (re.search(r'<(?:table|tr|td|th)\b', witness['quote'], re.I)
        or re.search(r'\b(?:nominal|prepared\s+amount|measured\s+amount|recovery|relative\s+error|accuracy|CV|coefficient\s+of\s+variation)\b', witness['quote'], re.I)))
    return {**{name: witness[name] for name in ('source_ref', 'artifact_ref', 'representation', 'start', 'end')},
        'display_text': '[Mixed numerical source context retained; requested operand scope unresolved.]' if mixed else shown,
        'status': 'numerical_scope_unresolved' if mixed else 'unrequested_numbers_withheld' if spans else 'selected',
        'unavailable_reason': 'unrequested_numerical_scope_unresolved' if mixed else None}


def _project_saved(saved, reference, components):
    """Select every retained instance of each requested component, in source order."""
    data = saved['extraction']; locations = _locations(data)
    meaning = lambda w: _meaning(w, locations)
    interpreted = lambda value: {'value': value['value'], 'support': [meaning(w) for w in value['witnesses']]}
    metadata = {'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'],
        'evaluation_scope': SCOPE, 'source_kind': data['source_kind'],
        'source_meanings': {name: None if value is None else meaning(value['witness']) for name, value in data['context'].items()},
        'source_scope': deepcopy(saved['input_source_refs']), 'withheld_locations': locations,
        'recovery_operand_scope': 'possessed_rows_retained_without_unrequested_values_or_invented_source_locations',
        'qualifications': list(QUALIFICATIONS)}
    rows = []
    for family in ('precision', 'zprime'):
        for record, extraction in zip(saved['sheet'][family], data[family]):
            extra = {'measurement_key': record['measurement_key'], 'family': family,
                'basis': record.get('basis'),
                'relationships': {name: interpreted(extraction[name]) for name in RELATIONSHIPS}
                    if family == 'precision' else None,
                'formula_relation': interpreted(extraction['formula_relation']) if family == 'zprime' else None}
            for component in components:
                if component in record['cells']:
                    rows.append({**deepcopy(metadata), **extra, 'component': component,
                                 **deepcopy(record['cells'][component])})
    if 'raw_control_zprime' in components:
        rows.append({**deepcopy(metadata), 'measurement_key': None, 'family': 'raw_control', 'basis': None,
            'relationships': None, 'formula_relation': None, 'component': 'raw_control_zprime',
            **deepcopy(saved['sheet']['raw_control_zprime'])})
    return rows


def _key(row):
    return row['sheet_ref'], row['measurement_key'], row['component']


class LiteratureMeasurementValidationRepository(LiteratureRateRepository):
    provider, record_version, components = PROVIDER, VERSION, COMPONENTS
    binding_fields = ()


    @staticmethod
    def _components(values):
        if (not isinstance(values, (list, tuple)) or any(type(v) is not str or v not in COMPONENTS for v in values)
                or len(set(values)) != len(values)):
            raise ContractError('measurement_validation_component_selection_invalid')
        return list(values)

    def _ancestors(self, scope, references):
        result = list(dict.fromkeys(references))
        for ref in result:
            for parent in self._native_provenance(scope, ref).get('parent_source_refs', ()):
                if parent not in result:
                    result.append(parent)
        return result

    def populate(self, context, arguments, operation_key):
        args = plain(arguments); validate_schema(args, measurement_validation_population_schema())
        requested = self._components(plain(context.assignment.get(REQUESTED, [])))
        request = {'operation_key': operation_key,
            'scope': plain(context.scope), 'arguments': args, 'components': requested,
            'role': context.role, 'assignment': plain(context.assignment)}
        source = self._native_source(context, args['source_ref'])
        snapshots = []
        def read_source(ref, representation):
            row = self._native_source(context, ref)
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self.store.get_artifact(artifact)}
        def read_component(selection):
            refs = [selection['sheet_ref']]
            if self.store.reference_subset(refs, plain(context.scope)) != refs:
                raise ContractError('literature_source_outside_scope')
            rows = LiteratureCalibrationRecoveryRepository(self.store).fact_cells(
                context, refs, components=[selection['component']])
            if len(rows) != 1:
                raise ContractError('selected_recovery_component_not_received')
            snapshots.append({'selection': deepcopy(selection), 'row': deepcopy(rows[0])})
            return rows
        extraction = read_measurement_validation_inputs(args, read_source=read_source, read_component=read_component)
        sheet = populate_measurement_validation(extraction)
        direct = extraction['source_refs']
        parents = self._ancestors(context.scope, [*direct, *(s['selection']['sheet_ref'] for s in snapshots)])
        payload = {'version': VERSION, 'input_source_ref': args['source_ref'], 'input_artifact_ref': source['artifact_ref'],
            'selection': args, 'direct_input_source_refs': direct, 'input_source_refs': parents,
            'source_metadata': {ref: self.store.get(ref) for ref in parents}, 'input_snapshots': snapshots,
            'extraction': extraction, 'sheet': sheet}
        with self.store.transaction():
            artifact = self.store.artifact(canonical(payload), 'application/json')
            req_ref = self.store.artifact(canonical(request), 'application/json')
            value = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                'text_ref': artifact, 'request_ref': req_ref, 'version': VERSION, 'retrieved_at': None, 'parent_source_refs': parents}
            reference = identity('source', {'origin': 'tool', 'record': value})
            exists = self.store.holds(reference)
            self.store.put('source', value, origin='tool', scope=plain(context.scope))
            rows = _project_saved(payload, reference, requested); validate_schema(rows, measurement_validation_cells_schema())
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'key': operation_key}), 'record_refs': [reference],
                'changed_record_refs': [] if exists else [reference],
                'result': {'sheet_ref': reference, 'view': VIEW, 'cells': rows}, 'feedback': None}

        return outcome

    def _json(self, reference):
        raw = self.store.get_artifact(reference)
        if 'artifact_' + hashlib.sha256(raw).hexdigest() != reference:
            raise ContractError('measurement_validation_saved_artifact_hash_mismatch')
        try:
            value = json.loads(raw)
        except (ValueError, TypeError) as error:
            raise ContractError('measurement_validation_saved_json_invalid') from error
        if not isinstance(value, dict):
            raise ContractError('measurement_validation_saved_object_required')
        return value

    def _validate_bindings(self, saved, request):
        """Structural associations only; never parse or recalculate a statistic."""
        e = saved['extraction']; args = request['arguments']
        validate_schema(e, measurement_validation_extraction_schema())
        validate_schema(saved['sheet'], measurement_validation_sheet_schema())
        if (e['version'] != INPUT_VERSION or e['source_ref'] != saved['input_source_ref']
                or e['artifact_ref'] != saved['input_artifact_ref'] or e['source_kind'] != args['source_kind']
                or e['source_refs'] != saved['direct_input_source_refs'] or saved['sheet']['extraction'] != e):
            raise ContractError('measurement_validation_saved_extraction_mismatch')
        def witness(selected):
            source = self._native_provenance(request['scope'], selected['source_ref'])
            artifact = source['artifact_ref'] if selected['representation'] == 'original' else source.get('text_ref')
            if artifact is None or selected['source_ref'] not in e['source_refs']:
                raise ContractError('measurement_validation_saved_source_binding_mismatch')
            return {**deepcopy(selected), 'artifact_ref': artifact}
        for name, selected in args['context'].items():
            expected = None if selected is None else {'value': selected['quote'], 'witness': witness(selected)}
            if e['context'][name] != expected:
                raise ContractError('measurement_validation_saved_meaning_mismatch')
        snapshots = []
        for role in ('recovery', 'relative_bias'):
            selection, operand = args[role], e[role]
            if (selection is None) != (operand is None):
                raise ContractError('measurement_validation_saved_recovery_binding_mismatch')
            if selection is not None:
                if (operand['selection'] != selection
                        or operand['row']['sheet_ref'] != selection['sheet_ref'] or operand['row']['component'] != role):
                    raise ContractError('measurement_validation_saved_recovery_binding_mismatch')
                snapshots.append({'selection': selection, 'row': operand['row']})
        if snapshots != saved['input_snapshots']:
            raise ContractError('measurement_validation_saved_recovery_binding_mismatch')
        for family in ('precision', 'zprime'):
            expected = []; seen = {}
            fields = RELATIONSHIPS if family == 'precision' else {'formula_relation': FORMULA_RELATIONS}
            for selected in args[family]:
                number = selected['number']; w = witness(number['witness'])
                a, b = number['number_start'], number['number_end']
                start, end = w['start']+len(w['quote'][:a].encode()), w['start']+len(w['quote'][:b].encode())
                key = identity('literature_measurement', {'artifact_ref': w['artifact_ref'], 'number_start': start, 'number_end': end})
                item = {'selector': {**number, 'witness': w}, 'key': key, 'start': start, 'end': end,
                    'label': witness(selected['quantity_label']), 'aliases': [],
                    'interpretations': {name: {'kind': 'source_interpretation', 'value': selected[name]['value'],
                        'witnesses': [witness(q) for q in selected[name]['witnesses']]} for name in fields}}
                if family == 'precision':
                    item['unit'] = {'value': selected['unit']['value'], 'witness': witness(selected['unit']['witness'])}
                if key in seen:
                    seen[key]['aliases'].append(item['selector'])
                else:
                    expected.append(item); seen[key] = item
            if len(expected) != len(e[family]) or len(expected) != len(saved['sheet'][family]):
                raise ContractError('measurement_validation_saved_measurement_roster_mismatch')
            for expected_item, actual, section in zip(expected, e[family], saved['sheet'][family]):
                number = actual['number']
                if (number['selector'] != expected_item['selector'] or number['measurement_key'] != expected_item['key']
                        or number['number_start_bytes'] != expected_item['start'] or number['number_end_bytes'] != expected_item['end']
                        or actual['aliases'] != expected_item['aliases'] or actual['quantity_label'] != expected_item['label']
                        or section['measurement_key'] != expected_item['key']
                        or any(actual[name] != value for name, value in expected_item['interpretations'].items())
                        or family == 'precision' and (actual['unit'] != expected_item['unit'] or section['basis'] != actual['basis']['value'])):
                    raise ContractError('measurement_validation_saved_measurement_binding_mismatch')
                for name, cell in section['cells'].items():
                    if cell['formula'] != FORMULAS[name]:
                        raise ContractError('measurement_validation_saved_formula_binding_mismatch')

    def read(self, reference):
        source = self.store.get(reference)
        value = {k:v for k,v in source.items() if k not in ('id', 'record_type', 'origin')}
        if (source.get('record_type') != 'source' or source.get('origin') != 'tool' or source.get('provider') != PROVIDER
                or source.get('version') != VERSION or identity('source', {'origin': 'tool', 'record': value}) != reference):
            raise ContractError('literature_measurement_validation_sheet_required')
        request = self._json(source['request_ref'])
        if (set(request) != {'operation_key', 'scope', 'arguments', 'components', 'role', 'assignment'}
                or not all(isinstance(request[f], str) and request[f] for f in ('operation_key', 'role'))
                or request['components'] != request['assignment'].get(REQUESTED, [])):
            raise ContractError('measurement_validation_saved_request_mismatch')
        validate_schema(request['arguments'], measurement_validation_population_schema()); self._components(request['components'])
        self._native_provenance(request['scope'], reference)
        saved = self._json(source['artifact_ref'])
        if (set(saved) != {'version', 'input_source_ref', 'input_artifact_ref', 'selection', 'direct_input_source_refs',
                'input_source_refs', 'source_metadata', 'input_snapshots', 'extraction', 'sheet'}
                or saved['version'] != VERSION or saved['selection'] != request['arguments']
                or saved['input_source_ref'] != request['arguments']['source_ref'] or source['text_ref'] != source['artifact_ref']
                or saved['input_source_refs'] != source['parent_source_refs']
                or self._ancestors(request['scope'], [*saved['direct_input_source_refs'], *(s['selection']['sheet_ref'] for s in saved['input_snapshots'])]) != saved['input_source_refs']
                or set(saved['source_metadata']) != set(saved['input_source_refs'])
                or any(canonical(self._native_provenance(request['scope'], ref)) != canonical(row) for ref, row in saved['source_metadata'].items())
                or self.store.get(saved['input_source_ref'])['artifact_ref'] != saved['input_artifact_ref']):
            raise ContractError('measurement_validation_saved_source_mismatch')
        self._validate_bindings(saved, request)
        rows = _project_saved(saved, reference, request['components']); validate_schema(rows, measurement_validation_cells_schema())
        return saved

    def project_cells(self, sheet_refs, *, components=None):
        selected = None if components is None else self._components(components); rows = []
        for ref in dict.fromkeys(sheet_refs):

            saved = self.read(ref); requested = self._json(self.store.get(ref)['request_ref'])['components']
            if selected is not None and any(name not in requested for name in selected):
                raise ContractError('measurement_validation_component_not_selected')
            rows.extend(_project_saved(saved, ref, requested if selected is None else selected))
        return rows

    def validate_returned_values(self, cells):
        validate_schema(cells, measurement_validation_cells_schema())
        seen = set()
        for row in cells:
            key = _key(row)
            if key in seen:
                raise ContractError('duplicate_measurement_validation_return_cell')
            seen.add(key)
            expected = self.project_cells([row['sheet_ref']], components=[row['component']])
            matching = [candidate for candidate in expected if _key(candidate) == key]
            if len(matching) != 1 or canonical(row) != canonical(matching[0]):
                raise ContractError('measurement_validation_return_differs_from_saved_cells')

    def fact_cells(self, context, sheet_refs, *, components):
        refs = list(dict.fromkeys(sheet_refs)); selected = self._components(components)
        if self.store.reference_subset(refs, plain(context.scope)) != refs:
            raise ContractError('literature_source_outside_scope')
        result = []
        for ref in refs:
            requested = self._json(self.store.get(ref)['request_ref'])['components']
            result.extend(self.project_cells([ref], components=[name for name in selected if name in requested]))
        return result

    def validate_fact_values(self, context, cells):
        self.validate_returned_values(cells)
        expected = {_key(row): row for row in self.fact_cells(context,
            list(dict.fromkeys(row['sheet_ref'] for row in cells)),
            components=list(dict.fromkeys(row['component'] for row in cells)))}
        if any(canonical(row) != canonical(expected.get(_key(row))) for row in cells):
            raise ContractError('literature_cell_not_received')


    def selected_sheet_refs(self, context):
        refs = self.held_sheet_refs()
        for ref in refs:
            self.read(ref)
        return refs

    def owned_sheet_refs(self, context):
        return self.selected_sheet_refs(context)

    def available_sheet_refs(self, context):
        return self.selected_sheet_refs(context)

    def has_work(self, context):
        return bool(self.available_sheet_refs(context))

    @staticmethod
    def cell_record_refs(cells):
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_ion_discrimination_storage import LiteratureIonDiscriminationRepository
        return LiteratureIonDiscriminationRepository.cell_record_refs(cells)


__all__ = ['LiteratureMeasurementValidationRepository', 'measurement_validation_cells_schema',
    'PROVIDER', 'VERSION', 'NAMESPACE', 'REQUESTED', 'VIEW', 'COMPONENTS', 'SCOPE']
