"""Prepare a caller descriptor without starting a model, child or tool job."""
from pathlib import Path

from .scientific_process_episodes import ScientificProcessEpisodes
from .scientific_process_library import ScientificProcessLibrary
from .scientific_tool_library import ScientificToolLibrary


def prepare_scientific_binding(*, run_directory, source_directory, tool_catalog, child_roles,
                               tool_retrieval=None):
    library = ScientificProcessLibrary.freeze(
        Path(run_directory) / "scientific-process-library", source=source_directory)
    tools = ScientificToolLibrary.freeze(
        Path(run_directory) / "scientific-tool-library", catalog=tool_catalog)
    # Service methods are used only by an actual Episode invocation; descriptor
    # preparation intentionally owns no executable workflow or model connection.
    return ScientificProcessEpisodes(None, library=library, tool_library=tools,
        child_roles=child_roles, tool_retrieval=tool_retrieval).as_record()


__all__ = ["prepare_scientific_binding"]
