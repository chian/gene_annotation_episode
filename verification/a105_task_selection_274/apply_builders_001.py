from pathlib import Path
p=Path('gene_annotation_episode/literature_experimental_prompt.py');s=p.read_text()
s=s.replace('from collections.abc import Mapping\n','from collections.abc import Mapping\nfrom .literature_task_selection import selected_literature_task_sections\n',1)
s=s.replace('def _task(state, instructions):','def _task(state, instructions, *, selected_sections=None):',1)
a=s.index('    if _measurement_comparison.task_relevant(state)',s.index('def _task('));b=s.index("    profile = ",a)
s=s[:a]+'''    sections = selected_literature_task_sections(state) if selected_sections is None else selected_sections
    for aspect, task in sections:
        if task not in normalized:
            _section(parts, "Selected scientific instructions: " + aspect.removeprefix('literature_').removesuffix('_cells').replace('_', ' '), task)
'''+s[b:]
a=s.index('    # These are presentation copies',s.index('def render_literature_experimental_prompt'))
s=s[:a]+'''    # Select using the original actual assignments, declarations and completed
    # lookups before any numerical-return presentation compaction/sanitization.
    sections = selected_literature_task_sections(state, lookup_results)
    if state.get("literature_experimental_work", {}).get("aspect") == "reference_evidence_parent":
        from .literature_reference_parent_prompt import render_reference_evidence_parent_prompt
        return render_reference_evidence_parent_prompt(state, instructions, lookup_results=lookup_results)
'''+s[a:]
a=s.index('    if state.get("literature_experimental_work", {}).get("aspect") == "reference_evidence_parent":',s.index('    # These are presentation copies'))
b=s.index("    if state.get('contract_information_profile')",a)
s=s[:a]+s[b:]
s=s.replace('_task(state, instructions), lookup_results)', '_task(state, instructions, selected_sections=sections), lookup_results)')
s=s.replace('_task(state, instructions) + "\\n\\n"','_task(state, instructions, selected_sections=sections) + "\\n\\n"')
p.write_text(s)
p=Path('gene_annotation_episode/literature_reference_parent_prompt.py');s=p.read_text()
s=s.replace('from .literature_numerical_return_presentation import state_view\n','from .literature_numerical_return_presentation import state_view\nfrom .literature_task_selection import selected_literature_task_sections\n',1)
s=s.replace('def _task(state, instructions, descriptor):','def _task(state, instructions, descriptor, *, selected_sections=None):',1)
a=s.index('    from .literature_measurement_comparison_render import',s.index('def _task('));b=s.index('    additional = ',a)
s=s[:a]+'''    sections = selected_literature_task_sections(state) if selected_sections is None else selected_sections
    for aspect, task in sections:
        if task not in normalized:
            _section(parts, "Selected scientific instructions: " + aspect.removeprefix('literature_').removesuffix('_cells').replace('_', ' '), task)
'''+s[b:]
a=s.index('    from .literature_rate_observation_prompt import grid_state_view',s.index('def render_reference_evidence_parent_prompt'))
s=s[:a]+'''    sections = selected_literature_task_sections(state, lookup_results)
'''+s[a:]
s=s.replace('_task(state, instructions, descriptor), lookup_results)', '_task(state, instructions, descriptor, selected_sections=sections), lookup_results)')
s=s.replace('_task(state, instructions, descriptor) + "\\n\\n"','_task(state, instructions, descriptor, selected_sections=sections) + "\\n\\n"')
p.write_text(s)
