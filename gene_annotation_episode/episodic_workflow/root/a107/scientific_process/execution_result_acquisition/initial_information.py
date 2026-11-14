"""Private initial information selected by this actual recipient."""
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_initial_information.presentation import (
    resource_information, received_api_information)

def initial_information(self, context, catalog):
    if self.local_file_sources.applies(context):
        target = self._target(context)
        return {'execution_resource_capabilities': [{'resource_id': target['resource_id'], 'resource_kind': 'local'}], 'execution_initial_information': {}}
    readers = catalog.readers('scientific_process/execution_result_acquisition', context)
    value = resource_information(readers)
    value.update(received_api_information(context, readers))
    return value
