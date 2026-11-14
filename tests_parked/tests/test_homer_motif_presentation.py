"""Human views of fixed HOMER returns, using retained native bytes.

Engineered Source identities exercise pure presentation only. Runtime custody
and requested-return evidence belong to the ordinary Workflow verification.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3

import pytest

from gene_annotation_episode import homer_motif_measurements as measurements
from gene_annotation_episode.scientific_process_prompt import _values
from test_homer_motif_measurements import complete_sheet, retained, selection, series_for, SOURCE


def _forbidden(*args, **kwargs):
    raise AssertionError('HOMER presentation must only consume fixed return values')


def test_retained_homer_display_keeps_native_precision_and_distinct_populations(complete_sheet, monkeypatch):
    known = series_for(complete_sheet, 'known_results')
    ordinal = 0
    assert known['observations'][ordinal]['name'].startswith('NF1')
    components = measurements.calculate_homer_components(complete_sheet,
        selector=selection(known, offset=ordinal, limit=1))
    packet = measurements.project_homer_return(components, source_ref=SOURCE)
    original = deepcopy(packet)
    monkeypatch.setattr(measurements, 'calculate_homer_components', _forbidden)
    monkeypatch.setattr(measurements, 'parse_homer_motif_sheet', _forbidden)
    text = _values({'result': packet, 'status': 'completed', 'record_refs': [SOURCE],
        'changed_record_refs': [SOURCE], 'same_fixed_result': deepcopy(packet)})
    assert text.count('Callable operand') == 1
    assert text.count(SOURCE) == 1 and text.count(known['series_id']) == 1
    assert all(text.count(series['series_id']) == 1 for series in packet['available_series'])
    assert 'Retained series available for saved selection' in text
    assert '1e-78' in text and '-1.800e+02' in text and '-180.016288' in text
    assert '6.734334' in text and '0.0000' in text and 'fixed_4' in text
    assert 'unique_joined_background_members | 1000' in text
    assert '| background | 956 | 956 | available |' in text
    assert 'Effective native motif denominators remain separate' in text
    assert 'not_provided' in text and 'known_table' in text and 'native_pwm' in text
    assert 'homer_occurrence_' not in text and 'homer_input_population_' not in text
    assert packet == original


def test_retained_homer_display_preserves_pwm_order_and_auxiliary_meanings(complete_sheet, monkeypatch):
    series = series_for(complete_sheet, 'denovo_pwm', 'homerMotifs.motifs8')
    components = measurements.calculate_homer_components(complete_sheet,
        selector=selection(series, limit=1))
    packet = measurements.project_homer_return(components, source_ref=SOURCE)
    original = deepcopy(packet)
    monkeypatch.setattr(measurements, 'calculate_homer_components', _forbidden)
    text = _values(packet)
    assert 'TTGCCAAG' in text and '1e-202' in text and '-466.553334' in text
    assert 'native column order A, C, G, T' in text
    representation = packet['selected_series'][0]['observations'][0]['representations'][0]
    cursor = 0
    for row in representation['pwm_rows']:
        tokens = json.dumps(row['raw_fields'], separators=(',', ':'))
        cursor = text.index('| ' + str(row['ordinal_0based']) + ' | ' + tokens, cursor) + 1
    for auxiliary in representation['native_auxiliary_measurements']:
        assert auxiliary['raw_field'] in text and auxiliary['definition'] in text
        assert auxiliary['population'] in text and auxiliary['denominator'] in text
        assert auxiliary['coordinate_origin'] in text
    assert packet == original


def test_homer_display_does_not_merge_distinct_source_or_selection_views(complete_sheet):
    known = series_for(complete_sheet, 'known_results')
    first = measurements.project_homer_return(measurements.calculate_homer_components(
        complete_sheet, selector=selection(known, limit=1)), source_ref=SOURCE)
    second = deepcopy(first)
    second['source_ref'] = 'source_' + 'b' * 24
    third = measurements.project_homer_return(measurements.calculate_homer_components(
        complete_sheet, selector=selection(known, offset=1, limit=1)), source_ref=SOURCE)
    text = _values([first, second, third, deepcopy(first)])
    assert text.count('Callable operand') == 3
    assert text.count(SOURCE) == 2 and text.count(second['source_ref']) == 1


