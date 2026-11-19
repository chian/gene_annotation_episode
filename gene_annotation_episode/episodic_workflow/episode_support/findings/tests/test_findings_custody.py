"""The findings library on the scoped store: image views, typed findings, their validity and progress, run as
tool units of a real episode through the real runner on a real Store."""
import pytest

from .probe_world import outcomes, run, tool, world  # noqa: F401 - ``world`` is the fixture

IMAGE_AXES = ['biochemical_feasibility_evidence', 'evolutionary_history_evidence', 'gene_context_evidence',
              'partner_presence_evidence', 'perturbation_evidence', 'sample_context_evidence',
              'sequence_homology_evidence', 'structural_homology_evidence']


@pytest.mark.parametrize('axis', IMAGE_AXES)
def test_an_image_view_is_made_read_and_resolved_through_custody(world, axis):
    held = [world['image_source'], world['png']]
    run(world, 'image_' + axis, [tool('image_view', axis=axis, source_ref=world['image_source'],
                                      colour_conversion='preserve'),
                                 tool('image_view_refused', axis=axis, source_ref=world['image_source'], frame=3)],
        held=held)
    made, refused = [unit['outcome'] for unit in outcomes(world, 'image_' + axis)]
    body = made['body']
    assert (body['width'], body['height'], body['frame_count'], body['native_format']) == (6, 4, 1, 'PNG')
    assert made['metadata_is_view'] and made['shown_type'] == 'localImage'
    assert made['copy_is_display'] and made['copy_inside_scratch']
    assert refused['raised'].startswith('ContractError: image_frame_outside_source')
    assert world['store'].get(made['display'])['record_type'] == 'artifact'
    # The scratch directory of the unit is gone with its copy.
    scratch = world['tmp'] / 'store' / 'scratch'
    assert not scratch.exists() or [path for episode in scratch.iterdir() for path in episode.iterdir()] == []


VALIDITY_AXES = ['biochemical_feasibility_evidence', 'evolutionary_history_evidence', 'experimental_activity_evidence',
                 'partner_presence_evidence', 'perturbation_evidence', 'sample_context_evidence',
                 'structural_homology_evidence']
REPLACING_AXES = [axis for axis in VALIDITY_AXES if axis not in ('sample_context_evidence', 'experimental_activity_evidence')]
PROGRESS_AXES = [axis for axis in VALIDITY_AXES if axis != 'evolutionary_history_evidence']


def held(world):
    return [world['source']]


@pytest.mark.parametrize('axis', VALIDITY_AXES)
def test_a_typed_finding_is_rooted_extended_and_eligible_through_custody(world, axis):
    run(world, 'finding_' + axis, [tool('findings', axis=axis, target=world['target'], source=world['source'],
                                       withdraw=True, replaces=axis in REPLACING_AXES)], held=held(world))
    done = outcomes(world, 'finding_' + axis)[0]['outcome']
    assert done['roots'] == [world['target']]
    assert done['extent'] is True and done['correction'] is True
    assert world['store'].get(done['second'])['investigation_finding']['replaces_refs'] == (
        [done['first']] if axis in REPLACING_AXES else [])


@pytest.mark.parametrize('axis', PROGRESS_AXES)
def test_a_superseded_known_finding_is_inactive_with_the_withdrawal_of_its_current_revision(world, axis):
    run(world, 'progress_' + axis, [tool('findings', axis=axis, target=world['target'], source=world['source'],
                                        withdraw=True, replaces=False, investigation_progress=2.0)], held=held(world))
    done = outcomes(world, 'progress_' + axis)[0]['outcome']
    progress = done['progress']
    assert progress['credit'] == 0.0
    assert [item['assessment_ref'] for item in progress['inactive_dependencies']] == [done['first']]
    inactive = progress['inactive_dependencies'][0]
    assert inactive['reason'] == 'scientific_finding_withdrawn'
    assert inactive['current_assessment_ref'] == done['second']
    assert inactive['withdrawal_reason'] == 'superseded_evidence'


@pytest.mark.parametrize('axis', PROGRESS_AXES)
def test_a_current_retained_known_finding_earns_its_unit(world, axis):
    run(world, 'earn_' + axis, [tool('findings', axis=axis, target=world['target'], source=world['source'],
                                    withdraw=False, replaces=False, investigation_progress=2.0)], held=held(world))
    progress = outcomes(world, 'earn_' + axis)[0]['outcome']['progress']
    assert progress['credit'] == 2.0 and progress['inactive_dependencies'] == []
