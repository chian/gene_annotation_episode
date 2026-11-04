"""Real saved FastqUtils forms remain exact after additional native formats."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_fastqutils_contracts import (
    FastqUtilsContractError, canonical_json, make_requested_schema, validate_requested_form,
)
from gene_annotation_episode.bvbrc_fastqutils_saved_codec import validate_saved_projection

_SAVED_RELATIVE = Path('verification/tool_graders_bvbrc_fastqutils_implementation_2026-10-25_198/evidence_c/integration_handoff_002')
ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / _SAVED_RELATIVE / 'requested_schema.json').is_file())
SAVED = ROOT / _SAVED_RELATIVE


def read(name):
    return json.loads((SAVED / name).read_text())


def test_exact_old_and_new_forms_preserve_original_field_order():
    old = read('requested_schema.json')
    before = canonical_json(old)
    form = validate_requested_form(json.loads(before))
    assert [field['field'] for field in form['fields']] == old['required']
    current = make_requested_schema(form)
    assert current != old
    assert validate_requested_form(current) == form
    assert canonical_json(old) == before


@pytest.mark.parametrize('damage', ['open_object', 'missing_field', 'extra_keyword', 'altered_definition'])
def test_damaged_legacy_forms_are_rejected(damage):
    schema = read('requested_schema.json')
    if damage == 'open_object':
        schema['additionalProperties'] = True
    elif damage == 'missing_field':
        schema['required'].pop()
    elif damage == 'extra_keyword':
        schema['title'] = 'foreign'
    else:
        # This is an actual old generated definition, not a guessed shape.
        schema['$defs']['ProjectedField']['additionalProperties'] = True
    with pytest.raises(FastqUtilsContractError, match='^requested_form_invalid$'):
        validate_requested_form(schema)


def test_mixing_old_and_new_grammar_fragments_is_rejected():
    old = read('requested_schema.json')
    current = make_requested_schema(validate_requested_form(old))
    changed = [name for name in old['$defs'] if old['$defs'][name] != current['$defs'][name]]
    assert len(changed) > 1
    old['$defs'][changed[0]] = deepcopy(current['$defs'][changed[0]])
    with pytest.raises(FastqUtilsContractError, match='^requested_form_invalid$'):
        validate_requested_form(old)


def test_old_grammar_cannot_smuggle_a_new_metric_selector():
    old = read('requested_schema.json')
    selector = old['properties']['read_count']['x-bvbrc-fastqutils']['target']['selector']
    selector['metric'] = 'cutadapt_processed_count'
    selector['section_key'] = 'cutadapt_summary'
    with pytest.raises(FastqUtilsContractError, match='^requested_form_invalid$'):
        validate_requested_form(old)
    # A newly generated full grammar permits the explicitly selected metric.
    form = {'version': 'fastqutils_projection_v2', 'fields': [
        {'field': name, 'selection': old['properties'][name]['x-bvbrc-fastqutils']}
        for name in old['required']]}
    assert validate_requested_form(make_requested_schema(form)) == form


def test_retained_provider_result_replays_without_scientific_work(monkeypatch):
    original = read('provider_result.json')
    bundle = read('bundle.json')
    parameters = read('parameters.json')
    schema = read('requested_schema.json')
    before = canonical_json([original, bundle, parameters, schema])
    attempted = []

    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise AssertionError('Saved communication attempted acquisition or scientific work')

    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    for suffix in ('native', 'fastq_reader', 'fastqc_reader', 'trim_reader', 'metadata',
                   'sheet', 'calculators', 'composition', 'quality', 'mapping', 'retention', 'consistency'):
        module = importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_' + suffix)
        for name, value in list(vars(module).items()):
            if callable(value) and name.startswith(('parse_', 'populate_', 'extract_', 'calculate_')):
                monkeypatch.setattr(module, name, forbidden)
    validate_saved_projection(original['sheet'], original['components'],
        facts=original['facts'], status=original['status'],
        missing_requirements=original['missing_requirements'], diagnostics=original['diagnostics'],
        requested_form=schema, parameters=parameters, original_task=bundle['original_task'], bundle=bundle)
    assert not attempted
    assert canonical_json([original, bundle, parameters, schema]) == before
    values = {name: original['facts'][name]['records'][0]['payload']['value']
              for name in ('read_count', 'gc', 'errors', 'retained')}
    assert values == {'read_count': 2, 'gc': 5/9, 'errors': .001, 'retained': .75}
