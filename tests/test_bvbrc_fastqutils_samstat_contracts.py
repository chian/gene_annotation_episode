"""Finite shared SAMstat vocabulary and exact historical requested grammars."""

import pytest

from gene_annotation_episode import bvbrc_fastqutils_contracts as c
from gene_annotation_episode.bvbrc_fastqutils_metric_specs import metric_spec,component_spec
from gene_annotation_episode.bvbrc_fastqutils_samstat_specs import SAMSTAT_METRICS,SAMSTAT_COMPONENTS


def test_all_sixty_native_specs_are_concrete_and_independently_accessible():
    assert len(SAMSTAT_METRICS)==60 and len(SAMSTAT_COMPONENTS)==2
    for metric in SAMSTAT_METRICS:
        spec=metric_spec(metric)
        assert spec['metric']==metric
        assert spec['meaning'] in c._DEFS['Cell']['properties']['meaning']['enum']
        assert spec['precision'] in c._DEFS['Cell']['properties']['precision']['enum']
        assert spec['native_fields'] and spec['interpretation'] and spec['missing_behavior']
        assert all(unit in c._DEFS['Cell']['properties']['unit']['enum'] for unit in spec['units'])
        assert all(axis in c._DEFS['Axis']['properties']['kind']['enum'] for axis in spec['axis_kinds'])
        assert metric in c._DEFS['Cell']['properties']['metric']['enum']
        assert metric in c._DEFS['MeasurementPayload']['properties']['quantity']['enum']
        assert metric in c._DEFS['MeasurementSelector']['oneOf'][1]['properties']['metric']['enum']
    for metric in SAMSTAT_COMPONENTS:
        spec=component_spec(metric)
        assert spec['method']=='samstat_report_mapping'
        assert spec['meaning']=='native_report_derived'
        assert spec['units']==['fraction'] and spec['uncertainty']=='not_estimated'
        assert 'MAPQ255' in spec['denominator']


def test_precision_differences_are_explicit_and_no_slash_delimited_cell_meaning():
    assert metric_spec('samstat_paired_flag_record_count_display')['allowed_precisions']==['exact_for_retained_population','native_rounded']
    assert metric_spec('samstat_gap_compressed_median_identity_percent')['meaning']=='native_estimate'
    assert metric_spec('samstat_median_length')['allowed_precisions']==['exact_for_retained_population','native_rounded','native_estimator','not_reported']
    assert metric_spec('samstat_reported_item_count')['population_keys']==[]
    assert all('/' not in s['meaning'] for s in SAMSTAT_METRICS.values())


def test_closed_new_calculation_request_and_finite_mirrors():
    selected=dict(selection='semantic',document_id='report',population_key='samstat_report_records',population_ordinal=0)
    request=dict(calculation_id='report_mapping',method='samstat_report_mapping',populations=[selected])
    assert c.validate_contract('CalculationRequest',request)==request
    for changed in [dict(request,populations=[]),dict(request,populations=[selected,selected]),
                    dict(request,populations=[selected,dict(selected,population_ordinal=1),dict(selected,population_ordinal=2)]),
                    dict(request,threshold=30),dict(request,populations=[dict(selected,population_key='made_up')])]:
        with pytest.raises(c.FastqUtilsContractError): c.validate_contract('CalculationRequest',changed)
    for name,path in [('ParseContext','declared_format'),('Artifact','actual_format'),('DocumentBinding','format')]:
        assert {'samstat_html_2_2_3','samstat_html_2_5_0','samstat_bvbrc_error_html'}<=set(c._DEFS[name]['properties'][path]['enum'])
    for name in ('Component','CalculationBinding','ComponentPayload'):
        assert 'samstat_report_mapping' in c._DEFS[name]['properties']['method']['enum']
    assert all(value in c._DEFS['Diagnostic']['properties']['code']['enum'] for value in
               ('samstat_svg_values_not_retained','samstat_native_prefix','samstat_caller_failure','samstat_mapq255_merged'))


def test_description_access_does_not_mutate_registries():
    spec=metric_spec('samstat_alignment_bin_count');spec['units'].append('unknown')
    assert 'unknown' not in metric_spec('samstat_alignment_bin_count')['units']
