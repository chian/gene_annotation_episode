"""Selected A105 ion components and authenticated, exactly scoped saved returns.

Only population reads scientific artifacts and invokes the frozen reader and
calculator. Reconstruction copies original facts and checks their custody; it
does not reattest current scientific code or reinterpret original evidence.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from .communication import plain
from .domain import ContractError, canonical, identity, obj, validate_schema
from .literature_rate_storage import LiteratureRateRepository
from .literature_compiled_assay_storage import LiteratureCompiledAssayRepository, compiled_assay_cells_schema
from .literature_ion_discrimination_inputs import (
    VERSION as EXTRACTION_VERSION, ion_discrimination_population_schema,
    ion_discrimination_sheet_schema, read_ion_discrimination_inputs,
)
from .literature_ion_discrimination_calculations import COMPONENTS, FORMULAS, populate_ion_discrimination

PROVIDER = 'literature.a105.ion_discrimination'
VERSION = 'literature_ion_discrimination_record_v1'
NAMESPACE = 'literature_ion_discrimination_cells'
REQUESTED = 'requested_ion_discrimination_components'
VIEW = 'ion_discrimination_components'
SCOPE = 'source_ion_discrimination'
_FROZEN = {
    'literature_ion_discrimination_numbers.py': '080f5dbb79f3036186293c9c39c9faa38e17396150482d7d45774b2e4e7b9cf2',
    'literature_ion_discrimination_inputs.py': '850cc2053c372beaf87877c2c89bc0de2509ce6f51584c4515e363f1cc769ef6',
    'literature_ion_discrimination_calculations.py': 'b7576ca52c45b69675c4241428afcb983273fef555e4f6a85b650e1bdd3c8ce4',
    'literature_ion_discrimination_prompt.py': '44797ebe7a49fc732e31deb61ebdebeffd608733e5246b650040b512c12cf99b',
}


def _array(schema):
    return {'type': 'array', 'items': deepcopy(schema)}


def _ref(nullable=False, namespace='source'):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference',
            'x-reference-namespace': namespace}


def _enum(values):
    return {'type': 'string', 'enum': list(values)}


def _meaning_schema():
    return {'anyOf': [obj({'source_ref': _ref(), 'artifact_ref': _ref(namespace='artifact'),
        'representation': _enum(('original', 'text')), 'start': {'type': 'integer', 'minimum': 0},
        'end': {'type': 'integer', 'minimum': 1}, 'display_text': {'type': 'string', 'minLength': 1},
        'status': _enum(('selected', 'unrequested_numbers_withheld'))}), {'type': 'null'}]}


def _interpreted(schema):
    return obj({'value': deepcopy(schema['properties']['value']), 'support': _array(_meaning_schema())})


def ion_discrimination_cells_schema():
    """Exact host type; the numerical definitions are never prompt instructions."""
    original = ion_discrimination_population_schema()['$defs']
    sheet = ion_discrimination_sheet_schema()
    contexts = original['Context']['properties']
    context = obj({name: obj({field: _meaning_schema() for field in schema['properties']})
        if name in ('preferred', 'alternative') else _meaning_schema() for name, schema in contexts.items()})
    relationships = obj({name: _interpreted(node) for name, node in original['Relationships']['properties'].items()})
    quantity = obj({name: _interpreted(node) for name, node in original['SourceQuantity']['properties'].items()
        if name not in ('number', 'unit')})
    compiled = compiled_assay_cells_schema()['items']['properties']
    compiled_meanings = obj({**{name: deepcopy(compiled[name]) for name in
        ('operand_meanings', 'assay_meanings', 'endpoint_kind', 'arrangement_kind', 'correction_stages')},
        'literal_display_status': obj({name: _enum(('selected', 'not_selected', 'unrequested_numerical_scope_unresolved'))
            for name in compiled['assay_meanings']['properties']}),
        'literal_source_ref': _ref(), 'literal_location_status': {'const': 'not_available_in_possessed_compiled_row'}})
    operand = obj({'role': _enum(('preferred', 'alternative', 'reported')),
        'route': _enum(('source_quantity', 'compiled_activity')),
        'source_quantity_meanings': {'anyOf': [quantity, {'type': 'null'}]},
        'compiled_meanings': {'anyOf': [compiled_meanings, {'type': 'null'}]}})
    cell = deepcopy(sheet['$defs']['Cell'])
    properties = {**cell['properties'], 'sheet_ref': _ref(), 'evidence_source_ref': _ref(),
        'evaluation_scope': {'const': SCOPE}, 'route': deepcopy(sheet['properties']['route']),
        'source_kind': _enum(('primary_source', 'retained_extraction', 'synthetic_fixture')),
        'source_meanings': context, 'relationships': relationships, 'operands': _array(operand),
        'nonintended_differences': _array(obj({'aspect': deepcopy(original['NonintendedDifference']['properties']['aspect']),
            'support': _array(_meaning_schema())})),
        'adjustment_bindings': _array(obj({**{name: deepcopy(node) for name, node in original['AdjustmentBinding']['properties'].items()
            if name != 'witnesses'}, 'support': _array(_meaning_schema()), 'compiled_stage_verified': {'type': 'boolean'}})),
        'covariance': obj({'status': _enum(('not_selected', 'valid', 'covariance_owner_or_dependency_mismatch',
            'covariance_units_incompatible', 'covariance_status_unknown', 'shared_activity_covariance_inconsistent', 'covariance_invalid')),
            'source_ref': _ref(True), 'origin': {'type': ['string', 'null'], 'enum': ['reported', 'derived', 'synthetic', None]}}),
        'source_scope': _array(_ref()),
        'withheld_locations': _array(obj({'source_ref': _ref(), 'artifact_ref': _ref(namespace='artifact'),
            'representation': _enum(('original', 'text')), 'start': {'type': 'integer', 'minimum': 0},
            'end': {'type': 'integer', 'minimum': 1}})),
        'replication_status': {'const': 'not_evaluated_by_this_component'}}
    def inline(node):
        if isinstance(node, dict):
            if '$ref' in node:
                return inline(sheet['$defs'][node['$ref'].removeprefix('#/$defs/')])
            return {name: inline(value) for name, value in node.items()}
        if isinstance(node, list): return [inline(value) for value in node]
        return node
    return {'type': 'array', 'items': inline(obj(properties)), 'x-source': NAMESPACE}


_NUMBER = r'[+−-]?(?:[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?'
# Display-only masks: ion rate/spread values, not pH, ionic concentration,
# membrane voltage or numbers embedded in biological identifiers such as Ec2.
_RATE_DISPLAY = re.compile(r'(?<![A-Za-z0-9_.])(?P<number>' + _NUMBER + r'|10<sup>[+−-]?[0-9]+</sup>)'
    r'(?=\s*(?:ions?\s*/\s*s\b|/\s*(?:s|min)\b|s\s*<sup>[−-]1</sup>|(?:per[_ ]?(?:s|min))\b|s[−-]1\b|-?fold\b))')
_SPREAD_DISPLAY = re.compile(r'(?:±|\+\s*/\s*[-−])\s*(?P<number>' + _NUMBER + ')')
_CONTROL_DISPLAY = re.compile(r'\b(?:recovery|calibration|amount|protein\s+amount|protein\s+concentration|'
    r'contaminant|normalizer|normalization\s+factor|q|g|k|E|u|v)\s*(?:(?:was|is|of)\s+|[:=]\s*)?'
    r'(?P<number>' + _NUMBER + r')(?![A-Za-z0-9_.])')
_FRACTION_DISPLAY = re.compile(r'(?<![A-Za-z0-9_.])(?P<number>' + _NUMBER + r')(?=\s*(?:fraction|dimensionless)\b)')
_DISPLAY_PATTERNS = (_RATE_DISPLAY, _SPREAD_DISPLAY, _CONTROL_DISPLAY, _FRACTION_DISPLAY)


def _safe_literal(text):
    """Possessed free literals have no operand spans; do not guess their scope."""
    if text is None: return None, 'not_selected'
    if re.search(r'(?<![A-Za-z0-9_])' + _NUMBER, text):
        return None, 'unrequested_numerical_scope_unresolved'
    return text, 'selected'


def _source_locations(extraction):
    result = []
    for role in ('preferred', 'alternative', 'reported'):
        if role not in extraction['operands']: continue
        operand = extraction['operands'][role]
        number = operand.get('number')
        if number is not None:
            w = number['selector']['witness']; span = number['byte_span']
            result.append({**{key: w[key] for key in ('source_ref', 'artifact_ref', 'representation')},
                'start': span['start'], 'end': span['end']})
    return result


def _safe_meaning(witness, locations, covariance_ref):
    if witness is None:
        return None
    text = witness['quote']; intervals = []
    for pattern in _DISPLAY_PATTERNS:
        intervals.extend(match.span('number') for match in pattern.finditer(text))
    if witness['source_ref'] == covariance_ref:
        intervals.extend(match.span() for match in re.finditer(_NUMBER, text))
    for location in locations:
        if (witness['artifact_ref'] == location['artifact_ref']
                and witness['representation'] == location['representation']
                and witness['start'] < location['end'] and location['start'] < witness['end']):
            a = max(witness['start'], location['start']) - witness['start']
            b = min(witness['end'], location['end']) - witness['start']
            intervals.append((len(text.encode()[:a].decode()), len(text.encode()[:b].decode())))
    flags = [False] * len(text)
    for a, b in intervals:
        flags[a:b] = [True] * (b-a)
    display = []; masked = False
    for index, character in enumerate(text):
        if flags[index]:
            if not masked: display.append('[unrequested numerical operand]')
            masked = True
        else:
            display.append(character); masked = False
    return {**{key: witness[key] for key in ('source_ref', 'artifact_ref', 'representation', 'start', 'end')},
        'display_text': ''.join(display), 'status': 'unrequested_numbers_withheld' if intervals else 'selected'}


def _project_saved(saved, reference, components):
    e = saved['extraction']; locations = _source_locations(e)
    covariance = e['covariance']; cov_ref = covariance['source_ref']
    def meaning(w): return _safe_meaning(w, locations, cov_ref)
    def interpreted(value): return {'value': value['value'], 'support': [meaning(w) for w in value['witnesses']]}
    contexts = {name: {field: meaning(w) for field, w in value.items()} if name in ('preferred', 'alternative')
        else meaning(value) for name, value in e['context'].items()}
    operands = []
    for role in ('preferred', 'alternative', 'reported'):
        if role not in e['operands']: continue
        operand = e['operands'][role]
        compiled = None
        if operand['kind'] == 'compiled_activity':
            row = operand['row']
            compiled = {name: deepcopy(row[name]) for name in ('operand_meanings', 'endpoint_kind', 'arrangement_kind', 'correction_stages')}
            # These optional source literals are not direct numeric returns.
            literals = {name: _safe_literal(text) for name, text in row['assay_meanings'].items()}
            compiled['assay_meanings'] = {name: result[0] for name, result in literals.items()}
            compiled['literal_display_status'] = {name: result[1] for name, result in literals.items()}
            compiled['literal_source_ref'] = row['evidence_source_ref']
            compiled['literal_location_status'] = 'not_available_in_possessed_compiled_row'
        operands.append({'role': role, 'route': operand['kind'], 'compiled_meanings': compiled,
            'source_quantity_meanings': {name: interpreted(value) for name, value in operand['interpretations'].items()}
                if operand['kind'] == 'source_quantity' else None})
    metadata = {'sheet_ref': reference, 'evidence_source_ref': saved['input_source_ref'], 'evaluation_scope': SCOPE,
        'route': e['route'], 'source_kind': e['selection']['source_kind'], 'source_meanings': contexts,
        'relationships': {name: interpreted(value) for name, value in e['relationships'].items()},
        'operands': operands, 'source_scope': deepcopy(saved['input_source_refs']), 'withheld_locations': locations,
        'nonintended_differences': [{'aspect': d['aspect'], 'support': [meaning(w) for w in d['witnesses']]} for d in e['nonintended_differences']],
        'adjustment_bindings': [{**{key: deepcopy(value) for key, value in b.items() if key != 'witnesses'},
            'support': [meaning(w) for w in b['witnesses']]} for b in e['adjustment_bindings']],
        'covariance': {'status': covariance['status'], 'source_ref': cov_ref,
            'origin': covariance['data']['origin'] if covariance['data'] is not None else None},
        'replication_status': 'not_evaluated_by_this_component'}
    return [{**deepcopy(metadata), **deepcopy(saved['sheet']['cells'][name])} for name in components]


class LiteratureIonDiscriminationRepository(LiteratureRateRepository):
    provider, record_version, components = PROVIDER, VERSION, COMPONENTS
    operations_table = 'literature_ion_discrimination_operations'
    received_table = 'literature_ion_discrimination_received'
    binding_fields = ()

    def __init__(self, store, run_id):
        if not isinstance(run_id, str) or not run_id: raise ValueError('explicit_literature_run_required')
        self.store, self.run_id = store, run_id

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    @staticmethod
    def _components(values):
        if (not isinstance(values, (list, tuple)) or any(type(v) is not str or v not in COMPONENTS for v in values)
                or len(set(values)) != len(values)):
            raise ContractError('ion_discrimination_component_selection_invalid')
        return list(values)

    def _ancestors(self, scope, references):
        result = list(dict.fromkeys(references))
        for ref in result:
            for parent in self._native_provenance(scope, ref).get('parent_source_refs', ()):
                if parent not in result: result.append(parent)
        return result

    def _implementation_receipt(self):
        actual = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in _FROZEN}
        if actual != _FROZEN: raise ContractError('ion_discrimination_prospective_dependency_mismatch')
        return {'version': 'ion_discrimination_original_implementation_v1', 'files': actual}

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id: raise ContractError('literature_run_mismatch')
        if not isinstance(operation_key, str) or not operation_key: raise ContractError('operation_key_required')
        args = plain(arguments); validate_schema(args, ion_discrimination_population_schema())
        requested = self._components(plain(context.assignment.get(REQUESTED, [])))
        request = {'run_id': self.run_id, 'episode_id': context.episode_id, 'operation_key': operation_key,
            'scope': plain(context.scope), 'arguments': args, 'components': requested,
            'role': context.role, 'assignment': plain(context.assignment), 'received_record_refs': list(context.received_record_refs)}
        signature = canonical(request)
        old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old is not None:
            if old['signature'] != signature: raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome']); self.read(outcome['result']['sheet_ref'])
            return outcome
        source = self._native_source(context, args['source_ref'])
        receipt = self._implementation_receipt()
        snapshots = []
        def read_source(ref, representation):
            row = self._native_source(context, ref)
            artifact = row['artifact_ref'] if representation == 'original' else row.get('text_ref')
            if artifact is None: raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self.store.get_artifact(artifact)}
        def read_component(selection):
            refs = [selection['sheet_ref']]
            if self.store.reference_subset(refs, plain(context.scope)) != refs: raise ContractError('literature_source_outside_scope')
            rows = LiteratureCompiledAssayRepository(self.store, self.run_id).fact_cells(context, refs, components=['corrected_activity'])
            if len(rows) != 1: raise ContractError('selected_activity_not_received')
            snapshots.append({'selection': deepcopy(selection), 'row': deepcopy(rows[0])})
            return rows
        extraction = read_ion_discrimination_inputs(args, read_source=read_source, read_component=read_component)
        sheet = populate_ion_discrimination(extraction)
        if extraction['route'] == 'compiled_activity_pair':
            snapshots = [{'selection': deepcopy(extraction['operands'][role]['selection']),
                'row': deepcopy(extraction['operands'][role]['row'])} for role in ('preferred', 'alternative')]
        direct = extraction['source_refs']; parents = self._ancestors(context.scope, [*direct, *(s['selection']['sheet_ref'] for s in snapshots)])
        payload = {'version': VERSION, 'input_source_ref': args['source_ref'], 'input_artifact_ref': source['artifact_ref'],
            'selection': args, 'direct_input_source_refs': direct, 'input_source_refs': parents,
            'source_metadata': {ref: self.store.get(ref) for ref in parents}, 'input_snapshots': snapshots,
            'original_implementation': receipt, 'extraction': extraction, 'sheet': sheet}
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(payload), 'application/json')
            req_ref = self.store.artifact(canonical(request), 'application/json')
            value = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                'text_ref': artifact, 'request_ref': req_ref, 'version': VERSION, 'retrieved_at': None, 'parent_source_refs': parents}
            reference = identity('source', {'origin': 'tool', 'record': value})
            exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (reference,)).fetchone()
            self.store.put('source', value, origin='tool', scope=plain(context.scope))
            rows = _project_saved(payload, reference, requested); validate_schema(rows, ion_discrimination_cells_schema())
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id,
                'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': [reference],
                'changed_record_refs': [] if exists else [reference],
                'result': {'sheet_ref': reference, 'view': VIEW, 'cells': rows}, 'feedback': None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _json(self, reference):
        raw = self.store.get_artifact(reference)
        if 'artifact_' + hashlib.sha256(raw).hexdigest() != reference: raise ContractError('ion_saved_artifact_hash_mismatch')
        try:
            value = json.loads(raw)
        except (ValueError, TypeError) as error: raise ContractError('ion_saved_json_invalid') from error
        if not isinstance(value, dict): raise ContractError('ion_saved_object_required')
        return value

    def _validate_bindings(self, saved, request):
        """Original structural/source/role bindings only; no science recalculation."""
        e = saved['extraction']; args = request['arguments']
        if (set(e) != {'version', 'selection', 'source_ref', 'artifact_ref', 'source_refs', 'route', 'context',
                'relationships', 'nonintended_differences', 'operands', 'covariance', 'adjustment_bindings', 'adjustment_reasons'}
                or e['version'] != EXTRACTION_VERSION or e['selection'] != args or e['route'] != args['route']
                or e['source_ref'] != saved['input_source_ref'] or e['artifact_ref'] != saved['input_artifact_ref']
                or e['source_refs'] != saved['direct_input_source_refs']): raise ContractError('ion_saved_extraction_mismatch')
        def witness(w):
            source = self._native_provenance(request['scope'], w['source_ref'])
            artifact = source['artifact_ref'] if w['representation'] == 'original' else source.get('text_ref')
            if (artifact is None or w['source_ref'] not in e['source_refs'] or w['source_ref'] not in request['received_record_refs']
                    or w['end'] - w['start'] != len(w['quote'].encode())): raise ContractError('ion_saved_source_binding_mismatch')
            return {**deepcopy(w), 'artifact_ref': artifact}
        def interpreted(value):
            result = {'kind': 'source_interpretation', 'value': value['value'], 'witnesses': [witness(w) for w in value['witnesses']]}
            unique = {(w['artifact_ref'], w['representation'], w['start'], w['end']) for w in result['witnesses']}
            if len(unique) < (2 if value['value'] == 'conflicting' else 0 if value['value'] == 'unknown' else 1):
                raise ContractError('ion_saved_interpretation_mismatch')
            return result
        expected_context = {name: {key: None if w is None else witness(w) for key, w in value.items()}
            if name in ('preferred', 'alternative') else None if value is None else witness(value) for name, value in args['context'].items()}
        if e['context'] != expected_context or e['relationships'] != {k: interpreted(v) for k, v in args['relationships'].items()}:
            raise ContractError('ion_saved_meaning_mismatch')
        if e['nonintended_differences'] != [{**d, 'witnesses': [witness(w) for w in d['witnesses']]} for d in args['nonintended_differences']]:
            raise ContractError('ion_saved_meaning_mismatch')
        if args['route'] == 'compiled_activity_pair':
            selected = [args['activities'][role] for role in ('preferred', 'alternative')]
            if selected != [s['selection'] for s in saved['input_snapshots']] or set(e['operands']) != {'preferred', 'alternative'}:
                raise ContractError('ion_saved_activity_binding_mismatch')
            for role, snapshot in zip(('preferred', 'alternative'), saved['input_snapshots']):
                validate_schema([snapshot['row']], compiled_assay_cells_schema())
                selection = snapshot['selection']; operand = e['operands'][role]
                if (selection['sheet_ref'] not in request['received_record_refs'] or operand != {'kind': 'compiled_activity',
                        'selection': selection, 'activity_key': identity('selected_ion_activity', selection), 'row': snapshot['row']}
                        or snapshot['row']['sheet_ref'] != selection['sheet_ref'] or snapshot['row']['component'] != 'corrected_activity'):
                    raise ContractError('ion_saved_activity_binding_mismatch')
            if e['covariance']['source_ref'] != args['activity_covariance_source_ref']:
                raise ContractError('ion_saved_covariance_binding_mismatch')
            expected_adjustments = [{**b, 'witnesses': [witness(w) for w in b['witnesses']]} for b in args['adjustment_bindings']]
            if len(expected_adjustments) != len(e['adjustment_bindings']) or any(
                    {k:v for k,v in got.items() if k != 'compiled_stage_verified'} != wanted
                    or type(got['compiled_stage_verified']) is not bool for got, wanted in zip(e['adjustment_bindings'], expected_adjustments)):
                raise ContractError('ion_saved_adjustment_binding_mismatch')
        else:
            if saved['input_snapshots']: raise ContractError('ion_saved_activity_binding_mismatch')
            quantities = {'reported': args['reported_ratio']} if args['route'] == 'reported_ratio' else args['thresholds']
            if set(e['operands']) != set(quantities): raise ContractError('ion_saved_quantity_binding_mismatch')
            for role, selection in quantities.items():
                q = e['operands'][role]
                if q['kind'] != 'source_quantity' or q['selection'] != selection or q['interpretations'] != {
                        k: interpreted(v) for k, v in selection.items() if k not in ('number', 'unit')}:
                    raise ContractError('ion_saved_quantity_binding_mismatch')
                if q['unit'] is not None and q['unit']['witness'] != witness(selection['unit']):
                    raise ContractError('ion_saved_quantity_binding_mismatch')
                if q['number'] is not None:
                    chosen = selection['number']; number = q['number']; w = witness(chosen['witness'])
                    a, b = chosen['number_start'], chosen['number_end']
                    span = {'artifact_ref': w['artifact_ref'], 'start': w['start'] + len(w['quote'][:a].encode()),
                        'end': w['start'] + len(w['quote'][:b].encode())}
                    if (not 0 <= a < b <= len(w['quote']) or number['selector'] != {**chosen, 'witness': w}
                            or number['raw_token'] != w['quote'][a:b] or number['byte_span'] != span
                            or number['measurement_key'] != identity('ion_numeric_span', span)):
                        raise ContractError('ion_saved_number_binding_mismatch')
        validate_schema(saved['sheet'], ion_discrimination_sheet_schema())
        if saved['sheet']['route'] != args['route']: raise ContractError('ion_saved_sheet_mismatch')
        for name, cell in saved['sheet']['cells'].items():
            if cell['component'] != name or cell['formula_code'] != FORMULAS[name]: raise ContractError('ion_saved_cell_mismatch')
            for dependency in cell['dependencies']:
                if dependency['source_ref'] not in saved['input_source_refs'] or dependency['component_ref'] is not None and dependency['component_ref'] not in saved['input_source_refs']:
                    raise ContractError('ion_saved_dependency_mismatch')

    def read(self, reference):
        source = self.store.get(reference)
        value = {k:v for k,v in source.items() if k not in ('id', 'record_type', 'origin')}
        if (source.get('record_type') != 'source' or source.get('origin') != 'tool' or source.get('provider') != PROVIDER
                or source.get('version') != VERSION or identity('source', {'origin': 'tool', 'record': value}) != reference):
            raise ContractError('literature_ion_discrimination_sheet_required')
        request = self._json(source['request_ref'])
        if (set(request) != {'run_id', 'episode_id', 'operation_key', 'scope', 'arguments', 'components', 'role', 'assignment', 'received_record_refs'}
                or request['run_id'] != self.run_id or not all(isinstance(request[f], str) and request[f] for f in ('episode_id', 'operation_key', 'role'))
                or request['components'] != request['assignment'].get(REQUESTED, [])):
            raise ContractError('ion_saved_request_mismatch')
        validate_schema(request['arguments'], ion_discrimination_population_schema()); self._components(request['components'])
        self._native_provenance(request['scope'], reference)
        operation = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone() if self._installed(self.operations_table) else None
        if operation is None or operation['signature'] != canonical(request): raise ContractError('literature_sheet_not_selected_output')
        saved = self._json(source['artifact_ref'])
        if (set(saved) != {'version', 'input_source_ref', 'input_artifact_ref', 'selection', 'direct_input_source_refs',
                'input_source_refs', 'source_metadata', 'input_snapshots', 'original_implementation', 'extraction', 'sheet'}
                or saved['version'] != VERSION or saved['selection'] != request['arguments']
                or saved['input_source_ref'] != request['arguments']['source_ref'] or source['text_ref'] != source['artifact_ref']
                or saved['input_source_refs'] != source['parent_source_refs']
                or self._ancestors(request['scope'], [*saved['direct_input_source_refs'], *(s['selection']['sheet_ref'] for s in saved['input_snapshots'])]) != saved['input_source_refs']
                or set(saved['source_metadata']) != set(saved['input_source_refs'])
                or any(canonical(self._native_provenance(request['scope'], ref)) != canonical(row) for ref, row in saved['source_metadata'].items())
                or self.store.get(saved['input_source_ref'])['artifact_ref'] != saved['input_artifact_ref']):
            raise ContractError('ion_saved_source_mismatch')
        receipt = saved['original_implementation']
        if (set(receipt) != {'version', 'files'} or receipt['version'] != 'ion_discrimination_original_implementation_v1'
                or not isinstance(receipt['files'], dict) or any(not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v) for v in receipt['files'].values())):
            raise ContractError('ion_saved_original_receipt_mismatch')
        self._validate_bindings(saved, request)
        rows = _project_saved(saved, reference, request['components']); validate_schema(rows, ion_discrimination_cells_schema())
        outcome = json.loads(operation['outcome'])
        if (outcome.get('status') != 'completed' or outcome.get('record_refs') != [reference] or outcome.get('feedback') is not None
                or canonical(outcome.get('result')) != canonical({'sheet_ref': reference, 'view': VIEW, 'cells': rows})
                or outcome.get('operation_ref') != identity('operation', {'run_id': self.run_id, 'episode_id': request['episode_id'], 'key': request['operation_key']})):
            raise ContractError('ion_saved_outcome_mismatch')
        return saved

    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = None if components is None else self._components(components)
        rows = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs: raise ContractError('literature_sheet_not_received')
            saved = self.read(ref); requested = self._json(self.store.get(ref)['request_ref'])['components']
            if selected is not None and any(name not in requested for name in selected): raise ContractError('ion_discrimination_component_not_selected')
            rows.extend(_project_saved(saved, ref, requested if selected is None else selected))
        return rows

    def fact_cells(self, context, sheet_refs, *, components):
        if context.run_id != self.run_id: raise ContractError('literature_run_mismatch')
        refs = list(dict.fromkeys(sheet_refs)); selected = self._components(components)
        if self.store.reference_subset(refs, plain(context.scope)) != refs: raise ContractError('literature_source_outside_scope')
        received = None; result = []
        for ref in refs:
            if ref not in context.received_record_refs: raise ContractError('literature_sheet_not_received')
            if self._sheet_owner(ref) == context.episode_id:
                requested = self._json(self.store.get(ref)['request_ref'])['components']
                result.extend(self.project_cells([ref], permitted_record_refs=context.received_record_refs,
                    components=[name for name in selected if name in requested]))
            else:
                if received is None: received = {(r['sheet_ref'], r['component']):r for r in self.received_cells(context)}
                result.extend(deepcopy(received[(ref, name)]) for name in selected if (ref, name) in received)
        return result

    def received_cells(self, context):
        if context.run_id != self.run_id: raise ContractError('literature_run_mismatch')
        return super().received_cells(context) if self._installed(self.received_table) else []

    def receive_cells(self, context, cells, operation_key):
        if not cells: return
        with self.store.transaction():
            self._install(); return super().receive_cells(context, cells, operation_key)

    def selected_sheet_refs(self, context):
        if context.run_id != self.run_id: raise ContractError('literature_run_mismatch')
        if not self._installed(self.operations_table): return []
        refs = list(dict.fromkeys(json.loads(row['outcome'])['result']['sheet_ref'] for row in self.store.db.execute(
            f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? ORDER BY rowid', (self.run_id, context.episode_id))))
        for ref in refs: self.read(ref)
        return refs

    def owned_sheet_refs(self, context):
        return [ref for ref in self.selected_sheet_refs(context) if ref in context.received_record_refs]

    def available_sheet_refs(self, context):
        return list(dict.fromkeys([*self.owned_sheet_refs(context), *(r['sheet_ref'] for r in self.received_cells(context)
            if r['sheet_ref'] in context.received_record_refs)]))

    def has_work(self, context):
        return bool(self.available_sheet_refs(context))

    @staticmethod
    def cell_record_refs(cells):
        refs = []
        def visit(value):
            if isinstance(value, dict):
                for name, child in value.items():
                    if (name.endswith('_ref') and isinstance(child, str)): refs.append(child)
                    elif name in ('source_scope',): refs.extend(child)
                    else: visit(child)
            elif isinstance(value, list):
                for child in value: visit(child)
        visit(cells)
        return list(dict.fromkeys(refs))


__all__ = ['LiteratureIonDiscriminationRepository', 'ion_discrimination_cells_schema',
    'PROVIDER', 'VERSION', 'NAMESPACE', 'REQUESTED', 'VIEW', 'COMPONENTS']
