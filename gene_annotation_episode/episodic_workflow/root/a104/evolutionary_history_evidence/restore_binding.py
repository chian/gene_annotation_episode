"""Restore the caller's pinned scientific construction from this run only."""
from pathlib import Path


def restore_scientific_binding(services, *, descriptor, directory):
    from .episode import EvolutionaryHistoryEvidenceEpisode
    from ..evolutionary_history_evidence_library import EvolutionaryHistoryEvidenceLibrary
    from ..scientific_tool_library import ScientificToolLibrary
    from ..episode_composition import _failure, _same_record, scientific_binding_compatible
    reference = 'evolutionary_history_evidence'
    if directory is None:
        raise _failure('unavailable_binding', reference)
    try:
        if descriptor.get('version') not in {'evolutionary_history_evidence_episodes_v5',
                'evolutionary_history_evidence_episodes_v6', 'evolutionary_history_evidence_episodes_v7',
                'evolutionary_history_evidence_episodes_v8', 'evolutionary_history_evidence_episodes_v9',
                'evolutionary_history_evidence_episodes_v10', 'evolutionary_history_evidence_episode_v10'}:
            raise _failure('unavailable_binding', reference)
        configuration = descriptor['configuration']
        expected = {'library', 'tool_library', 'child_roles'}
        if (descriptor['version'] == 'evolutionary_history_evidence_episodes_v6'
                or descriptor['version'] in {'evolutionary_history_evidence_episodes_v7', 'evolutionary_history_evidence_episodes_v8',
                    'evolutionary_history_evidence_episodes_v9', 'evolutionary_history_evidence_episodes_v10',
                    'evolutionary_history_evidence_episode_v10'}
                and 'tool_retrieval' in configuration):
            expected.add('tool_retrieval')
        if descriptor['version'] in {'evolutionary_history_evidence_episodes_v8', 'evolutionary_history_evidence_episodes_v9',
                'evolutionary_history_evidence_episodes_v10', 'evolutionary_history_evidence_episode_v10'} and 'contract_information_profile' in configuration:
            expected.add('contract_information_profile')
        if descriptor['version'] in {'evolutionary_history_evidence_episodes_v10', 'evolutionary_history_evidence_episode_v10'} and 'yield_bindings' in configuration:
            expected.add('yield_bindings')
        if set(configuration) != expected:
            raise _failure('unavailable_binding', reference)
        library = EvolutionaryHistoryEvidenceLibrary(Path(directory)/'scientific-process-library')
        _same_record(library.as_record(), configuration['library'], reference)
        tools = ScientificToolLibrary(Path(directory)/'scientific-tool-library')
        _same_record(tools.as_record(), configuration['tool_library'], reference)
        binding = EvolutionaryHistoryEvidenceEpisode(services, library=library, tool_library=tools,
            child_roles=configuration['child_roles'],
            tool_retrieval=configuration.get('tool_retrieval'),
            contract_information_profile=configuration.get('contract_information_profile'),
            yield_bindings=configuration.get('yield_bindings'))
        if not scientific_binding_compatible(binding.as_record(), descriptor):
            raise _failure('identity_conflict', reference)
        return binding
    except (OSError, TypeError, ValueError, KeyError, AttributeError) as error:
        raise _failure('unavailable_binding', reference) from error
