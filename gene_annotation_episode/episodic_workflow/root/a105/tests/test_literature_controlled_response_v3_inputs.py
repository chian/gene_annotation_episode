"""Actual constructed text/pixels; no paper, model, or native execution claims."""
from copy import deepcopy as cp
import hashlib
import json
from pathlib import Path
import re
import pytest
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_v3_inputs as source
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_controlled_response_inputs as shared
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_contracts import ExperimentalContractError
ROLES = shared.PRIMITIVE_ORDER
DESIGN = Path(__file__).resolve().parent / 'fixtures/retained_reference/a105_controlled_full_source_design_069'
CASES = json.loads((DESIGN / 'CONSTRUCTED_SOURCE_SELECTIONS.json').read_text())

class Fixture:

    def __init__(self, index=0, *, companion=False, authority=False, joints=False, local=True):
        self.case = CASES[index]
        self.args = cp(self.case['selection'])
        self.data = {s['source_ref']: s['content_utf8'].encode() if s['content_utf8'] is not None else (DESIGN / s['encoded_image_file']).read_bytes() for s in json.loads((DESIGN / 'CONSTRUCTED_SOURCE_ROSTER_001.json').read_text())}
        self.cov_ref = self.args['covariance']['source_ref']
        self.main_ref = self.args['source_ref']
        self.data[self.cov_ref] = self.case['source_covariance_text'].encode()
        self.doc = json.loads(self.case['source_covariance_text'])
        self.calls = []
        if local:
            self.args['local_pair_assignments'] = [dict(pair_key='condition0-real', condition='condition0', protein=dict(role=ROLES[2], reading_key=None), control=dict(role=ROLES[3], reading_key=None), admissibility=self.interp('compatible', 'nmol/min'), scope=self.interp('same', 'nmol/min'), covariance_selection=cp(self.args['covariance']), variance_status=cp(self.args['variance_status']))]
        if companion:
            reading = cp(self.args['arms'][ROLES[0]])
            reading['measurement'] = cp(CASES[6]['selection']['arms'][ROLES[0]]['measurement'])
            self.args['companion_readings'] = [dict(reading_key='A-display', primary_role=ROLES[0], reading=reading)]
            if authority:
                self.append('The table reports the experimental mean; the graph displays this same mean.')
                witness = self.witness('The table reports the experimental mean; the graph displays this same mean.')
            else:
                witness = self.witness('nmol/min')
            relation = lambda value: dict(value=value, witnesses=[cp(witness)] if value != 'unknown' else [])
            self.args['reading_reconciliations'] = [dict(role=ROLES[0], relationship=relation('same_reported_mean_and_display' if authority else 'unknown'), authority=dict(status='source_explicit' if authority else 'not_established', reading=dict(role=ROLES[0], reading_key=None) if authority else None, witnesses=[cp(witness)] if authority else []), **{k: relation('same') for k in ('normalization', 'calibration', 'revision', 'model_scope')})]
            if joints:
                for key in (None, 'A-display'):
                    i = len(self.args['joint_scopes'])
                    self.args['joint_reading_assignments'].append(dict(assignment={r: key if r == ROLES[0] else None for r in ROLES}, admissibility=relation('compatible')))
                    self.args['joint_scopes'].append(dict(assignment_index=i, **{k: relation('same') for k in ('normalization', 'calibration', 'revision', 'covariance_scope', 'model_scope')}, covariance_selection=cp(self.args['covariance']), variance_status=cp(self.args['variance_status']), model_kind=cp(self.args['model_kind'])))

    def source(self, reference, representation):
        self.calls.append((reference, representation))
        raw = self.data[reference]
        return {'artifact_ref': 'artifact_' + hashlib.sha256(raw).hexdigest(), 'content': raw}

    def read(self):
        return source.read_controlled_response_v3_inputs(self.args, read_source=self.source)

    def witness(self, quote, ref=None, tagged=True, start=0):
        ref = ref or self.main_ref
        at = self.data[ref].index(quote.encode(), start)
        w = dict(source_ref=ref, representation='original', start=at, end=at + len(quote.encode()), quote=quote)
        return dict(kind='text', **w) if tagged else w

    def interp(self, value, quote=None):
        return dict(value=value, witnesses=[] if quote is None else [self.witness(quote)])

    def number(self, quote, token):
        at = quote.index(token)
        return dict(witness=self.witness(quote, tagged=False), number_start=at, number_end=at + len(token))

    def append(self, text):
        self.data[self.main_ref] += ('<p>' + text + '</p>\n').encode()

    def covariance(self, mapping=None):
        self.data[self.cov_ref] = (json.dumps(self.doc, indent=2) + '\n').encode()
        labels = list(re.finditer(b'"label":\\s*("(?:[^"\\\\]|\\\\.)*")', self.data[self.cov_ref]))
        for role in ROLES:
            b = self.args['covariance']['bindings'][role]
            if mapping is not None:
                index = mapping[ROLES.index(role)]
                if index is None:
                    self.args['covariance']['bindings'][role] = None
                    continue
                if b is None:
                    b = dict(variable_index=index, label_witness=None, owner_witness=cp(self.args['arms'][role]['physical_observation']['canonical_witness']), correspondence=None)
                    self.args['covariance']['bindings'][role] = b
                b['variable_index'] = index
            if b is None:
                continue
            at, end = labels[b['variable_index']].span(1)
            b['label_witness'] = dict(source_ref=self.cov_ref, representation='original', start=at, end=end, quote=self.data[self.cov_ref][at:end].decode())
            b['correspondence'] = dict(value='same', witnesses=[dict(kind='text', **b['label_witness'])])
        for name in ('variance_status', 'model_kind'):
            self.args[name] = dict(value=self.doc[name], witnesses=[self.witness(json.dumps(self.doc[name]), self.cov_ref)])

    def text_measurement(self, role, text, token, unit='nmol/min'):
        self.append(text)
        self.args['arms'][role]['measurement'] = dict(kind='source_literal', literal=dict(status='exact', candidates=[self.number(text, token)], fragments=[]), unit=self.witness(unit, tagged=False, start=self.data[self.main_ref].index(text.encode())) if unit else None)

