"""Private initial information selected by this actual recipient."""
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_initial_information.presentation import (
    resource_information)

def initial_information(self, context, catalog):
    if self.local_file_sources.applies(context):
        target = self._target(context)
        return {'execution_resource_capabilities': [{'resource_id': target['resource_id'], 'resource_kind': 'local'}], 'execution_initial_information': {}}
    readers = catalog.readers('hpc_work_planning/hpc_allocation_execution/execution_result_acquisition', context)
    value = resource_information(readers)
    return value
