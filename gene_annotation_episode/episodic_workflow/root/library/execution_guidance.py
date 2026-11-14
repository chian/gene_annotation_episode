"""Original execution recipe text for Root's selected operation contracts."""
from pathlib import Path


ROOT = Path(__file__).with_name('execution_instruction_library')


def recipe(name, resource):
    if resource not in ('api', 'local', 'hpc'):
        raise ValueError('actual_execution_resource_kind_required')
    sections = ['planning', resource]
    # All catalog entries get the common recipe. Native homology has additional
    # result and workload operands; this does not manufacture an HPC callable.
    if any(word in name.lower() for word in ('blast', 'hmmer', 'phmmer', 'hmmsearch', 'hmmscan', 'homology')):
        sections.append('homology')
    return 'Execution recipe for '+name+' ('+resource+')\n\n' + '\n\n'.join(
        (ROOT/(section+'.md')).read_text().strip() for section in sections)


__all__ = ['recipe']
