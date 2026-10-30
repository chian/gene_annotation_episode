"""One A105 form for original Fluc electrical and ion comparisons.

The selected source rows come from the retained original article. The tiny DNA
store is only an episode fixture; it supplies no target transfer or credit.
"""

import asyncio
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import re
from types import SimpleNamespace

import pytest

from gene_annotation_episode import literature_a105_worksheet as worksheet
from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, validate_form
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.tools import ToolRegistry
from test_literature_a105_worksheet import expand
from test_literature_channel_original_294 import _setup as channel_setup
from test_literature_compiled_assay_185 import remap
from test_literature_ion_discrimination_binding_199 import setup as ion_setup


CHANNEL = ['chord_conductance', 'charge_equivalent_rate', 'chord_conductance_variance']
ION = ['preferred_activity', 'alternative_activity', 'nominal_threshold_ratio']


def template():
    return worksheet.a105_worksheet_template([
        {'field': 'electrical', 'source': 'literature_channel_cells', 'components': CHANNEL},
        {'field': 'ion_comparison', 'source': 'literature_ion_discrimination_cells', 'components': ION},
    ])


def context():
    return {'version': worksheet.VERSION, 'assertion_refs': [], 'quantity_links': [], 'assertion_links': []}


def selector(form, field, component):
    row = next(row for row in form[field] if row['component'] == component)
    return {'field': field, 'sheet_ref': row['sheet_ref'], 'component': component, 'quantity': 'cell_value'}


