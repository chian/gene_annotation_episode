"""Original-source pure calculations and explicitly synthetic adversarial contrasts.

Callbacks stand for already possessed source/fact views. No Store, provider,
model, episode or credit controller is executed; this is not assay adequacy.
"""
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.domain import ContractError, identity, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_calibration_recovery_inputs import read_calibration_recovery_inputs
from gene_annotation_episode.literature_calibration_recovery_calculations import populate_calibration_recovery
from gene_annotation_episode.literature_calibration_recovery_storage import _project_saved
from gene_annotation_episode.literature_measurement_validation_inputs import (
    CONTEXT_FIELDS, RELATIONSHIPS, read_measurement_validation_inputs,
    measurement_validation_population_schema, measurement_validation_extraction_schema,
)
from gene_annotation_episode.literature_measurement_validation_calculations import (
    populate_measurement_validation, measurement_validation_sheet_schema,
)
from gene_annotation_episode.literature_measurement_validation_prompt import MEASUREMENT_VALIDATION_TASK

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_measurement_validation_pure_205'
PACKET = ROOT / 'verification/literature_reference_evidence_2026-10-25_001/a105_common_scoring_gap_review_200/SOURCE_PACKET_001.json'


class Source:
    def __init__(self, *, within='0.8', between='1.7', zprime='0.99', unit='%CV',
                 nominal='8.6', measured='8.72', content=None, source_kind='synthetic_fixture'):
        self.values = dict(within=within, between=between, zprime=zprime, nominal=nominal, measured=measured)
        self.unit = unit; self.source_kind = source_kind
        self.content = content if content is not None else (
            '<article><p>Prepared reporter standard NADPH in buffer; optical WST8 endpoint. '
            'Same population and displayed mean denominator. Different population. '
            'Held out validation observations and stock. Repeated technical readings, count unknown. '
            "Z'=1-3*(SDpos+SDneg)/abs(meanpos-meanneg).</p>"
            '<table><thead><tr><th>Prepared (nmol)</th><th>Measured (nmol)</th><th>Accuracy (%RE)</th>'
            '<th colspan="2">Precision CV (' + unit + ')</th><th>Z’- factor</th></tr>'
            '<tr><th colspan="3"></th><th>Within-run</th><th>Between-run</th></tr></thead><tbody><tr>'
            '<td id="n">' + nominal + '</td><td id="m">' + measured + '</td><td id="re">1.4</td>'
            '<td id="w">' + within + '</td><td id="b">' + between + '</td><td id="z">' + zprime + '</td>'
            '</tr></tbody></table></article>').encode()
        self.text = self.content.decode()
        self.artifact = 'artifact_' + hashlib.sha256(self.content).hexdigest()
        self.reference = identity('source', {'fixture': 'pure205', 'artifact': self.artifact})
        self.calls = []

    def witness(self, text, *, after=0):
        start = self.content.index(text.encode(), after)
        return self.span(start, start + len(text.encode()))

    def span(self, start, end):
        return {'source_ref': self.reference, 'representation': 'original', 'start': start,
                'end': end, 'quote': self.content[start:end].decode()}

    def selector(self, text, *, after=0):
        return {'witness': self.witness(text, after=after), 'number_start': 0, 'number_end': len(text)}

    def synthetic_number(self, role):
        text = self.values[role]
        tag = {'within': 'w', 'between': 'b', 'zprime': 'z', 'nominal': 'n', 'measured': 'm'}[role]
        start = self.content.index(('<td id="' + tag + '">').encode())
        return self.selector(text, after=start)

    def interpretation(self, value, quote=None):
        return {'value': value, 'witnesses': [] if quote is None else [self.witness(quote)]}

    def args(self, *, supported=False):
        precision = []
        for role in ('within', 'between'):
            item = {'number': self.synthetic_number(role), 'quantity_label': self.witness('Precision CV (' + self.unit + ')'),
                'unit': {'value': 'fraction' if self.unit in ('fraction', 'dimensionless', '1') else 'percent',
                         'witness': self.witness(self.unit, after=self.content.index(b'Precision CV ('))},
                **{name: self.interpretation('unknown') for name in RELATIONSHIPS}}
            item['basis'] = self.interpretation(role + '_run', 'Within-run' if role == 'within' else 'Between-run')
            if supported:
                for name, value in (('mean_precision_population', 'same'), ('cv_denominator', 'displayed_measured_mean'), ('recovery_context', 'same')):
                    item[name] = self.interpretation(value, 'Same population and displayed mean denominator')
            precision.append(item)
        return {'source_ref': self.reference, 'source_kind': self.source_kind,
            'context': {field: None for field in CONTEXT_FIELDS}, 'recovery': None, 'relative_bias': None,
            'precision': precision, 'zprime': [{'number': self.synthetic_number('zprime'),
                'quantity_label': self.witness('Z’- factor'),
                'formula_relation': self.interpretation('conventional_zprime', "Z'=1-3*(SDpos+SDneg)/abs(meanpos-meanneg)")}]}

    def read(self, reference, representation):
        assert reference == self.reference and representation == 'original'
        self.calls.append((reference, representation))
        return {'artifact_ref': self.artifact, 'content': self.content}

    def recovery_rows(self, *, control='reporter_standard'):
        args = {'source_ref': self.reference, 'source_kind': self.source_kind,
            **{name: None for name in ('experiment', 'analyte', 'matrix', 'endpoint', 'blank_treatment', 'expected_quantity_basis')},
            'control_kind': self.interpretation(control, None if control == 'unknown' else 'Prepared reporter standard'),
            'applicability': self.interpretation('unknown'), 'spread_kind': self.interpretation('unknown'),
            'nominal': self.synthetic_number('nominal'), 'measured': self.synthetic_number('measured'),
            'measured_spread': None, 'shared_unit': self.witness('nmol'), 'reported_recovery': None,
            'reported_recovery_unit': None}
        sheet = populate_calibration_recovery(read_calibration_recovery_inputs(args, read_source=self.read))
        return rows_for(sheet, self.reference)


