"""The task: search and read for sources through the access and acquisition tools, commission the source relevance
assessment to triage a set of returned search results, commit reasoning on what the sources say (and, for a
verified-source-leads commission, validated source leads), and grade each applicable experiment into an A105 assay-grading sheet within the same reasoning action.

Carried from the old task.py, task_decision.py, task_action.py, task_instructions.py,
scientific_interpretation.py, source_operations.py, source_catalog.py, source_admission.py, source_custody.py,
role_policy.py, contracts.py (``_ACCESS_TOOLS``, ``_ACQUISITION_TOOLS``) and episode.py (the one child role
``literature_search``). One unit is one model-selected tool call or one child commission. The task always offers a
unit and never ends the Episode: only the yield controller does. The assignment is a set of prior searches, not a page,
so no reading is bound to one source. The rate-population route of the old episode (rate_population and its populate
tools, the required assay-grading logic of evidence_grading.py) is not carried (no population tool); its
required assay grading is the reason unit (literature_required_grading.execute: commit and sheets in one action). This file
is a private copy: it imports nothing from another episode."""
from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.evolutionary_history_evidence.literature_required_grading import (
    action_schema as grading_action_schema, execute as execute_graded)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.evolutionary_history_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.evolutionary_history_evidence.experimental_database_acquisition import (
    catalog as experimental_database_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.evolutionary_history_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_task_credit import (
    _resolve, lead_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_assay_inputs import (
    _Sources)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.evolutionary_history_evidence.literature_sequence_discovery import (
    identity_schema, references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.evolutionary_history_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.readers.evolutionary_history_evidence.source_locations import (
    locate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.evolutionary_history_evidence.source_sequences import (
    scan_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    RECORD_SCHEMAS, REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.experimental_database_records import (
    reader_schema as experimental_records_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.evolutionary_history_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

# The one child (the old role_policy child role literature_search), by slot.
SOURCE_RELEVANCE = 'source_relevance_assessment'
CHILD_SLOTS = {
    SOURCE_RELEVANCE: 'evolutionary_history_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment',
}
SERVICES = ()

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}

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


# The acquisition tools of the old ``_ACQUISITION_TOOLS`` (this search role only): literature search and read,
# sequence identity, PubMed search, PMC versions, files and assets, then the experimental-database operations, whose
# descriptions and input schemas the library's acquisition module states.
EXPERIMENT_DATABASE = experimental_database_catalog()
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
})
DESCRIPTIONS.update({name: entry['description'] for name, entry in EXPERIMENT_DATABASE.items()})

ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references',
                'source.experimental.records', 'image.view', 'source.archive.members', 'source.archive.extract',
                'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page',
                'execution.estimate')
ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset',
                     *EXPERIMENT_DATABASE)

# python tool name -> the library's tool name (a tool name here is lowercase letters, digits and underscores)
LIBRARY_NAMES = {name.replace('.', '_'): name for name in (*ACCESS_TOOLS, *ACQUISITION_TOOLS)}
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
    'public.literature.search': obj({'query': TEXT, 'size': POSITIVE, 'cursor': TEXT}, ['query']),
    'public.literature.read': obj({'pmcid': TEXT}),
    'public.literature.sequence_identity': identity_schema(),
    # the old source catalog restricted the NCBI collection to PubMed for this role
    'public.ncbi.search': obj({'database': {'enum': ['pubmed']}, 'term': TEXT, 'size': POSITIVE, 'offset': INTEGER},
                              ['database', 'term']),
    'public.pmc.versions': obj({'pmcid': {'type': 'string', 'pattern': '^PMC[0-9]+$'}, 'continuation_token': TEXT},
                               ['pmcid']),
    'public.pmc.files': obj({'version_ref': REF, 'continuation_token': TEXT}, ['version_ref']),
    'public.pmc.asset': obj({'asset_ref': REF}),
}
INPUT_SCHEMAS.update({name: entry['input_schema'] for name, entry in EXPERIMENT_DATABASE.items()})
# ``execution.estimate`` is offered for the workbook tools only, and only when the run has timing statistics.
INPUT_SCHEMAS['execution.estimate'] = {'anyOf': [
    obj({'tool': {'const': name}, 'arguments': INPUT_SCHEMAS[name]}) for name in ('source.xlsx.sheets', 'source.xlsx.rows')]}

REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the examined sources and the records you hold: '
                      'extracted terms, source subjects, contexts, observations, hypotheses and assessments, each '
                      'with its exact source anchor. A commit with every section empty is rejected.')

# What the model supplies to commission the search child: the returned search results to triage (sources this
# episode holds), the triage's objective and, optionally, further held records the triage needs. ``action`` adds what
# it derives from the held source records (the custody references).
CHILD_DESCRIPTIONS = {
    SOURCE_RELEVANCE:
        'Commission a child triage of returned search results you hold (acquired search pages or prior searches): '
        'their search_result_refs, the objective of the triage and optionally other records you hold that the triage '
        'needs (for example the anchored reference subject of a source lead). The child investigates which returned '
        'sources merit examination with the same commissioned task and returns its interpretation and its credit.',
}


def child_input(input_list):
    """The commission arguments (nano-graphrag: child options only for unconsumed inputs): the search results to
    triage are chosen from the input list only, so a consumed result cannot be selected."""
    return {SOURCE_RELEVANCE: obj({
        'objective': TEXT,
        'search_result_refs': {'type': 'array', 'items': {'enum': list(input_list)}, 'minItems': 1,
                               'uniqueItems': True,
                               'description': 'Unconsumed search results of input_list; each handed out is consumed'},
        'extra_record_refs': {'type': 'array', 'items': REF, 'uniqueItems': True}},
        ['objective', 'search_result_refs'])}

