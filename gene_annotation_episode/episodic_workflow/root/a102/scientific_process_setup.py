"""Prepare a caller descriptor without starting a model, child or tool job."""
from pathlib import Path

from .scientific_process_library import ScientificProcessLibrary
from .scientific_tool_library import ScientificToolLibrary


def prepare_scientific_binding(*, run_directory, source_directory, tool_catalog, child_roles,
                               tool_retrieval=None, resource_catalogs=None,
                               contract_information_profile=None, yield_bindings=None,
                               episode_type):
    library = ScientificProcessLibrary.freeze(
        Path(run_directory) / "scientific-process-library", source=source_directory)
    tools = ScientificToolLibrary.freeze(
        Path(run_directory) / "scientific-tool-library", catalog=tool_catalog,
        resource_catalogs=resource_catalogs)
    # Service methods are used only by an actual Episode invocation; descriptor
    # preparation intentionally owns no executable workflow or model connection.
    return episode_type(None, library=library, tool_library=tools,
        child_roles=child_roles, tool_retrieval=tool_retrieval,
        contract_information_profile=contract_information_profile,
        yield_bindings=yield_bindings).as_record()


__all__ = ["prepare_scientific_binding"]
