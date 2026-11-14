"""Original improvement iterator/provider/action and shared source protocol."""
from .. import runtime as _original_runtime
from .task_next import next
from .provider import call
from .action import execute
from .to_parent import finish
from .instructions import instructions

class ImprovementTask(_original_runtime._annotation_source_base):
    next = next
    call = call
    execute = execute
    finish = finish
    instruction_composer = staticmethod(instructions)
