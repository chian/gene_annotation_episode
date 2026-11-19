"""The run-frozen instruction libraries as a declared service of the run
(``ctx.services['instruction_libraries']``).

A run reads two libraries of text that are frozen before it starts: the launch instructions (how to use each
resource; ``instructions/launch_instructions.py``, ``LaunchInstructions``) and the tool knowledge (how to use each
tool; ``tools/tool_knowledge.py``, ``ToolKnowledge``). They are files outside the Store. The run's caller names
both frozen directories in the service's factory; an episode names neither a directory nor a library class.

A decision reads through the service's read handle, so what it showed the model is recorded with the decision:
``.read('launch_instruction_library')`` and ``.read('tool_knowledge')`` (each library's listing),
``.read('catalog')`` (the lookup operations of both), ``.read('for_resource', configuration)`` (the resource's
configured prompt sections) and ``.read('materialize', selection)`` (the sections a commission pinned). A lookup
the model selects is one tool unit: ``execute(name, arguments)`` runs one operation of either library and returns
its outcome (``{'status', 'result', 'feedback', ...}``); the libraries never change during a run, so a unit that
runs again reads the same text.
"""
from __future__ import annotations

from ..instructions.launch_instructions import LaunchInstructions, catalog as launch_catalog
from ..tools.tool_knowledge import ToolKnowledge, catalog as knowledge_catalog


class InstructionLibraries:
    """The frozen launch instruction library and the frozen tool knowledge library of one run."""

    def __init__(self, launch_instructions_directory, tool_knowledge_directory):
        self._launch = LaunchInstructions(launch_instructions_directory)
        self._knowledge = ToolKnowledge(tool_knowledge_directory)
        self._operations = {**{entry['name']: self._knowledge for entry in knowledge_catalog()},
                            **{entry['name']: self._launch for entry in launch_catalog()}}

    def launch_instruction_library(self):
        return self._launch.context()

    def tool_knowledge(self):
        return self._knowledge.context()

    def context(self):
        return {'launch_instruction_library': self._launch.context(), 'tool_knowledge': self._knowledge.context()}

    def catalog(self):
        """The lookup operations of both libraries (name, description, input schema)."""
        return [*knowledge_catalog(), *launch_catalog()]

    def for_resource(self, configuration):
        """The launch instruction sections the resource's configuration names; ``None`` when it names none."""
        return self._launch.for_resource(configuration)

    def materialize(self, selection):
        """The text of the launch instruction sections a commission pinned."""
        return self._launch.materialize(selection)

    def entries_for_tool(self, name):
        return self._knowledge.entries_for_tool(name)

    def execute(self, name, arguments):
        """One lookup operation of the library that owns ``name``; an unknown name raises ``LookupError``."""
        if name not in self._operations:
            raise LookupError('instruction_library_operation_unknown:' + str(name))
        return self._operations[name].execute(name, arguments)


__all__ = ['InstructionLibraries']
