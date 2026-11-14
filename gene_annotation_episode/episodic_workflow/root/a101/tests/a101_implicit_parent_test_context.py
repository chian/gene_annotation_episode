"""Shared original A101 construction ports: annotation and improvement tests."""
from contextlib import contextmanager
from .test_a101_implicit_parent_protocol import actual_workflow, own


@contextmanager
def improvement_workflow(directory, *, workflow_type=None):
    runtime = own('runtime')
    def configured(*args, **kwargs):
        return (workflow_type or runtime.Workflow)(*args, root_role='improvement', **kwargs)
    with actual_workflow(directory, workflow_type=configured) as workflow:
        yield workflow


def improvement(workflow, key='root'):
    return workflow.build('improvement', key, 'Resolve the original annotation question', workflow.store.validate_scope())