@pytest.mark.parametrize('index', range(14))
def test_original_source_cases_and_saved_reconstruction(index):
    f = Fixture(index)
    before = cp(f.args)
    result = f.read()
    assert f.args == before
    assert f.calls == shared._reference_closure(f.args)
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result
    Draft202012Validator(source._extraction_schema()).validate(result)
    assert result['projection_status'] == 'ready'
    assert result['component_local_inputs']['readings'][0]['reading'] == dict(role=ROLES[0], reading_key=None)

def test_unresolved_actual_graph_is_not_equality_or_independent_experiment():
    f = Fixture(companion=True, joints=True)
    result = f.read()
    assert result['projection_status'] == 'unresolved_active_reconciliation'
    assert result['calculation_inputs'] is None
    assert result['partial_projection_state'] == 'ready'
    assert len(result['alternative_inputs']) == 2
    assert result['arms'][ROLES[0]]['calculation_operand']['value'] == 10
    assert result['companion_extractions'][0]['reading']['calculation_operand']['value'] == 10.05
    assert result['companion_extractions'][0]['reading']['graph_details']['measurement']['pixel_result']['status'] == 'measured'
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result

def test_source_explicit_mean_display_reconciles_without_extra_selection_gate():
    f = Fixture(companion=True, authority=True, joints=True)
    result = f.read()
    assert result['projection_status'] == 'ready'
    assert result['reconciliation_decisions'][0]['method'] == 'explicit_reported_mean_display'
    assert result['final_projection_basis']['reading_assignment'][ROLES[0]] is None
    assert result['calculation_inputs']['arms'][ROLES[0]] == result['arms'][ROLES[0]]['calculation_operand']
    assert 'selection_basis' not in str(source._schemas())
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result

def test_bad_joint_cannot_enter_conditional_population_and_no_generated_products():
    f = Fixture(companion=True, joints=True)
    f.args['joint_reading_assignments'][1]['admissibility'] = dict(value='unknown', witnesses=[])
    result = f.read()
    assert [r['scope_index'] for r in result['alternative_inputs']] == [0]
    assert len(result['joint_scope_extractions']) == 2

def test_absent_arm_has_no_source_kind_origin_or_fabricated_uncertainty():
    f = Fixture(local=False)
    f.args['arms'][ROLES[0]] = None
    f.args['covariance']['bindings'][ROLES[0]] = None
    result = f.read()
    row = result['component_local_inputs']['readings'][0]
    assert row['arm'] is None and row['source_kind'] is None and (row['measurement_method'] == 'not_selected')
    assert row['reported_uncertainty']['statistic'] == 'unknown'
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result

def test_wrong_role_selector_duplicate_pairs_and_mutated_saved_operand_rejected():
    f = Fixture(companion=True)
    f.args['local_pair_assignments'][0]['protein']['reading_key'] = 'A-display'
    with pytest.raises(ExperimentalContractError, match='controlled_reading_selector_unresolved'):
        f.read()
    f = Fixture()
    result = f.read()
    result['arms'][ROLES[2]]['calculation_operand']['value'] = 800
    with pytest.raises(ExperimentalContractError):
        source.validate_controlled_response_v3_extraction(f.args, result)

def test_request_arm_key_order_does_not_change_primary_reading_roster():
    f = Fixture()
    f.args['arms'] = {r: f.args['arms'][r] for r in reversed(ROLES)}
    result = f.read()
    assert [r['reading']['role'] for r in result['component_local_inputs']['readings']] == list(ROLES)

def test_unresolved_canceled_representations_do_not_require_favorable_reading():
    f = Fixture(companion=True)
    nomination = f.args['reading_reconciliations'][0]
    nomination['role'] = ROLES[1]
    reading = cp(f.args['arms'][ROLES[1]])
    reading['measurement'] = cp(f.args['arms'][ROLES[3]]['measurement'])
    f.args['companion_readings'] = [dict(reading_key='B-display', primary_role=ROLES[1], reading=reading)]
    result = f.read()
    assert result['reconciliation_decisions'][0]['state'] == 'unknown_authority'
    assert result['projection_status'] == 'ready'
    assert result['calculation_inputs']['arms'][ROLES[1]] == result['arms'][ROLES[1]]['calculation_operand']
    assert source.validate_controlled_response_v3_extraction(f.args, result) == result

def test_live_closed_schema_graph():
    schemas = source._schemas()
    assert len(schemas) == 7
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)

        def walk(value):
            if isinstance(value, dict):
                if '$ref' in value and value['$ref'].startswith('#/$defs/'):
                    assert value['$ref'][8:] in schema['$defs']
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(schema)
    assert schemas['EXTRACTION_SCHEMA_V3_007']['$defs']['CovarianceExtraction']['properties']['raw_text'] == {'anyOf': [{'type': 'string'}, {'type': 'null'}]}
