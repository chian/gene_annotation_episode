"""Compose this prediction task's original goal and selected library guidance."""


def instructions(source, context):
    binding = source.workflow.specialist(source)
    text = binding.instructions(source.workflow.binding_context(source))
    if 'tool_knowledge' in context:
        text += source.workflow.knowledge.instructions
    if 'launch_instruction_library' in context:
        text += source.workflow.launch_instructions.instructions
    return text