INSTRUCTIONS = (
    'You own an iterative scientific annotation improvement, not a tool itinerary.\n'
    "Use the fixed caller material within the parent's fixed subject and optional original-coordinate\n"
    "segments. Those bounds set this investigation's credit denominator; naming a new\n"
    'candidate or interpretation cannot expand them. Consider the working\n'
    'hypotheses, assumptions, prior results and biological/experimental context. Ask\n'
    'what would usually support an explanation, when that cue could mislead, what\n'
    'competing explanations remain, and which different outcomes would change your\n'
    'interpretation. Revise your next useful work from actual outcomes.\n'
    'Select one ordinary tool, one typed reasoning commitment based on available\n'
    'existing evidence, or one substantive child improvement. A tool lookup alone is\n'
    'not a child Episode. There are no biological departments or compulsory stages.\n'
    'Reasoning owns scientific interpretation and selected work; only the numerical\n'
    'controller owns scientific continuation. Do not emit a stop action or invent a\n'
    'turn budget, approval review, quality gate, experiment, term or observation.\n'
    'Text reading may produce typed extracted terms, source subjects, contexts and observations only with the\n'
    'registered source, exact artifact byte span and quote, and actual source-subject\n'
    'identity. An assay on a reference protein is not an assay on the input target.\n'
    'image.view supplies actual selected pixels in visual_evidence to this reasoning\n'
    'call. A plot or gel interpretation is a reasoned visual observation, not a\n'
    'performed experiment or a literal text extraction. For that observation use\n'
    'anchor=null and visual_anchor with the actual view_ref, image_artifact_ref and\n'
    "pixel region (top-left x,y,width,height); source_ref is the view's display source.\n"
    'The recorded origin distinguishes your interpretation. Preserve the actual\n'
    'assayed source subjects and relevant text-anchored conditions. A selected image\n'
    'alone establishes no biological role or target measurement.\n'
    'For a scientific claim, examine the relevant primary methods, results and\n'
    'qualifications to identify its actual subject, construct and conditions. A title,\n'
    'search snippet or copied annotation label does not establish that claim. Use\n'
    'source.read for the available pages; missing access is a limitation, not rejection.\n'
    'When an outcome differs between relevant constructs or conditions, retain the\n'
    'separate source-bound observations and conditions needed to interpret that\n'
    'contrast. A reported negative with data not shown remains that reported result.\n'
    "A global alignment's full coverage does not establish orthology, significance\n"
    'or substrate specificity; consider what the actual comparison distinguishes.\n'
    'A reasoned commitment can improve an annotation using existing evidence; a new\n'
    'external measurement is not required. Private planning and report formatting are\n'
    'not completed acquisitions. Retain alternatives and uncertainty rather than\n'
    'copying a public target annotation or manufacturing precision.\n'
    "current_evidence_vector contains the current projector's available component\n"
    'values from the same projection as current_credit. Interpret these using the\n'
    'recorded credit_binding; they describe the progress proxy, not biological truth.\n'
    'When working_state.record_view is received_immutable_versions, its scientific\n'
    'records are the versions delivered to this episode. received_revision_status\n'
    'distinguishes their current revision membership; it does not assert their\n'
    'scientific validity. Investigation-progress loss fields and episode.credit\n'
    'provide current correction provenance. Ordinary state.query remains available\n'
    'to discover or read other shared records explicitly.\n'
    'For a received-scientific-finding progress binding, assessment.investigation_finding\n'
    'records the actual source proposition and a typed qualification of its relevance\n'
    'to the target hypothesis. Preserve the observed source subjects and conditions.\n'
    'The selected observation must witness that source proposition. For example,\n'
    'a sequence-identity alignment witnesses identity; it does not contain a family\n'
    "annotation read in another source. Record that other source's actual assertion\n"
    'as a source-bound observation and retain the alignment as supporting identity\n'
    'evidence. Source annotations remain reported predictions, not measured target\n'
    "function. Preserve the source's term category, including domain versus family.\n"
    'A useful negative or nontransferability finding can remain retained information;\n'
    'withdrawn means the finding itself is no longer valid, with its declared reason.\n'
    'Repeated wording, quotations or opinion-only revisions do not make new findings.\n'
    'An article table and its supplement can report the same underlying observation.\n'
    "Keep each representation's actual source, subjects and quotation, but do not\n"
    'count the same source proposition, target question and qualification again merely\n'
    'because its source records or condition labels differ. When you establish that\n'
    'two representations express the same source proposition, declare\n'
    'same_source_claim_as_ref using the earlier assessment reference. That link shares\n'
    'the source-claim identity only: an unchanged qualification must also retain its\n'
    'established context_refs and assumption_refs. A new context record naming the\n'
    'same condition is not by itself a new qualification. Preserve genuinely different\n'
    'conditions, observations and qualifications; matching labels, rounded values or\n'
    'a shared publication alone do not establish equivalence. Determining what is the\n'
    'same remains part of your scientific reasoning. The host does not make that\n'
    'judgment or require a separate review. Additional source reading is not a new\n'
    'finding unless it adds or corrects information relevant to the target question.\n'
    "When correcting an earlier finding's subject, partner, construct or other\n"
    'reference binding, use replaces_refs to identify the earlier target assessment\n'
    'being repaired. same_source_claim_as_ref shares source-claim identity; it does\n'
    'not retire that earlier target finding. A different reference handle for the\n'
    'same source-established role does not by itself make another biological question.\n'
    'Keep the actual role/material identities and their witnesses distinct; declare\n'
    'replacement when the corrected binding supersedes the earlier finding, rather\n'
    'than retaining both representations as additional information. Preserve genuinely\n'
    'different questions and unresolved identity instead of equating entities by name.\n'
    'When annotation_score is supplied, it is a separate annotation-support measure\n'
    'with its own annotation_score_binding and annotation_evidence_vector. Useful new\n'
    'information can lower annotation support while advancing investigation progress.\n'
    'When proposed_annotations is supplied, each proposed annotation and subject has\n'
    'its own score and evidence vector. annotation_comparisons keeps best scored\n'
    'alternatives, ties and unscored candidates for the same subject and question.\n'
    'You retain the annotation decision and choose the next action.\n'
    "The recorded task credit supplies this episode's numerical yield observations.\n"
    'When current_credit.mode is annotation_axis_credit, controller.arms supplies\n'
    'each proposed annotation/axis credit, forecast, cutoff and transfer status.\n'
    'controller.annotation_credits totals received child credit per proposed annotation;\n'
    'controller.root_score is the largest such total. This is investigation progress,\n'
    'while proposed_annotations carries the separate signed functional-support scores.\n'
    "Each forecast concerns another whole axis invocation; a child's internal next\n"
    'action forecast is different. Choose an axis and its proposed_annotation_ref.\n'
    "The root stops only when every pair's available upper bound is at or below its\n"
    'own cutoff. Unknown scores or forecasts are not measured zeros. Coordinate\n'
    'unresolved transfer dependencies through the existing shared-information tools.\n'
    'Each child task must declare the credit calculation used for its own stopping decision.\n'
    'For an A105, A106 or A108 whole-axis investigation, include context.evidence_task\n'
    'with version evidence_axis_task_v1, kind whole_axis_findings, its evidence_axis,\n'
    "and the credit_unit from that task's configured credit_definition. Its task key is\n"
    "<axis>:whole_axis_findings. Do not copy another axis's unit or cutoff, or commission\n"
    'a separate episode merely to calculate A106/A108 scores.\n'
    'resource_tool_estimates, when supplied, describe expected execution time and\n'
    'configured resources for the declared execution classes. Use these expectations\n'
    'with your own yield estimate and prior outcomes to choose useful work. A timing\n'
    'experiment earns monitoring credit for timing information learned and updates\n'
    'execution expectations. Missing history means duration is unknown. Job elapsed\n'
    'time and the duration of an own monitoring action are distinct measurements.\n'
    'Define local rows with a bare alias, for example {"alias":"role"}, and use\n'
    '"@role" to reference an earlier successful row within this same commit. Later\n'
    'commits use the returned persistent IDs, not aliases from earlier commits.\n'
    'Sections resolve in this order: structural_proposals, terms, source_subjects,\n'
    'contexts, observations, hypotheses, assessments, interpretation_accounts,\n'
    'annotation_updates. An interpretation_account records your coherent evidence\n'
    'interpretation with runtime-bound episode ownership and assigned scope. It does\n'
    "not replace the parent's annotation. A binding admitting these accounts uses\n"
    'the same source-linked projection; copying an existing account adds no progress.\n'
    'Parent annotation integration remains a separate reasoning decision. After a\n'
    'partial result, read aliases and errors; independent successful rows persist.\n'
    'context_refs permits context or hypothesis records, not sources, protein/profile\n'
    'references or features. condition_refs permits context, hypothesis, observation\n'
    'or term records. assumption_refs permits only hypotheses. Do not invent contexts\n'
    'to make a source citation fit. Extracted labels and context names must occur\n'
    'literally in the exact anchored quote; e.g. DUF8182 is different from the composed\n'
    'label DUF8182 (Pfam PF26554). Retain identifiers and qualifications separately.\n'
    'For applicability, distinguish what an observation measures directly from what\n'
    'you infer for this particular hypothesis. Sequence identity establishes sequence\n'
    "equivalence; a reference's predicted functional label remains a prediction when\n"
    'transferred to that sequence. Preserve the source assertion and its dependencies.\n'
    'Each assessment explicitly chooses extent_basis. observed_extent projects only\n'
    "the observation's measured input/source extent; optional target_footprint can\n"
    'restrict it. inferred_extent records a non-direct reasoned attribution to an\n'
    'explicit bounded target_footprint independently of source coordinates. Preserve\n'
    'the actual source subjects and measurements. Missing inferred target_footprint\n'
    'keeps the assessment recorded but supplies no invented target extent; the\n'
    'completed commit returns a notice naming that assessment and missing field.\n'
    'direct applicability and inferred_extent are contradictory representations.\n'
    'For a nonmolecular sample/handling/physiology interpretation, context_allocation\n'
    'retains actual source subjects, observation kind and applicability while binding\n'
    'its contribution to fixed original material positions. Supply nonempty immutable\n'
    'context_account_scope for lineage identity, and context_scope for actual allocated\n'
    'positions. The latter may be {"subject_refs":[]} to withdraw only that allocation;\n'
    'missing allocation stays unlocalized with a notice. A context annotation uses\n'
    'whole_input_context and the actual sample/context subject; it has no invented\n'
    'physical sequence footprint. Frozen same-library read selections union in these\n'
    'masks, not in Episode scopes. Each revision must own both prior and proposed\n'
    'allocations; the immutable domain alone grants no edit permission. Reuse the same\n'
    'account domain and expected_revision when correcting an existing allocation.\n'
    "A commissioned child returns ONLY the parent's typed form. Fill report_update\n"
    'inside this existing reasoning response. It describes your actual interpretation\n'
    'of the supplied state BEFORE the selected next action. The result of a later tool\n'
    'has not thereby been interpreted. At yielding, recorded fact fields describe\n'
    'actual work, while interpretive fields retain their latest actual basis; prefer\n'
    'actual assessment/annotation references where those express the requested meaning.\n'
    "requested_report_purpose is the parent's actual information need. current_report_update\n"
    "contains the latest admitted interpretation fields, initially the parent's supplied\n"
    'initial values. Those initial values are not a new child judgment. Preserve their\n'
    'declared meanings when revising the form; neither input chooses your scientific action.\n'
    'As parent, request source-bound outcome and basis fields when needed to distinguish\n'
    'new observations from prior interpretations. There is no separate report composer.\n'
    'Your own earlier read outcomes are shown to you as own_literature_outcomes; that page creates '
    'no new action and does not execute or credit the historical work again.\n'
    'Do not execute native provider tools. The host executes your selected action.\n'
)

