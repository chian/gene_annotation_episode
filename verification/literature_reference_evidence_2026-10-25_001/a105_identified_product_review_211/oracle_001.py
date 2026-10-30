"""Root independent exact arithmetic on authenticated original table cells."""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal, localcontext
import hashlib
import json

BASE=Path(__file__).resolve().parent
PACKET=BASE.parent/'a105_identified_product_scoring_case_207/SOURCE_PACKET_001.json'
packet=json.loads(PACKET.read_text())
assert hashlib.sha256(PACKET.read_bytes()).hexdigest()=='7ca8c54df69f5591d410869e658ff47e31d34028088fec99a9a04829a979d8fb'
raw=Path(packet['paper']['original_path']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==packet['paper']['sha256']
rows=[]
for row in packet['table3_source_rows']:
    q=row['quantities']
    for value in q.values():
        witness=value['witness']
        assert raw[witness['start']:witness['end']]==witness['quote'].encode()
    p,h=Fraction(q['product_activity']['raw_number']),Fraction(q['nadh_consumption_activity']['raw_number'])
    reported=Fraction(q['reported_coupling_percent']['raw_number'])
    # The source's negligible/nondetected product statement overrides an exact
    # physical-zero interpretation. Preserve the literal without computing a
    # physical coupling point or a fictitious numerical upper limit.
    positive=row['product_semantics']=='positive_reported_turnover'
    ratio=p/h if positive else None
    discrepancy=None if ratio is None else 100*ratio-reported
    with localcontext() as context:
        context.prec=65
        if ratio is not None:
            independent=Decimal(q['product_activity']['raw_number'])/Decimal(q['nadh_consumption_activity']['raw_number'])
            assert abs(Decimal(ratio.numerator)/Decimal(ratio.denominator)-independent)<Decimal('1e-62')
    rows.append({'subject':row['subject'],'product_native_literal':str(p),'NADH_native_literal':str(h),
        'reported_coupling_percent':str(reported),'descriptive_product_per_NADH':None if ratio is None else str(ratio),
        'descriptive_product_per_NADH_float':None if ratio is None else float(ratio),
        'displayed_ratio_minus_reported_percentage_points':None if discrepancy is None else str(discrepancy),
        'physical_fraction_interpretation':'conditional_on_stoichiometry_and_assay_relationships' if positive else 'nondetection_unknown_limit_no_point',
        'sampling_uncertainty':None,'same_physical_aliquot':row['same_physical_aliquot'],
        'same_preparation':row['same_preparation'],'normalization':row['normalization']})

Pwt,Hwt=Fraction(206),Fraction(289)
Pm,Hm=Fraction(92),Fraction(216)
activity_ratio=Pm/Pwt
reporter_ratio=Hm/Hwt
utilization_ratio=(Pm/Hm)/(Pwt/Hwt)
assert reporter_ratio*utilization_ratio==activity_ratio
assert (Pm/Hm)*Hm==Pm
result={'source_sha256':packet['paper']['sha256'],'packet_sha256':hashlib.sha256(PACKET.read_bytes()).hexdigest(),
    'primary_rows':rows,'T252N_over_WT':{'identified_product_activity_ratio':str(activity_ratio),
        'NADH_consumption_ratio':str(reporter_ratio),'productive_utilization_ratio':str(utilization_ratio),
        'factorization_exact':True,'all_three_share_source_measurements':True},
    'native_ND_is_not_zero':True,'reconstructed_activity_is_not_independent_validation':True,
    'no_function_probability_or_annotation_credit':True}
(BASE/'ROOT_NUMERICAL_ORACLE_001.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
