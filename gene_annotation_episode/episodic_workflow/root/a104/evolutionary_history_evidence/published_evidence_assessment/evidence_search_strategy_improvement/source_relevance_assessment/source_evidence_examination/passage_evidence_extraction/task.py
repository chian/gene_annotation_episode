"""The task: read the assigned source's passages, with their neighbouring context, through the access tools,
commit reasoning on what they say (and, for a verified-source-leads commission, validated source leads), and
grade each applicable experiment into an A105 assay-grading sheet within the same reasoning action.

Carried from the old task.py, task_decision.py, task_action.py, task_instructions.py,
scientific_interpretation.py, source_operations.py, source_catalog.py, source_admission.py and
source_custody.py. One unit is one model-selected tool call. The task always offers a unit and never ends the
Episode: only the yield controller does. The episode has no child and cannot search or fetch new sources (no
acquisition tools). The required assay grading of the old ``evidence_grading.py`` is the ``reason`` unit: the library's
``literature_required_grading.execute`` commits the interpretation and saves the purpose-specific A105 assay-grading
sheet of every applicable experiment in one transaction (row 16 of ``LOST_CONTENT_a104.md``), or records the
source-grounded ``no_applicable_evidence`` declaration. There is no prose ``report`` tool: the parent receives the
credit and the controlled features code reads from the saved sheets."""
from jsonschema import ValidationError