def rows_for(sheet, source_ref):
    sheet_ref = identity('source', {'controlled_pure_projection': sheet})
    return _project_saved({'sheet': sheet, 'input_source_ref': source_ref}, sheet_ref, ['recovery', 'relative_bias'])


def bind(args, rows):
    for role in ('recovery', 'relative_bias'):
        row = next(r for r in rows if r['component'] == role)
        args[role] = {'namespace': 'literature_calibration_recovery_cells', 'sheet_ref': row['sheet_ref'], 'component': role}
    def read_component(selector):
        return [deepcopy(r) for r in rows if r['sheet_ref'] == selector['sheet_ref'] and r['component'] == selector['component']]
    return read_component


def run(source, args=None, rows=None):
    args = source.args() if args is None else args
    reader = None if rows is None else bind(args, rows)
    data = read_measurement_validation_inputs(args, read_source=source.read, read_component=reader)
    return data, populate_measurement_validation(data)


def exact(cell, name='exact_value'):
    x = cell[name]
    return None if x is None else Fraction(int(x['numerator']), int(x['denominator']))


def original(row_index=1):
    packet = json.loads(PACKET.read_text())
    content = Path(packet['source']['path']).read_bytes()
    assert hashlib.sha256(content).hexdigest() == packet['source']['sha256']
    s = Source(content=content, source_kind='primary_source')
    row = packet['standard_rows'][row_index]; table = packet['table_witnesses']['Tab2']
    def sw(w):
        assert content[w['start_byte']:w['end_byte']] == w['quote'].encode()
        return s.span(w['start_byte'], w['end_byte'])
    def num(field):
        w = row['field_witnesses'][field]['number']
        return {'witness': sw(w), 'number_start': 0, 'number_end': len(w['quote'])}
    args = {'source_ref': s.reference, 'source_kind': 'primary_source',
        'context': {field: None for field in CONTEXT_FIELDS}, 'recovery': None, 'relative_bias': None,
        'precision': [], 'zprime': []}
    args['context'].update({
        'experiment': s.witness('known NAD(P)H amounts within the linear range were measured',
                                after=packet['paragraphs']['Par32']['start_byte']),
        'analyte': s.witness('NADPH', after=packet['standard_rows'][0]['witness']['start_byte']),
        'matrix': s.witness('20\u2009mM Tris-HCl (pH\u20099.0 for NADH and pH\u20098.0 for NADPH), 200\u2009μM WST-8/8\u2009μM 1-mPMS',
                            after=packet['paragraphs']['Par31']['start_byte']),
        'method': s.witness('Colorimetric WST-8 (450\u2009nm)', after=table['start_byte']),
        'endpoint': s.witness('Formazan absorbance at 450\u2009nm', after=packet['paragraphs']['Par31']['start_byte']),
    })
    args['context']['repetition'] = {'source_ref': s.reference, 'representation': 'original',
        'start': packet['paragraphs']['Par32']['start_byte'], 'end': packet['paragraphs']['Par32']['end_byte'],
        'quote': packet['paragraphs']['Par32']['quote']}
    for role in ('within', 'between'):
        args['precision'].append({'number': num(role + '_run_CV_percent'),
            'quantity_label': s.witness('Precision (%CV)', after=table['start_byte']),
            'unit': {'value': 'percent', 'witness': s.witness('%CV', after=table['start_byte'])},
            **{name: s.interpretation('unknown') for name in RELATIONSHIPS}})
        args['precision'][-1]['basis'] = {'value': role + '_run', 'witnesses': [
            s.witness('Within-run' if role == 'within' else 'Between-run', after=table['start_byte'])]}
    formula = packet['paragraphs']['Par49']
    args['zprime'] = [{'number': num('reported_Zprime'),
        'quantity_label': s.witness('Z’- factor', after=table['start_byte']),
        'formula_relation': {'value': 'conventional_zprime', 'witnesses': [sw(formula)]}}]
    rec = {'source_ref': s.reference, 'source_kind': 'primary_source',
        **{name: None for name in ('experiment', 'analyte', 'matrix', 'endpoint', 'blank_treatment', 'expected_quantity_basis')},
        'control_kind': {'value': 'reporter_standard', 'witnesses': [sw(packet['paragraphs']['Par31'])]},
        'applicability': s.interpretation('unknown'), 'spread_kind': s.interpretation('unknown'),
        'nominal': num('nominal'), 'measured': num('measured'), 'measured_spread': None,
        'shared_unit': s.witness('nmole', after=table['start_byte']),
        'reported_recovery': None, 'reported_recovery_unit': None}
    for name in ('experiment','analyte','matrix','endpoint'):
        rec[name]=deepcopy(args['context'][name])
    rec['expected_quantity_basis']=s.witness('Prepared amount (nmole)',after=table['start_byte'])
    rows = rows_for(populate_calibration_recovery(read_calibration_recovery_inputs(rec, read_source=s.read)), s.reference)
    return s, args, rows, row['fields']


