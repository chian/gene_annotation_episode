"""Explicit unexecuted policy ports for public case-construction controls."""
from gene_annotation_episode.case_execution import PolicyBindings
from gene_annotation_episode.episodic_workflow.root.native_timing_information import NativeTimingInformation


def no_work(*args, **kwargs):
    raise AssertionError('public caller construction must not execute policy work')


def create_policy(parameters):
    if parameters != {'kind': 'public_case_fixture_v1'}:
        raise ValueError('unexpected_public_fixture_parameters')
    definition = {'kind': 'public_case_fixture_unexecuted_policy_v1'}
    return PolicyBindings(no_work, None, no_work, no_work, no_work,
        definition, None, definition, definition, definition,
        native_timing_information=NativeTimingInformation(0.25))
