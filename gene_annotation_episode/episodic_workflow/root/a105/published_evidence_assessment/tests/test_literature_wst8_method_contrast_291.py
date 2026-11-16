"""Case167 original-source Table 3 comparison; no invented common assay model."""
from copy import deepcopy
import hashlib
from pathlib import Path
import re
from gene_annotation_episode.episodic_workflow.root.a105.domain import identity
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_comparison_inputs import read_measurement_comparison_inputs, compile_measurement_comparison_inputs
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_comparison_calculations import populate_measurement_comparison
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_measurement_comparison_components_258 import source_fixture
ORIGINAL = Path(__file__).resolve().parents[6] / 'research/experimental_scoring_review_2026-10-23/a105_calibration_primary_case_167/source/PMC6454709.xml'
SHA256 = '86896c47556f7eeef975856dbbe2d3bab3b6143b91d1f826078e29771761b698'

def selection_from_original():
    content = ORIGINAL.read_bytes()
    assert hashlib.sha256(content).hexdigest() == SHA256
    text = content.decode()
    reference = identity('source', {'original': SHA256, 'case': 'wst8_method_contrast_291'})
    artifact = 'artifact_' + SHA256

    def witness(token, container=None, occurrence=0):
        if container is None:
            start = text.index(token)
        else:
            base = text.index(container)
            start = base
            for _ in range(occurrence + 1):
                start = text.index(token, start)
            assert start < base + len(container)
        return {'source_ref': reference, 'representation': 'original', 'start': len(text[:start].encode()), 'end': len(text[:start + len(token)].encode()), 'quote': token}

    def fragment(tag, identifier):
        match = re.search('<' + tag + '\\b[^>]*\\bid="' + identifier + '"[^>]*>.*?</' + tag + '>', text, re.S)
        assert match is not None
        return match.group()
    table, wst, uv = (fragment('table-wrap', 'Tab3'), fragment('p', 'Par33'), fragment('p', 'Par39'))
    plate = fragment('p', 'Par29')
    statistics = fragment('p', 'Par43')
    rows = re.findall('<tr(?:\\s[^>]*)?>.*?</tr>', table, re.S)
    method_rows = rows[-2:]
    heading = 'Enzyme activity (nmole/min/μg)'

    def meaning(value, quote=None, container=None):
        return {'value': value, 'witnesses': [] if quote is None else [witness(quote, container)]}
    selected, _, _ = source_fixture(table=True)
    selected.update(source_ref=reference, source_kind='primary_source', common_model=None, covariance_source_refs=[], optical=None)
    selected['assertion'] = {'question': 'quantitative_activity', 'molecule': witness('G6PD', table), 'functional_assertion': witness('NAD(P)H produced per minute per microgram of protein', wst)}
    selected['requested_cells'] = ['native_left', 'native_right', 'converted_left', 'converted_right', 'protocol_difference', 'protocol_ratio', 'common_ratio', 'difference_variance', 'combined_estimate']
    for role, row, protocol, value, spread in (('left', method_rows[0], wst, '12.51', '0.36'), ('right', method_rows[1], uv, '14.88', '0.39')):
        q = deepcopy(selected['quantities'][role])
        q['layout'] = 'table'
        q['record'] = None
        method = 'Colorimetric WST-8 (450\u2009nm)' if role == 'left' else 'UV-spectrophotometry (340\u2009nm)'
        q['row_label'] = witness(method, row)
        rate_cell = next((c for c in re.findall('<td[^>]*>.*?</td>', row, re.S) if value in c))
        q['number'] = {'witness': witness(rate_cell, row), 'number_start': rate_cell.index(value), 'number_end': rate_cell.index(value) + len(value)}
        q['quantity_label'] = witness('Enzyme activity', table)
        q['unit'] = witness('nmole/min/μg', table)
        q['quantity_kind'] = meaning('specific_activity', heading, table)
        q['estimator_scale'] = meaning('reported_mean', 'mean\u2009±\u2009standard deviation', statistics)
        q['semantics'] = meaning('reported_point_estimate', rate_cell, row)
        q['qualification'] = meaning('reported_point', rate_cell, row)
        q['normalization'] = meaning('protein_mass', 'per microgram of protein', protocol)
        q['subject'] = {field: None for field in q['subject']}
        q['subject']['molecule'] = witness('G6PD', protocol)
        q['subject']['organism'] = witness('human', fragment('p', 'Par28'))
        q['assay'] = {field: None for field in q['assay']}
        q['assay']['assay'] = witness(method, row)
        q['assay']['preparation'] = witness('Purified G6PD', table)
        q['assay']['substrates'] = witness('500\u2009μM G6P, 200\u2009μM NADP', protocol)
        q['assay']['conditions'] = witness(protocol, protocol)
        q['assay']['direct_endpoint'] = witness('WST-8', wst) if role == 'left' else witness('NAD(P)H absorption at 340\u2009nm', uv)
        q['assay']['inferred_quantity'] = witness('NAD(P)H produced per minute per microgram of protein', protocol)
        q['assay']['denominator'] = witness('microgram of protein', protocol)
        q['assay']['additional_differences'] = witness(plate, plate) if role == 'left' else witness(uv, uv)
        q['assay']['sampling_unit'] = witness('triplicate', statistics)
        q['physical_identity'] = None
        q['dependency_witnesses'] = []
        q['uncertainty'] = {'statistic': meaning('sd', 'standard deviation', statistics), 'magnitude': {'witness': witness(rate_cell, row), 'number_start': rate_cell.index(spread), 'number_end': rate_cell.index(spread) + len(spread)}, 'interval': None, 'confidence_level': None, 'unit': None, 'unit_relationship': meaning('same_as_estimate', heading, table), 'count': None, 'repetition_basis': meaning('unknown'), 'estimate_basis': meaning('unknown')}
        selected['quantities'][role] = q
    for role in ('epsilon_signal', 'epsilon_nuisance', 'nuisance'):
        selected['quantities'][role] = None
    relationships = dict(construct='unknown', preparation='unknown', preparation_target='unknown', protocol='additional_differences', endpoint='same_quantity', denominator='same_basis_supported', functional_bearing='same_quantitative_assertion', attribution='unknown', sampling='unknown', systematic_coverage='unknown', left_validity='identified_unresolved_interference', right_validity='unknown', left_readout_isolation='unknown', right_readout_isolation='unknown')
    support = {'protocol': ('0.1\u2009μg G6PD enzyme', wst), 'endpoint': ('NAD(P)H produced per minute per microgram of protein', wst), 'denominator': (heading, table), 'functional_bearing': ('NAD(P)H produced per minute per microgram of protein', wst), 'left_validity': ('formazan', fragment('p', 'Par31'))}
    selected['relationships'] = {name: meaning(value, *(support[name] if name in support else ())) for name, value in relationships.items()}
    selected['relationships']['protocol']['witnesses'] = [witness('0.1\u2009μg G6PD enzyme', wst), witness('0.5\u2009μg G6PD enzyme', uv), witness('150\u2009μL', plate), witness('1\u2009mL', uv)]
    selected['common_quantity']['label'] = witness('NAD(P)H produced per minute per microgram of protein', wst)
    selected['common_quantity']['unit'] = 'umol/min/mg'
    for role in ('left', 'right'):
        protocol = wst if role == 'left' else uv
        selected['common_quantity'][role + '_conversion'] = {'kind': 'identity', 'direction': meaning('same_direction_supported', 'NAD(P)H produced', protocol), 'support_status': meaning('supported', 'NAD(P)H produced per minute per microgram of protein', protocol), 'reaction': None, 'endpoint_species': witness('NAD(P)H', protocol), 'common_species': witness('NAD(P)H', wst), 'endpoint_coefficient': None, 'common_coefficient': None}

    def read_source(source_ref, representation):
        assert (source_ref, representation) == (reference, 'original')
        return {'artifact_ref': artifact, 'content': content}
    return (selected, read_source)