@pytest.mark.parametrize('row_index', range(3))
def test_original_source_six_alternative_precision_models_and_reported_z(row_index):
    s, args, rows, fields = original(row_index)
    data, sheet = run(s, args, rows)
    assert data['pair_unavailable_reasons'] == []
    assert [r['basis'] for r in sheet['precision']] == ['within_run', 'between_run']
    with localcontext() as ctx:
        ctx.prec = 65
        n, m = Decimal(fields['nominal']), Decimal(fields['measured'])
        for role, item in zip(('within', 'between'), sheet['precision']):
            cv = Decimal(fields[role + '_run_CV_percent']) / 100
            independent = ((m-n)**2 + (cv*m)**2) / n**2
            cells = item['cells']; loss = cells['relative_squared_deviation_plugin']
            assert loss['value'] is None and loss['status'] == 'conditional'
            assert loss['interpretation'] == 'conditional_plugin' and loss['origin'] == 'proposed'
            q = exact(loss, 'conditional_exact_value')
            assert abs(Decimal(q.numerator)/Decimal(q.denominator)-independent) < Decimal('1e-61')
            assert loss['conditional_value'] == pytest.approx(float(independent))
            assert cells['relative_rms_percent']['conditional_value'] == pytest.approx(float(100*independent.sqrt()))
            assert loss['contribution_key'] == cells['relative_rms_percent']['contribution_key']
            assert cells['reported_cv']['origin'] == 'reported'
            assert cells['reported_cv']['input_origins'] == ['reported']
            assert cells['cv_fraction']['origin'] == 'derived'
            assert 'cv_denominator_unknown' in loss['unavailable_reasons']
            assert 'mean_precision_population_unknown' in loss['unavailable_reasons']
            assert all('count' not in a for a in loss['assumptions'])
    z = sheet['zprime'][0]['cells']
    assert z['reported_zprime']['value'] == float(fields['reported_Zprime'])
    assert exact(z['control_band_ratio']) == (1-Fraction(fields['reported_Zprime']))/3
    assert z['reported_zprime']['contribution_key'] == z['control_band_ratio']['contribution_key']
    assert sheet['raw_control_zprime']['interpretation'] == 'unimplemented'
    assert sheet['annotation_credit'] is None
    assert 'five consecutive days in triplicate' in data['context']['repetition']['value']
    assert data['context']['analyte']['value']=='NADPH'
    assert data['recovery']['row']['source_meanings']['analyte']=='NADPH'
    assert data['context']['endpoint']['value']=='Formazan absorbance at 450\u2009nm'
    validate_schema(data, measurement_validation_extraction_schema())
    validate_schema(sheet, measurement_validation_sheet_schema())


def test_supported_synthetic_relationships_populate_estimated_population_variance_without_count_division():
    s = Source(); args = s.args(supported=True)
    args['context']['repetition'] = s.witness('Repeated technical readings, count unknown')
    data, sheet = run(s, args, s.recovery_rows())
    cells = sheet['precision'][0]['cells']
    assert cells['relative_squared_deviation_plugin']['value'] == pytest.approx(.00026049834505137914)
    assert cells['relative_squared_deviation_plugin']['conditional_value'] is None
    assert cells['relative_variance_plugin']['interpretation'] == 'estimated_plugin'
    assert cells['relative_variance_plugin']['origin'] == 'proposed'
    assert cells['reported_cv']['origin'] == 'synthetic'
    assert cells['relative_variance_plugin']['input_origins'] == ['synthetic']
    assert 'variance_of_specified_measurement_population' in cells['relative_variance_plugin']['meaning']
    before = deepcopy(data); previous = list(s.calls)
    assert populate_measurement_validation(data) == sheet
    assert data == before and s.calls == previous


@pytest.mark.parametrize('name,value,quote', [
    ('mean_precision_population', 'different', 'Different population'),
    ('cv_denominator', 'other_reported_mean', 'Different population'),
    ('recovery_context', 'different', 'Different population'),
    ('mean_precision_population', 'unknown', None),
    ('cv_denominator', 'unknown', None), ('recovery_context', 'unknown', None)])
