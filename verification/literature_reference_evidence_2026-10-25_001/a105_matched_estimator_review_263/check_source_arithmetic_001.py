"""Independent arithmetic on already reviewed original Fig6C cells; not a grader."""
from fractions import Fraction
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2] / 'research/experimental_scoring_review_2026-10-23/a105_matched_estimator_source_260'
selectors = json.loads((SOURCE / 'FIG6C_EXACT_SELECTORS_001.json').read_text())
raw = (SOURCE / 'originals/elife65773_fig6.xlsx').read_bytes()
assert sha256(raw).hexdigest() == selectors[0]['original_sha256']
with zipfile.ZipFile(BytesIO(raw)) as archive:
    member = archive.read('xl/worksheets/sheet2.xml')
assert sha256(member).hexdigest() == selectors[0]['member_sha256']
for selector in selectors:
    assert member[selector['member_byte_start']:selector['member_byte_end']].decode() == selector['exact_xml']
ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
cells = {node.attrib['r']: node.find('s:v', ns).text
         for node in ET.fromstring(member).findall('.//s:sheetData/s:row/s:c', ns)
         if node.find('s:v', ns) is not None and node.get('t') != 's'}
selected = {key: Fraction(cells[key]) for key in ('A2', 'A5', 'B2', 'B5', 'C2', 'C5', 'D2', 'D5')}
dt = selected['A5'] - selected['A2']
loss = selected['C2'] - selected['C5']
nam = selected['D5'] - selected['D2']
adpr = selected['B5'] - selected['B2']
assert (dt, loss, nam, adpr) == (49, 100, Fraction(189, 2), Fraction(52, 5))
values = {
    'reported_coordinate_window_seconds': dt,
    'substrate_loss_uM': loss,
    'nicotinamide_gain_uM': nam,
    'free_ADPR_gain_uM': adpr,
    'chemical_balance_discrepancy_uM': loss - nam,
    'substrate_loss_over_nicotinamide_gain': loss / nam,
    'free_ADPR_gain_over_nicotinamide_gain': adpr / nam,
    'substrate_interval_average_uM_per_s': loss / dt,
    'nicotinamide_interval_average_uM_per_s': nam / dt,
    'substrate_interval_average_uM_per_min': 60 * loss / dt,
    'nicotinamide_interval_average_uM_per_min': 60 * nam / dt,
}
result = {
    'status': 'independent_original_cell_arithmetic_verified',
    'not_an_implemented_population_reader_or_selected_execution': True,
    'source_workbook_sha256': sha256(raw).hexdigest(),
    'member_sha256': sha256(member).hexdigest(),
    'exact_selectors_verified': len(selectors),
    'values': {key: {'numerator': str(value.numerator), 'denominator': str(value.denominator),
                     'display': float(value)} for key, value in values.items()},
    'difference_coefficient_rows_order_S1_S50_N1_N50_A1_A50': [
        [1, -1, 0, 0, 0, 0], [0, 0, -1, 1, 0, 0], [0, 0, 0, 0, -1, 1]],
    'covariance_of_estimates': None,
    'source_mean_standard_errors': None,
    'independent_preparation_count': None,
    'rate_meaning': 'conditional interval average using released coordinates; not initial rate or kcat',
    'sampling_time_relationship': 'preserve reported coordinates; no substitution of unreported zero time',
    'source_positive_joint_covariance_demonstrated': False,
    'A105_complete': False,
    'goal_changed': False,
}
with (HERE / 'ROOT_INDEPENDENT_ARITHMETIC_001.json').open('x') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps({'status': result['status'], 'exact_selectors_verified': len(selectors),
                  'chemical_balance_discrepancy_uM': float(loss - nam),
                  'free_ADPR_fraction': float(adpr / nam)}))
