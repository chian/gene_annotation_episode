"""Public E facade using upstream native bytes and synthetic receipt custody."""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.root.library import bvbrc_genome_alignment_bundle_adapter as facade


def member(index=0, namespace='mauve_v4_member_0based'):
    return {'namespace': namespace, 'index': index}


def measurement(request_id='anchors', family='v4_coverage', field='known_union_bases', **location):
    if not location:
        location = {'member': member()}
    return {'kind': 'measurement', 'request_id': request_id, 'metric': {'family': family, 'field': field, **location}}


