"""Actual private task constructor identity boundary, without runtime creation.

Install under root/tests only with the corresponding reviewed task change.
The actual task module and its real imports must be available: no module stubs,
mocked imports, skipped imports, or alternate axis task are accepted here.
"""
import pytest


class UnavailableRuntimeOperand:
    """A wrong private path must fail before using any runtime operand."""

    def __getattribute__(self, name):
        raise AssertionError('rejected task identity touched runtime operand: ' + name)


@pytest.mark.parametrize('path', [
    (),
    (('scientific_process', 'root'),),
    (('improvement', 'root'),),
    (('annotation', 'parent'), ('annotation', 'child')),
    (('scientific_process', 'parent'), ('annotation', 'child')),
])
def test_annotation_task_rejects_foreign_or_nested_identity_before_runtime_access(path):
    from gene_annotation_episode.episodic_workflow.root.task import AnnotationTask

    source = object.__new__(AnnotationTask)
    unavailable = UnavailableRuntimeOperand()
    with pytest.raises(ValueError, match='^annotation_task_requires_root_annotation_identity$'):
        AnnotationTask.__init__(source, unavailable, path, unavailable, unavailable)
    assert vars(source) == {}
