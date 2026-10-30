"""Whole original scalar/grouped/JATS tokens; no model or source normalization."""
from fractions import Fraction
import hashlib
import pytest
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_ion_discrimination_numbers import read_ion_number, read_ion_unit, check_explicit_unit, fraction

SOURCE='source_'+('194a'*6)


def fixture(text,token,*,at=None):
    raw=text.encode();artifact='artifact_'+hashlib.sha256(raw).hexdigest()
    def source(ref,representation):
        assert ref==SOURCE and representation=='original'
        return {'artifact_ref':artifact,'content':raw}
    s=_Sources(source);i=text.index(token) if at is None else at
    w={'source_ref':SOURCE,'representation':'original','start':0,'end':len(raw),'quote':text}
    return s,{'witness':w,'number_start':i,'number_end':i+len(token)}


@pytest.mark.parametrize('text,token,value,relation,approx',[
    ('Reported lower limit of ∼30,000 s<sup>−1</sup>.','30,000',30000,'lower_limit',True),
    ('Rates exceed 30,000 s<sup>−1</sup>.','30,000',30000,'gt',False),
    ('Turnover &lt;30 ions/s.','30',30,'lt',False),
    ('Selectivity &gt;10<sup>4</sup>-fold.','10<sup>4</sup>',10000,'gt',False),
    ('Estimate about >= 3.25e2 ions/s.','3.25e2',325,'ge',True),
    ('Signed estimate −0.03 per_min.','−0.03',Fraction('-0.03'),'point',False),
    ('Estimate 0 per_min.','0',0,'point',False),
])
def test_complete_native_tokens_preserve_context_and_exact_value(text,token,value,relation,approx):
    s,selection=fixture(text,token);result=read_ion_number(selection,sources=s)
    assert fraction(result['exact'])==value
    assert result['raw_token']==token and result['relation']==relation and result['adjacent_approximate']==approx
    w=result['selector']['witness'];span=result['byte_span']
    assert text.encode()[span['start']:span['end']].decode()==token
    assert w['quote']==text


@pytest.mark.parametrize('text,token',[
    ('Rate 30,000 ions/s.','000'),('Rate 30,000 ions/s.','30'),('Rate 30,00 ions/s.','30,00'),
    ('Rate 30,0000 ions/s.','30,0000'),('Rate 3×10<sup>4</sup> ions/s.','10<sup>4</sup>'),
    ('Rate 10<sup>4</sup> ions/s.','10'),('Rate 10<sup>4</sup> ions/s.','4'),
    ('Signed −100 mV and a100-fold limit.','100'),('Between 1 and 2 ions/s.','2'),
    ('Bound not greater than 3 ions/s.','3'),('SD ±3 ions/s.','3'),
    ('Estimate 3–4 ions/s.','3'),('LOD 3 ions/s.','3'),
])
def test_clipped_composite_interval_or_untyped_limit_is_not_a_point(text,token):
    s,selection=fixture(text,token)
    with pytest.raises(ExperimentalContractError):read_ion_number(selection,sources=s)


def test_dimensionless_role_cannot_hide_voltage_token():
    text='Pulse at −100 mV; a lower limit of ∼100 on the permeability ratio.'
    s,selection=fixture(text,'−100');number=read_ion_number(selection,sources=s)
    with pytest.raises(ExperimentalContractError,match='source_number_unit_role_mismatch'):
        check_explicit_unit(number,None,sources=s,dimensionless=True)
    _,selection=fixture(text,'100',at=text.rindex('100'))
    correct=read_ion_number(selection,sources=s)
    check_explicit_unit(correct,None,sources=s,dimensionless=True)
    assert correct['relation']=='lower_limit' and correct['value']==100


