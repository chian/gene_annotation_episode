"""One-case research extraction and independent arithmetic, no production imports."""
from pathlib import Path
from decimal import Decimal, getcontext
from fractions import Fraction
import hashlib, json, math, re, xml.etree.ElementTree as ET

BASE=Path(__file__).resolve().parent
SRC=BASE/'source/PMC6454709.xml'
raw=SRC.read_bytes(); tree=ET.fromstring(raw)
getcontext().prec=45

def save(name,obj): (BASE/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def byte_witness(selector,token=None):
    element=tree.find(selector)
    if element is None:raise ValueError(selector)
    # Original XML is kept exact; semantic XPath is paired with a byte-exact anchor.
    ident=element.get('id')
    if ident:
        marker=('id="'+ident+'"').encode(); mid=raw.index(marker)
        start=raw.rfind(b'<',0,mid); end=raw.index(('</'+element.tag+'>').encode(),mid)+len(element.tag)+3
    else:raise ValueError('id required')
    quote=raw[start:end].decode()
    out={'file':'source/PMC6454709.xml','sha256':hashlib.sha256(raw).hexdigest(),
         'xpath':selector,'utf8_byte_start':start,'utf8_byte_end':end,'exact_xml':quote}
    assert raw[start:end].decode()==quote
    return out

witnesses={name:byte_witness(f'.//*[@id="{name}"]') for name in ['Par27','Par28','Par29','Par31','Par32','Par33','Par35','Par36','Par37','Par38','Par39','Par43','Par48','Par49','Par50','Par51','Par53','Par55','Par64','Tab1','Tab2','Tab3','Tab4','Tab6']}
save('source_witnesses.json',witnesses)

def cell(tid,row,col):
    t=tree.find(f'.//table-wrap[@id="{tid}"]')
    x=list(list(t.iter('tr'))[row])[col]
    text=''.join(x.itertext())
    return {'table':tid,'row_index_including_header_zero_based':row,'cell_index_zero_based':col,
            'xpath':f'.//table-wrap[@id="{tid}"]//tr[{row+1}]/*[{col+1}]',
            'original_cell_text':text,'original_cell_xml':ET.tostring(x,encoding='unicode'),
            'table_witness':tid}
# These indices explicitly include header rows and honor original rowspans.
std=[]
for row,nom,meas in [(5,'4.3','4.39'),(6,'8.6','8.72'),(7,'12.9','12.98')]:
    # The first NADPH row includes the analyte cell; next two use rowspans.
    start=1 if row==5 else 0
    a=cell('Tab2',row,start);b=cell('Tab2',row,start+1)
    assert a['original_cell_text']==nom and b['original_cell_text']==meas
    std.append({'analyte':'NADPH','nominal_nmol':nom,'measured_nmol':meas,
        'nominal_witness':a,'measured_witness':b,
        'reported_relative_error_percent':cell('Tab2',row,start+2),
        'reported_within_run_cv_percent':cell('Tab2',row,start+3),
        'reported_between_run_cv_percent':cell('Tab2',row,start+4),
        'reported_z_prime':cell('Tab2',row,start+5)})
spikes=[]
for row,name in [(2,'GDH'),(3,'G6PD')]:
    assert cell('Tab4',row,0)['original_cell_text']==name
    spikes.append({'enzyme':name,'expected_amount_rate':cell('Tab4',row,1),
        'measured_amount_rate_mean_sd':cell('Tab4',row,2),
        'reported_recovery_percent_mean_sd':cell('Tab4',row,3),
        'unit':'nmole/min','matrix':'1.5 uL fetal bovine serum; standard assay total150 uL if inherited',
        'spike_mass_ug':'1' if name=='GDH' else '0.2','replicates':3,
        'replicate_independence':'not established','blank':'FBS rate subtracted, individual rates unreported',
        'expected_rate_derivation':'unreported in this original article',
        'meaning':'observed net enzyme-activity recovery; reporter gain and enzyme modulation not separated'})
save('selected_operands.json',{'version':'research_case167_operands_v1','axis':'A105',
 'production_operation':False,'doi':'10.1186/s12858-019-0108-1','pmcid':'PMC6454709',
 'standards':{'identity':'NADPH purchased from Sigma-Aldrich','unit':'nmole',
  'conditions':'150uL;20mM Tris-HCl pH8.0;200uM WST-8/8uM1-mPMS',
  'matrix_linkage':'same NADPH detection chemistry; assay substrate, oxidized cofactor, MgCl2, serum or lysate absent from standard recipe',
  'repetition':'triplicate on five consecutive days; independent preparations not established',
  'selected_rows':std},
 'calibration_fit':{'origin':'source-reported fit, visually read from retained Fig3.png panelB inset',
    'slope':'0.0999','slope_unit':'absorbance/nmole','intercept':'0.0166','intercept_unit':'absorbance',
    'r_squared':'0.9994','range_nmole':['0','19'],'LLOQ_nmole':'0.4','LOD_nmole':'0.29',
    'residuals':None,'slope_uncertainty':None,'point_data':None,
    'figure_custody':'source/figure_custody.json','raw_point_availability':'datasets available from author on reasonable request; not retrieved'},
 'functional_assay':{'molecule':'human G6PD','source_organism':'Homo sapiens','genotype':None,
    'expression_host':'E. coli BL21(DE3)','construct_boundaries':None,
    'reagent_role':'WST-8/1-mPMS reports NADPH through formazan, not enzyme identity or sugar-product identity',
    'conditions_WST8':'150uL;25C;20mMTris pH8;10mMMgCl2;500uMG6P;200uMNADP+;200uMWST8;0.1ugG6PD;10min',
    'reported_specific_activity_nmol_min_ug':{'mean':'12.51','sd':'0.36','witness':'Tab3'},
    'comparison_UV':{'specific_activity_mean':'14.88','specific_activity_sd':'0.39','unit':'nmole/min/ug',
      'conditions':'1mL;25C;20mMTris pH8;10mMMgCl2;500uMG6P;200uMNADP+;0.5ugG6PD;10min;340nm',
      'epsilon_M_inverse_cm_inverse':'6220','epsilon_kind':'conventional extinction conversion, not measured recovery'},
    'measured_entity':'NADPH-linked formazan absorbance at450nm,600nm reference',
    'assertion':'G6P-dependent NADP+ reduction in the human-G6PD preparation',
    'sugar_product_identification':None,'active_molecule_fraction':None,'quantitative_contaminant_activity':None},
 'FBS_enzyme_spikes':spikes,
 'unpopulated':{'same_matrix_reporter_gain':None,'sample_to_blank_ratio':None,
   'independent_preparation_count':None,'sugar_product_attribution_fraction':None,
   'same_endpoint_condition_response_excluding_intended_variable':None,
   'known_sampling_variance':None,'normal_observation_model':None,'overall_experimental_reliability':None}})

# Independent calculations: exact rational decimals versus Decimal division.
def ratio(a,b):
    f=Fraction(a)/Fraction(b); d=Decimal(a)/Decimal(b)
    assert abs(float(f)-float(d))<1e-14
    return {'fraction_numerator':str(f.numerator),'fraction_denominator':str(f.denominator),
            'decimal':str(d),'verification':'Fraction and Decimal agree to1e-14'}
checks={'NADPH_standard_recovery':[{**{'nominal_nmol':r['nominal_nmol'],'measured_nmol':r['measured_nmol']},
 'recovery':ratio(r['measured_nmol'],r['nominal_nmol']),
 'relative_error_percent':str(100*(Decimal(r['measured_nmol'])/Decimal(r['nominal_nmol'])-1))} for r in std],
 'FBS_activity_recovery':{name:{'ratio':ratio(obs,exp),'excess_rate_nmol_min':str(Decimal(obs)-Decimal(exp)),
    'relative_excess_percent':str(100*(Decimal(obs)/Decimal(exp)-1)),
    'measured_rate_cv':ratio(sd,obs),'sd_in_recovery_percentage_points_if_expected_fixed':str(100*Decimal(sd)/Decimal(exp))}
    for name,obs,exp,sd in [('GDH','0.084','0.071','0.002'),('G6PD','1.235','1.024','0.004')]},
 'G6PD_method_activity_ratio':ratio('12.51','14.88'),
 'G6PD_WST8_specific_activity_cv':ratio('0.36','12.51'),
 'G6PD_enzyme_concentration_WST8_over_UV':ratio('0.1','0.075'),
 'G6PD_FBS_expected_not_reconstructed_by_Table3':{'Table3_specific_activity_times_spiked_mass':str(Decimal('12.51')*Decimal('0.2')),
   'Table4_expected':'1.024','unit':'nmole/min'},
 'G6PD_FBS_recovery_source_disagreement':{'ratio_from_displayed_cells_percent':str(100*Decimal('1.235')/Decimal('1.024')),
   'reported_percent':'120.57','sd_from_displayed_cells_percent_if_expected_fixed':str(100*Decimal('0.004')/Decimal('1.024')),
   'reported_sd_percentage_points':'0.33','unrounded_data':None},
 'std_midpoint_correction_multiplier_research_only':ratio('8.6','8.72'),
 'FBS_correction_multiplier_research_only':ratio('1.024','1.235'),
 'correction_applied_to_unknown_sample':False,
 'variance_or_function_probability_fabricated':False}
save('arithmetic_verification.json',checks)
print(json.dumps(checks,indent=2))

def numeric_cell(value,unit,formula,scope,witnesses,*,origin='derived',reason=None):
    return {'value':value,'unit':unit,'formula':formula,'scope':scope,'origin':origin,
            'status':'populated' if value is not None else 'unavailable',
            'unavailable_reason':reason,'witnesses':witnesses}
cells={}
for n,r in enumerate(std,1):
    scope='buffer_NADPH_standard_'+r['nominal_nmol']+'_nmol'
    value=float(Fraction(r['measured_nmol'])/Fraction(r['nominal_nmol']))
    cells[f'standard_{n}_recovery']=numeric_cell(value,'dimensionless','measured_NADPH_amount/nominal_NADPH_amount',scope,['Tab2','Par31','Par32'])
    cells[f'standard_{n}_relative_bias_percent']=numeric_cell((value-1)*100,'percent','100*(recovery-1)',scope,['Tab2'])
cells.update({
 'NADPH_calibration_slope':numeric_cell(.0999,'absorbance/nmol','source_reported_linear_fit_slope','buffer_NADPH_calibration',['source/Fig3.png:panelB inset'],origin='reported'),
 'NADPH_calibration_intercept':numeric_cell(.0166,'absorbance','source_reported_linear_fit_intercept','buffer_NADPH_calibration',['source/Fig3.png:panelB inset'],origin='reported'),
 'NADPH_calibration_R_squared':numeric_cell(.9994,'dimensionless','source_reported_fit_R_squared','buffer_NADPH_calibration',['source/Fig3.png:panelB inset'],origin='reported'),
 'midpoint_within_run_CV_percent':numeric_cell(.8,'percent','source_reported_within_run_CV','8.6nmol_buffer_NADPH',['Tab2','Par32'],origin='reported'),
 'midpoint_between_run_CV_percent':numeric_cell(1.7,'percent','source_reported_between_run_CV','8.6nmol_buffer_NADPH',['Tab2','Par32'],origin='reported'),
 'FBS_G6PD_activity_recovery_from_displayed_rates':numeric_cell(float(Fraction('1.235')/Fraction('1.024')),'dimensionless','measured_net_activity/reported_expected_activity','0.2ug_G6PD_spiked_FBS',['Tab4','Par37']),
 'FBS_G6PD_activity_recovery_reported_percent':numeric_cell(120.57,'percent','source_reported_percent_recovery','0.2ug_G6PD_spiked_FBS',['Tab4'],origin='reported'),
 'FBS_G6PD_activity_recovery_reported_SD_percentage_points':numeric_cell(.33,'percentage_points','source_reported_recovery_SD','0.2ug_G6PD_spiked_FBS',['Tab4','Par43'],origin='reported'),
 'FBS_G6PD_activity_excess_over_expected':numeric_cell(.211,'nmol/min','measured_net_activity-reported_expected_activity','0.2ug_G6PD_spiked_FBS',['Tab4']),
 'FBS_G6PD_measured_rate_CV':numeric_cell(float(Fraction('.004')/Fraction('1.235')),'dimensionless','reported_SD/reported_mean','0.2ug_G6PD_spiked_FBS',['Tab4','Par43']),
 'G6PD_method_specific_activity_ratio':numeric_cell(float(Fraction('12.51')/Fraction('14.88')),'dimensionless','WST8_specific_activity/UV_specific_activity','purified_G6PD_method_comparison',['Tab3','Par33','Par39']),
 'G6PD_method_enzyme_concentration_ratio':numeric_cell(float(Fraction(4,3)),'dimensionless','(0.1ug/0.150mL)/(0.5ug/1mL)','purified_G6PD_method_comparison',['Par33','Par39']),
})
for name,reason in [('same_matrix_reporter_gain','enzyme_spike_and_buffer_analyte_calibration_do_not_isolate_it'),
 ('matched_blank_fraction','individual_sample_and_blank_values_unreported'),
 ('chemical_product_attribution_fraction','quantitative_sugar_product_identity_or_coupling_not_measured'),
 ('corrected_molar_G6PD_activity','molar_E_attribution_condition_response_and_applicable_recovery_not_established'),
 ('calibration_residual_SD','point_data_and_residuals_unavailable'),
 ('independent_preparation_count','preparation_independence_not_reported'),
 ('overall_experimental_reliability','no_justified_compilation_to_overall_grade_defined')]:
    cells[name]=numeric_cell(None,'unknown','unavailable','scoped_functional_assay',[],reason=reason)
save('proposed_numeric_sheet.json',{'version':'research_case167_numeric_components_v1','axis':'A105',
 'cells':cells,'independence':'not inferred; recovery, relative error and inverse multiplier share operands',
 'compilation':{'calibration_relation':'A=m*N+b','matched_blank_relation_conditional':'(A_sample-A_blank)/(m*t)',
  'additional_recovery_multiplier_conditional':'1/r only if independently established for same matrix and assay',
  'corrected_functional_result':None,'unknowns_not_imputed':True,'W05_aggregation':None}})
