"""Private A108 scientific library, support and provenance service implementations."""
from __future__ import annotations

class ScientificLibraryServices:

    def scientific_library_catalog(self):
        from ..scientific_process_library import catalog
        return catalog()

    def scientific_retriever_catalog(self):
        from ..scientific_tool_library import catalog
        configuration = self.tool_retrieval
        return catalog(retrieval_mode=None if configuration is None else configuration['mode'], tool_info=self.tool_library.supports_tool_info)

    def execute_scientific_library(self, context, name, arguments):
        from ..library.scientific_support_metadata import SUPPORT_ENTRY_VERSION, support_observation_kinds
        outcome = self.library.execute(name, arguments)
        if name == 'process.entry' and outcome['status'] == 'completed':
            result = outcome['result']
            if result['entry'].get('entry_version') == SUPPORT_ENTRY_VERSION:
                outcome = {**outcome, 'result': {**result, 'annotation_support_routes': self.services.scientific_support_routes(context, observation_kinds=support_observation_kinds(result['entry']))}}
        return outcome

    def scientific_support_routes(self, projector, score_binding, *, observation_kinds):
        from ..library.scientific_support_metadata import annotation_policy_routes
        return annotation_policy_routes(projector, score_binding, observation_kinds=observation_kinds)

    def create_scientific_provenance(self, *, store, journal):
        """Construct this binding's reader over the owning workflow's real ports."""
        from ..scientific_process_provenance import ScientificProcessProvenance
        return ScientificProcessProvenance(store, journal, library=self.library, tool_library=self.tool_library)

    def create_tool_retriever(self, *, store, run_id, provider):
        """Use this binding's frozen retrieval configuration and tool library."""
        from ..scientific_tool_retrieval import ScientificToolRetriever
        return ScientificToolRetriever(store, run_id=run_id, provider=provider, library=self.tool_library, configuration=self.tool_retrieval)

    def read_scientific_preparation(self, provenance, context, preparation_ref, *, owner='self'):
        """Preserve the private reader's distinct self and parent authentication."""
        if owner == 'self':
            return provenance.preparation(context, preparation_ref)
        if owner == 'parent':
            return provenance.parent_preparation(context, preparation_ref)
        raise ValueError('scientific_preparation_owner_invalid')

