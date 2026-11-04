"""Positive original-member correspondence using an explicitly synthetic map."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode import bvbrc_genome_alignment_bundle_contracts as c
from test_bvbrc_genome_alignment_bundle_projection import synthetic_original_sheet
from test_bvbrc_genome_alignment_returns import (
    CELL, MEASUREMENTS, ORIGINAL, example, measurement, project, fact_form, forbid_science, run,
)


def mapped_example():
    sheet, original = synthetic_original_sheet()
    fields = {'mapped': {'kind': 'xmfa_original_coordinates', 'request_id': 'cell', 'cell': CELL},
        'fraction': measurement('coverage', 'xmfa_original_coverage', 'coverage_fraction',
            member_number=1, original_member=original)}
    return example(fields, sheet), original


def test_original_member_coordinate_and_denominator_are_copied_without_science(monkeypatch):
    args, original = mapped_example()
    forbid_science(monkeypatch)
    values = project(args, (ORIGINAL, MEASUREMENTS))
    mapped, = values[ORIGINAL][0]['value']['value']['original_coordinates']
    assert (mapped['position_0based'], mapped['original_length'], mapped['strand']) == (59, 100, '-')
    assert json.loads(c.decode_reference(mapped['member_ref'])[2]) == original
    assert c.decode_reference(mapped['transformation_ref'])[2] == 'synthetic-feature-map'
    cell = values[MEASUREMENTS][0]['value']['value']
    assert (cell['value'], cell['numerator'], cell['denominator'], cell['unit']) == (0.5, 50, 100, 'fraction')


def test_original_member_relationship_survives_recorded_typed_custody(run, monkeypatch):
    args, original = mapped_example()
    child = run.child(run.saved.root, 'results', args[0], sources=(ORIGINAL, MEASUREMENTS))
    body = run.publications.add(child, args)
    forbid_science(monkeypatch)
    _, schema, _, refs = run.admit(run.saved.root, child)
    assert refs == [body['source_ref']]
    received = run.host.received_facts(run.saved.root, schema)
    mapped, = received[ORIGINAL][0]['value']['value']['original_coordinates']
    assert json.loads(c.decode_reference(mapped['member_ref'])[2]) == original
    assert run.host.resolve_received(run.saved.root, mapped['member_ref'], 'bvbrc_genome_alignment_member') is True


@pytest.mark.parametrize('field,value', [('position_0based', 49), ('original_length', 50),
    ('strand', '+'), ('member_ref', 'bvbrc_genome_alignment_member:wrong/member'),
    ('transformation_ref', 'bvbrc_genome_alignment_transformation:wrong/transformation')])
def test_original_map_cannot_be_replaced_by_native_coordinate_or_another_member(field, value):
    args, _ = mapped_example()
    body = deepcopy(args[0])
    mapped = body['publication']['adapter_result']['facts']['mapped']['value']['original_coordinates'][0]
    mapped[field] = value
    with pytest.raises(ValueError, match='saved_facts_conflict'):
        project((body, args[1], args[2]), (ORIGINAL, MEASUREMENTS))
