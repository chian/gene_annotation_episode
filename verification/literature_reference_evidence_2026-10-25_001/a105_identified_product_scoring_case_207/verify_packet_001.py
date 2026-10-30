"""Independent byte-custody and numerical-value verification of the frozen packet."""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal,localcontext
import hashlib,json
base=Path(__file__).resolve().parent
source=(base/'acquisition_001.bin').read_bytes()
packet=json.loads((base/'SOURCE_PACKET_001.json').read_text())
oracle=json.loads((base/'NUMERICAL_ORACLE_001.json').read_text())
assert hashlib.sha256(source).hexdigest()==packet['paper']['sha256']==oracle['source_sha256']
assert hashlib.sha256((base/'Fig4.jpg').read_bytes()).hexdigest()==packet['figure']['sha256']
checks=[]
def visit(item):
    if isinstance(item,dict):
        if {'artifact_ref','representation','start','end','quote'}==set(item):
            assert item['representation']=='original'
            assert source[item['start']:item['end']]==item['quote'].encode('utf8')
            checks.append((item['start'],item['end']))
        else:
            for value in item.values():visit(value)
    elif isinstance(item,list):
        for value in item:visit(value)
visit(packet)
assert set(packet['tables'])=={'T1','T2','T3','T4'}
assert 'min<sup>−1</sup>' in packet['tables']['T3']['witness']['quote']
assert '%' in packet['tables']['T3']['witness']['quote']
math_checks=0
with localcontext() as ctx:
    ctx.prec=70
    for raw,row in zip(packet['table3_source_rows'],oracle['rows']):
        assert raw['subject']==row['subject']
        p=Decimal(raw['quantities']['product_activity']['raw_number'])
        h=Decimal(raw['quantities']['nadh_consumption_activity']['raw_number'])
        r=Decimal(raw['quantities']['peroxide_activity']['raw_number'])
        for key,want in [('diagnostic_displayed_ratio',p/h),('diagnostic_water_from_displayed_operands',(h-r-p)/2)]:
            got=row[key];exact=Decimal(got['exact_numerator'])/Decimal(got['exact_denominator'])
            assert abs(exact-want)<Decimal('1e-68');math_checks+=1
        assert row['diagnostic_numerical_closure']['exact_numerator']=='0'
        assert not row['closure_independent_check']
        if raw['subject']=='T252A':
            assert 'unknown' in row['physical_product_rate']
            assert row['physical_coupling']=='unavailable_nondetection_limit_unknown'
        else:assert row['uncertainty'] is None
protected=json.loads((base/'POST_PAPER_RESET_002.json').read_text())['documents_actually_displayed_completely']
changed=[x['path'] for x in protected if hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()!=x['sha256']]
assert not changed,changed
print(json.dumps({'frozen_source_sha256':packet['paper']['sha256'],'verified_packet_witnesses':len(checks),'unique_original_byte_spans':len(set(checks)),'independent_decimal_checks':math_checks,'all_four_tables_present':True,'nondetection_not_physical_zero':True,'protected_read_contract_changes':changed,'production_imports':0,'source_acquisition':0,'episode_or_controller_execution':0,'writes':0},indent=2))