REASONING_COMMIT_REQUIREMENT = (
    'A common scientific reason action needs at least one proposed commit row. A request with every '
    'commit section empty is rejected before acquisition and creates no completed-action observation. A '
    'return-form update alone does not make that request executable. Where the supplied action schema '
    'explicitly permits evidence_processing.kind=no_applicable_evidence, its source-grounded declaration '
    'is the existing exception. Keep current report references when the interpretation is unchanged; '
    'existing saved results require no empty reasoning action.'
)

REPORT_START = "A commissioned child returns ONLY the parent's typed form."
REPORT_END = 'Your own earlier read outcomes are shown to you'
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the features code reads from the assay-grading '
                   'sheets you and your children saved (evidence type, quantity kind, measured effect, variance, '
                   'evidence ratio, criterion statuses, with the sheet reference), the count and sources of the '
                   'relevant source leads and the coverage of a screening answer; no prose of yours is returned. '
                   'Selecting a tool does not end your work: only the numerical controller does.')
# The owner's A104 copy of the A105 assay grader: its task text, part of the instructions of every decision.
GRADING_SECTION = ('\nLiterature assay grading (in the reason action, evidence_processing.gradings).\n'
                   + ASSAY_GRADING_TASK + '\n')
CHILD_GUIDANCE = ('\nA relevance child investigation (source_relevance_assessment) is selected with an objective and the '
                  'returned search results it triages, search pages you acquired or prior searches; it carries out '
                  'the same commissioned task and returns its interpretation and credit, shown to you as '
                  'child_reports. input_list is the search results not yet handed to a child: only these can be '
                  'selected, a result handed to a child is consumed and no longer offered, and the child is offered '
                  'only while input_list is not empty. A tool lookup alone is not a child investigation. The literature, PMC, NCBI and '
                  'experimental-database tools acquire sources; search results are discovery information.')