def selected_original(tmp_path):
    # Both helpers authenticate the retained original XML. The original
    # electrical and efflux packet choose different measurements from it.
    store, base, ion_args = ion_setup(tmp_path/'shared', requested=ION,
                                      original='efflux_summary_thresholds')
    electrical_store, _electrical_context, electrical_args, _raw = channel_setup(tmp_path/'electrical_helper')
    try:
        electrical_args = remap(electrical_args, electrical_args['source_ref'], ion_args['source_ref'])
    finally:
        electrical_store.close()
    chosen = template()
    assignment = {**base.assignment, **chosen['assignment_rosters']}
    child = replace(base, assignment=assignment)
    host = SimpleNamespace(store=store, run_id=child.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True,
                                  channel_population=True, ion_discrimination_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return store, child, binding, chosen, electrical_args, ion_args


def test_original_fluc_two_formats_are_one_typed_worksheet_with_distinct_scopes(tmp_path):
    store, child, binding, chosen, electrical_args, ion_args = selected_original(tmp_path)
    with store:
        electrical = asyncio.run(binding.execute(child, 'literature.channel.populate',
                                                  electrical_args, 'fluc-electrical'))
        ion = asyncio.run(binding.execute(child, 'literature.ion_discrimination.populate',
                                           ion_args, 'fluc-ion'))
        assert electrical['status'] == ion['status'] == 'completed'
        selected = (*electrical['record_refs'], *ion['record_refs'])
        delivered = replace(child, received_record_refs=(*child.received_record_refs, *selected))
        schema = expand(chosen)
        facts = binding.facts(delivered, {'committed_record_refs': selected})
        form = form_with_facts({'assessment_context': context()}, schema, facts)
        validate_form(form, schema, lambda ref, namespace: binding.resolve(delivered, ref, namespace))
        binding.validate_report(delivered, form, schema)

        assert [row['component'] for row in form['electrical']] == CHANNEL
        assert [row['component'] for row in form['ion_comparison']] == ION
        assert form['electrical'][0]['value'] == float(Fraction(1800, 253))
        assert form['electrical'][0]['unit'] == 'pS'
        assert form['electrical'][2]['value'] is None
        assert form['electrical'][2]['unavailable_reason'] == 'primitive_covariance_not_supplied'
        assert [row['threshold'] for row in form['ion_comparison']] == [30000, 30, 1000]
        assert form['ion_comparison'][2]['physical_domain'] is None
        assert form['ion_comparison'][2]['zero_denominator_case'] == 'possible_in_source_domain'
        assert all(row['evaluation_scope'] == 'source_electrical_activity' for row in form['electrical'])
        assert all(row['evaluation_scope'] == 'source_ion_discrimination' for row in form['ion_comparison'])
        assert form['electrical'][0]['source_meanings']['molecule']['witness']['quote'] == 'Fluc-Ec2 reconstituted liposomes'
        assert form['electrical'][0]['current_kind']['value'] == 'current_step_magnitude'
        assert form['ion_comparison'][0]['route'] == 'reported_threshold_pair'
        assert form['ion_comparison'][0]['source_meanings']['preferred_ion'] is not None
        assert form['ion_comparison'][0]['source_meanings']['alternative_ion'] is not None
        assert form['ion_comparison'][0]['source_meanings']['preferred']['molecule'] is None
        assert form['ion_comparison'][0]['source_meanings']['preferred']['construct'] is None
        assert form['ion_comparison'][0]['relationships']['subject_construct']['value'] == 'unknown'
        # An electrical current and an ion-efflux threshold retain separate
        # physical dependencies even though the paper artifact is shared.
        electrical_keys = set(form['electrical'][0]['measurement_keys'])
        ion_keys = {key for row in form['ion_comparison'] for dep in row['dependencies']
                    for key in (*dep['physical_keys'], *dep['opaque_dependency_keys'])}
        assert electrical_keys and ion_keys and electrical_keys.isdisjoint(ion_keys)

        unresolved = {'left': selector(form, 'electrical', 'chord_conductance'),
                      'right': selector(form, 'ion_comparison', 'nominal_threshold_ratio'),
                      'relation': 'unresolved', 'support_record_refs': []}
        form['assessment_context']['quantity_links'] = [unresolved]
        binding.validate_report(delivered, form, schema)
        false_join = deepcopy(form)
        false_join['assessment_context']['quantity_links'][0]['relation'] = 'same_reported_parameter'
        with pytest.raises(ReportBoundaryError, match='a105_worksheet_link_not_supported'):
            binding.validate_report(delivered, false_join, schema)

        parent_state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
                        'goal': {'objective': 'Assess the returned Fluc experimental measurements.'},
                        'literature_assignment': {}, 'child_reports': [form],
                        'action_yields': {'rows': []}, 'controller': {}, 'working_state': {}}
        prompt = render_literature_experimental_prompt(parent_state,
            'Assess what the received Fluc measurements establish and preserve their limits.')
        task, steering = prompt.split('\n\nSTEERING', 1)
        assert 'source_electrical_activity' not in task
        assert 'source_ion_discrimination' not in task
        assert 'Requested electrical numerical sections' in steering
        assert 'Requested ion-discrimination numerical components' in steering
        assert '7.1146245059288535' in steering and 'pS' in steering
        assert '30000' in steering and 'ions_per_s' in steering
        assert 'primitive_covariance_not_supplied' in steering
        assert 'relationship unresolved; no independence or equality inferred' in steering
        assert not re.search(r'\b(?:source|artifact|operation)_[0-9a-f]{24,64}\b', steering)


def test_exact_rosters_and_original_nine_remain_available():
    chosen = template()
    assert len(worksheet.FAMILIES) == 11
    assert list(worksheet.FAMILIES)[-2:] == ['literature_channel_cells',
                                           'literature_ion_discrimination_cells']
    assert chosen['assignment_rosters'] == {
        'requested_channel_components': CHANNEL,
        'requested_ion_discrimination_components': ION,
    }
    schema = expand(chosen)
    for field, source in [('electrical', 'literature_channel_cells'),
                          ('ion_comparison', 'literature_ion_discrimination_cells')]:
        assert schema['properties'][field] == worksheet._schema(source)
    assert list(worksheet.FAMILIES)[:9] == [
        'literature_concentration_window_cells', 'literature_kinetic_cells',
        'literature_kinetic_summary_precision_cells', 'literature_measurement_comparison_cells',
        'literature_endpoint_signal_cells', 'literature_product_coupling_cells',
        'literature_calibration_recovery_cells', 'literature_compiled_assay_v2_cells',
        'literature_compiled_assay_v3_cells',
    ]
