"""A107 partner source task selection from this episode's own assignments."""
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.a107.library.partner_source_contracts import population_family_specs

def population_task_metadata_specs():
    from gene_annotation_episode.episodic_workflow.root.a107.literature_partner_storage import LiteraturePartnerRepository
    from gene_annotation_episode.episodic_workflow.root.a107.library.literature_partner_sheet_records import PROVIDER
    yield ('literature_partner_cells', LiteraturePartnerRepository.operations_table, PROVIDER, (LiteraturePartnerRepository.record_version,))

def selected_literature_task_sections(state, lookup_results=()):
    if not isinstance(state, Mapping):
        return ()
    assignment = state.get('literature_assignment')
    selected = isinstance(assignment, Mapping) and 'requested_partner_components' in assignment
    if not selected:
        form = state.get('requested_form')
        selected = isinstance(form, Mapping) and 'literature_partner_cells' in str(form)
    if not selected:
        return ()
    source, task, *_ = population_family_specs()[0]
    return ((source, task),)
