"""The task: decide which published evidence bears on the assigned scientific question. The model searches for and
acquires sources through the acquisition tools, reads them through the access tools, commits reasoning on what they
say (and, for a verified-source-leads commission, validated source leads), commissions a search strategy
investigation (child ``literature_strategy``), constructs a BV-BRC intervention analysis contract, commissions the
launch of a permitted execution request (child ``launch``) and the acquisition of its results (child ``results``),
and grades what it reads on the A106 sheets.

The base investigation text and the reasoning-commit requirement are the library's A106
``literature_investigation_prompt`` texts (the old ``INSTRUCTIONS`` source).

Carried from the old task.py, task_decision.py, task_instructions.py, source_contracts.py, source_operations.py,
source_references.py, to_child_*.py of role ``literature`` at 97308b94c. One unit is one model-selected tool call or
one commissioned child. The task always offers a unit and never ends the Episode: only the yield controller does. The
old ``wait`` and ``redeliver_report`` actions are not carried (a child completes inside the unit that commissioned
it). The population route of the old episode is carried through the library's
``literature_population_route`` (the population operations, the intervention grading sheet G1, the A106 final
subscore G2 and the automatic score judgment); the old ``report`` tool is gone: what returns is the credit and the
controlled features of the G1 and G2 sheets.

The old ``analysis_children`` offered ``launch`` and ``results`` only when an execution binding was configured, and the
old ``contract_catalog`` offered ``literature.intervention_analysis.contract`` only when that binding had a BV-BRC
TnSeq or RNASeq AppService resource. The run's configuration of its execution resources is outside the Store: it is
the declared service ``execution_binding``, whose value ``execution_resources`` ({'resource_ids',
'intervention_contract_resource_ids'}) a decision reads (a recorded read) and whose ``resource(resource_id)`` the
contract tool uses. No such service exists in the repository yet: a run that links this episode must supply it."""
from copy import deepcopy

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.perturbation_evidence.experimental_database_acquisition import (
    catalog as experimental_database_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sequence_and_context_sources.perturbation_evidence.ncbi_sra_acquisition import (
    sra_file_argument_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.bvbrc_intervention_contracts import (
    parameters_schema as intervention_parameters_schema, selection_schema as intervention_selection_schema)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_task_credit import (
    _resolve, lead_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.perturbation_evidence.literature_assay_inputs import (
    _Sources)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_sequence_discovery import (
    identity_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.perturbation_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.readers.perturbation_evidence.source_locations import (
    locate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.readers.service_calls.perturbation_evidence.bvbrc_appservice_adapters import (
    selected_adapter)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.perturbation_evidence.source_sequences import (
    scan_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage import literature_population_route as route
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_discovery_values import (
    references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
    RECORD_SCHEMAS, REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.experimental_database_records import (
    reader_schema as experimental_records_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_and_context_sources.perturbation_evidence.geo_tools import (
    geo_tool_contract)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_and_context_sources.perturbation_evidence.ncbi_entrez_tools import (
    ncbi_entrez_tool_contract)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

# The roles of the old ``_CHILDREN['literature']`` and ``analysis_children``, under their old names.
CHILD_SLOTS = {
    'literature_strategy': 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement',
    'launch': 'perturbation_evidence/published_evidence_assessment/execution_job_submission',
    'results': 'perturbation_evidence/published_evidence_assessment/execution_result_acquisition',
}
EXECUTION_SLOTS = ('launch', 'results')
SERVICES = ('execution_binding',)
ROLE = 'literature'      # the old role of this episode (the library repositories read it)
CONTRACT_TOOL = 'literature_intervention_analysis_contract'

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}
REPRESENTATION = {'enum': ['text', 'original', 'stdout', 'stderr']}


# The access tools of the old ``_ACCESS_TOOLS``; descriptions as the tool library states them.
DESCRIPTIONS = {
    'state.query':
        'Read an exact page of typed scientific records, current revisions, or records referring to actual references. Follow the returned next_query for the same selection and order. Exact refs is a separate mode and cannot be combined with page selectors.',
    'source.read':
        'Read a bounded UTF-8 byte window from an actual source. Choose original for retained source bytes, including XML tables/headings omitted by a paragraph projection; text selects that projection when available. Explicit stdout/stderr select retained native stream bytes when present, without falling back to another representation. Returned artifact/offsets support exact anchors.',
    'source.locate':
        'Locate an exact supplied literal quote in an explicitly received original or text source representation. Return UTF-8 byte witnesses, unchanged neighboring context and bounded match continuation. Multiple occurrences remain separate. No normalization, scientific interpretation, measurement parsing or evidence credit is performed; no literal match means only no match in the examined bytes.',
    'source.sequence.scan':
        'Recognize candidate protein sequence blocks in received source text/XML/HTML, preserving original UTF-8 positions. Normalize case, whitespace, numbering and soft hyphens; report exact containment, extra residues and literal differences. For numbered GenBank/GenPept blocks, include the ORIGIN marker and contiguous residue rows in the selected window. Hard hyphens remain explicit, with conditional correspondence, until their byte offsets are selected as formatting_hyphen_offsets after inspecting the layout. A document boundary may require an overlapping window. No biological gaps, tags or substitutions are silently removed.',
    'source.sequence.references':
        'Read a page of publication identifiers, titles and reported citation scopes from a received sequence-identity response. Reverify full sequence equality for the selected record. Citation metadata supplies leads; it does not establish experimental results.',
    'source.experimental.records':
        'Inspect one page of a received experimental database response. Return native assay records, source measurement selectors and literal record links. Optional contains and contains_all filter retained rows by one or several literal terms, including their native headers and section labels. Record and whole-page link continuations are separate. These records locate the characterized homolog and its source evidence; metadata and deposited scores retain their native meanings.',
    'image.view':
        'Inspect one explicitly selected frame of a registered scientific image. The next reasoning call receives its actual pixels and exact source/frame metadata. Stored axes are preserved; no contrast adjustment, resizing, interpretation or annotation is performed. An optional RGB conversion is explicit and recorded; original bytes remain intact.',
    'source.archive.members':
        'Inventory one page of an actual ZIP/TAR source. Member IDs preserve ordinal identity, including duplicate names; no members are extracted or selected for you.',
    'source.archive.extract':
        "Extract exactly one inventoried regular member to a source artifact; never follow a member's host path or link. Original archive and member identity remain attached.",
    'source.xlsx.sheets':
        'Read the actual sheet names, relationship keys and package parts of a retained XLSX source. No sheet or biological interpretation is selected for you.',
    'source.xlsx.rows':
        'Read a selected page of actual XLSX rows, optionally matching literal cell values. Select sheet_key from source.xlsx.sheets; row offsets count matching rows, while returned row numbers/cell addresses retain native identity. Header row is caller-selected or null. Original numeric/date lexical values, styles, formulas and caches remain distinct; no formula is recalculated or biology inferred.',
    'source.pdf.info':
        'Read native PDF information and physical page count for a selected actual source; no biological interpretation.',
    'source.pdf.text':
        'Extract a selected physical PDF page or contiguous page range as a reusable UTF-8 text derivative. page is the first page; optional last_page is inclusive and defaults to page. Use source.pdf.info for the physical page count, then source.locate on the extracted text to find a section without guessing pages. Native page breaks and the selected range are retained. Byte offsets refer to this text derivative, not the PDF. No OCR or interpretation is performed.',
    'source.pdf.page':
        'Render one explicitly selected physical PDF page as a reusable PNG source. Rendering does not by itself supply image input to a model or interpret a figure.',
    'execution.estimate':
        'Obtain recorded duration expectations before a proposed native alignment or workbook selection. Uses the same operands, actual settings and caller resource as execution. Creates no native job or scientific evidence; missing history stays unknown. This is an optional information tool, not a scheduling or continuation decision.',
}

# The acquisition tools of the old ``_ACQUISITION_TOOLS`` and the NCBI entrez, sequence, GEO and SRA file tools the
# old catalog allowed; descriptions as the tool library states them. The entrez and GEO tools, the SRA file schema,
# the sequence-identity schema and the experimental-database tools are the library's own contracts.
DESCRIPTIONS.update({
    'public.literature.search':
        'Acquire one literature search page. Read the actual source before extracting biological evidence.',
    'public.literature.read':
        "Acquire an actual open article, an ordered paragraph projection and separate cited-publication metadata. Bibliography identifiers and paragraph links support further source discovery; they do not identify the acquired article or establish a cited experiment's result. Read the retained original XML with source.read representation=original for tables, headings and other omitted elements.",
    'public.literature.sequence_identity':
        'Find publication leads from a supplied protein sequence: retrieve one UniProtKB checksum-search page and verify each complete residue string. Return all equal records on the page, names, organisms, citation counts and explicit continuation. The optional reviewed filter selects database curation status. These are source identities and discovery metadata; experimental evidence requires reading the actual publications.',
    'public.ncbi.search':
        'Search one page of a named NCBI collection for selected references, taxa or sample context.',
    'public.pmc.versions':
        'List one actual public PMC cloud version page. No version is chosen as latest/preferred; source versions can differ in manuscript status and can change in place.',
    'public.pmc.files':
        "Read the selected advertised version's actual file inventory and its listed JSON metadata. Returns reusable listed-object/advertised-asset IDs; optional metadata failure preserves listed files. Choose a version ID, not a URL or guessed filename.",
    'public.pmc.asset':
        'Acquire exactly one selected advertised/listed PMC asset ID. Preserve actual HTTP bytes, original advertisement and checksums; source content is evidence, not target annotation.',
    'public.ncbi.sequence':
        'Acquire an external GenBank/GenPept sequence and its original feature context; optional nucleotide interval uses zero-based half-open coordinates.',
    'public.ncbi.sra.file':
        'Acquire exactly one explicitly selected SRA or FASTQ file advertised in a received experiment-package XML File, within the supplied byte limit. Select its exact native package, run, file and URL occurrence. Return only acquired, source_ref, data_ref and failure_code. The file is retained for later analysis; archive decoding is a separate operation.',
})
# Entries of the library contracts that carry more than a description and an input schema (``resources`` and
# ``instructions`` of the entrez and GEO tools) are shown to the model as the old catalog showed them.
EXTRAS = {}
_EXPERIMENTAL = experimental_database_catalog()
for _name, _contract in {**_EXPERIMENTAL, 'public.ncbi.entrez': ncbi_entrez_tool_contract(),
                         'public.ncbi.geo': geo_tool_contract()}.items():
    DESCRIPTIONS[_name] = _contract['description']
    EXTRAS[_name] = {key: value for key, value in _contract.items()
                     if key not in ('name', 'description', 'input_schema')}



# python tool name -> the library's tool name (a tool name here is lowercase letters, digits and underscores)
ACCESS_LIBRARY_NAMES = {
    'state_query': 'state.query', 'source_read': 'source.read', 'source_locate': 'source.locate',
    'source_sequence_scan': 'source.sequence.scan', 'source_sequence_references': 'source.sequence.references',
    'source_experimental_records': 'source.experimental.records', 'image_view': 'image.view',
    'source_archive_members': 'source.archive.members', 'source_archive_extract': 'source.archive.extract',
    'source_xlsx_sheets': 'source.xlsx.sheets', 'source_xlsx_rows': 'source.xlsx.rows',
    'source_pdf_info': 'source.pdf.info', 'source_pdf_text': 'source.pdf.text', 'source_pdf_page': 'source.pdf.page',
    'execution_estimate': 'execution.estimate'}
ACQUISITION_LIBRARY_NAMES = {name.replace('.', '_'): name for name in (
    'public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
    'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset',
    *_EXPERIMENTAL, 'public.ncbi.entrez', 'public.ncbi.sequence', 'public.ncbi.geo', 'public.ncbi.sra.file')}
LIBRARY_NAMES = {**ACCESS_LIBRARY_NAMES, **ACQUISITION_LIBRARY_NAMES}
ACQUISITION_NAMES = tuple(ACQUISITION_LIBRARY_NAMES)
# Tools whose source reads are bound to the records this episode holds (the old ``authorization``).
HELD_SOURCE_TOOLS = ('source.locate', 'source.sequence.scan', 'source.sequence.references',
                     'source.experimental.records')


INPUT_SCHEMAS = {
    'state.query': obj({
        'kind': {'enum': list(RECORD_SCHEMAS) + ['subject']}, 'offset': INTEGER, 'limit': POSITIVE,
        'refs': {**REFS,
                 'description': 'Exact reference mode: supply refs alone, including an empty array for no records. '
                                'Omit kind, offset, limit, current_only and references in this mode.'},
        'current_only': {'type': 'boolean'},
        'references': {'type': 'array', 'items': REF, 'minItems': 1,
                       'description': "Select records that refer to any supplied ID through reference fields or "
                                      "provenance anchors. This does not match a record's own ID; to read known "
                                      "records themselves, supply refs alone instead."}}, required=[]),
    'source.read': obj({'source_ref': REF, 'offset': INTEGER, 'limit': POSITIVE,
                        'representation': {'enum': ['text', 'original', 'stdout', 'stderr']}}, ['source_ref']),
    'source.locate': locate_schema(),
    'source.sequence.scan': scan_schema(),
    'source.sequence.references': references_schema(),
    'source.experimental.records': experimental_records_schema(),
    'image.view': obj({'source_ref': REF, 'frame': INTEGER, 'colour_conversion': {'enum': ['preserve', 'rgb']}},
                      ['source_ref']),
    'source.archive.members': obj({'source_ref': REF, 'offset': INTEGER, 'limit': POSITIVE}, ['source_ref']),
    'source.archive.extract': obj({'member_ref': REF}),
    'source.xlsx.sheets': obj({'source_ref': REF}),
    'source.xlsx.rows': obj({
        'source_ref': REF, 'sheet_key': TEXT, 'offset': INTEGER, 'limit': INTEGER,
        'header_row': {'type': ['integer', 'null'], 'minimum': 1},
        'where': {**obj({'column': {'type': ['string', 'null'], 'pattern': '^[A-Z]+$'},
                         'match': {'enum': ['equals', 'contains']}, 'value': TEXT,
                         'case_sensitive': {'type': 'boolean'}}), 'type': ['object', 'null']}}),
    'source.pdf.info': obj({'source_ref': REF}),
    'source.pdf.text': obj({'source_ref': REF, 'page': POSITIVE, 'last_page': POSITIVE,
                            'layout': {'enum': ['reading_order', 'layout', 'raw']}}, ['source_ref', 'page']),
    'source.pdf.page': obj({'source_ref': REF, 'page': POSITIVE, 'dpi': {'type': 'number', 'exclusiveMinimum': 0}},
                           ['source_ref', 'page']),
}
# ``execution.estimate`` is offered for the workbook tools only, and only when the run has timing statistics.
INPUT_SCHEMAS['execution.estimate'] = {'anyOf': [
    obj({'tool': {'const': name}, 'arguments': INPUT_SCHEMAS[name]}) for name in ('source.xlsx.sheets', 'source.xlsx.rows')]}

INPUT_SCHEMAS.update({
    'public.literature.search': obj({'query': TEXT, 'size': POSITIVE, 'cursor': TEXT}, ['query']),
    'public.literature.read': obj({'pmcid': TEXT}),
    'public.literature.sequence_identity': identity_schema(),
    # The old catalog restricted the NCBI search to the literature collection.
    'public.ncbi.search': obj({'database': {'enum': ['pubmed']}, 'term': TEXT, 'size': POSITIVE, 'offset': INTEGER},
                              ['database', 'term']),
    'public.pmc.versions': obj({'pmcid': {'type': 'string', 'pattern': '^PMC[0-9]+$'}, 'continuation_token': TEXT},
                               ['pmcid']),
    'public.pmc.files': obj({'version_ref': REF, 'continuation_token': TEXT}, ['version_ref']),
    'public.pmc.asset': obj({'asset_ref': REF}),
    'public.ncbi.sequence': obj({'accession': TEXT, 'database': {'enum': ['protein', 'nuccore']}, 'start': INTEGER,
                                 'end': POSITIVE}, ['accession', 'database']),
    'public.ncbi.sra.file': sra_file_argument_schema(),
    **{name: contract['input_schema'] for name, contract in _EXPERIMENTAL.items()},
    'public.ncbi.entrez': ncbi_entrez_tool_contract()['input_schema'],
    'public.ncbi.geo': geo_tool_contract()['input_schema'],
})


# What the model chooses for a child. The strategy investigation takes the records that give the question its context
# and the earlier searches' sources (the old ``strategy_assignment_v1`` without its version, which ``msg_to_child``
# supplies) and the literature task of the investigation (the old ``task_schema`` without ``credit_unit`` and
# ``yield_settings``, which ``msg_to_child`` supplies from this episode's own commission, where the old
# ``prepare_assignment`` filled them from the private yield binding). The launch takes the old
# ``execution_launch_assignment_v1`` properties; the results the old ``execution_results_assignment_v1`` ones.
REFERENCES = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
UNIQUE_REFERENCES = {'type': 'array', 'items': REF, 'uniqueItems': True}
SPAN = obj({'source_ref': REF, 'artifact_ref': REF, 'start': {'type': 'integer', 'minimum': 0},
            'end': {'type': 'integer', 'minimum': 1}})
TASK_VERSION = 'literature_local_task_v1'
STRATEGY_TASK = {'description': 'The A106 commissioned result of the strategy investigation. Select only a task '
                                'whose typed result this episode counts. A106 score computation is automatic work, '
                                'not an episode-credit task.',
                 'anyOf': [obj({'version': {'const': TASK_VERSION}, 'evidence_axis': {'const': 'A106'},
                                'kind': {'const': 'verified_source_leads'}}),
                           obj({'version': {'const': TASK_VERSION}, 'evidence_axis': {'const': 'A106'},
                                'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'},
                                'source_refs': REFERENCES}),
                           obj({'version': {'const': TASK_VERSION}, 'evidence_axis': {'const': 'A106'},
                                'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'},
                                'examined': {'type': 'array', 'minItems': 1, 'items': SPAN}})]}
OPEN_RECORD = {'type': 'object'}
COMMISSION = {
    'literature_strategy': 'Commission an investigation of which search approach is productive for the assigned '
                           'question. It names the records that give the question context (question_context_refs) '
                           'and the earlier searches whose sources it builds on (prior_search_refs, sources this '
                           'episode holds, see literature_source_custody); the literature_task is the typed answer '
                           'asked of the investigation.',
    'launch': 'Commission the launch of permitted concrete execution requests on explicit resource ids: requests '
              '(resource_id -> request), the immutable input versions, the constraints and, optionally, a pinned '
              'launch-instruction selection. It returns the references of the usable handoffs.',
    'results': 'Commission the acquisition of the original results of a launched job through its handoff '
               '(handoff_ref, a handoff this episode holds from a launch), a selector naming which results, and the '
               'API service of the original job. It returns the retained result records and, selected, the '
               'application observations (bvbrc_application_outcomes).'}

REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the examined sources and the records you hold: '
                      'extracted terms, source subjects, contexts, observations, hypotheses and assessments, each '
                      'with its exact source anchor. A commit with every section empty is rejected.')
HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier read and acquisition outcomes are shown to you as own_literature_outcomes; '
                    'that page creates no new action and does not execute or credit the historical work again.\n')
COMMISSION_GUIDANCE = ('\nCommission a search strategy investigation (literature_strategy) when a narrower question '
                       'warrants iteration: it returns its credit, the controlled features of the A106 sheets '
                       'saved below it and, for the literature task you choose for it, its typed answers as counts and '
                       'references. The input list (context.input_list) is the held sources not yet handed to a '
                       'strategy child (the assigned sources, then the sources your acquisitions produced): a source '
                       'handed to the child as a prior search is consumed (context.consumed_source_refs) and is not '
                       'offered again; the child takes only sources of the input list, and is not offered once the '
                       'list is empty.')
EXECUTION_GUIDANCE = ('\nWhen execution resources are configured (execution_resources), commission the launch of '
                      'a permitted execution request (launch) and, from the handoff it returns, the acquisition of '
                      'its results (results); the received intervention analysis rows are shown as '
                      'received_intervention_analysis_rows. literature_intervention_analysis_contract, when '
                      'offered, constructs the native adapter and requested schema for an existing BV-BRC '
                      'TnSeq/RNASeq AppService results selector; it acquires nothing.')
LEAD_GUIDANCE = ('\nFor a verified_source_leads commission, a reason selection also carries source_lead: the '
                 'inspected source, its anchored reference subject, whether it is a useful lead for the original '
                 'question and the exact witnessed byte interval. A search hit or title alone verifies nothing.')


def instructions(*, knowledge, leads, execution, launch_library):
    """The old task_instructions.instructions: the investigation text, the reasoning-commit requirement, this
    episode's goal, the tool-knowledge text when it is offered, the launch-instruction text when the library is
    configured. The decision-exchange paragraph, the pending-delivery paragraph, the wait paragraphs and the
    redeliver_report text are not carried: no such action exists."""
    text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    text += COMMISSION_GUIDANCE
    if execution['resource_ids']:
        text += EXECUTION_GUIDANCE
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    if leads:
        text += LEAD_GUIDANCE
    return text + route.GRADER_SECTION + route.RETURN_GUIDANCE


def execution_resources(ctx):
    """The configured execution resources (the old ``_execution`` binding): a recorded read of the service."""
    return ctx.services['execution_binding'].read('execution_resources')


def offered(settings, execution, opened):
    """The tools offered now: the access and acquisition tools (execution_estimate only with timing statistics
    configured), the intervention analysis contract when a configured resource has a BV-BRC intervention adapter,
    then the population tools (``open_population``, the opened population operation, the automatic score judgment)
    and the reasoning commit."""
    tools = [name for name in LIBRARY_NAMES
             if name != 'execution_estimate' or settings.get('tool_registry', {}).get('native_statistics') is not None]
    if execution['intervention_contract_resource_ids']:
        tools.append(CONTRACT_TOOL)
    return tools + route.offered_population_tools(opened) + ['reason']


def offered_slots(execution, input_list):
    """The children offered now: the old ``analysis_children`` offered ``launch`` and ``results`` only when an
    execution binding was configured; the strategy child only while the input list holds an unconsumed source."""
    return [*(['literature_strategy'] if input_list else ()), *(EXECUTION_SLOTS if execution['resource_ids'] else ())]


def reason_schema(commit_schema, leads):
    """The old reasoning_action_schema (the reason selection without the assay-grading logic of the
    population route): the typed commit and, for a verified_source_leads commission, a source_lead."""
    properties = {'commit': commit_schema}
    if leads:
        properties['source_lead'] = lead_schema()
    return source_location_inputs(obj(properties, required=['commit']))


def contract_input_schema(resource_ids):
    """The old ``contract_catalog`` input schema of ``literature.intervention_analysis.contract``."""
    return {'type': 'object', 'properties': {
        'resource_id': {'enum': list(resource_ids)}, 'parameters': intervention_parameters_schema(),
        'fields': {'type': 'array', 'minItems': 1, 'items': {'type': 'object', 'properties': {
            'field': {'type': 'string', 'minLength': 1}, 'selection': intervention_selection_schema()},
            'required': ['field', 'selection'], 'additionalProperties': False}}},
        'required': ['resource_id', 'parameters', 'fields'], 'additionalProperties': False}


CONTRACT_DESCRIPTION = (
    'Construct the exact native adapter and requested_schema for an existing AppService results selector. Select '
    'the configured resource, application, document-to-requirement bindings and result fields. For intervention '
    'operands select records with measurements and source_location members, or all members. The returned schema '
    "describes native selected fields; request bvbrc_application_outcomes in the child's typed parent report. This "
    'local information operation acquires nothing and establishes no service availability.')


def catalog(names, commit_schema, leads, execution, settings):
    """The tools the model is shown: name, description and input schema (the old catalog; every input schema
    is projected through source_location_inputs)."""
    entries = []
    population_tools = {route.OPEN, route.JUDGMENT, *route.POPULATION_NAMES}
    for name in names:
        if name in population_tools:
            entries.append(route.population_tool_entry(name, settings))
        elif name == 'reason':
            entries.append({'name': 'reason', 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(commit_schema, leads)})
        elif name == CONTRACT_TOOL:
            entries.append({'name': name, 'description': CONTRACT_DESCRIPTION, 'input_schema': source_location_inputs(
                contract_input_schema(execution['intervention_contract_resource_ids']))})
        else:
            library = LIBRARY_NAMES[name]
            entries.append({'name': name, 'description': DESCRIPTIONS[library], **EXTRAS.get(library, {}),
                            'input_schema': source_location_inputs(INPUT_SCHEMAS[library])})
    return entries


def commission_arguments(slot, input_list):
    """The arguments of a commission: the child assignment's own properties (no text passes to the child: its
    objective is fixed by its slot in ``msg_to_child``), which this episode does not fill itself (the old child assignments:
    ``strategy_assignment_v1``, ``execution_launch_assignment_v1``, ``execution_results_assignment_v1``)."""
    head = {}
    if slot == 'literature_strategy':
        # The prior searches are chosen among the input list only (the held sources no strategy child has been
        # handed); a source handed out is consumed and offered no more.
        return obj({**head, 'question_context_refs': UNIQUE_REFERENCES,
                    'prior_search_refs': {'type': 'array', 'items': {'enum': list(input_list)}, 'uniqueItems': True,
                                          'minItems': 1, 'description': 'Unconsumed sources of input_list only'},
                    'literature_task': STRATEGY_TASK})
    if slot == 'launch':
        return obj({**head, 'requests': OPEN_RECORD, 'immutable_input_versions': {'type': 'array'},
                    'constraints': OPEN_RECORD, 'launch_instructions': {'type': ['object', 'null']},
                    'input_refs': UNIQUE_REFERENCES,
                    'already_handed_off_resource_ids': {'type': 'array', 'items': TEXT}},
                   required=['requests', 'immutable_input_versions', 'constraints'])
    return obj({**head, 'handoff_ref': REF, 'selector': OPEN_RECORD, 'service': TEXT})


def commissions(execution, input_list):
    """The children the model may commission, shown with the tools (the old ``child_option_information``)."""
    return [{'slot': slot, 'description': COMMISSION[slot], 'input_schema': commission_arguments(slot, input_list)}
            for slot in offered_slots(execution, input_list)]


def selection_schema(names, commit_schema, leads, execution, settings, input_list):
    """What the model answers with: one tool and its arguments, or one commissioned child (the old action
    schema)."""
    return obj({'selection': {'anyOf': [
        *(obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
          for entry in catalog(names, commit_schema, leads, execution, settings)),
        *(obj({'kind': {'const': 'child'}, 'slot': {'const': entry['slot']}, 'arguments': entry['input_schema']})
          for entry in commissions(execution, input_list))]}})


def admitted(name, arguments):
    """The old ``_tool_arguments``: the arguments against the offered schema. A violation is a ``ContractError``.
    This role has no assigned page, so the old confinement of a reading to the page's source does not apply."""
    validate_schema(arguments, source_location_inputs(INPUT_SCHEMAS[name]))


async def run_access_tool(tool, envelope, ctx):
    """Execute one access or acquisition tool. A contract error is returned as an ``invalid`` outcome with
    ``arguments_or_reference`` feedback, as the old ``execute`` did; the outcome is the unit's outcome like any other."""
    name = LIBRARY_NAMES[tool]
    arguments, scope = envelope['arguments'], envelope['scope']
    try:
        admitted(name, arguments)
    except (ContractError, ValidationError) as error:
        detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
        return {'status': 'invalid',
                'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
                'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}
    registry = ToolRegistry(ctx.store, **ctx.settings.get('tool_registry', {}))
    permitted = tuple(ctx.store.refs()) if name in HELD_SOURCE_TOOLS else None
    try:
        return await registry.execute_async(name, arguments, scope=scope, operation_key=ctx.operation_key,
                                            permitted_record_refs=permitted)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


async def state_query(arguments, ctx):
    return await run_access_tool('state_query', arguments, ctx)


async def source_read(arguments, ctx):
    return await run_access_tool('source_read', arguments, ctx)


async def source_locate(arguments, ctx):
    return await run_access_tool('source_locate', arguments, ctx)


async def source_sequence_scan(arguments, ctx):
    return await run_access_tool('source_sequence_scan', arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await run_access_tool('source_sequence_references', arguments, ctx)


async def source_experimental_records(arguments, ctx):
    return await run_access_tool('source_experimental_records', arguments, ctx)


async def image_view(arguments, ctx):
    return await run_access_tool('image_view', arguments, ctx)


async def source_archive_members(arguments, ctx):
    return await run_access_tool('source_archive_members', arguments, ctx)


async def source_archive_extract(arguments, ctx):
    return await run_access_tool('source_archive_extract', arguments, ctx)


async def source_xlsx_sheets(arguments, ctx):
    return await run_access_tool('source_xlsx_sheets', arguments, ctx)


async def source_xlsx_rows(arguments, ctx):
    return await run_access_tool('source_xlsx_rows', arguments, ctx)


async def source_pdf_info(arguments, ctx):
    return await run_access_tool('source_pdf_info', arguments, ctx)


async def source_pdf_text(arguments, ctx):
    return await run_access_tool('source_pdf_text', arguments, ctx)


async def source_pdf_page(arguments, ctx):
    return await run_access_tool('source_pdf_page', arguments, ctx)


async def execution_estimate(arguments, ctx):
    return await run_access_tool('execution_estimate', arguments, ctx)


async def public_literature_search(arguments, ctx):
    return await run_access_tool('public_literature_search', arguments, ctx)


async def public_literature_read(arguments, ctx):
    return await run_access_tool('public_literature_read', arguments, ctx)


async def public_literature_sequence_identity(arguments, ctx):
    return await run_access_tool('public_literature_sequence_identity', arguments, ctx)


async def public_ncbi_search(arguments, ctx):
    return await run_access_tool('public_ncbi_search', arguments, ctx)


async def public_pmc_versions(arguments, ctx):
    return await run_access_tool('public_pmc_versions', arguments, ctx)


async def public_pmc_files(arguments, ctx):
    return await run_access_tool('public_pmc_files', arguments, ctx)


async def public_pmc_asset(arguments, ctx):
    return await run_access_tool('public_pmc_asset', arguments, ctx)


async def public_sabiork_search(arguments, ctx):
    return await run_access_tool('public_sabiork_search', arguments, ctx)


async def public_sabiork_read(arguments, ctx):
    return await run_access_tool('public_sabiork_read', arguments, ctx)


async def public_brenda_search(arguments, ctx):
    return await run_access_tool('public_brenda_search', arguments, ctx)


async def public_brenda_read(arguments, ctx):
    return await run_access_tool('public_brenda_read', arguments, ctx)


async def public_bioassay_search(arguments, ctx):
    return await run_access_tool('public_bioassay_search', arguments, ctx)


async def public_bioassay_read(arguments, ctx):
    return await run_access_tool('public_bioassay_read', arguments, ctx)


async def public_chembl_search(arguments, ctx):
    return await run_access_tool('public_chembl_search', arguments, ctx)


async def public_chembl_read(arguments, ctx):
    return await run_access_tool('public_chembl_read', arguments, ctx)


async def public_mavedb_search(arguments, ctx):
    return await run_access_tool('public_mavedb_search', arguments, ctx)


async def public_mavedb_read(arguments, ctx):
    return await run_access_tool('public_mavedb_read', arguments, ctx)


async def public_brenda_graph_search(arguments, ctx):
    return await run_access_tool('public_brenda_graph_search', arguments, ctx)


async def public_ncbi_entrez(arguments, ctx):
    return await run_access_tool('public_ncbi_entrez', arguments, ctx)


async def public_ncbi_sequence(arguments, ctx):
    return await run_access_tool('public_ncbi_sequence', arguments, ctx)


async def public_ncbi_geo(arguments, ctx):
    return await run_access_tool('public_ncbi_geo', arguments, ctx)


async def public_ncbi_sra_file(arguments, ctx):
    return await run_access_tool('public_ncbi_sra_file', arguments, ctx)


def validate_source_lead(store, lead, outcome, proposed):
    """The old library ``validate_lead`` re-expressed on custody (private copy; library candidate): the lead's
    identity and exact source witness against the records this episode holds. A violation is a ``ContractError``."""
    value = _resolve(lead, outcome.get('aliases', {}))
    validate_schema(value, source_location_inputs(lead_schema()))
    if value['proposed_annotation_ref'] != proposed or value['witness']['source_ref'] != value['source_ref']:
        raise ContractError('literature_lead_question_or_source_mismatch')
    if not value['relevance_rationale'].strip():
        raise ContractError('literature_lead_relevance_rationale_required')
    known = {*store.refs(), *outcome.get('record_refs', [])}
    if not {value['source_ref'], value['subject_ref'], proposed} <= known:
        raise ContractError('literature_lead_original_inputs_not_received')
    source = store.require(value['source_ref'], {'source'})
    subject = store.require(value['subject_ref'], {'reference'})
    if subject['source_ref'] != value['source_ref'] or not subject.get('anchor'):
        raise ContractError('literature_lead_subject_not_anchored_in_source')
    uri = (source.get('uri') or '').split('?', 1)[0].rstrip('/')
    if uri.endswith(('/search', '/esearch.fcgi')):
        raise ContractError('literature_lead_requires_acquired_source_not_search_page')

    def read_source(ref, representation):
        if ref != value['source_ref']:
            raise ContractError('literature_lead_source_mismatch')
        artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
        if artifact is None:
            raise ContractError('literature_lead_source_representation_unavailable')
        return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
    witness = _Sources(read_source).witness(value['witness'], 'source_lead.witness')
    anchor = subject['anchor']
    if anchor['artifact_ref'] != witness['artifact_ref'] or not witness['start'] <= anchor['start'] < anchor['end'] <= witness['end']:
        raise ContractError('literature_lead_subject_outside_witness')
    return {**value, 'witness': {**value['witness'], 'quote': witness['quote']}}


def reason(arguments, ctx):
    """Commit the model's typed reasoning (the old ``Store.commit_reasoning`` path of ``execute``; the owner of
    interpretation accounts is named by the system). With a ``source_lead`` the commit and the validated lead are
    one transaction (the old ``execute_reasoning``): a lead that does not hold returns an ``invalid`` outcome and
    nothing is committed."""
    envelope = arguments
    arguments, scope = envelope['arguments'], envelope['scope']
    store = ctx.store
    if 'source_lead' not in arguments:
        return store.commit_reasoning(arguments['commit'], scope, ctx.operation_key)
    try:
        witness = arguments['source_lead']['witness']
        admitted('source.read', {'source_ref': witness['source_ref'], 'representation': witness['representation'],
                                 'offset': witness['start'], 'limit': witness['end'] - witness['start']})
        with store.transaction():
            result = store.commit_reasoning(arguments['commit'], scope, ctx.operation_key)
            if result['status'] not in ('completed', 'partial'):
                return result
            lead = validate_source_lead(store, arguments['source_lead'], result, envelope['proposed_annotation_ref'])
            return {**result, 'literature_source_lead': lead}
    except (ContractError, ExperimentalContractError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}


def literature_concentration_window_populate(arguments, ctx):
    return route.populate('literature.concentration_window.populate', arguments, ctx, ROLE, GOAL)


def literature_measurement_comparison_populate(arguments, ctx):
    return route.populate('literature.measurement_comparison.populate', arguments, ctx, ROLE, GOAL)


def literature_product_coupling_populate(arguments, ctx):
    return route.populate('literature.product_coupling.populate', arguments, ctx, ROLE, GOAL)


def literature_measurement_validation_populate(arguments, ctx):
    return route.populate('literature.measurement_validation.populate', arguments, ctx, ROLE, GOAL)


def literature_ion_discrimination_populate(arguments, ctx):
    return route.populate('literature.ion_discrimination.populate', arguments, ctx, ROLE, GOAL)


def literature_channel_populate(arguments, ctx):
    return route.populate('literature.channel.populate', arguments, ctx, ROLE, GOAL)


def literature_assay_components_populate(arguments, ctx):
    return route.populate('literature.assay.components.populate', arguments, ctx, ROLE, GOAL)


def literature_rate_populate(arguments, ctx):
    return route.populate('literature.rate.populate', arguments, ctx, ROLE, GOAL)


def literature_calibration_recovery_populate(arguments, ctx):
    return route.populate('literature.calibration.recovery.populate', arguments, ctx, ROLE, GOAL)


def literature_rate_observations_populate(arguments, ctx):
    return route.populate('literature.rate.observations.populate', arguments, ctx, ROLE, GOAL)


def literature_rate_replicates_populate(arguments, ctx):
    return route.populate('literature.rate.replicates.populate', arguments, ctx, ROLE, GOAL)


def literature_rate_source_populate(arguments, ctx):
    return route.populate('literature.rate.source.populate', arguments, ctx, ROLE, GOAL)


def literature_quantity_populate(arguments, ctx):
    return route.populate('literature.quantity.populate', arguments, ctx, ROLE, GOAL)


def literature_assay_populate(arguments, ctx):
    return route.populate('literature.assay.populate', arguments, ctx, ROLE, GOAL)


def literature_amount_populate(arguments, ctx):
    return route.populate('literature.amount.populate', arguments, ctx, ROLE, GOAL)


def literature_completion_time_populate(arguments, ctx):
    return route.populate('literature.completion_time.populate', arguments, ctx, ROLE, GOAL)


def literature_active_site_populate(arguments, ctx):
    return route.populate('literature.active_site.populate', arguments, ctx, ROLE, GOAL)


def literature_parent_depletion_populate(arguments, ctx):
    return route.populate('literature.parent_depletion.populate', arguments, ctx, ROLE, GOAL)


def literature_stoichiometric_balance_populate(arguments, ctx):
    return route.populate('literature.stoichiometric_balance.populate', arguments, ctx, ROLE, GOAL)


def literature_intervention_grading_populate(arguments, ctx):
    return route.populate('literature.intervention_grading.populate', arguments, ctx, ROLE, GOAL)


def literature_a106_finalize(arguments, ctx):
    return route.populate('literature.a106.finalize', arguments, ctx, ROLE, GOAL)


def literature_product_partition_populate(arguments, ctx):
    return route.populate('literature.product_partition.populate', arguments, ctx, ROLE, GOAL)


def literature_optical_populate(arguments, ctx):
    return route.populate('literature.optical.populate', arguments, ctx, ROLE, GOAL)


def literature_kinetic_populate(arguments, ctx):
    return route.populate('literature.kinetic.populate', arguments, ctx, ROLE, GOAL)


def literature_kinetic_model_populate(arguments, ctx):
    return route.populate('literature.kinetic.model.populate', arguments, ctx, ROLE, GOAL)


def literature_binding_interaction_populate(arguments, ctx):
    return route.populate('literature.binding.interaction.populate', arguments, ctx, ROLE, GOAL)


def literature_binding_interaction_model_populate(arguments, ctx):
    return route.populate('literature.binding.interaction.model.populate', arguments, ctx, ROLE, GOAL)


def literature_ratio_populate(arguments, ctx):
    return route.populate('literature.ratio.populate', arguments, ctx, ROLE, GOAL)


def literature_ratio_source_populate(arguments, ctx):
    return route.populate('literature.ratio.source.populate', arguments, ctx, ROLE, GOAL)


def literature_controlled_response_source_v3_populate(arguments, ctx):
    return route.populate('literature.controlled_response.source_v3.populate', arguments, ctx, ROLE, GOAL)


def literature_gel_populate(arguments, ctx):
    return route.populate('literature.gel.populate', arguments, ctx, ROLE, GOAL)


def literature_binding_populate(arguments, ctx):
    return route.populate('literature.binding.populate', arguments, ctx, ROLE, GOAL)


def literature_binding_model_populate(arguments, ctx):
    return route.populate('literature.binding.model.populate', arguments, ctx, ROLE, GOAL)


def literature_transport_response_populate(arguments, ctx):
    return route.populate('literature.transport.response.populate', arguments, ctx, ROLE, GOAL)


def literature_perturbation_populate(arguments, ctx):
    return route.populate('literature.perturbation.populate', arguments, ctx, ROLE, GOAL)


def literature_figure_populate(arguments, ctx):
    return route.populate('literature.figure.populate', arguments, ctx, ROLE, GOAL)


def open_population(arguments, ctx):
    return route.open_population(arguments)


async def literature_a106_score_judgment(arguments, ctx):
    return await route.score_judgment(arguments, ctx, ROLE, GOAL)


def prepare_analysis_contract(binding, arguments):
    """The old ``prepare_analysis_contract`` (library candidate): the exact native adapter and requested schema of an
    existing BV-BRC TnSeq / RNASeq AppService results selector, over the configured resource of the
    ``execution_binding`` service. It acquires nothing."""
    service = binding.resource(arguments['resource_id'])
    if service is None or service.service != 'bvbrc_appservice':
        raise ContractError('intervention_analysis_execution_unbound')
    parameters = arguments['parameters']
    adapter_id = {'TnSeq': 'bvbrc_tnseq', 'RNASeq': 'bvbrc_rnaseq'}.get(parameters.get('application_id'))
    selection = {'adapter_id': adapter_id, 'adapter_version': '1', 'parameters': parameters}
    implementation = selected_adapter(service, selection)
    if implementation is None:
        raise ContractError('intervention_analysis_adapter_unbound')
    try:
        parameters = implementation.validate_parameters(parameters)
        schema = implementation.requested_form_schema(arguments['fields'])
    except ValueError as error:
        raise ContractError(str(error)) from error
    documents = {row['document_id'] for row in parameters['documents']}
    if any(row['selection']['document_id'] not in documents for row in arguments['fields']):
        raise ContractError('intervention_analysis_selected_document_unbound')
    return {'resource_id': arguments['resource_id'], 'adapter': deepcopy(selection), 'requested_schema': schema,
            'parent_report_source': 'bvbrc_application_outcomes', 'service_availability': 'not_observed'}


def literature_intervention_analysis_contract(arguments, ctx):
    """``literature.intervention_analysis.contract``: describes a locally bound scientific contract and performs no
    service I/O. The arguments were validated against the offered schema by ``action``; a contract error is an
    ``invalid`` outcome, as the old ``execute`` returned it."""
    arguments = arguments['arguments']
    try:
        value = prepare_analysis_contract(ctx.services['execution_binding'], arguments)
    except ContractError as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': value, 'feedback': None}


TOOLS = {'state_query': state_query, 'source_read': source_read, 'source_locate': source_locate, 'source_sequence_scan': source_sequence_scan, 'source_sequence_references': source_sequence_references, 'source_experimental_records': source_experimental_records, 'image_view': image_view, 'source_archive_members': source_archive_members, 'source_archive_extract': source_archive_extract, 'source_xlsx_sheets': source_xlsx_sheets, 'source_xlsx_rows': source_xlsx_rows, 'source_pdf_info': source_pdf_info, 'source_pdf_text': source_pdf_text, 'source_pdf_page': source_pdf_page, 'execution_estimate': execution_estimate, 'public_literature_search': public_literature_search, 'public_literature_read': public_literature_read, 'public_literature_sequence_identity': public_literature_sequence_identity, 'public_ncbi_search': public_ncbi_search, 'public_pmc_versions': public_pmc_versions, 'public_pmc_files': public_pmc_files, 'public_pmc_asset': public_pmc_asset, 'public_sabiork_search': public_sabiork_search, 'public_sabiork_read': public_sabiork_read, 'public_brenda_search': public_brenda_search, 'public_brenda_read': public_brenda_read, 'public_bioassay_search': public_bioassay_search, 'public_bioassay_read': public_bioassay_read, 'public_chembl_search': public_chembl_search, 'public_chembl_read': public_chembl_read, 'public_mavedb_search': public_mavedb_search, 'public_mavedb_read': public_mavedb_read, 'public_brenda_graph_search': public_brenda_graph_search, 'public_ncbi_entrez': public_ncbi_entrez, 'public_ncbi_sequence': public_ncbi_sequence, 'public_ncbi_geo': public_ncbi_geo, 'public_ncbi_sra_file': public_ncbi_sra_file,
         CONTRACT_TOOL: literature_intervention_analysis_contract, 'reason': reason,
         'literature_a106_score_judgment': literature_a106_score_judgment, 'open_population': open_population,
         **{name: globals()[name] for name in route.POPULATION_NAMES}}


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the assignment, the custody of the sources it holds, its own read and
    acquisition outcomes, the controlled features of the A106 sheets saved here and below, the reports of its
    children, the latest image it looked at,
    the received intervention analysis rows, the tools and the children it may commission, the measured time and
    the yield table (the old decision state and inputs, over this episode's summary)."""
    execution = execution_resources(ctx)
    names = offered(ctx.settings, execution, summary['opened_population'])
    leads = summary['task']['kind'] == 'verified_source_leads'
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    launch_directory = ctx.settings.get('launch_instruction_directory')
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'credit_binding': summary['credit_binding'], 'visual_evidence': summary['visual_evidence'],
               'last_local_outcome': summary['last_local_outcome'], 'held_record_refs': summary['held_record_refs'],
               'a106_findings': summary['a106_findings'],
               'source_lead_dispositions': summary['source_lead_dispositions'],
               'child_reports': summary['child_reports'],
               'received_intervention_analysis_rows': summary['received_intervention_analysis_rows'],
               'handoff_refs': summary['handoff_refs'],
               'literature_experimental_work': summary['literature_experimental_work'],
               'execution_resources': execution,
               'tools': catalog(names, summary['reasoning_schema'], leads, execution, ctx.settings),
               'input_list': summary['input_list'], 'consumed_source_refs': summary['consumed_source_refs'],
               'child_options': commissions(execution, summary['input_list']),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    launch_library = None if launch_directory is None else LaunchInstructions(launch_directory)
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context(),
        'launch_instruction_library': None if launch_library is None else launch_library.context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=context.get('tool_knowledge'), leads=leads,
                                                   execution=execution, launch_library=launch_library),
                        context, generation_schema(selection_schema(names, summary['reasoning_schema'], leads,
                                                                    execution, ctx.settings,
                                                                    summary['input_list'])))


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test: every section the schema names is present or absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one commission, or reject it (no unit). An answer that selects
    no offered tool or child, arguments that do not fit its schema, an empty reasoning commit without a source
    lead, or a results commission naming a handoff this
    episode does not hold is invalid. A launch commission carries the credit one handoff earns, which is this
    episode's setting ``execution_handoff_unit`` (the old child binding's ``handoff_unit``); a missing setting fails."""
    execution = execution_resources(ctx)
    names = offered(ctx.settings, execution, summary['opened_population'])
    leads = summary['task']['kind'] == 'verified_source_leads'
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema, leads, execution, ctx.settings, summary['input_list'])
    try:
        selection = validate_selection(decode_response(response, schema), schema)
        if selection['kind'] == 'child':
            if selection['slot'] == 'results' and not records.holds(selection['arguments']['handoff_ref']):
                raise ContractError('literature_reference_unavailable',
                                    detail={'reference': selection['arguments']['handoff_ref']})
            child, arguments = selection['slot'], selection['arguments']
        else:
            child = None
            name, arguments = selection['tool'], selection['arguments']
            if name == 'reason' and empty_commit(arguments['commit'], commit_schema) and 'source_lead' not in arguments:
                raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if child == 'launch':
        return ChildCall('launch', {**arguments, 'handoff_unit': ctx.settings['execution_handoff_unit']})
    if child is not None:
        return ChildCall(child, arguments)
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'page_source_ref': None, 'assignment': summary['literature_assignment'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref']})


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']