def test_relationship_limit_retains_conditional_math_and_native_partials(name, value, quote):
    s = Source(); args = s.args(supported=True)
    args['precision'][0][name] = s.interpretation(value, quote)
    _, sheet = run(s, args, s.recovery_rows())
    loss = sheet['precision'][0]['cells']['relative_squared_deviation_plugin']
    assert loss['value'] is None and loss['conditional_value'] is not None
    assert name + '_' + value in loss['unavailable_reasons']
    assert sheet['precision'][1]['cells']['relative_squared_deviation_plugin']['interpretation'] == 'estimated_plugin'


def test_conflicting_relation_requires_two_distinct_physical_witnesses_and_retains_conditional():
    s = Source(); args = s.args(supported=True)
    args['precision'][0]['cv_denominator'] = {'value': 'conflicting', 'witnesses': [
        s.witness('Same population and displayed mean denominator'), s.witness('Different population')]}
    _, sheet = run(s, args, s.recovery_rows())
    assert 'cv_denominator_conflicting' in sheet['precision'][0]['cells']['relative_squared_deviation_plugin']['unavailable_reasons']
    args['precision'][0]['cv_denominator']['witnesses'].pop()
    with pytest.raises(ExperimentalContractError, match='interpretation_witness_required'):
        run(s, args, s.recovery_rows())


def test_native_source_statistics_need_no_recovery_or_framework_sheet():
    s = Source(); data, sheet = run(s)
    assert data['pair_unavailable_reasons'] == ['recovery_pair_not_supplied']
    assert sheet['precision'][0]['cells']['cv_fraction']['value'] == .008
    assert sheet['zprime'][0]['cells']['reported_zprime']['value'] == .99
    assert sheet['precision'][0]['cells']['relative_squared_deviation_plugin']['value'] is None


@pytest.mark.parametrize('unit,value', [('%CV','0.8'), ('%', '0.8'), ('percent', '0.8'),
                                      ('fraction', '0.008'), ('dimensionless', '0.008'), ('1', '0.008')])
def test_percent_fraction_conversion_is_exact_and_native_units_stay_native(unit, value):
    s = Source(unit=unit, within=value)
    _, sheet = run(s)
    assert exact(sheet['precision'][0]['cells']['cv_fraction']) == Fraction(1,125)
    assert sheet['precision'][0]['cells']['reported_cv']['value'] == float(value)


@pytest.mark.parametrize('mutator,reason', [
    (lambda r: r[1].update(evidence_source_ref='source_'+'2'*24), 'recovery_pair_identity_mismatch'),
    (lambda r: r[1].update(input_measurement_keys=['literature_measurement_'+'2'*24]), 'recovery_pair_dependencies_mismatch'),
    (lambda r: r[1].update(exact_value={'numerator':'0','denominator':'1'}, value=0), 'recovery_pair_exact_identity_mismatch'),
    (lambda r: r[1]['source_meanings'].update(analyte='different analyte'), 'recovery_pair_source_meanings_mismatch'),
    (lambda r: [x.update(control_kind='unknown') for x in r], 'recovery_pair_control_unknown'),
    (lambda r: [x.update(control_kind='enzyme_activity_spike') for x in r], 'enzyme_activity_spike_is_not_reporter_standard'),
    (lambda r: [x.update(unit='nmol/min') for x in r], 'recovery_pair_units_mismatch'),
])
def test_actual_inconsistent_pair_retains_native_partials_with_specific_reason(mutator, reason):
    s = Source(); rows=s.recovery_rows(); mutator(rows)
    data, sheet = run(s, rows=rows)
    assert reason in data['pair_unavailable_reasons']
    assert sheet['precision'][0]['cells']['reported_cv']['value'] == .8
    assert sheet['precision'][0]['cells']['relative_squared_deviation_plugin']['conditional_value'] is None
    assert sheet['zprime'][0]['cells']['reported_zprime']['value'] == .99


def test_different_actual_sheet_and_incomplete_possession_are_not_repaired():
    s = Source(); rows=s.recovery_rows(); rows[1]['sheet_ref']='source_'+'3'*24
    data, _ = run(s, rows=rows)
    assert 'recovery_pair_identity_mismatch' in data['pair_unavailable_reasons']
    args=s.args(); bind(args, s.recovery_rows()); args['relative_bias']=None
    data=read_measurement_validation_inputs(args, read_source=s.read,
        read_component=lambda selector:[r for r in s.recovery_rows() if r['component']==selector['component']])
    assert data['pair_unavailable_reasons']==['recovery_pair_incomplete']


def test_wrong_or_missing_callback_row_fails_instead_of_private_sheet_lookup():
    s=Source(); args=s.args(); rows=s.recovery_rows(); bind(args, rows)
    calls=[]
    def unreceived(selector):
        calls.append(selector); return []
    with pytest.raises(ExperimentalContractError, match='selected_component_not_received'):
        read_measurement_validation_inputs(args, read_source=s.read, read_component=unreceived)
    assert len(calls)==1
    with pytest.raises(ExperimentalContractError, match='selected_component_not_received'):
        read_measurement_validation_inputs(args, read_source=s.read, read_component=lambda selector:[rows[1]])


