"""Source-populated review example and arithmetic oracle, NOT a reader implementation."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3

from jsonschema import Draft202012Validator
from gene_annotation_episode.spreadsheet_tools import Workbook

SPEC = importlib.util.spec_from_file_location('proposal275', Path(__file__).with_name('build_proposal_001.py'))
P = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(P)
HERE, CASE = P.HERE, P.CASE
HTML_REF = 'source:elife65773_original_html'
XLSX_REF = 'source:elife65773_original_fig6_xlsx'
html_path = CASE/'originals/elife65773.html'
xlsx_path = CASE/'originals/elife65773_fig6.xlsx'
html_bytes = html_path.read_bytes(); xlsx_bytes = xlsx_path.read_bytes()
original_hashes = {HTML_REF: hashlib.sha256(html_bytes).hexdigest(), XLSX_REF: hashlib.sha256(xlsx_bytes).hexdigest()}
selectors = json.loads((CASE/'FIG6C_EXACT_SELECTORS_001.json').read_text())
selector_by_cell = {row['cell']: row for row in selectors}
workbook = Workbook(xlsx_path)
try:
    layout = workbook.layout()
    sheet, = [row for row in layout['sheets'] if row['name'] == 'Fig6C']
    connection = sqlite3.connect(':memory:')
    workbook.index_strings(connection, layout['shared_strings_part'])
    xml_bytes = workbook.archive.read(sheet['worksheet_part'])
    shared_bytes = workbook.archive.read(layout['shared_strings_part'])
    shared_matches = list(re.finditer(rb'<si(?:\s[^>]*)?>.*?</si>', shared_bytes, re.S))
    xml = workbook.xml(sheet['worksheet_part'])
    cells = {el.get('r'): Workbook.cell(el, connection) for el in xml.iter() if el.tag.rsplit('}',1)[-1] == 'c'}
finally:
    connection.close(); workbook.close()
for row in selectors:
    assert xml_bytes[row['member_byte_start']:row['member_byte_end']].decode() == row['exact_xml']
    assert hashlib.sha256(xml_bytes).hexdigest() == row['member_sha256']
    assert cells[row['cell']]['value'] == row['resolved_value']['value']


def field_text(needle, lo=0, hi=None):
    needle = needle.encode()
    start = html_bytes.index(needle, lo, hi)
    return dict(kind='text', source_ref=HTML_REF, representation='original',
                start=start, end=start+len(needle), quote=needle.decode())


def field_region(lo, hi):
    return dict(kind='text', source_ref=HTML_REF, representation='original',
                start=lo, end=hi, quote=html_bytes[lo:hi].decode())


def field_cell(cell, quote=None):
    text = cells[cell]['value']
    start = 0 if quote is None else text.index(quote)
    end = len(text) if quote is None else start+len(quote)
    return dict(kind='xlsx_cell_slice', source_ref=XLSX_REF, representation='original',
        sheet_key=sheet['sheet_key'], sheet_name=sheet['name'], worksheet_part=sheet['worksheet_part'],
        cell=cell, decoded_start=start, decoded_end=end, quote=text[start:end])


def number(cell):
    field = field_cell(cell)
    return dict(field=field, number_start=0, number_end=len(field['quote']))


def meaning(v, *w): return dict(value=v, witnesses=list(w))
def reasons(**values): return {k: list(values.get(k, [])) for k in P.REASONS}


caption = field_region(186309,187805)
method = field_region(224329,225939)
calibration = field_text('The area under the curve', 222847,224328)
reaction = field_region(175628,177455)
purification = field_region(211330,212043)
assay = {k: None for k in P.D['assay']['properties']}
assay.update(molecule=field_text('Wild-type PARP1',211330,212043),
    accession=field_text('P09874',207583,207815), construct=field_text('Wild-type PARP1',211330,212043),
    expression_host=None, experimental_system=caption,
    conditions=method, intended_change=None, endpoint=caption,
    calibration=field_region(222847,224328), normalization=method,
    arrangement=meaning('single_preparation',method), participants=[
        dict(identity=field_text('PARP1',224329,225939),role='assayed_molecule',presence='present'),
        dict(identity=field_text('Nuc165',224329,225939),role='activator',presence='present'),
        dict(identity=field_text('HPF1',186309,187805),role='partner',presence='absent')])
unit_concentration = field_cell('D1','µM'); unit_time = field_cell('A1','s')
roles_cells = dict(zip(P.ROLES,('C2','C5','D2','D5','B2','B5','A2','A5')))
quantities = {}
for role, cell in roles_cells.items():
    is_time = role.startswith('coordinate')
    coordinate = 'A2' if role.endswith('start') else 'A5'
    quantities[role] = dict(number=number(cell), unit=unit_time if is_time else unit_concentration,
        record=None, analyte=field_cell(cell[0]+'1'), coordinate=field_cell(coordinate),
        measurement_identity=None,
        unit_association=meaning('source_header' if is_time or cell[0]=='D' else 'source_shared_header',
            field_cell('A1' if is_time else 'D1'), *([] if is_time else [caption])),
        reading_meaning=meaning('reported_point', field_cell(cell)),
        concentration_basis=meaning('coordinate' if is_time else 'native_reaction_concentration',
            field_cell('A1') if is_time else method), uncertainty=[])
selection = dict(version='a105_concentration_window_selection_v1',source_ref=XLSX_REF,
    source_kind='primary_source', assay=assay,
    grid=dict(source_ref=XLSX_REF,sheet_key=sheet['sheet_key'],sheet_name='Fig6C',
        worksheet_part=sheet['worksheet_part'],header_row=1,start_row=2,end_row=5,
        coordinate_column='A',columns=dict(substrate='C',total_product='D',fate_product='B')),
    quantities=quantities,
    relationships={r:meaning('supported',caption,method) for r in P.RELATIONS},
    stoichiometry={r:dict(kind='implicit_unit_coefficient',number=None,reaction=reaction,
                         relationship=meaning('supported',reaction,caption))
                   for r in ('substrate','total_product','fate_product')},
    timing=dict(source_meaning=meaning('unknown',field_cell('A1'),method),
                scenario=dict(kind='coordinates_are_elapsed_sampling_times',status='stipulated_sensitivity')),
    covariance_source_ref=None,covariance_material='not_selected',
    evidence=[dict(role='chemical_relation',witness=reaction),dict(role='product_identity',witness=caption),
        dict(role='calibration',witness=field_region(222847,224328)),
        dict(role='timing',witness=method)],requested_cells=P.COMPONENTS)

artifacts = [dict(source_ref=source,representation='original',artifact_ref='artifact:'+sha,sha256=sha)
             for source,sha in original_hashes.items()]
calibration_key = 'dependency:'+P.digest(field_region(222847,224328))


def location(cell):
    s = selector_by_cell[cell]; raw = cells[cell]
    shared = None
    if raw['cell_type']=='s':
        m = shared_matches[int(raw['raw_value'])]
        shared = dict(member=layout['shared_strings_part'], member_sha256=hashlib.sha256(shared_bytes).hexdigest(),start=m.start(),end=m.end())
    return dict(kind='xlsx_cell',source_ref=XLSX_REF,artifact_ref='artifact:'+original_hashes[XLSX_REF],
        representation='original',worksheet_part=sheet['worksheet_part'],member_sha256=hashlib.sha256(xml_bytes).hexdigest(),
        sheet_key=sheet['sheet_key'],sheet_name='Fig6C',cell=cell,xml_start=s['member_byte_start'],xml_end=s['member_byte_end'],
        decoded_start=0,decoded_end=len(raw['value']),shared_string_location=shared)


readings = {}
for role, cell in roles_cells.items():
    token = cells[cell]['value']; q = Fraction(token)
    key = 'source_observation:'+P.digest([original_hashes[XLSX_REF],sheet['worksheet_part'],cell])
    readings[role] = dict(role=role,value=float(q),exact_value=P.exact(q),
        unit='s' if role.startswith('coordinate') else 'uM',raw_number=token,
        raw_unit='s' if role.startswith('coordinate') else 'µM',unit_multiplier=P.exact(1),
        relation='eq',status='point',approximate=False,origin='reported',owner_key=key,
        physical_owner_key=None,dependency_keys=[key]+([] if role.startswith('coordinate') else [calibration_key]),
        locations=[location(cell)],reported_uncertainty=[],reasons=reasons())
coefficients = {r:dict(value=1.0,exact_value=P.exact(1),origin='implicit_chemical_notation',
                      dependency_keys=['chemical_relation:'+P.digest(reaction)],reasons=reasons())
                for r in selection['stoichiometry']}
extraction = dict(version='a105_concentration_window_extraction_v1',selection=selection,
    quantities=readings,coefficients=coefficients,covariance=None,source_artifacts=artifacts)
inputs = dict(version='a105_concentration_window_calculation_inputs_v1',extraction_digest=P.digest(extraction),
    source_kind='primary_source',context=deepcopy(assay),quantities=deepcopy(readings),coefficients=deepcopy(coefficients),
    relationships=deepcopy(selection['relationships']),timing=deepcopy(selection['timing']),covariance=None,
    covariance_material='not_selected',requested_cells=P.COMPONENTS,source_artifacts=deepcopy(artifacts))
u = {r:Fraction(cells[c]['value']) for r,c in roles_cells.items()}
S = u['substrate_start']-u['substrate_end']; T=u['total_product_end']-u['total_product_start']; F=u['fate_product_end']-u['fate_product_start']
dt=u['coordinate_end']-u['coordinate_start']
values = {**u,'substrate_loss':S,'total_product_gain':T,'fate_product_gain':F,'coordinate_span':dt,
    'chemical_discrepancy':S-T,'chemical_ratio':S/T,'chemical_relative_discrepancy':S/T-1,
    'fate_fraction':F/T,'substrate_depletion_fraction':S/u['substrate_start']}
for name, expected in dict(substrate_loss=Fraction(100), total_product_gain=Fraction(189,2),
    fate_product_gain=Fraction(52,5), coordinate_span=Fraction(49), chemical_discrepancy=Fraction(11,2),
    chemical_ratio=Fraction(200,189), fate_fraction=Fraction(104,945)).items():
    assert values[name] == expected
contribution_key='contribution:'+P.digest([original_hashes[XLSX_REF],sheet['worksheet_part'],2,5,'noHPF1'])
cells_out=[]
for name,definition in P.DEFINITIONS.items():
    role_deps=definition['operands']
    deps=list(dict.fromkeys(k for role in role_deps for k in readings[role]['dependency_keys']))
    value=values.get(name); conditional=None; status='populated'; why=reasons()
    if name.startswith('source_interval_average') and not name.endswith('_variance'):
        status='unavailable'; why=reasons(source=['timing_meaning_unknown'])
    elif name.startswith('scenario_interval_average'):
        conditional={'substrate':S,'total_product':T,'fate_product':F}[name.removeprefix('scenario_interval_average_')]*60/dt
        status='conditional_scenario'
    elif definition['covariance_required']:
        status='unavailable'; why=reasons(selection=['covariance_not_selected'])
        if name.startswith('source_interval_average'): why['source'].append('timing_meaning_unknown')
    assert value is not None or conditional is not None or status=='unavailable'
    cells_out.append(dict(component=name,value=float(value) if value is not None else None,
        exact_value=P.exact(value) if value is not None else None,
        conditional_value=float(conditional) if conditional is not None else None,
        conditional_exact_value=P.exact(conditional) if conditional is not None else None,
        status=status,unit=definition['unit'],formula=definition['formula'],meaning=definition['meaning'],
        origin='reported' if name in P.ROLES else 'calculated',operand_roles=role_deps,
        dependency_keys=deps,contribution_key=contribution_key,approximate=False,bound='none',threshold=None,
        outside_physical_fraction_range=bool(name in ('fate_fraction','substrate_depletion_fraction') and value is not None and not 0<=value<=1),
        negative_observed_change=bool(name in ('substrate_loss','total_product_gain','fate_product_gain') and value is not None and value<0),
        timing_stipulation='coordinates_are_elapsed_sampling_times' if conditional is not None else None,
        uncertainty_method='not_available' if definition['covariance_required'] else 'not_applicable',reasons=why))
sheet_out = dict(version='a105_concentration_window_sheet_v1',axis='A105',section='observed_concentration_window',
    cells=cells_out,assertion_resolution='total_chemical_extent_and_selected_product_fate',
    relationship_meanings={k:v['value'] for k,v in selection['relationships'].items()},source_timing_meaning='unknown',
    source_artifacts=artifacts,estimate_bindings=[{k:r[k] for k in ('role','owner_key','physical_owner_key','dependency_keys')}
        for r in readings.values()],derived_covariance=None,limits=[
        'observed_source_scale_not_blank_corrected','no_unique_molecular_attribution','unknown_calibration_systematics',
        'no_independent_replication_inferred','shared_derived_contribution','interval_average_not_initial_or_turnover_rate',
        'no_cumulative_amount_from_initial_volume','selected_integration_unimplemented',
        'general_reliability_compilation_unfinished','no_target_transfer_or_W05'],annotation_credit=None)
assert all(row['value'] is None for row in cells_out if row['component'].startswith('source_interval_average'))
assert all(row['value'] is None and row['conditional_value'] is not None for row in cells_out
           if row['component'].startswith('scenario_interval_average'))
assert all(row['origin'] != 'reported' for row in cells_out if row['component'] not in P.ROLES)

# This checks selected source custody. It is not validation of the scientific
# interpretations and does not invoke the proposed reader or calculator.
field_count=0
def check_fields(node):
    global field_count
    if isinstance(node,dict):
        if node.get('kind')=='text' and 'quote' in node:
            assert html_bytes[node['start']:node['end']].decode()==node['quote']; field_count+=1
        elif node.get('kind')=='xlsx_cell_slice':
            assert cells[node['cell']]['value'][node['decoded_start']:node['decoded_end']]==node['quote']; field_count+=1
        else:
            for child in node.values(): check_fields(child)
    elif isinstance(node,list):
        for child in node: check_fields(child)
check_fields(selection)

examples={'SELECTION':selection,'EXTRACTION':extraction,'CALCULATION_INPUTS':inputs,'SHEET':sheet_out}
for kind,value in examples.items():
    Draft202012Validator(P.resource(kind.lower())).validate(value)
    P.write('SOURCE_'+kind+'_PROPOSAL_001.json',value)

# Entirely synthetic positive covariance fixture. Its numbers are deliberately
# distinct from the paper and have no evidentiary role for that paper.
su=[Fraction(x) for x in (120,60,4,61,2,14,3,33)]
v=[x/Fraction(100) for x in su[:6]]+[Fraction(0),Fraction(0)]
C=[[v[i]*v[j]+(Fraction(1,4) if i==j and i<6 else Fraction(1,100) if i==j else 0)
    for j in range(8)] for i in range(8)]
covdoc=dict(version='a105_concentration_window_covariance_v1',roles=list(P.ROLES),
    owner_keys=['synthetic:'+r for r in P.ROLES],units=['uM']*6+['s']*2,
    dependency_keys=[['synthetic:'+r,'synthetic:shared_scale'] if i<6 else ['synthetic:'+r]
                     for i,r in enumerate(P.ROLES)],covariance=[[float(x) for x in row] for row in C],
    basis='joint_covariance_of_selected_estimates',variance_status='known',origin='synthetic',
    derivation='synthetic_model',systematic_coverage='included_as_declared')
Draft202012Validator(P.resource('covariance_document')).validate(covdoc)
bS=[1,-1,0,0,0,0,0,0]; bT=[0,0,-1,1,0,0,0,0]; bF=[0,0,0,0,-1,1,0,0]
bD=[Fraction(a)-Fraction(b) for a,b in zip(bS,bT)]
sx=su[0]-su[1];ty=su[3]-su[2];fz=su[5]-su[4]
gR=[Fraction(a)/ty-sx*Fraction(b)/(ty*ty) for a,b in zip(bS,bT)]
gF=[Fraction(a)/ty-fz*Fraction(b)/(ty*ty) for a,b in zip(bF,bT)]
def quadratic(g): return sum(g[i]*C[i][j]*g[j] for i in range(8) for j in range(8))
synthetic_expected=dict(status='synthetic_arithmetic_fixture_only',operands=[P.exact(x) for x in su],
    construction='diag(1/4 for first six,1/100 for final two)+v*v^T; v=(first six operands)/100,0,0',
    covariance_exact=[[P.exact(x) for x in row] for row in C],
    expected=dict(chemical_discrepancy=P.exact(sx-ty),chemical_discrepancy_variance=P.exact(quadratic(bD)),
                  chemical_ratio=P.exact(sx/ty),chemical_ratio_variance=P.exact(quadratic(gR)),
                  fate_fraction=P.exact(fz/ty),fate_fraction_variance=P.exact(quadratic(gF))),
    no_paper_uncertainty_inferred=True)
P.write('SYNTHETIC_COVARIANCE_DOCUMENT_001.json',covdoc)
P.write('SYNTHETIC_COVARIANCE_ORACLE_001.json',synthetic_expected)
P.write('SOURCE_SELECTOR_MAP_001.json',dict(original_hashes=original_hashes,sheet=sheet,
    selected_cells=[selector_by_cell[c] for c in ('A1','B1','C1','D1','A2','B2','C2','D2','A5','B5','C5','D5')],
    all_original_cell_selectors_verified=len(selectors),source_fields_verified=field_count,
    source_paragraph_locations=[dict(start=175628,end=177455),dict(start=186309,end=187805),
        dict(start=222847,end=224328),dict(start=224329,end=225939),dict(start=211330,end=212043),
        dict(start=207583,end=207815),dict(start=207815,end=208010)],
    caveat='Workbook/HTML custody and arithmetic only; source-supported meanings require root review.'))
P.write('PROPOSAL_CHECKS_001.json',dict(status='review_artifacts_checked_not_production',
    valid_resource_schemas=5,valid_source_examples=4,valid_synthetic_covariance_documents=1,
    original_selectors_checked=len(selectors),source_fields_checked=field_count,
    independent_fraction_arithmetic=True,production_functions_run=False,selected_operation_run=False,
    scientific_model_run=False))
print(json.dumps({'status':'source_fixture_and_oracle_created_not_production',
    'source_fields_checked':field_count,'source_examples':len(examples),'native_selectors_checked':len(selectors)}))