LEAD_GUIDANCE = ('\nFor a verified_source_leads commission, a reason selection also carries source_lead: the '
                 'inspected source, its anchored reference subject, whether it is a useful lead for the original '
                 'question and the exact witnessed byte interval. A search hit or title alone verifies nothing.')


def instructions(*, knowledge, leads):
    """The old task_instructions.instructions: the investigation text, the reasoning-commit requirement, this
    episode's goal, the tool-knowledge text when it is offered. The decision-exchange paragraph, the
    pending-delivery paragraph, the wait paragraphs and the redeliver_report text are not carried: no such
    action exists."""
    text = replace_span(INSTRUCTIONS, REPORT_START, REPORT_END, '')
    text += '\n' + GOAL
    text += '\n' + REASONING_COMMIT_REQUIREMENT + CHILD_GUIDANCE
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if leads:
        text += LEAD_GUIDANCE
    return text + GRADING_SECTION + RETURN_GUIDANCE


def offered(settings, input_list):
    """The tools offered now: the access and acquisition tools (execution_estimate only with timing statistics
    configured), then the reasoning commit and, while the input list holds an unconsumed search result, the search
    child commission (nano-graphrag ``_valid_children``)."""
    tools = [name for name in LIBRARY_NAMES
             if name != 'execution_estimate' or settings.get('tool_registry', {}).get('native_statistics') is not None]
    return tools + ['reason', *(CHILD_SLOTS if input_list else ())]