@pytest.mark.parametrize('wrong', ['re', 'z'])
def test_CV_cannot_borrow_RE_or_Z_numeric_column(wrong):
    s=Source(); args=s.args()
    text='1.4' if wrong=='re' else '0.99'
    args['precision'][0]['number']=s.selector(text, after=s.content.index(('<td id="'+wrong+'">').encode()))
    with pytest.raises(ExperimentalContractError, match='source_quantity_column_mismatch'):
        run(s,args)


def test_Z_cannot_borrow_CV_column_and_wrong_statistic_labels_fail():
    s=Source(); args=s.args(); args['zprime'][0]['number']=s.synthetic_number('within')
    with pytest.raises(ExperimentalContractError, match='source_quantity_column_mismatch'):
        run(s,args)
    args=s.args(); args['precision'][0]['quantity_label']=s.witness('Accuracy (%RE)')
    with pytest.raises(ExperimentalContractError, match='source_statistic_label_mismatch'):
        run(s,args)


def test_table_basis_columns_do_not_swap_within_and_between():
    s=Source(); args=s.args(); args['precision'][0]['basis']=s.interpretation('between_run','Between-run')
    with pytest.raises(ExperimentalContractError, match='source_quantity_column_mismatch'):
        run(s,args)


@pytest.mark.parametrize('printed', ['0.8 nmol', '0.8 ± 0.1 nmol', '0.8 ± 0.1 %/min',
    '0.8 ± 0.1 fraction', '0.8 ± 0.1 nM', '0.8 ± 0.1 %<br/>min−1'])
def test_header_cannot_erase_explicit_incompatible_or_compound_units_after_spread(printed):
    s=Source(within=printed); args=s.args()
    args['precision'][0]['number']=s.selector('0.8', after=s.content.index(b'<td id="w">'))
    with pytest.raises(ExperimentalContractError, match='explicit_precision_unit_mismatch|partial_source_unit'):
        run(s,args)


@pytest.mark.parametrize('printed', ['%/min','%<br/>min−1','%<sup>−1</sup>','percent/min','nonfraction'])
def test_incomplete_unit_selection_is_a_repair_error(printed):
    s=Source(unit=printed); args=s.args()
    selected='fraction' if printed=='nonfraction' else 'percent' if printed.startswith('percent') else '%'
    args['precision'][0]['unit']={'value':'fraction' if selected=='fraction' else 'percent','witness':s.witness(selected)}
    with pytest.raises(ExperimentalContractError, match='partial_source_unit'):
        run(s,args)


def test_unit_or_label_in_another_table_is_not_borrowed():
    first=Source().text
    content=first.replace('</article>', '<table><tr><th>Precision (%CV)</th></tr><tr><td>7.7</td></tr></table></article>').encode()
    s=Source(content=content); args=s.args()
    args['precision'][0]['unit']['witness']=s.witness('%CV',after=s.content.index(b'</table>'))
    with pytest.raises(ExperimentalContractError, match='source_quantity_column_mismatch'):
        run(s,args)


@pytest.mark.parametrize('within', ['-0.8','0','1e400','1e-400'])
def test_negative_zero_and_range_failure_keep_exact_native_facts_and_other_partials(within):
    s=Source(within=within); _, sheet=run(s, s.args(supported=True),s.recovery_rows())
    cells=sheet['precision'][0]['cells']
    assert exact(cells['reported_cv'])==Fraction(within)
    if within=='-0.8':
        assert cells['reported_cv']['value']==-.8
        assert cells['relative_variance_plugin']['value'] is None
        assert 'negative_reported_CV_incompatible' in cells['relative_variance_plugin']['unavailable_reasons']
    elif within=='0':
        assert cells['relative_variance_plugin']['value']==0
        assert cells['relative_squared_deviation_plugin']['value']==cells['relative_bias_squared']['value']
    else:
        assert cells['reported_cv']['value'] is None
        assert 'numerical_model_range' in cells['reported_cv']['unavailable_reasons']
    assert sheet['precision'][1]['cells']['reported_cv']['value']==1.7
    assert sheet['zprime'][0]['cells']['reported_zprime']['value']==.99


@pytest.mark.parametrize('measured', ['0','-8.72'])
def test_nonpositive_mean_keeps_received_bias_and_withholds_CV_population_interpretation(measured):
    s=Source(measured=measured)
    _, sheet=run(s,s.args(supported=True),s.recovery_rows())
    cells=sheet['precision'][0]['cells']
    assert cells['relative_bias_squared']['value'] is not None
    assert cells['relative_variance_plugin']['value'] is None
    assert 'nonpositive_displayed_measured_mean' in cells['relative_variance_plugin']['unavailable_reasons']