def test_original_wst8_uv_reported_protocol_contrast_without_common_correction():
    selected, read_source = selection_from_original()
    extraction = read_measurement_comparison_inputs(selected, read_source=read_source)
    sheet = populate_measurement_comparison(compile_measurement_comparison_inputs(extraction))
    cells = {row['component']: row for row in sheet['cells']}
    assert cells['native_left']['value'] == 12.51
    assert cells['native_right']['value'] == 14.88
    assert cells['converted_left']['value'] == 12.51
    assert cells['converted_right']['value'] == 14.88
    assert cells['protocol_ratio']['exact_value'] == {'numerator': '417', 'denominator': '496'}
    assert cells['protocol_difference']['exact_value'] == {'numerator': '-237', 'denominator': '100'}
    assert cells['common_ratio']['value'] is None
    assert 'protocols_not_matched' in cells['common_ratio']['reasons']['relationship']
    assert cells['difference_variance']['value'] is None
    assert cells['combined_estimate']['value'] is None
    assert extraction['quantities']['left']['value']['canonical_unit'] == 'umol/min/mg'
    assert extraction['quantities']['left']['reported_uncertainty']['statistic'] == 'sd'
    assert extraction['quantities']['right']['reported_uncertainty']['statistic'] == 'sd'
    assert sheet['annotation_credit'] is None