def reason_schema(commit_schema, leads):
    """The old reasoning_action_schema: the typed commit (each assessment with its typed investigation_finding), the
    required evidence processing (the gradings of the applicable experiments, or the no-applicable-evidence
    declaration) and, for a verified_source_leads commission, a source_lead."""
    graded = grading_action_schema(commit_schema, LiteratureAssayGradingRepository.population_schema())
    properties = {'commit': graded['properties']['commit'],
                  'evidence_processing': graded['properties']['evidence_processing']}
    if leads:
        properties['source_lead'] = lead_schema()
    return source_location_inputs(obj(properties, required=['commit']))


def catalog(names, commit_schema, leads, input_list):
    """The tools the model is shown: name, description and input schema (the old catalog; every input schema
    is projected through source_location_inputs)."""
    entries = []
    children = child_input(input_list)
    for name in names:
        if name == 'reason':
            entries.append({'name': 'reason', 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(commit_schema, leads)})
        elif name in CHILD_SLOTS:
            entries.append({'name': name, 'description': CHILD_DESCRIPTIONS[name], 'input_schema': children[name]})
        else:
            entries.append({'name': name, 'description': DESCRIPTIONS[LIBRARY_NAMES[name]],
                            'input_schema': source_location_inputs(INPUT_SCHEMAS[LIBRARY_NAMES[name]])})
    return entries


def selection_schema(names, commit_schema, leads, input_list):
    """What the model answers with: one tool and its arguments, or one child and its objective and source (the
    old action schema; the report_update of the old response is gone: the return is read by code from the sheets)."""
    return obj({'selection': {'anyOf': [
        obj({'kind': {'const': 'child'}, 'slot': {'const': entry['name']}, 'arguments': entry['input_schema']})
        if entry['name'] in CHILD_SLOTS else
        obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
        for entry in catalog(names, commit_schema, leads, input_list)]}})


def admitted(name, arguments):
    """The old ``_tool_arguments`` of this role: the tool is in the catalog and its arguments fit the offered schema.
    The old page restriction does not apply (the assignment has no page); a violation is a ``ContractError``."""
    validate_schema(arguments, source_location_inputs(INPUT_SCHEMAS[name]))


async def run_access_tool(name, envelope, ctx):
    """Execute one access or acquisition tool. A contract error is returned as an ``invalid`` outcome with
    ``arguments_or_reference`` feedback, as the old ``execute`` did; the outcome is the unit's outcome like any
    other."""
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
    return await run_access_tool('state.query', arguments, ctx)


async def source_read(arguments, ctx):
    return await run_access_tool('source.read', arguments, ctx)


async def source_locate(arguments, ctx):
    return await run_access_tool('source.locate', arguments, ctx)


