"""Strict reconstruction of A107 current scientific and literature private owners.

The composer admits the complete saved counterpart set before calling this
helper. Only literal current private paths are constructible here. Reopening
reads the existing frozen libraries; it selects no work and changes no receipt.
"""
from pathlib import Path

from .private_reconstruction_protocol import (
    _failure, _json_object, _same_record, verify_owner,
)


CATALOG = {
    'partner_presence_evidence': {
        'version': 'partner_presence_evidence_episode_v10',
        'required': ('library', 'tool_library', 'child_roles'),
        'optional': ('tool_retrieval', 'contract_information_profile', 'yield_bindings'),
        'parent': 'legacy_annotation',
        'roles': ('partner_presence_evidence',), 'entry_roles': ('partner_presence_evidence',),
        'owner_class': 'PartnerPresenceEvidenceEpisode',
    },
    'published_evidence_assessment': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'legacy_annotation',
        'roles': ('literature',), 'entry_roles': ('literature',),
        'owner_class': 'LiteratureEpisode',
    },
    'published_evidence_assessment/evidence_search_strategy_improvement': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'published_evidence_assessment',
        'roles': ('literature_strategy',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'published_evidence_assessment/evidence_search_strategy_improvement',
        'roles': ('literature_search',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment',
        'roles': ('literature_page',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination',
        'roles': ('literature_table',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination',
        'roles': ('literature_ordered',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination',
        'roles': ('literature_targeted',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
    'partner_presence_evidence/published_evidence_assessment': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'partner_presence_evidence',
        'roles': ('literature',), 'entry_roles': ('literature',),
        'owner_class': 'LiteratureEpisode',
    },
    'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'partner_presence_evidence/published_evidence_assessment',
        'roles': ('literature_strategy',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
    'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement',
        'roles': ('literature_search',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
    'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment',
        'roles': ('literature_page',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
    'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination',
        'roles': ('literature_table',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
    'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination',
        'roles': ('literature_ordered',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
    'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction': {
        'version': 'literature_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('reference_parent_sources', 'contract_information_profile'),
        'parent': 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination',
        'roles': ('literature_targeted',), 'entry_roles': (),
        'owner_class': 'LiteratureEpisode',
    },
}


def reconstruct(services, descriptor, *, store, journal, directory, tool_registry,
                execution_backend=None):
    """Reconstruct one already counterpart-admitted current private owner.

    The full descriptor set belongs to the composer's strict preflight. These
    local checks also reject malformed or unknown single-owner requests before
    a constructor or frozen-library read. Caller services/resources remain the
    actual supplied instances; descriptors never supply executable callbacks.
    """
    record = _json_object(descriptor, 'episode_bindings')
    name = record.get('binding_id')
    reference = name if isinstance(name, str) and name else 'episode_bindings'
    if not isinstance(name, str) or name not in CATALOG:
        raise _failure('unavailable_binding', reference)
    declaration = CATALOG[name]
    if (set(record) != {'version', 'binding_id', 'configuration'}
            or record['version'] != declaration['version']):
        raise _failure('unavailable_binding', reference)
    configuration = record['configuration']
    required, optional = set(declaration['required']), set(declaration['optional'])
    if (type(configuration) is not dict or not required <= configuration.keys()
            or configuration.keys() - required - optional):
        raise _failure('unavailable_binding', reference)
    try:
        if name == 'partner_presence_evidence':
            if directory is None:
                raise _failure('unavailable_binding', reference)
            from .partner_presence_evidence_library import PartnerPresenceEvidenceLibrary
            from .scientific_tool_library import ScientificToolLibrary
            from .partner_presence_evidence.episode import PartnerPresenceEvidenceEpisode
            library = PartnerPresenceEvidenceLibrary(Path(directory) / 'scientific-process-library')
            _same_record(library.as_record(), configuration['library'], reference)
            tools = ScientificToolLibrary(Path(directory) / 'scientific-tool-library')
            _same_record(tools.as_record(), configuration['tool_library'], reference)
            binding = PartnerPresenceEvidenceEpisode(services, library=library, tool_library=tools,
                child_roles=configuration['child_roles'],
                tool_retrieval=configuration.get('tool_retrieval'),
                contract_information_profile=configuration.get('contract_information_profile'),
                yield_bindings=configuration.get('yield_bindings'))
        elif name == 'published_evidence_assessment':
            from .published_evidence_assessment.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'published_evidence_assessment/evidence_search_strategy_improvement':
            from .published_evidence_assessment.evidence_search_strategy_improvement.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment':
            from .published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination':
            from .published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction':
            from .published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement':
            from .published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction':
            from .published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'partner_presence_evidence/published_evidence_assessment':
            from .partner_presence_evidence.published_evidence_assessment.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement':
            from .partner_presence_evidence.published_evidence_assessment.evidence_search_strategy_improvement.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment':
            from .partner_presence_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination':
            from .partner_presence_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction':
            from .partner_presence_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement':
            from .partner_presence_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        elif name == 'partner_presence_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction':
            from .partner_presence_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction.episode import LiteratureEpisode
            binding = LiteratureEpisode(services,
                outcome_page_size=configuration['outcome_page_size'],
                reference_parent_sources=configuration.get('reference_parent_sources'),
                contract_information_profile=configuration.get('contract_information_profile'))
        else:
            # Catalogue/constructor divergence is an unavailable owner, never a
            # shared-role fallback or a dynamically selected module path.
            raise _failure('unavailable_binding', reference)
        verify_owner(binding, record, declaration, axis_package=__package__)
        return binding
    except (OSError, TypeError, ValueError, KeyError, AttributeError) as error:
        raise _failure('unavailable_binding', reference) from error


__all__ = ['CATALOG', 'reconstruct']
