"""The A107 partner grader operations as an episode offers them to the model, restored from
``root/a107/library/partner_source_contracts.py`` at ``60889621e`` (``population_catalog_entries``,
``fact_sources``): the owner's description of each grader operation, its input schema, and the meaning of the partner
sheet's cells. Every literature episode that runs the partner graders offers these entries; each episode's tool calls
``literature_partner_storage.populate_partner_sheet``.

The witness ``quote`` of an input schema is not the model's: the model selects source locations and the host reads
the quotation (``source_location_inputs``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.partner_presence_evidence.literature_partner_operand_information import (
    partner_source_population_schema_with_information)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.literature_partner_sheet_records import (
    partner_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import (
    source_location_inputs)

# Owner's grading decision (row 3): censor domains are not confidence intervals; bypass and partner swaps do not
# establish necessity.
POPULATE_DESCRIPTION = 'Populate source experimental partner-removal and addback components from received retained measurements and exact source witnesses. Preserve directed molecule/partner roles, nitrogen and other nonpartner conditions, normalization identity, physical measurement identity and reported spread meanings. Incompatible or incomplete comparisons keep native values and explicit unknown components. Censor domains are not confidence intervals; chemical bypass and partner swaps do not establish universal partner necessity, genomic presence, target transfer or annotation credit.'
# Owner's grading decision (row 4): source-defined activity units are tied to their endpoint, no universal U
# conversion, a repeated representation is not a new measurement.
SOURCE_POPULATE_DESCRIPTION = 'Populate the same experimental partner components directly from selected literal source spans. Select complete rate/limit tokens, native units, spread meanings and source-bound entity/physical-measurement identities; do not supply scientific numbers or a prepared numeric JSON dataset. For source-defined activity units such as U/mg, select the endpoint-specific definition, quantity, molecular entity and time basis; no universal U conversion is assumed. Deterministic readers preserve original tokens, convert supported rate units and retain unknown normalization, conditions or observation identity. A repeated representation is not a new measurement. No sampling uncertainty, universal necessity, target correspondence or annotation credit is inferred.'
# Owner's grading decision (row 6): what the partner sheet's cells record; native rates survive unavailable
# comparisons and bounds are not sampling confidence.
PARTNER_CELLS_MEANING = 'Saved experimental partner-removal and addback components with actual molecule/partner identities, nonpartner-condition comparisons, normalization, physical observation identity and reported spread meanings. Native rates survive unavailable controlled comparisons. Bounds condition on supplied censor domains and exact reported means; they are not sampling confidence. Directed condition-specific dependence does not establish universal necessity, genomic presence, coexpression, target correspondence or annotation credit.'

# The model's tool name (no dots) -> the grader operation.
POPULATION = {'literature_partner_populate': 'literature.partner.populate',
              'literature_partner_source_populate': 'literature.partner.source.populate'}


def population_catalog_entries():
    """The two grader operations: name, the owner's description and the closed input schema."""
    return ({'name': 'literature.partner.populate', 'description': POPULATE_DESCRIPTION,
             'input_schema': partner_population_schema(include_assessment=True)},
            {'name': 'literature.partner.source.populate', 'description': SOURCE_POPULATE_DESCRIPTION,
             'input_schema': partner_source_population_schema_with_information()})


def population_tools():
    """The entries as the model is shown them, by tool name, each input schema with source locations."""
    entries = {entry['name']: entry for entry in population_catalog_entries()}
    return [{'name': name, 'description': entries[operation]['description'],
             'input_schema': source_location_inputs(entries[operation]['input_schema'])}
            for name, operation in POPULATION.items()]


def grading_instructions(partner_requested):
    """The grader text every decision of a partner-grading episode carries: the partner-grading lead when the parent
    requested partner components (the old ``selected_family`` 'partner'), the owner's filling instructions of the
    partner sheet (``PARTNER_TASK``), and what the sheet's cells mean, paired with the grader operations as the old
    ``population_family_specs`` paired ``PARTNER_TASK`` with ``literature_partner_cells``."""
    from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_partner_prompt import (
        PARTNER_LEAD, PARTNER_TASK)
    lead = PARTNER_LEAD + '\n\n' if partner_requested else ''
    return ('\nLiterature partner grading (tools literature_partner_populate and literature_partner_source_populate, '
            'grader partner_requirement, sheet literature_partner_cells).\n' + lead + PARTNER_TASK
            + '\n\nThe saved sheet (literature_partner_cells): ' + PARTNER_CELLS_MEANING + '\n')
