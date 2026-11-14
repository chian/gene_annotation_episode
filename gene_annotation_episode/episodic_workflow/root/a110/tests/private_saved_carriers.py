"""A110 entrypoint for the explicit two-axis saved-carrier test mechanics.

The test mechanics are shared with A107; every application import, actual
constructor, identity class and runtime method resolves to A110. This is a test
helper reuse, not an application binding or historical compatibility alias.
"""
from gene_annotation_episode.episodic_workflow.root.a107.tests.private_saved_carriers import (
    capture as _capture, read_probe as _read_probe,
)


def capture(directory):
    return _capture("a110", directory)


def read_probe(captured, output):
    return _read_probe("a110", captured, output)