from episode_runtime import CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.evolutionary_history_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.evolutionary_history_evidence.literature_required_grading import (
    action_schema as grading_action_schema, execute as execute_graded)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.evolutionary_history_evidence.literature_assay_grading_prompt import (
    ASSAY_GRADING_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_task_credit import (
    _resolve, lead_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_assay_inputs import (
    _Sources)
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
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import read_record_in_scope
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_discovery_values import (
    references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    RECORD_SCHEMAS, REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.experimental_database_records import (
    reader_schema as experimental_records_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.evolutionary_history_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {}
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

# python tool name -> the library's tool name (a tool name here is lowercase letters, digits and underscores)
LIBRARY_NAMES = {
    'state_query': 'state.query', 'source_read': 'source.read', 'source_locate': 'source.locate',
    'source_sequence_scan': 'source.sequence.scan', 'source_sequence_references': 'source.sequence.references',
    'source_experimental_records': 'source.experimental.records', 'image_view': 'image.view',
    'source_archive_members': 'source.archive.members', 'source_archive_extract': 'source.archive.extract',
    'source_xlsx_sheets': 'source.xlsx.sheets', 'source_xlsx_rows': 'source.xlsx.rows',
    'source_pdf_info': 'source.pdf.info', 'source_pdf_text': 'source.pdf.text', 'source_pdf_page': 'source.pdf.page',
    'execution_estimate': 'execution.estimate'}
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

REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the supplied passages and the records you hold: '
                      'extracted terms, source subjects, contexts, observations, hypotheses and assessments, each '
                      'with its exact source anchor, and grade each applicable experiment in evidence_processing '
                      '(graded, with one gradings entry per experiment), or declare no_applicable_evidence with the '
                      'examined spans. A commit with every section empty is rejected.')

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
    'A report_delivery_failure is operational feedback about an already completed\n'
    'child. You can select redeliver_report with a revised closed contract, using the\n'
    'delivery_ref shown in report_deliveries or report_delivery_failure. It reuses\n'
    "saved facts and exactly the child's existing interpretation fields; it performs\n"
    'no new scientific work and cannot answer a new interpretive question. Do not\n'
    'recommission the same investigation merely to fix its representation.\n'
    'On a fresh provider conversation, restored_episode_history is a bounded index\n'
    'of your own actual prior decisions, not a generated scientific summary. Use the\n'
    'ordinary episode.history tool when an older selected action, exact outcome or\n'
    'admitted direct-child form matters. Its indices belong only to this Episode;\n'
    "another Episode's same index names different work. A failed saved outcome stays\n"
    'failed. Where the journal retained a pre-execution rejection, its status is\n'
    'rejected and view=records supplies the original rejection_feedback separately\n'
    'from an executed outcome. Reading history does not execute that work again.\n'
    'A selected history read is one ordinary action with its actual zero or changed progress, while\n'
    'automatic context restoration creates no completed action. Current report\n'
    'values retain their actual current_report_basis_refs, not a later tool result.\n'
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

HISTORY_START = 'On a fresh provider conversation,'
REPORT_START = "A commissioned child returns ONLY the parent's typed form."
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier read outcomes are shown to you as own_literature_outcomes; that page creates '
                    'no new action and does not execute or credit the historical work again.\n')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the features code reads from the assay-grading '
                   'sheets you saved (evidence type, quantity kind, measured effect, variance, evidence ratio, '
                   'criterion statuses, with the sheet reference), the count and sources of your relevant source '
                   'leads and the coverage of a screening answer; no prose of yours is returned. Selecting a tool '
                   'does not end your work: only the numerical controller does.')
# The owner's A104 copy of the A105 assay grader: its task text, part of the instructions of every decision.
GRADING_SECTION = '\nLiterature assay grading (in the reason action, evidence_processing.gradings).\n' + ASSAY_GRADING_TASK + '\n'
LEAD_GUIDANCE = ('\nFor a verified_source_leads commission, a reason selection also carries source_lead: the '
                 'inspected source, its anchored reference subject, whether it is a useful lead for the original '
                 'question and the exact witnessed byte interval. A search hit or title alone verifies nothing.')


def instructions(*, knowledge, leads):
    """The old task_instructions.instructions: the investigation text, the reasoning-commit requirement, this
    episode's goal, the tool-knowledge text when it is offered. The decision-exchange paragraph, the
    pending-delivery paragraph, the wait paragraphs and the redeliver_report text are not carried: no such
    action exists."""
    text = replace_span(INSTRUCTIONS, REPORT_START, HISTORY_START, '')
    text = replace_span(text, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if leads:
        text += LEAD_GUIDANCE
    return text + GRADING_SECTION + RETURN_GUIDANCE


def offered(settings):
    """The access tools offered now: execution_estimate only with timing statistics configured; then the
    reasoning commit (with its required grading)."""
    tools = [name for name in LIBRARY_NAMES
             if name != 'execution_estimate' or settings.get('tool_registry', {}).get('native_statistics') is not None]
    return tools + ['reason']


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


def catalog(names, commit_schema, leads):
    """The tools the model is shown: name, description and input schema (the old catalog; every input schema
    is projected through source_location_inputs)."""
    entries = []
    for name in names:
        if name == 'reason':
            entries.append({'name': 'reason', 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(commit_schema, leads)})
        else:
            entries.append({'name': name, 'description': DESCRIPTIONS[LIBRARY_NAMES[name]],
                            'input_schema': source_location_inputs(INPUT_SCHEMAS[LIBRARY_NAMES[name]])})
    return entries


def selection_schema(names, commit_schema, leads):
    """What the model answers with: one tool and its arguments (the old action schema; the report_update of the
    old response is gone: the return is read by code from the saved sheets)."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                                             'arguments': entry['input_schema']})
                                        for entry in catalog(names, commit_schema, leads)]}})


def within_source(store, reference, root, scope):
    """Whether ``reference`` is ``root`` or a source derived from it through ``parent_source_refs`` (the old
    ``_within_source``; each source on the way is read in scope)."""
    pending, seen = [reference], set()
    while pending:
        current = pending.pop()
        if current == root:
            return True
        if current in seen:
            continue
        seen.add(current)
        source = read_record_in_scope(store, current, scope, 'source')
        pending.extend(source.get('parent_source_refs', ()))
    return False


def admitted(store, name, arguments, scope, root):
    """The old ``_tool_arguments``: the arguments against the offered schema, and the source they name against the
    assigned page's source. A violation is a ``ContractError``."""
    validate_schema(arguments, source_location_inputs(INPUT_SCHEMAS[name]))
    selected = arguments['arguments'] if name == 'execution.estimate' else arguments
    source_ref = selected.get('source_ref')
    if name == 'source.archive.extract':
        source_ref = read_record_in_scope(store, arguments['member_ref'], scope, 'archive_member')['source_ref']
    if source_ref is not None and not within_source(store, source_ref, root, scope):
        raise ContractError('literature_reading_outside_assigned_source')


async def run_access_tool(name, envelope, ctx):
    """Execute one access tool. A contract error is returned as an ``invalid`` outcome with ``arguments_or_reference``
    feedback, as the old ``execute`` did; the outcome is the unit's outcome like any other."""
    arguments, scope, root = envelope['arguments'], envelope['scope'], envelope['page_source_ref']
    try:
        admitted(ctx.store, name, arguments, scope, root)
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
    arguments, scope, root = envelope['arguments'], envelope['scope'], envelope['page_source_ref']
    store = ctx.store

    def authorize_source_access(reference, representation):
        if not within_source(store, reference, root, scope):
            raise ContractError('literature_reading_outside_assigned_source')

    selection = {'kind': 'reason', 'commit': arguments['commit'],
                 **({'evidence_processing': arguments['evidence_processing']}
                    if 'evidence_processing' in arguments else {})}
    repository = LiteratureAssayGradingRepository(store)
    if 'source_lead' not in arguments:
        return execute_graded(scope, root, selection, ctx.operation_key, repository,
                              authorize_source_access=authorize_source_access)
    try:
        witness = arguments['source_lead']['witness']
        admitted(store, 'source.read', {'source_ref': witness['source_ref'], 'representation': witness['representation'],
                                        'offset': witness['start'], 'limit': witness['end'] - witness['start']},
                 scope, root)
        with store.transaction():
            result = execute_graded(scope, root, selection, ctx.operation_key, repository,
                                    authorize_source_access=authorize_source_access)
            if result['status'] not in ('completed', 'partial'):
                return result
            lead = validate_source_lead(store, arguments['source_lead'], result, envelope['proposed_annotation_ref'])
            return {**result, 'literature_source_lead': lead}
    except (ContractError, ExperimentalContractError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}




TOOLS = {'state_query': state_query, 'source_read': source_read, 'source_locate': source_locate,
         'source_sequence_scan': source_sequence_scan, 'source_sequence_references': source_sequence_references,
         'source_experimental_records': source_experimental_records, 'image_view': image_view,
         'source_archive_members': source_archive_members, 'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets, 'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info, 'source_pdf_text': source_pdf_text, 'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate, 'reason': reason}


def decide(summary, feedback, ctx):
    """Ask the model for the next tool, shown the assignment, the custody of the source, its own read outcomes,
    the interpretation so far, the latest image it looked at, the tools, the measured time and the yield table
    (the old decision state and inputs, over this episode's summary)."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'credit_binding': summary['credit_binding'], 'visual_evidence': summary['visual_evidence'],
               'last_local_outcome': summary['last_local_outcome'], 'held_record_refs': summary['held_record_refs'],
               'assay_sheets': summary['assay_sheets'],
               'source_lead_dispositions': summary['source_lead_dispositions'],
               'tools': catalog(names, summary['reasoning_schema'], leads),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=context.get('tool_knowledge'), leads=leads), context,
                        generation_schema(selection_schema(names, summary['reasoning_schema'], leads)))


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test: every section the schema names is present or absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit). An answer that selects no offered tool,
    arguments that do not fit its schema, or an empty reasoning commit without a source lead or a no-applicable-
    evidence declaration is invalid."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema, leads)
    try:
        selection = validate_selection(decode_response(response, schema), schema)
        name, arguments = selection['tool'], selection['arguments']
        if (name == 'reason' and empty_commit(arguments['commit'], commit_schema) and 'source_lead' not in arguments
                and arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'page_source_ref': summary['literature_assignment']['page']['source_ref'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref']})


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']
