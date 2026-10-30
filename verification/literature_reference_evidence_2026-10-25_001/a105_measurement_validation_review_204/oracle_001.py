"""Root independent displayed-standard arithmetic; no production imports."""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal, localcontext
import hashlib
import json
import time

OUT = Path(__file__).resolve().parent
PACKET = OUT.parent / 'a105_common_scoring_gap_review_200/SOURCE_PACKET_001.json'
data = json.loads(PACKET.read_text())
source = Path(data['source']['path']).read_bytes()
assert hashlib.sha256(source).hexdigest() == data['source']['sha256']
anchors = []


def check_witnesses(value):
    if isinstance(value, dict):
        if {'path', 'sha256', 'start_byte', 'end_byte', 'quote'} <= set(value):
            assert value['path'] == data['source']['path']
            assert value['sha256'] == data['source']['sha256']
            assert source[value['start_byte']:value['end_byte']] == value['quote'].encode()
            anchors.append((value['start_byte'], value['end_byte']))
        else:
            for child in value.values():
                check_witnesses(child)
    elif isinstance(value, list):
        for child in value:
            check_witnesses(child)


check_witnesses(data)
image = Path(data['visual_fit']['path']).read_bytes()
assert hashlib.sha256(image).hexdigest() == data['visual_fit']['sha256']


def exact(q):
    return {'numerator': str(q.numerator), 'denominator': str(q.denominator)}


def decimal(q):
    return Decimal(q.numerator) / Decimal(q.denominator)


rows = []
with localcontext() as ctx:
    ctx.prec = 60
    for row in data['standard_rows']:
        f = row['fields']
        nominal, measured = Fraction(f['nominal']), Fraction(f['measured'])
        r = measured / nominal
        result = {'nominal_nmol': str(nominal), 'measured_nmol': str(measured),
                  'recovery': float(r), 'relative_bias': float(r - 1),
                  'reported_zprime': f['reported_Zprime'],
                  'scientific_status': 'conditional arithmetic only; source CV-to-displayed-mean population relation unresolved'}
        for basis in ('within_run', 'between_run'):
            cv = Fraction(f[basis + '_CV_percent']) / 100
            bias_squared = (r - 1) ** 2
            relative_variance = (cv * r) ** 2
            loss = bias_squared + relative_variance
            dn, dm, dc = Decimal(f['nominal']), Decimal(f['measured']), Decimal(f[basis + '_CV_percent']) / 100
            independent = ((dm - dn) ** 2 + (dc * dm) ** 2) / dn**2
            assert abs(decimal(loss) - independent) < Decimal('1e-57')
            result[basis] = {'reported_cv_fraction': float(cv),
                             'conditional_bias_squared': float(bias_squared),
                             'conditional_relative_variance': float(relative_variance),
                             'conditional_relative_squared_deviation': float(loss),
                             'exact_conditional_loss': exact(loss),
                             'conditional_relative_rms_percent': str(100 * independent.sqrt())}
        z = Fraction(f['reported_Zprime'])
        result['same_reported_z_control_band_ratio'] = float((1 - z) / 3)
        rows.append(result)
    slope, intercept = Fraction(data['visual_fit']['slope']), Fraction(data['visual_fit']['intercept'])
    # Same calibration applied to a matched pair: intercept cancels exactly.
    # Values below are explicit synthetic signals, not paper observations.
    As, Ab = Fraction('0.5'), Fraction('0.1')
    separate = (As - intercept) / slope - (Ab - intercept) / slope
    net = (As - Ab) / slope
    assert separate == net
    intercept_amount = intercept / slope
    consequences = {'same_calibration_intercept_cancels_exactly': True,
                    'signal_example_origin': 'synthetic algebra check only',
                    'intercept_equivalent_nmol': float(intercept_amount),
                    'double_subtraction_error_percent_relative_to_displayed_8_6': float(-100 * intercept_amount / Fraction('8.6')),
                    'double_subtraction_error_percent_relative_to_LLOQ_0_4': float(-100 * intercept_amount / Fraction('.4'))}

result = {'time': time.time(), 'unique_original_byte_anchors_checked': len(set(anchors)),
          'source_sha256': data['source']['sha256'], 'native_figure_hash_verified': True,
          'rows': rows, 'calibration_algebra': consequences,
          'limitations': ['No loss interpreted as source-reported MSE or functional-confidence probability.',
                          'Within/between precision are separate bases and are never added.',
                          'No product-rate/coupling observation or population relationship fabricated.',
                          'No production module, provider, model, episode or controller used.']}
with (OUT / 'ROOT_ORACLE_001.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result, indent=2))
