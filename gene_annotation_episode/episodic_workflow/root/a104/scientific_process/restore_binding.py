"""Restore the caller's pinned scientific construction from this run only."""
from pathlib import Path


def restore_scientific_binding(services, *, descriptor, directory):
    from .episode import ScientificProcessEpisode
    from ..scientific_process_library import ScientificProcessLibrary
    from ..scientific_tool_library import ScientificToolLibrary
    from ..episode_composition import _failure, _same_record, scientific_binding_compatible
    reference = 'scientific_process'
    if directory is None:
        raise _failure('unavailable_binding', reference)
    try:
        if descriptor.get('version') not in {'scientific_process_episodes_v5',
                'scientific_process_episodes_v6', 'scientific_process_episodes_v7',
                'scientific_process_episodes_v8', 'scientific_process_episodes_v9',
                'scientific_process_episodes_v10', 'scientific_process_episode_v10'}:
            raise _failure('unavailable_binding', reference)
        configuration = descriptor['configuration']
        expected = {'library', 'tool_library', 'child_roles'}
        if (descriptor['version'] == 'scientific_process_episodes_v6'
                or descriptor['version'] in {'scientific_process_episodes_v7', 'scientific_process_episodes_v8',
                    'scientific_process_episodes_v9', 'scientific_process_episodes_v10',
                    'scientific_process_episode_v10'}
                and 'tool_retrieval' in configuration):
            expected.add('tool_retrieval')
        if descriptor['version'] in {'scientific_process_episodes_v8', 'scientific_process_episodes_v9',
                'scientific_process_episodes_v10', 'scientific_process_episode_v10'} and 'contract_information_profile' in configuration:
            expected.add('contract_information_profile')
        if descriptor['version'] in {'scientific_process_episodes_v10', 'scientific_process_episode_v10'} and 'yield_bindings' in configuration:
            expected.add('yield_bindings')
        if set(configuration) != expected:
            raise _failure('unavailable_binding', reference)
        library = ScientificProcessLibrary(Path(directory)/'scientific-process-library')
        _same_record(library.as_record(), configuration['library'], reference)
        tools = ScientificToolLibrary(Path(directory)/'scientific-tool-library')
        _same_record(tools.as_record(), configuration['tool_library'], reference)
        binding = ScientificProcessEpisode(services, library=library, tool_library=tools,
            child_roles=configuration['child_roles'],
            tool_retrieval=configuration.get('tool_retrieval'),
            contract_information_profile=configuration.get('contract_information_profile'),
            yield_bindings=configuration.get('yield_bindings'))
        if not scientific_binding_compatible(binding.as_record(), descriptor):
            raise _failure('identity_conflict', reference)
        return binding
    except (OSError, TypeError, ValueError, KeyError, AttributeError) as error:
        raise _failure('unavailable_binding', reference) from error