@pytest.mark.parametrize('printed,relation', [('&lt;0.8','lt'), ('≤0.8','le'), ('>0.8','gt'), ('≥0.8','ge')])
def test_CV_limits_remain_native_limits_and_do_not_supply_point_precision(printed,relation):
    s=Source(within=printed); args=s.args(supported=True)
    args['precision'][0]['number']=s.selector('0.8',after=s.content.index(b'<td id="w">'))
    _,sheet=run(s,args,s.recovery_rows()); cells=sheet['precision'][0]['cells']
    assert cells['reported_cv']['relation']==relation and cells['reported_cv']['value']==.8
    assert cells['relative_variance_plugin']['value'] is None
    assert 'bounded_precision_plugin_unimplemented' in cells['relative_variance_plugin']['unavailable_reasons']


@pytest.mark.parametrize('printed,token,reason', [('approximately 0.8','0.8','source_approximation_unimplemented'),
    ('0.7–0.9','0.7–0.9','source_range_unimplemented'), ('between 0.7 and 0.9','between 0.7 and 0.9','source_range_unimplemented')])
def test_complete_source_approximations_and_ranges_are_per_quantity_capability_gaps(printed,token,reason):
    s=Source(within=printed); args=s.args(); args['precision'][0]['number']=s.selector(token,after=s.content.index(b'<td id="w">'))
    data,sheet=run(s,args,Source().recovery_rows()); cells=sheet['precision'][0]['cells']
    assert data['precision'][0]['number']['representation_witness']['quote']==printed
    assert cells['reported_cv']['value'] is None
    assert reason in cells['reported_cv']['unavailable_reasons']
    assert cells['relative_bias_squared']['value'] is not None
    assert sheet['precision'][1]['cells']['reported_cv']['value']==1.7
    assert sheet['zprime'][0]['cells']['reported_zprime']['value']==.99


@pytest.mark.parametrize('z', ['-0.5','0','1','1.1'])
def test_reported_Z_negative_valid_and_above_one_incompatible_without_clamping(z):
    s=Source(zprime=z); _,sheet=run(s)
    cells=sheet['zprime'][0]['cells']; assert cells['reported_zprime']['value']==float(z)
    if Fraction(z)>1:
        assert cells['control_band_ratio']['value'] is None
        assert 'zprime_above_one_incompatible_with_formula' in cells['control_band_ratio']['unavailable_reasons']
    else:
        assert exact(cells['control_band_ratio'])==(1-Fraction(z))/3


@pytest.mark.parametrize('printed,relation', [('≤0.9','ge'),('≥0.9','le'),('&lt;0.9','gt'),('>0.9','lt')])
def test_supported_Z_limits_reverse_in_same_statistic_reexpression(printed,relation):
    s=Source(zprime=printed); args=s.args(); args['zprime'][0]['number']=s.selector('0.9',after=s.content.index(b'<td id="z">'))
    _,sheet=run(s,args); ratio=sheet['zprime'][0]['cells']['control_band_ratio']
    assert ratio['relation']==relation and exact(ratio)==Fraction(1,30)


def test_reported_Z_survives_unknown_or_conflicting_formula():
    s=Source(); args=s.args(); args['zprime'][0]['formula_relation']=s.interpretation('unknown')
    _,sheet=run(s,args)
    assert sheet['zprime'][0]['cells']['reported_zprime']['value']==.99
    assert sheet['zprime'][0]['cells']['control_band_ratio']['unavailable_reasons']==['source_formula_unknown']


def test_compatible_repeated_aliases_share_keys_and_do_not_multiply_sections():
    s=Source(); args=s.args(); args['precision'].append(deepcopy(args['precision'][0]))
    alias='source_'+'9'*24
    args['precision'][-1]['number']['witness']['source_ref']=alias
    def source(reference,representation):
        assert reference in (s.reference,alias)
        return {'artifact_ref':s.artifact,'content':s.content}
    data=read_measurement_validation_inputs(args,read_source=source)
    assert len(data['precision'])==2 and len(data['precision'][0]['aliases'])==1
    assert len(populate_measurement_validation(data)['precision'])==2
    args['precision'][-1]['mean_precision_population']=s.interpretation('same','Same population and displayed mean denominator')
    with pytest.raises(ExperimentalContractError,match='duplicate_measurement_meaning_conflict'):
        read_measurement_validation_inputs(args,read_source=source)


def test_equal_numbers_in_distinct_original_fields_are_not_deduplicated():
    s=Source(within='1.7'); data,sheet=run(s)
    assert len(data['precision'])==2
    assert data['precision'][0]['number']['measurement_key']!=data['precision'][1]['number']['measurement_key']
    assert sheet['precision'][0]['cells']['reported_cv']['value']==sheet['precision'][1]['cells']['reported_cv']['value']


def test_clipped_numeric_tokens_and_source_quote_mismatch_are_repair_failures():
    s=Source(within='10.8'); args=s.args(); args['precision'][0]['number']['number_start']=1
    with pytest.raises(ExperimentalContractError,match='partial_source_numeric_token'):
        run(s,args)
    args=s.args(); args['precision'][0]['number']['witness']['quote']='10.9'
    with pytest.raises(ExperimentalContractError,match='source_quote_mismatch'):
        run(s,args)


