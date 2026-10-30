"""Root independent native-workbook arithmetic; not a production reader binding."""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json,math,statistics,zipfile
import xml.etree.ElementTree as E
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CASE=ROOT/'research/experimental_scoring_review_2026-10-23/a105_raw_rate_primary_case_164'
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def cells(path,expected):
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
    with zipfile.ZipFile(path) as z:
        strings=[''.join(x.itertext()) for x in E.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS)]
        result={}
        for c in E.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//m:c',NS):
            v=c.find('m:v',NS);token=v.text if v is not None else None
            result[c.attrib['r']]={'type':c.attrib.get('t','n'),'lexeme':token,
                'value':strings[int(token)] if c.attrib.get('t')=='s' else token,
                'formula':c.findtext('m:f',None,NS)}
    return result

def exact(value):return {'numerator':str(value.numerator),'denominator':str(value.denominator)}

def main():
    source=cells(CASE/'originals/S1Data.xlsx','e6d31a25930fe62cf10dd13c1b3e8193202687e78ed935cb3dfd21fd51ff4a7a')
    table=cells(CASE/'originals/S1Table.xlsx','331a7dd5f2f28fb5d538714e9617430e28bc427b8a899183c64f0502105c476b')
    assert source['C2']['value']=='U/mg' and source['J3']['value']=='Actinobacteria bifidobacterium'
    summaries={};means={};checks=0
    for label,start,header in [('D-EUS',16,15),('L-EUS',12,11),('DHA',8,7)]:
        assert source[f'C{header}']['value']==label
        data=[];witnesses=[]
        for index,row in enumerate(range(start,start+3),1):
            assert source[f'C{row}']['value']==f'Parallel {index}'
            c=source[f'J{row}'];assert c['type']=='n' and c['formula'] is None
            data.append(F(c['lexeme']));witnesses.append({'cell':f'J{row}','numeric_lexeme':c['lexeme'],'source_parallel_label':source[f'C{row}']['value'],'unit_cell':'C2','subject_cell':'J3'})
        mean=sum(data)/3;variance=(sum(x*x for x in data)-3*mean*mean)/2;sd=math.sqrt(float(variance));cv=sd/float(mean)
        assert math.isclose(float(mean),statistics.mean(float(x) for x in data),rel_tol=1e-15)
        assert math.isclose(sd,statistics.stdev(float(x) for x in data),rel_tol=1e-14)
        checks+=2;means[label]=mean
        summaries[label]={'witnesses':witnesses,'reported_parallel_entry_count':3,'experimental_unit_grouping':None,'independent_preparation_count':None,'pairing':None,'mean':float(mean),'mean_exact':exact(mean),'sample_sd_descriptive_only':sd,'sd_over_mean':cv,'unit':'source-native U/mg; no physical conversion supplied'}
    comparisons={}
    for label in ('L-EUS','DHA'):
        d,t=means['D-EUS'],means[label]
        comparisons[label]={'reference':'D-EUS','difference':float(d-t),'difference_unit':'U/mg','retained_fraction':float(t/d),'retained_fraction_exact':exact(t/d),'fractional_decrease':float(1-t/d),'shared_reference_source_cells':['J16','J17','J18'],'difference_se':None,'correction_factors':None,'corrected_ratio':None}
        assert math.isclose(comparisons[label]['retained_fraction'],summaries[label]['mean']/summaries['D-EUS']['mean'],rel_tol=1e-15);checks+=1
    printed=F(table['H7']['value'].split('±')[0]);discrepancy=printed-means['DHA']
    assert format(float(means['DHA']),'.4f')=='0.1568'
    assert table['H7']['value']=='0.1569±0.0054';checks+=2
    result={'scope':'Independent root arithmetic from original XLSX numeric lexemes after full source-packet instruction reset; no production reader/episode/assay reliability proof.','summaries':summaries,'comparisons':comparisons,'DHA_summary_conflict':{'printed_cell':'H7','printed':table['H7']['value'],'raw_mean':float(means['DHA']),'printed_minus_raw':float(discrepancy),'interpretation':'Representations disagree; reason unknown; not independent experiments.'},'arithmetic_checks':checks,'canonical_U_definition':None,'raw_reading_method_binding':None,'calibration_recovery':None,'matched_blank':None,'goal_status':'active'}
    with (HERE/'PRIMARY_ARITHMETIC_001.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'scope':result['scope'],'arithmetic_checks':checks,'means':{k:v['mean'] for k,v in summaries.items()},'L_over_D':comparisons['L-EUS']['retained_fraction'],'DHA_conflict':result['DHA_summary_conflict']}))
if __name__=='__main__':main()