def test_grouped_rate_unit_is_read_from_original_jats_and_scale_checked():
    text='Rate >30,000 s<sup>−1</sup>; a reference uses per_min.'
    s,selection=fixture(text,'30,000');number=read_ion_number(selection,sources=s)
    i=text.index('s<sup>');j=i+len('s<sup>−1</sup>')
    w={'source_ref':SOURCE,'representation':'original','start':len(text[:i].encode()),'end':len(text[:j].encode()),'quote':text[i:j]}
    unit=read_ion_unit(w,sources=s);check_explicit_unit(number,unit,sources=s,dimensionless=False)
    assert unit['unit']=='per_s' and fraction(unit['canonical_rate_scale'])==1
    i=text.index('per_min');w.update(start=len(text[:i].encode()),end=len(text[:i+7].encode()),quote='per_min')
    wrong=read_ion_unit(w,sources=s)
    with pytest.raises(ExperimentalContractError,match='source_number_unit_role_mismatch'):
        check_explicit_unit(number,wrong,sources=s,dimensionless=False)


@pytest.mark.parametrize('text,number,unit,dimensionless',[
    ('Voltage 100 ±3 mV.','100',None,True),
    ('Rate 30 ±2 per_min; other unit ions/s.','30','ions/s',False),
    ('Rate 30 ±>2 ions/s.','30','ions/s',False),
    ('Rate 30 ±2–3 ions/s.','30','ions/s',False),
    ('Rate 30 ±2% ions/s.','30','ions/s',False),
    ('Rate 30 ±2 ions/s/mg.','30','ions/s',False),
    ('Voltage 100 (±3 mV).','100',None,True),
    ('Rate 30 ±2,00 ions/s.','30','ions/s',False),
])
def test_actual_following_spread_unit_cannot_be_erased_by_a_header(text,number,unit,dimensionless):
    sources,selection=fixture(text,number);n=read_ion_number(selection,sources=sources)
    with pytest.raises(ExperimentalContractError):
        u=None
        if unit:
            i=text.index(unit);w={'source_ref':SOURCE,'representation':'original','start':len(text[:i].encode()),'end':len(text[:i+len(unit)].encode()),'quote':unit}
            u=read_ion_unit(w,sources=sources)
        check_explicit_unit(n,u,sources=sources,dimensionless=dimensionless)


@pytest.mark.parametrize('suffix',[')⁻¹',')^-1',')−1',')²','/mg'])
def test_clipped_unit_after_closing_parenthesis_or_power_is_rejected(suffix):
    text='Rate 30 ions/s'+suffix+'.';sources,selection=fixture(text,'30');i=text.index('ions/s')
    unit={'source_ref':SOURCE,'representation':'original','start':i,'end':i+6,'quote':'ions/s'}
    with pytest.raises(ExperimentalContractError,match='partial_source_rate_unit'):read_ion_unit(unit,sources=sources)


@pytest.mark.parametrize('suffix',['','.',').','); next sentence.'])
def test_complete_rate_unit_and_closing_punctuation_remain_valid(suffix):
    text='Rate 30 ions/s'+suffix;sources,selection=fixture(text,'30');n=read_ion_number(selection,sources=sources);i=text.index('ions/s')
    unit={'source_ref':SOURCE,'representation':'original','start':i,'end':i+6,'quote':'ions/s'}
    u=read_ion_unit(unit,sources=sources);check_explicit_unit(n,u,sources=sources,dimensionless=False)


@pytest.mark.parametrize('suffix',['%','mg','°C',' nm',' counts',' mM'])
def test_explicit_percent_mass_temperature_or_other_unit_is_not_a_fold_ratio(suffix):
    text='Reported value 100'+suffix+'.';sources,selection=fixture(text,'100');n=read_ion_number(selection,sources=sources)
    with pytest.raises(ExperimentalContractError,match='source_number_unit_role_mismatch'):
        check_explicit_unit(n,None,sources=sources,dimensionless=True)


@pytest.mark.parametrize('suffix',['-fold.',' on the F/Cl permeability ratio.',' (±3).'])
def test_legitimate_ratio_prose_and_unspecified_dimensionless_spread_are_preserved(suffix):
    text='Lower limit of 100'+suffix;sources,selection=fixture(text,'100');n=read_ion_number(selection,sources=sources)
    check_explicit_unit(n,None,sources=sources,dimensionless=True)