def test_closed_arguments_and_mutated_retained_numeric_and_identity_fail():
    s=Source(); args=s.args(); args['precision'][0]['number']['value']=.8
    with pytest.raises(ContractError):
        validate_schema(args,measurement_validation_population_schema())
    data,_=run(s)
    wrong=deepcopy(data); wrong['precision'][0]['number']['native_exact_value']['numerator']='999'
    with pytest.raises(ExperimentalContractError,match='number_record_mismatch'):
        populate_measurement_validation(wrong)
    wrong=deepcopy(data); wrong['precision'][0]['number']['measurement_key']='literature_measurement_'+'8'*24
    with pytest.raises(ExperimentalContractError,match='measurement_binding_mismatch'):
        populate_measurement_validation(wrong)


def test_prompt_is_exact_reviewed_detailed_insert_without_sheet_dump():
    assert MEASUREMENT_VALIDATION_TASK==(ARTIFACT/'FINAL_TASK_001.txt').read_text().rstrip('\n')
    assert len(MEASUREMENT_VALIDATION_TASK.split('\n\n'))==5
    assert 'a candidate annotation or public name is not required' in MEASUREMENT_VALIDATION_TASK
    assert 'without an overall reliability grade' not in MEASUREMENT_VALIDATION_TASK
    assert 'source_ref' not in MEASUREMENT_VALIDATION_TASK


@pytest.mark.parametrize('printed', ['NaN', 'Infinity', '-Inf'])
def test_source_nonfinite_representation_is_retained_as_per_quantity_unavailable(printed):
    s=Source(within=printed)
    data,sheet=run(s)
    assert data['precision'][0]['number']['raw_number']==printed
    assert data['precision'][0]['number']['representation_witness']['quote']==printed
    cell=sheet['precision'][0]['cells']['reported_cv']
    assert cell['value'] is None and cell['exact_value'] is None
    assert cell['unavailable_reasons']==['nonfinite_source_statistic_unavailable']
    assert sheet['precision'][1]['cells']['reported_cv']['value']==1.7
    assert sheet['zprime'][0]['cells']['reported_zprime']['value']==.99


def test_derived_variance_float_underflow_preserves_exact_rational_and_finite_total():
    s=Source(within='1e-200')
    _,sheet=run(s,s.args(supported=True),s.recovery_rows())
    cells=sheet['precision'][0]['cells']; variance=cells['relative_variance_plugin']
    assert variance['value'] is None and exact(variance)>0
    assert variance['unavailable_reasons']==['numerical_model_range']
    assert cells['relative_squared_deviation_plugin']['value']>0
    assert cells['relative_rms_percent']['value']>0


@pytest.mark.parametrize('printed', ['>1', '>1.01', '≥1.01', '<1.1'])
def test_Z_formula_does_not_emit_negative_physical_band_ratio(printed):
    s=Source(zprime=printed); args=s.args()
    token=printed.lstrip('>≥<')
    args['zprime'][0]['number']=s.selector(token,after=s.content.index(b'<td id="z">'))
    _,sheet=run(s,args); ratio=sheet['zprime'][0]['cells']['control_band_ratio']
    assert ratio['value'] is None
    assert ratio['unavailable_reasons']
    assert sheet['zprime'][0]['cells']['reported_zprime']['value']==float(token)


@pytest.mark.parametrize('printed,token', [('approximately 0.9','0.9'),('0.8–0.9','0.8–0.9')])
def test_Z_source_capability_gap_does_not_erase_native_CV(printed,token):
    s=Source(zprime=printed); args=s.args()
    args['zprime'][0]['number']=s.selector(token,after=s.content.index(b'<td id="z">'))
    data,sheet=run(s,args)
    assert data['zprime'][0]['number']['representation_witness']['quote']==printed
    assert sheet['zprime'][0]['cells']['reported_zprime']['value'] is None
    assert sheet['precision'][0]['cells']['reported_cv']['value']==.8


def test_clipped_sign_on_complete_range_and_negated_limit_do_not_become_measurements():
    s=Source(within='+0.7–0.9'); args=s.args()
    args['precision'][0]['number']=s.selector('0.7–0.9',after=s.content.index(b'<td id="w">'))
    with pytest.raises(ExperimentalContractError,match='partial_source_numeric_token'):
        run(s,args)
    s=Source(within='not greater than 0.8'); args=s.args()
    args['precision'][0]['number']=s.selector('0.8',after=s.content.index(b'<td id="w">'))
    data,sheet=run(s,args)
    assert data['precision'][0]['number']['relation']=='unresolved'
    assert sheet['precision'][0]['cells']['reported_cv']['value'] is None
    assert sheet['precision'][0]['cells']['reported_cv']['unavailable_reasons']==['source_negated_comparison_unimplemented']
    assert sheet['zprime'][0]['cells']['reported_zprime']['value']==.99


def test_duplicate_conflict_witnesses_via_alias_do_not_supply_two_physical_witnesses():
    s=Source(); args=s.args(); alias='source_'+'7'*24
    witness=s.witness('Same population and displayed mean denominator')
    duplicate={**witness,'source_ref':alias}
    args['precision'][0]['cv_denominator']={'value':'conflicting','witnesses':[witness,duplicate]}
    def read(reference,representation):
        assert reference in (s.reference,alias)
        return {'artifact_ref':s.artifact,'content':s.content}
    with pytest.raises(ExperimentalContractError,match='interpretation_witness_required'):
        read_measurement_validation_inputs(args,read_source=read)