async def source_sequence_scan(arguments, ctx):
    return await run_access_tool('source.sequence.scan', arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await run_access_tool('source.sequence.references', arguments, ctx)


async def source_experimental_records(arguments, ctx):
    return await run_access_tool('source.experimental.records', arguments, ctx)


async def image_view(arguments, ctx):
    return await run_access_tool('image.view', arguments, ctx)


async def source_archive_members(arguments, ctx):
    return await run_access_tool('source.archive.members', arguments, ctx)


async def source_archive_extract(arguments, ctx):
    return await run_access_tool('source.archive.extract', arguments, ctx)


async def source_xlsx_sheets(arguments, ctx):
    return await run_access_tool('source.xlsx.sheets', arguments, ctx)


async def source_xlsx_rows(arguments, ctx):
    return await run_access_tool('source.xlsx.rows', arguments, ctx)


async def source_pdf_info(arguments, ctx):
    return await run_access_tool('source.pdf.info', arguments, ctx)


async def source_pdf_text(arguments, ctx):
    return await run_access_tool('source.pdf.text', arguments, ctx)


async def source_pdf_page(arguments, ctx):
    return await run_access_tool('source.pdf.page', arguments, ctx)


async def execution_estimate(arguments, ctx):
    return await run_access_tool('execution.estimate', arguments, ctx)


async def public_literature_search(arguments, ctx):
    return await run_access_tool('public.literature.search', arguments, ctx)


async def public_literature_read(arguments, ctx):
    return await run_access_tool('public.literature.read', arguments, ctx)


async def public_literature_sequence_identity(arguments, ctx):
    return await run_access_tool('public.literature.sequence_identity', arguments, ctx)


async def public_ncbi_search(arguments, ctx):
    return await run_access_tool('public.ncbi.search', arguments, ctx)


async def public_pmc_versions(arguments, ctx):
    return await run_access_tool('public.pmc.versions', arguments, ctx)


async def public_pmc_files(arguments, ctx):
    return await run_access_tool('public.pmc.files', arguments, ctx)


async def public_pmc_asset(arguments, ctx):
    return await run_access_tool('public.pmc.asset', arguments, ctx)


async def public_sabiork_search(arguments, ctx):
    return await run_access_tool('public.sabiork.search', arguments, ctx)


async def public_sabiork_read(arguments, ctx):
    return await run_access_tool('public.sabiork.read', arguments, ctx)


async def public_brenda_search(arguments, ctx):
    return await run_access_tool('public.brenda.search', arguments, ctx)


async def public_brenda_read(arguments, ctx):
    return await run_access_tool('public.brenda.read', arguments, ctx)


async def public_bioassay_search(arguments, ctx):
    return await run_access_tool('public.bioassay.search', arguments, ctx)


async def public_bioassay_read(arguments, ctx):
    return await run_access_tool('public.bioassay.read', arguments, ctx)


async def public_chembl_search(arguments, ctx):
    return await run_access_tool('public.chembl.search', arguments, ctx)


async def public_chembl_read(arguments, ctx):
    return await run_access_tool('public.chembl.read', arguments, ctx)


async def public_mavedb_search(arguments, ctx):
    return await run_access_tool('public.mavedb.search', arguments, ctx)


async def public_mavedb_read(arguments, ctx):
    return await run_access_tool('public.mavedb.read', arguments, ctx)


async def public_brenda_graph_search(arguments, ctx):
    return await run_access_tool('public.brenda.graph_search', arguments, ctx)


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

    def authorize_source_access(reference, representation):
        if not store.holds(reference):
            raise ContractError('literature_source_not_received')

    selection = {'kind': 'reason', 'commit': arguments['commit'],
                 **({'evidence_processing': arguments['evidence_processing']}
                    if 'evidence_processing' in arguments else {})}
    repository = LiteratureAssayGradingRepository(store)
    if 'source_lead' not in arguments:
        return execute_graded(scope, None, selection, ctx.operation_key, repository,
                              authorize_source_access=authorize_source_access)
    try:
        with store.transaction():
            result = execute_graded(scope, None, selection, ctx.operation_key, repository,
                                    authorize_source_access=authorize_source_access)
            if result['status'] not in ('completed', 'partial'):
                return result
            lead = validate_source_lead(store, arguments['source_lead'], result, envelope['proposed_annotation_ref'])
            return {**result, 'literature_source_lead': lead}
    except (ContractError, ExperimentalContractError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}




TOOLS = {'state_query': state_query,
         'source_read': source_read,
         'source_locate': source_locate,
         'source_sequence_scan': source_sequence_scan,
         'source_sequence_references': source_sequence_references,
         'source_experimental_records': source_experimental_records,
         'image_view': image_view,
         'source_archive_members': source_archive_members,
         'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets,
         'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info,
         'source_pdf_text': source_pdf_text,
         'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate,
         'public_literature_search': public_literature_search,
         'public_literature_read': public_literature_read,
         'public_literature_sequence_identity': public_literature_sequence_identity,
         'public_ncbi_search': public_ncbi_search,
         'public_pmc_versions': public_pmc_versions,
         'public_pmc_files': public_pmc_files,
         'public_pmc_asset': public_pmc_asset,
         'public_sabiork_search': public_sabiork_search,
         'public_sabiork_read': public_sabiork_read,
         'public_brenda_search': public_brenda_search,
         'public_brenda_read': public_brenda_read,
         'public_bioassay_search': public_bioassay_search,
         'public_bioassay_read': public_bioassay_read,
         'public_chembl_search': public_chembl_search,
         'public_chembl_read': public_chembl_read,
         'public_mavedb_search': public_mavedb_search,
         'public_mavedb_read': public_mavedb_read,
         'public_brenda_graph_search': public_brenda_graph_search,
         'reason': reason}

def decide(summary, feedback, ctx):
    """Ask the model for the next tool or child, shown the assignment, the custody of the prior-search sources, its own
    read and acquisition outcomes, what its child returned, the interpretation so far, the latest image it looked at,
    the tools, the measured time and the yield table (the old decision state and inputs, over this episode's
    summary)."""
    input_list = summary['input_list']
    names = offered(ctx.settings, input_list)
    leads = summary['task']['kind'] == 'verified_source_leads'
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'credit_binding': summary['credit_binding'], 'visual_evidence': summary['visual_evidence'],
               'last_local_outcome': summary['last_local_outcome'], 'held_record_refs': summary['held_record_refs'],
               'child_reports': summary['child_reports'],
               'input_list': input_list, 'consumed_search_result_refs': summary['consumed_search_result_refs'],
               'assay_sheets': summary['assay_sheets'],
               'source_lead_dispositions': summary['source_lead_dispositions'],
               'tools': catalog(names, summary['reasoning_schema'], leads, input_list),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=context.get('tool_knowledge'), leads=leads), context,
                        generation_schema(selection_schema(names, summary['reasoning_schema'], leads, input_list)))


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test: every section the schema names is present or absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def search_call(slot, arguments, records, input_list):
    """The search child's commission from the model's choice: every returned search result must be a source this
    episode holds and every further record a held record (the old ``_validate_page`` of the references the parent
    assigned, applied here to the model's answer, never to the commission), and the custody references of the held
    sources (their artifacts and the sources they derive from) travel with the pass."""
    extra = arguments.get('extra_record_refs', [])
    unconsumed = [ref for ref in arguments['search_result_refs'] if ref not in input_list]
    if unconsumed:
        raise ContractError('literature_search_result_not_in_input_list', detail={'references': unconsumed})
    custody = []
    for reference in (*arguments['search_result_refs'], *extra):
        if not records.holds(reference):
            raise ContractError('literature_reference_unavailable', detail={'reference': reference})
    for source_ref in arguments['search_result_refs']:
        source = records.get(source_ref)
        custody.extend(reference for reference in dict.fromkeys(
            (source.get('artifact_ref'), source.get('text_ref'), source.get('stdout_ref'), source.get('stderr_ref'),
             *source.get('parent_source_refs', ())))
            if reference is not None and reference not in arguments['search_result_refs'] and records.holds(reference))
    return ChildCall(slot, {'objective': arguments['objective'],
                            'search_result_refs': list(arguments['search_result_refs']),
                            'custody_refs': list(dict.fromkeys(custody)), 'context_refs': list(extra)})


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit). An answer that
    selects no offered tool or child, arguments that do not fit its schema, an empty reasoning commit without a
    source lead, a report or a child search result this episode does not hold is invalid."""
    names = offered(ctx.settings, summary['input_list'])
    leads = summary['task']['kind'] == 'verified_source_leads'
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema, leads, summary['input_list'])
    try:
        selection = validate_selection(decode_response(response, schema), schema)
        if selection['kind'] == 'child':
            return search_call(selection['slot'], selection['arguments'], records, summary['input_list'])
        name, arguments = selection['tool'], selection['arguments']
        if (name == 'reason' and empty_commit(arguments['commit'], commit_schema) and 'source_lead' not in arguments
                and arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref']})


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']