def test_missing_precision_retains_original_possessed_recovery_and_bias_rows():
    s=Source(); args=s.args(); args['precision']=[]
    rows=s.recovery_rows(); data,sheet=run(s,args,rows)
    assert data['recovery']['row']==rows[0] and data['relative_bias']['row']==rows[1]
    assert sheet['precision']==[]
    assert sheet['zprime'][0]['cells']['reported_zprime']['value']==.99


def test_zero_nominal_recovery_failure_does_not_remove_source_precision():
    s=Source(nominal='0'); data,sheet=run(s,rows=s.recovery_rows())
    assert 'recovery_pair_unavailable' in data['pair_unavailable_reasons']
    assert data['recovery']['row']['unavailable_reason']=='nonpositive_nominal'
    assert sheet['precision'][0]['cells']['cv_fraction']['value']==.008


def test_exact_rational_root_display_and_shared_loss_contribution():
    s=Source(nominal='10',measured='10',within='1')
    _,sheet=run(s,s.args(supported=True),s.recovery_rows())
    cells=sheet['precision'][0]['cells']
    assert exact(cells['relative_rms_percent'])==1
    assert cells['relative_squared_deviation_plugin']['contribution_key']==cells['relative_rms_percent']['contribution_key']


@pytest.mark.parametrize('kind', ['retained_extraction','synthetic_fixture'])
def test_source_origins_remain_distinct_from_proposed_arithmetic(kind):
    s=Source(source_kind=kind)
    _,sheet=run(s,s.args(supported=True),s.recovery_rows())
    cells=sheet['precision'][0]['cells']
    assert cells['reported_cv']['origin']==('derived' if kind=='retained_extraction' else 'synthetic')
    assert cells['relative_variance_plugin']['origin']=='proposed'


def test_borrowed_non_table_statistic_label_fails_even_if_bytes_match_elsewhere():
    s=Source(content=b"<p>CV 0.8 percent. Z' 0.99.</p>"); other=Source(content=b'<p>CV percent</p>')
    args={'source_ref':s.reference,'source_kind':'synthetic_fixture',
        'context':{f:None for f in CONTEXT_FIELDS},'recovery':None,'relative_bias':None,
        'precision':[{'number':s.selector('0.8'),'quantity_label':other.witness('CV'),
            'unit':{'value':'percent','witness':s.witness('percent')},
            **{name:s.interpretation('unknown') for name in RELATIONSHIPS}}], 'zprime':[]}
    def read(reference,representation):
        return (s if reference==s.reference else other).read(reference,representation)
    with pytest.raises(ExperimentalContractError,match='borrowed_source_quantity_witness'):
        read_measurement_validation_inputs(args,read_source=read)


def test_markup_attribute_one_cannot_supply_fraction_unit_or_source_number():
    s=Source(unit='fraction'); args=s.args()
    # Select the span count attribute on the same precision header.
    start=s.content.index(b'colspan="2"'); args['precision'][0]['unit']={
        'value':'fraction','witness':s.span(start+9,start+10)}
    with pytest.raises(ExperimentalContractError,match='source_markup_is_not_statistic'):
        run(s,args)
    args=s.args(); args['precision'][0]['number']={
        'witness':s.span(start+9,start+10),'number_start':0,'number_end':1}
    with pytest.raises(ExperimentalContractError,match='source_markup_is_not_statistic'):
        run(s,args)


def test_inline_formatted_complete_percent_unit_remains_supported():
    s=Source(unit='<italic>%</italic>'); args=s.args()
    _,sheet=run(s,args)
    assert sheet['precision'][0]['cells']['cv_fraction']['value']==.008


def test_selected_digits_inside_numeric_entity_do_not_manufacture_source_measurement():
    s=Source(within='&#56;'); args=s.args()
    args['precision'][0]['number']=s.selector('56',after=s.content.index(b'<td id="w">'))
    with pytest.raises(ExperimentalContractError,match='partial_source_entity'):
        run(s,args)


@pytest.mark.parametrize('printed,token', [('about <0.8','0.8'),('approximately 0.8','approximately 0.8'),
    ('≈0.8','≈0.8'),('[0.7, 0.9]','[0.7, 0.9]'),('0.7 to 0.9','0.7 to 0.9')])
def test_complete_alternative_approximation_and_interval_encodings_keep_capability_partials(printed,token):
    s=Source(within=printed);args=s.args()
    args['precision'][0]['number']=s.selector(token,after=s.content.index(b'<td id="w">'))
    data,sheet=run(s,args)
    number=data['precision'][0]['number']
    assert number['representation_witness']['quote']==printed
    assert number['capability_reason'] in ('source_approximation_unimplemented','source_range_unimplemented')
    assert sheet['precision'][0]['cells']['reported_cv']['value'] is None
    assert sheet['zprime'][0]['cells']['reported_zprime']['value']==.99
