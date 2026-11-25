"""The task of the A101 head: one model-selected unit per decision. The model investigates the assigned subject with
the selected tools of its commission (``execute_selected_tool``), commits scientific interpretations (``reason``) and
commissions its children. It never ends the Episode: only the yield controller does.

Tools. ``reason`` is the ``Store.commit_reasoning`` path. ``execute_selected_tool`` dispatches a tool the commission
selected to the library's ``ToolRegistry``, called with ``ctx.store`` (a tool name here has lowercase letters, digits
and underscores, so the selected name travels as an argument). ``pairwise_blast`` is this episode's own defined tool:
the model fills out one request (the query, the reference sequence record, the program and a bound resource, each
from a fixed set). ``action`` runs the library's one deterministic check of that request against what the episode
holds and the bound resources (``check_pairwise_request``): a request with problems is rejected with the things to
fix and no unit is made; a request that passes runs as one unit (``pairwise_blast_comparison``: the search, the
fetch of its report and the grading). The graded comparison is counted by the credit as soon as its sheet is saved (the
reference sequence is a candidate; ``CREDIT_TEXT`` says how the credit counts); no reasoning commit is needed for it.

Children. The head's child episodes in the A101 tree are ``bvbrc_blast``, ``bvbrc_msa``, ``bvbrc_metacats`` and ``all_vs_all``
(HMMER later). A child is declared in ``CHILD_SLOTS`` when its episode is built (the runner
refuses a declared slot with no episode behind it), together with its commission in ``COMMISSIONS``. The model is the
router: for a child it answers with the slot and the controlled fields of that slot's commission
(``commission_fields``); it writes no assignment, objective or message. ``msg_to_child`` builds the child's
assignment, in the child's own form, from those choices and the summary. A slot is offered while its commission can
be stated from what this episode holds. A BV-BRC job a child launched and returned parked is always finished
(``resume_action``: the episode does not stop while one is parked, and once it is due, or when nothing else is worth its
cost, its resume is the unit; the rule is the system's, ``method_loop.episode_type``). The service ``job_access`` is read for the bound resources a commission or a
tool may name (``bound_resources``).

Settings: ``process_library_directory`` (the frozen process library), ``tool_library_directory`` (the frozen
scientific tool library), ``tool_registry`` (the keyword settings of the library's ``ToolRegistry``),
``blast_executable_directory`` (the directory that holds the BLAST programs) and ``yield_bindings``
(``yield_estimator.py``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError, canonical, identity
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    GROUPING_PROVIDER)
from gene_annotation_episode.episodic_workflow.episode_support.configuration.sequence_homology_evidence.process_options import (
    SequenceHomologyEvidenceLibrary, evidence_axis_instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.sequence_homology_evidence.evidence_axis_instructions import (
    VERSION as INSTRUCTION_VERSION, instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.evidence_axis_contracts import (
    VERSION as EVIDENCE_AXIS_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sequence_homology_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sequence_homology_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.construction_records import (
    selection_fields)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import obj
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    bvbrc_blast_search as bvbrc)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    all_vs_all_run as all_vs_all)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    bvbrc_msa_alignment as msa)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    bvbrc_metacats_search as metacats)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    seconds_between)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.pairwise_blast_comparison import (
    PROGRAM_MOLECULES, check_pairwise_request, pairwise_blast_comparison)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.hmmer_profile_scan import (
    check_profile_scan_request, hmmer_profile_scan)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .credit import APPLY_GROUPING
from .goal import GOAL

HEAD = 'sequence_homology_evidence'
# The child episodes that are built, by slot. A child is added here with its entries in ``COMMISSIONS``,
# ``CHILD_DESCRIPTIONS`` and ``SELECTABLE`` and its builder in ``messages/msg_to_child.py``.
CHILD_SLOTS = {'bvbrc_blast': 'sequence_homology_evidence/bvbrc_blast',
               'bvbrc_msa': 'sequence_homology_evidence/bvbrc_msa',
               'bvbrc_metacats': 'sequence_homology_evidence/bvbrc_metacats',
               'all_vs_all': 'sequence_homology_evidence/all_vs_all'}
# What the model supplies to commission each slot: a function of (summary, resources) that returns
# ``(properties, required)`` of controlled values, or ``None`` while the commission cannot be stated.
COMMISSIONS = {'bvbrc_blast': lambda summary, resources: bvbrc_blast_fields(summary, resources),
               'bvbrc_msa': lambda summary, resources: bvbrc_msa_fields(summary, resources),
               'bvbrc_metacats': lambda summary, resources: bvbrc_metacats_fields(summary, resources),
               'all_vs_all': lambda summary, resources: all_vs_all_fields(summary, resources)}
# The one deterministic check of each slot's filled commission: a function of (the model's commission, summary,
# resources, records: the custody reader) that returns the things to fix (an empty list: it can be commissioned). Added with the slot.
COMMISSION_CHECKS = {'bvbrc_blast': lambda commission, summary, resources, records: check_bvbrc_blast(
                         commission, summary, resources),
                     'bvbrc_msa': lambda commission, summary, resources, records: check_bvbrc_msa(
                         commission, summary, resources),
                     'bvbrc_metacats': lambda commission, summary, resources, records: check_bvbrc_metacats(
                         commission, summary, resources, records),
                     'all_vs_all': lambda commission, summary, resources, records: check_all_vs_all(commission, summary)}
# The programs the head commissions: those its credit can score. The A101 subscore (``route_native_grading``) scores the
# sheet of a ``blastp`` search; for any other program it raises (``a101_translated_or_nucleotide_map_not_bound``,
# ``a101_original_protein_mapping_required``), which would end the run (offline run O3). The child itself takes every
# program of the service.
COMMISSION_PROGRAMS = ('blastp',)
SERVICES = ('job_access',)

# The common tool names a selected tool may not reuse.
COMMON_TOOLS = ('process.search', 'process.entry', 'process.sources', 'process.tools', 'knowledge.search',
                'knowledge.entry', 'knowledge.read', 'episode.history', 'episode.credit',
                'episode.annotation_score', 'episode.monitoring_information', 'episode.estimate_wait',
                'shared.request_information', 'shared.publish_information', 'shared.resolve_information_need',
                'shared.read_information', 'shared.list_information')
# The old ``scientific_operations``: these two tools were given the records this episode received.
RECEIVED_RECORD_READERS = ('result.blast.hsp', 'source.locate')
TEXT = {'type': 'string', 'minLength': 1}
OPEN = {'anyOf': [{'type': 'object'}]}   # an object the host validates; the provider carries it as JSON text
THOUGHT_FIELDS = ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                  'outcome_contingencies', 'boundary')
# The optional return fields a commission may select from what the child declares (read from the child's own
# ``RETURN_FORM``); credit and finding are always returned. A child's entry is added with its commission.
SELECTABLE = {'bvbrc_blast': [], 'bvbrc_msa': [], 'bvbrc_metacats': [], 'all_vs_all': []}

# The two bodies the old ``ScientificGoal.instructions`` appended after the goal text, by the entry version of the
# selected evidence axis (instruction text, unchanged).
INSTRUCTION_ENTRY_BODY = "Determine what the supplied target does within the parent's assigned question, scope and constraints. Start with the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and known context. No initial candidate annotation or publicly searchable name is required. Possible functions can emerge from the evidence and be compared or revised. Apply the complete selected investigation instructions and thought-pattern guidance on every decision. Use actual outcomes and received child results to choose and revise your approach. Selected instructions describe how to investigate; they are not evidence about this target. Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits of inference when interpreting evidence. Missing information remains unknown.\n\nChoose an available tool action, commit a scientific interpretation through the reasoning action, or commission one of the offered children (child_options) by choosing the controlled fields of its commission; code builds the child's assignment from your choices. Use only the selected actual tools and their supplied resource instructions; choose callable operands through the declared response contract. Preserve the parent's exact requested result meanings and allowed values. Recorded facts come from actual records. Keep inherited information distinct from new findings and completed work distinct from attempts. Return valid partial findings and specific failures through the requested form.\n\nKeep the assigned evidence axis, thought pattern and selected tools for this episode. Children own their iterative choices. The configured controller owns continuation. Waiting and unchanged observations do not manufacture progress."
EVIDENCE_AXIS_BODY = "Investigate the parent's assigned scientific problem iteratively in the shared Episode loop. The selected scientific support proposition and operands define the support problem; the thought pattern supplies alternatives and outcome-sensitive guidance; the selected real tools supply their exact callable contracts. Choose your own actions using actual outcomes and received child forms. The selection is no prescribed sequence or automatic compatibility verdict. Library sources are instruction provenance, not scientific evidence about this target. Inspect actual source subjects, conditions and target applicability before interpreting evidence. annotation_support_routes describes the actual separately bound annotation policy's kind dispatch. An unmapped kind has no base-axis mapping in that known policy. Unavailable metadata means this reader cannot declare the bound policy; it is no verdict on evidence or the actual score. Metadata itself earns no credit and never replaces or filters the actual projectors, annotation formula or continuation rule. Keep the parent's objective, scope, constraints and exact typed form; support metadata never adds form fields or scoring axes. Use common reasoning to commit scientific interpretations. Keep the originally assigned scientific support, thought pattern and selected tool set throughout this episode. Only retrieved actual tools are available; their descriptions do not grant execution. The configured controller owns continuation."

HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier outcomes are shown to you as own_outcomes, one row per completed unit, with '
                    'the records each produced; a failed or invalid outcome is shown with its feedback. Your '
                    'children\'s reports are in child_reports. Reading them creates no completed action or '
                    'observation and does not execute or credit the historical work again.\n')
# What the credit is, in plain words, as every description of an action that earns it states it (the definition record
# ``credit_binding`` has the fixed fields; ``candidates``, ``tests`` and ``differentials`` of the context are its data).
CREDIT_TEXT = ('Your credit counts possible annotations (candidates). A candidate found with positive evidence is '
               'admitted to the list and earns its score; a possible annotation with no positive evidence is not on '
               'the list. A test also earns the difference of the moves of the scores of the top two candidates '
               'already on the list that it measures (those two, no other pair). A repeat earns nothing.')
PAIRWISE_TOOL = 'pairwise_blast'
PROFILE_TOOL = 'hmmer_profile_scan'
DESCRIPTIONS = {
    PROFILE_TOOL: ('Scan one protein sequence of your scope against a database of protein family profiles (HMMER '
                   'hmmscan) on a local resource. No reference sequence is needed: the database holds one trained '
                   'profile per family, each with its own trained reporting threshold. Fill out the three fields of '
                   'its request: query_ref (a protein sequence of your scope), database (a profile database of the '
                   'schema) and resource_id (a local resource of bound_resources). Code checks the request before '
                   'anything runs; if something is wrong it comes back in feedback with the things to fix and '
                   'nothing has run. A request that passes runs as one unit, with no second call: code runs the '
                   'scan, fetches its report and tables and grades them. The completed outcome lists each family '
                   'that passed its own threshold: its reference record, its accession and name in the profile '
                   'database, and for each matched domain the interval of your sequence, the bit score, the '
                   'independent E-value, the fraction of the profile that is paired and the match strength. A scan '
                   'that matched no family is completed with no family. A scan you already hold is not run again. '
                   'The grading is automatic: each matched family is a candidate (vocabulary profile_family; its '
                   'accession and name are the profile database\'s) and is counted as soon as the unit completes. ' + CREDIT_TEXT + ' A failed outcome is a fault of the environment and the same request '
                   'is not made again.'),
    'reason': REASONING_COMMIT_REQUIREMENT,
    PAIRWISE_TOOL: ('Compare one query sequence with one reference sequence by a pairwise BLAST on a local resource. Fill '
                    'out the four fields of its request: query_ref (a sequence of your scope), reference_ref (another '
                    'sequence record you hold; held_sequences gives each record with its molecule), program (blastp '
                    'compares a protein query with a protein reference, blastn nucleotide with nucleotide, blastx a '
                    'nucleotide query with a protein reference, tblastn a protein query with a nucleotide '
                    'reference, tblastx two nucleotide sequences in translation) and resource_id (a local resource '
                    'of bound_resources). Code checks the request before anything runs. If something is wrong the '
                    'request comes back in feedback with the things to fix (each names the field, a code and what to '
                    'choose from) and nothing has run: correct those fields. A request that passes the check runs '
                    'as one unit, with no second call: code runs the search, fetches its report and grades it. The '
                    'completed outcome shows the controlled features of the saved pairwise sheet (counts and '
                    'fractions of paired and identical residues, the two lengths, the native E-value with the '
                    'search-space context the report gives) and observation_refs: one alignment observation per '
                    'reported alignment, which you now hold. A comparison you already hold is not run again. The '
                    'grading is automatic: the reference sequence is a candidate (vocabulary reference_sequence) and is '
                    'counted as soon as the unit completes; no reasoning commit is needed for it and none changes it. ' + CREDIT_TEXT + ' A failed outcome is a fault of '
                    'the environment, not of your request: it is reported once and the same request is not made '
                    'again.'),
}
# What every BV-BRC child's description says of a parked job (the system's rule, ``resume_action``).
PARKED_TEXT = ('A parked job is always finished: this episode does not end while one is parked; once its expected '
               'remaining seconds have passed, or when none of your other actions is worth its cost, code commissions '
               'its continuation (until extracted) as the next unit without asking you; before then you may do other '
               'work worth its cost.')
# What the model is told of each child it may commission: what the child does, the controlled fields of its
# commission (the model chooses values; code builds the child's assignment) and what comes back. A child's entry is
# added with its commission.
CHILD_DESCRIPTIONS = {
    'bvbrc_blast': (
        'Search one query sequence of your scope against a precomputed BV-BRC database through the BV-BRC application '
        'service (the Homology application, run on the owner\'s account): the identification of the query from the best '
        'hits of the database (when the search is extracted, each distinct product the hits carry is a candidate of vocabulary '
        'product, with the score of its hits\' alignments over your scope, and is counted as soon as the search is extracted; '
        'product is BV-BRC\'s name of a feature; a hit with no product names no candidate). ' + CREDIT_TEXT + ' Fill the five fields of its commission: query_ref (a sequence of '
        'your scope; held_sequences gives the molecule of each), program (only blastp is offered: a protein query against '
        'a protein database), database (bacteria-archaea holds the proteins of the '
        'reference and representative bacterial and archaeal genomes; viral-reference holds the proteins of the '
        'reference and representative viral genomes; neither holds the other\'s proteins. organism_candidates, when it '
        'is not empty, says which organism the query\'s DNA is from: the leading candidate taxon, the vaguer candidates on '
        'its lineage and its leading rival, each with its score; search the database that holds that kind of organism '
        'first. When it is empty nothing says which kind of organism the query is from), resource_id (a bvbrc resource of bound_resources) '
        'and until. Code checks the commission before the child is commissioned; if something is wrong it comes back in '
        'feedback with the things to fix and nothing was commissioned. While a child runs, you do nothing else: your next '
        'decision comes after it returns. What until means: with until launched the child estimates the duration, launches '
        'the search and returns at once; the search then keeps running at the service, you can use your other actions '
        'while it runs, and the child is said to be parked. ' + PARKED_TEXT + ' With until extracted the child follows the search '
        'to its end, waiting between status requests for as long as the search takes and extracts the result into the graded sheet; it is also how a '
        'parked search is continued: while bvbrc_searches shows a search of the query as outstanding, commissioning the '
        'child again with the same query, program, database and resource and until extracted continues that search and '
        'submits nothing (code passes back the records the child returned). What comes back: the state of the search '
        '(no_estimate, estimated, launched, finished, extracted or failed), the hit count, the controlled identification '
        'features of the graded sheet, the seconds estimated and observed, the last failure code and the credit. When the '
        'search is parked (parked true) the report is a wait notice: seconds_since_launch, estimated_seconds and '
        'expected_remaining_seconds (the estimate minus the seconds since the launch, not below zero, or the later '
        'revised figure of a status request), and bvbrc_searches keeps showing the search with the seconds since its launch '
        'and the seconds still expected as of each decision. A search that failed or is already held extracted is not '
        'commissioned again.'),
    'bvbrc_msa': (
        'Align the target (a protein sequence of your scope) with sequences of several candidates of a graded BV-BRC '
        'database search you hold, through the BV-BRC application service (the MSA application, Muscle, protein, run on the '
        'owner\'s account). Code, not you, chooses the sequences: for each candidate you name, the hits of that search with '
        'the highest values (one per distinct sequence), the number per candidate you choose; the target is always in the '
        'alignment. When the alignment is extracted, code reads from it the conserved sites of each candidate group (the '
        'reference sequences of one product; the target is in no group): the alignment columns where at least 80% of the '
        'group\'s sequences carry the same residue, for a group of at least 3 sequences. A conserved site whose residue '
        'differs from the residue another group conserves at the same column is a distinguishing site; it is identified by '
        'the target\'s residue position, the group\'s residue and the candidate (never by the column or the job). For each '
        'candidate with distinguishing sites that no earlier alignment you hold has identified, the measurement in one more '
        'test, msa, is the fraction of those new sites where the target carries the group\'s residue. Repeating the same '
        'residue pattern on the same sites adds nothing, and an alignment with no new distinguishing site earns nothing. '
        'The top two candidates already on your list that undergo this test earn the difference of their moves. ' + CREDIT_TEXT + ' Fill the six fields of its commission: query_ref (a protein sequence of your scope), '
        'search_ref (a held graded BV-BRC search of that query; msa_options shows each with the product candidates you '
        'admitted from it), candidates (two or more of those product names, exactly as shown), per_candidate (2 to 20 '
        'sequences of each), resource_id (a bvbrc resource of bound_resources) and until. Code checks the commission before '
        'the child is commissioned; if something is wrong it comes back in feedback with the things to fix and nothing was '
        'commissioned. While a child runs, you do nothing else: your next decision comes after it returns. What until '
        'means: with until launched the child estimates the duration, launches the job and returns at once; the job then '
        'keeps running at the service, you can use your other actions while it runs, and the child is said to be parked. '
        + PARKED_TEXT + ' With until extracted the child follows the job to its end and extracts the alignment into the graded sheet; it is '
        'also how a parked job is continued: while bvbrc_msa_jobs shows a job as outstanding, commissioning the child again '
        'with the same fields and until extracted continues that job and submits nothing. What comes back: the state of the '
        'job (no_estimate, estimated, launched, finished, extracted or failed), the sequences, columns and candidates of the '
        'alignment, the seconds estimated and observed, the last failure code and the credit; when parked (parked true) a '
        'wait notice: seconds_since_launch, estimated_seconds and expected_remaining_seconds. The alignment is also kept as '
        'a labelled data product (data_products shows it with where it also lies in the BV-BRC workspace) that a later '
        'child that needs an alignment is passed. An alignment already held is not commissioned again; a job that failed is '
        'not commissioned again.'),
    'all_vs_all': (
        'Put the target (a protein sequence of your scope) and the sequences of several candidates of a graded BV-BRC database search '
        'you hold in one set, search the set against itself with BLAST+ on a local resource (every sequence against all) and cluster '
        'it with MCL on the pairwise bit scores, to see where the target falls among each candidate\'s sequences. Code, not you, '
        'chooses the sequences: for each candidate you name, the hits of that search with the highest values (one per distinct '
        'sequence), the number per candidate you choose; the target is always in the set. The child\'s own model prepares the '
        'database, runs the all-against-all and tunes the clustering (the inflation and how the pairwise scores are contrasted), '
        'trying clusterings and committing one. The committed clustering is graded: for each candidate with sequences in the set, '
        'the measurement in one more test, cluster, is the share of that candidate\'s sequences that fall in the target\'s cluster '
        '(0 to 1; about 1 when they cluster with the target, 0 when none does). The top two candidates already on your list that undergo '
        'this test earn the difference of their moves. ' + CREDIT_TEXT + ' Fill the four fields of its commission: query_ref (a protein '
        'sequence of your scope), search_ref (a held graded BV-BRC search of that query; msa_options shows each with the product '
        'candidates you admitted from it), candidates (two or more of those product names, exactly as shown) and per_candidate (2 '
        'to 20 sequences of each). Code checks the commission before the child is commissioned; if something is wrong it comes back '
        'in feedback with the things to fix and nothing was commissioned. The child works to its end in this one commission '
        '(minutes on a local resource). What comes back: the state of the work (nothing_done, database_ready, matrix_ready, tried or '
        'clustered), the sequences and letters of the set, the pairs of the matrix, the number of tries, the committed clustering '
        '(inflation, contrast, cluster count, size of the target\'s cluster), the last failure code and the credit. The set, '
        'database, matrix and clusters are kept as labelled data products (data_products). A set already commissioned is not '
        'commissioned again.'),
    'bvbrc_metacats': (
        'Test the alignment you hold with MetaCATS through the BV-BRC application service (the MetaCATS application, protein, '
        'run on the owner\'s account). The alignment must be a labelled data product of kind multiple_sequence_alignment that '
        'you hold (data_products shows it; metacats_options shows each one MetaCATS can take, with its candidate groups). '
        'MetaCATS looks for the alignment positions where the sequences of different groups differ significantly (a '
        'chi-square test per position at the p-value 0.05, which is fixed and not your choice). Code, not you, builds the '
        'groups: one group per product candidate of the alignment, its members that candidate\'s reference sequences; the '
        'target is in no group, because it is what is being placed. When the result is extracted, for each significant '
        'position the residue counts per group and the target\'s residue are saved. It confirms the candidates\' conserved '
        'sites by comparing the families: a site where a candidate\'s group keeps the target\'s own residue (the conserved-site '
        'reading described for bvbrc_msa) is confirmed when MetaCATS finds its position significant, and each candidate is '
        'measured by the sites this analysis confirms that no earlier analysis confirmed. A second analysis of the same '
        'alignment is not made. ' + CREDIT_TEXT +' Fill the four fields of its commission: query_ref (the alignment\'s target), '
        'alignment_ref (a row_ref of metacats_options), resource_id (a bvbrc resource of '
        'bound_resources) and until. Code checks the commission before the child is commissioned; if something is wrong it '
        'comes back in feedback with the things to fix and nothing was commissioned. While a child runs, you do nothing '
        'else: your next decision comes after it returns. What until means: with until launched the child estimates the '
        'duration, launches the job and returns at once; the job then keeps running at the service, you can use your other '
        'actions while it runs, and the child is said to be parked. ' + PARKED_TEXT + ' With until extracted the child follows the job to its '
        'end and extracts the result into the graded sheet; it is also how a parked job is continued: while '
        'bvbrc_metacats_jobs shows a job as outstanding, commissioning the child again with the same fields and until '
        'extracted continues that job and submits nothing. What comes back: the state of the job (no_estimate, estimated, '
        'launched, finished, extracted or failed), the groups, sequences, columns and significant positions, the seconds '
        'estimated and observed, the last failure code and the credit; when parked (parked true) a wait notice: '
        'seconds_since_launch, estimated_seconds and expected_remaining_seconds. The result is also kept as a labelled data '
        'product (an alignment position report). A report of the same groups already held is not commissioned '
        'again; a job that failed is not commissioned again.'),
}


def axis_entry(library, selection):
    """The old ``configuration._evidence_axis_view`` reading: the entry of the selected axis and its view."""
    entry = library.resolve(selection[selection_fields(selection)[0]])
    if entry.get('entry_version') == INSTRUCTION_VERSION:
        return entry, instruction_view(entry)
    if entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
        return entry, evidence_axis_instruction_view(entry)
    raise ContractError('a101_evidence_axis_entry_invalid')


def replaces_default_instructions(library):
    """The old ``ScientificConfiguration.replaces_default_instructions``: every evidence axis of the library is a
    published instruction entry."""
    axes = [header['option_ref'] for header in library.headers() if header['option_ref']['slot'] == 'evidence_axis']
    return bool(axes) and all(library.resolve(ref).get('entry_version') == INSTRUCTION_VERSION for ref in axes)


def instructions(library, selection):
    """The investigation text (replaced by the goal text when every axis is a published instruction entry) and the
    reasoning-commit requirement. The text lives in this episode's own files: no knowledge or launch instruction
    library is assembled into it."""
    entry, _ = axis_entry(library, selection)
    body = INSTRUCTION_ENTRY_BODY if entry.get('entry_version') == INSTRUCTION_VERSION else EVIDENCE_AXIS_BODY
    specialized = GOAL + '\n\n' + body
    if replaces_default_instructions(library):
        text = specialized
    else:
        text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE) + '\n' + specialized
    return text + '\n' + REASONING_COMMIT_REQUIREMENT


def selected_tools(settings, selection):
    """The old ``tool_selection.catalog``: the direct-route tools of the selection, resolved from the tool library
    (a selected tool may not reuse a common tool name), without ``instructions`` and ``invocation_route``."""
    tools = ScientificToolLibrary(settings['tool_library_directory'])
    resolved = tools.resolve_invocations(selection['child_tool_info'])
    if any(row['name'] in COMMON_TOOLS for row in resolved):
        raise ContractError('scientific_primitive_uses_common_tool_name')
    direct = [row for row in resolved if row.get('invocation_route', {'kind': 'direct'})['kind'] == 'direct']
    return [{key: value for key, value in row.items() if key not in ('instructions', 'invocation_route')}
            for row in direct]


def bound_resources(ctx):
    """The resources bound to the job service, each with its kind, which a commission or a tool may name (read
    through the service's read handle, so the read is recorded with the decision)."""
    access = ctx.services['job_access']
    return {resource['resource_id']: resource['kind'] for resource in access.read('resources')}


def pairwise_options(summary, resources):
    """The request of the ``pairwise_blast`` tool, as the model fills it out: each field from a fixed set (the held
    sequence records, the programs, the bound resources). Whether the filled request can run is decided by
    ``check_pairwise_request`` in ``action``. Not offered while fewer than two sequence records are held or no
    resource is bound."""
    held = list(summary['held_sequences'])
    if len(held) < 2 or not resources:
        return []
    return [obj({'kind': {'const': 'tool'}, 'tool': {'const': PAIRWISE_TOOL},
                 'arguments': obj({'query_ref': {'enum': held}, 'reference_ref': {'enum': held},
                                   'program': {'enum': list(PROGRAM_MOLECULES)},
                                   'resource_id': {'enum': list(resources)}})})]


def profile_scan_options(summary, resources, databases):
    """The request of the ``hmmer_profile_scan`` tool, as the model fills it out: each field from a fixed set (the
    held sequence records, the configured profile databases, the bound resources). Whether the filled request can
    run is decided by ``check_profile_scan_request`` in ``action``. Not offered while no profile database is
    configured, no sequence record is held or no resource is bound."""
    held = list(summary['held_sequences'])
    if not databases or not held or not resources:
        return []
    return [obj({'kind': {'const': 'tool'}, 'tool': {'const': PROFILE_TOOL},
                 'arguments': obj({'query_ref': {'enum': held}, 'database': {'enum': list(databases)},
                                   'resource_id': {'enum': list(resources)}})})]


def scans_made(summary):
    """The profile scans this episode holds (``completed``) or saw fail (``failed``), by query and database: what
    ``check_profile_scan_request`` refuses to run again."""
    made = {(row['scan']['query_ref'], row['scan']['database']): 'failed'
            for row in summary['units'] if row['kind'] == 'tool' and row['tool'] == PROFILE_TOOL
            and row['status'] != 'completed'}
    made.update({(row['query_ref'], row['database']): 'completed' for row in summary['held_profile_scans']})
    return made


def comparisons_made(summary):
    """The comparisons this episode holds (``completed``) or saw fail (``failed``), by query, reference and
    program: what ``check_pairwise_request`` refuses to run again."""
    made = {(row['comparison']['query_ref'], row['comparison']['reference_ref'], row['comparison']['program']): 'failed'
            for row in summary['units'] if row['kind'] == 'tool' and row['tool'] == PAIRWISE_TOOL
            and row['status'] != 'completed'}
    made.update({(row['query_ref'], row['reference_ref'], row['program']): 'completed'
                 for row in summary['held_comparisons']})
    return made


def bvbrc_blast_fields(summary, resources):
    """The commission of ``bvbrc_blast``: the query among the scope's held sequences, the program, the precomputed BV-BRC
    database and the BV-BRC resource, each from a fixed set. Not offered while the scope holds no sequence or no BV-BRC
    resource is bound."""
    queries = [ref for ref in summary['scope']['subject_refs'] if ref in summary['held_sequences']]
    services = [name for name, kind in resources.items() if kind == bvbrc.ROUTE_KIND]
    if not queries or not services:
        return None
    properties = {'query_ref': {'enum': queries}, 'program': {'enum': list(COMMISSION_PROGRAMS)},
                  'database': {'enum': list(bvbrc.DATABASES)}, 'resource_id': {'enum': services},
                  'until': {'enum': list(bvbrc.UNTIL)}}
    return properties, list(properties)


def bvbrc_msa_fields(summary, resources):
    """The commission of ``bvbrc_msa``: the target and the held graded BV-BRC search (each from the held ones that admit
    at least two product candidates for it), the candidates (two or more of the admitted names), the number of sequences
    per candidate and the BV-BRC resource, each from a fixed set. Not offered while no held graded BV-BRC search admits two
    product candidates or no BV-BRC resource is bound."""
    options = [item for item in summary['msa_options'] if len(item['candidates']) >= msa.MINIMUM_CANDIDATES
               and summary['held_sequences'].get(item['query_ref']) == 'protein']
    services = [name for name, kind in resources.items() if kind == bvbrc.ROUTE_KIND]
    if not options or not services:
        return None
    names = list(dict.fromkeys(name for item in options for name in item['candidates']))
    properties = {'query_ref': {'enum': list(dict.fromkeys(item['query_ref'] for item in options))},
                  'search_ref': {'enum': [item['search_ref'] for item in options]},
                  'candidates': {'type': 'array', 'uniqueItems': True, 'minItems': msa.MINIMUM_CANDIDATES,
                                 'items': {'enum': names}},
                  'per_candidate': {'type': 'integer', 'minimum': msa.PER_CANDIDATE_RANGE[0],
                                    'maximum': msa.PER_CANDIDATE_RANGE[1]},
                  'resource_id': {'enum': services}, 'until': {'enum': list(bvbrc.UNTIL)}}
    return properties, list(properties)


def check_bvbrc_msa(commission, summary, resources):
    """The things to fix in a commission of ``bvbrc_msa`` (``bvbrc_msa_alignment.check_commission``)."""
    return msa.check_commission(
        commission, scope_subjects=summary['scope']['subject_refs'], sequences=summary['held_sequences'],
        options=summary['msa_options'], resources=resources, jobs=summary['bvbrc_msa_jobs'],
        commissioned=[(row['arguments']['search_ref'], sorted(row['arguments']['candidates']),
                       row['arguments']['per_candidate']) for row in summary['units']
                      if row['kind'] == 'child' and row['slot'] == 'bvbrc_msa'],
        reusable=next((row for row in summary['reusable_alignments']
                       if commission['search_ref'] in row['used'] and row['settings']['candidates'] == sorted(
                           commission['candidates']) and row['settings']['per_candidate'] == commission['per_candidate']),
                      None))


def all_vs_all_fields(summary, resources):
    """The commission of ``all_vs_all``: the target and the held graded BV-BRC search (each from the held ones that admit at least
    two product candidates for it), the candidates (two or more of the admitted names) and the number of sequences per candidate. Not
    offered while no held graded BV-BRC search admits two product candidates. (The child runs on a local resource and its model
    chooses the clustering tuning: neither is a field of the commission.)"""
    options = [item for item in summary['msa_options'] if len(item['candidates']) >= all_vs_all.MINIMUM_CANDIDATES
               and summary['held_sequences'].get(item['query_ref']) == 'protein']
    if not options:
        return None
    names = list(dict.fromkeys(name for item in options for name in item['candidates']))
    properties = {'query_ref': {'enum': list(dict.fromkeys(item['query_ref'] for item in options))},
                  'search_ref': {'enum': [item['search_ref'] for item in options]},
                  'candidates': {'type': 'array', 'uniqueItems': True, 'minItems': all_vs_all.MINIMUM_CANDIDATES,
                                 'items': {'enum': names}},
                  'per_candidate': {'type': 'integer', 'minimum': all_vs_all.PER_CANDIDATE_RANGE[0],
                                    'maximum': all_vs_all.PER_CANDIDATE_RANGE[1]}}
    return properties, list(properties)


def check_all_vs_all(commission, summary):
    """The things to fix in a commission of ``all_vs_all`` (``all_vs_all_run.check_commission``)."""
    return all_vs_all.check_commission(
        commission, scope_subjects=summary['scope']['subject_refs'], sequences=summary['held_sequences'],
        options=summary['msa_options'], commissioned=all_vs_all.commission_keys(summary))


def bvbrc_metacats_fields(summary, resources):
    """The commission of ``bvbrc_metacats``: the alignment (a held data-product row of kind ``multiple_sequence_alignment``
    with at least two candidate groups of at least two sequences: ``metacats_options``), its target and the
    BV-BRC resource (the p-value is fixed, not a field), each from a fixed set. Not offered while no such alignment is held or no BV-BRC resource is bound."""
    options = summary['metacats_options']
    services = [name for name, kind in resources.items() if kind == bvbrc.ROUTE_KIND]
    if not options or not services:
        return None
    properties = {'query_ref': {'enum': list(dict.fromkeys(item['query_ref'] for item in options))},
                  'alignment_ref': {'enum': [item['alignment_ref'] for item in options]},
                  'resource_id': {'enum': services},
                  'until': {'enum': list(bvbrc.UNTIL)}}
    return properties, list(properties)


def check_bvbrc_metacats(commission, summary, resources, records):
    """The things to fix in a commission of ``bvbrc_metacats`` (``bvbrc_metacats_search.check_commission``: the requirement
    that the alignment is a held data product of its kind comes first)."""
    return metacats.check_commission(
        commission, reader=records, options=summary['metacats_options'], resources=resources,
        jobs=summary['bvbrc_metacats_jobs'],
        commissioned=[row['arguments']['alignment_ref'] for row in summary['units']
                      if row['kind'] == 'child' and row['slot'] == 'bvbrc_metacats'])


def bvbrc_searches_view(searches, now, msa=False):
    """The BV-BRC searches this episode holds as the model sees them at ``now`` (the decision's recorded time): each with its
    state, whether it is outstanding, and for an outstanding one the seconds since its launch and the seconds still
    expected: the estimate recorded with its launch minus those seconds, not below zero. Facts, never a deadline."""
    shown = []
    for search in searches:
        keys = (('handoff_ref', 'resource_id', 'latest_state', 'outstanding', 'closed', 'estimated_seconds') if msa else
                ('handoff_ref', 'query_ref', 'program', 'database', 'resource_id', 'latest_state', 'outstanding',
                 'closed', 'estimated_seconds'))
        row = {key: search[key] for key in keys}
        if msa:
            row['identity'] = search['identity']
        if search['outstanding']:
            elapsed = seconds_between(search['launched_at'], now)
            row.update(seconds_since_launch=elapsed, expected_remaining_seconds=max(search['estimated_seconds'] - elapsed, 0.0))
        shown.append(row)
    return shown


def check_bvbrc_blast(commission, summary, resources):
    """The things to fix in a commission of ``bvbrc_blast`` (``bvbrc_blast_search.check_commission``)."""
    return bvbrc.check_commission(
        commission, programs=COMMISSION_PROGRAMS, sequences=summary['held_sequences'],
        scope_subjects=summary['scope']['subject_refs'], resources=resources, searches=summary['bvbrc_searches'],
        commissioned=[(row['arguments']['query_ref'], row['arguments']['program'], row['arguments']['database'])
                      for row in summary['units'] if row['kind'] == 'child' and row['slot'] == 'bvbrc_blast'])


def commission_fields(slot, summary, resources):
    """What the model supplies to commission ``slot``, as ``(properties, required)``: controlled values only.
    ``None`` while this episode holds nothing the commission could be chosen from: the slot is then not offered.
    ``msg_to_child`` builds the child's assignment from these fields and the summary; the model writes no
    assignment, objective or message."""
    return COMMISSIONS[slot](summary, resources)


def offered_children(summary, resources):
    """The children this decision offers: those whose commission this episode can state now."""
    return [slot for slot in CHILD_SLOTS if commission_fields(slot, summary, resources) is not None]


def child_option(slot, summary, resources):
    """One child the model may commission: the slot, the controlled fields of its commission
    (``commission_fields``) and ``selection``, the optional return fields the commission may select from what the
    child declares; a child that declares none has no ``selection`` (an array schema needs its ``items``, and an
    ``enum`` of no names admits nothing)."""
    properties, required = commission_fields(slot, summary, resources)
    properties = {'kind': {'const': 'episode_child'}, 'slot': {'const': slot}, **properties}
    if SELECTABLE[slot]:
        properties['selection'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': SELECTABLE[slot]}}
    return obj(properties, required=['kind', 'slot', *required])


def selection_schema(summary, tools, resources, databases):
    """What the model answers with: one reasoning commit, one selected tool, one pairwise comparison, one profile
    scan, or one child.
    The reasoning commit is the tool ``reason``, as the model is shown it: the arguments of a tool whose schema is
    composed travel as JSON text, and the Store's reasoning schema sent as output schema itself has more enum
    values than the model endpoint takes in one schema."""
    options = [obj({'kind': {'const': 'tool'}, 'tool': {'const': 'reason'},
                    'arguments': obj({'commit': summary['reasoning_schema']})})]
    options.extend(obj({'kind': {'const': 'tool'}, 'tool': {'const': row['name']},
                        'arguments': row.get('input_schema', OPEN)}) for row in tools)
    options.extend(pairwise_options(summary, resources))
    options.extend(profile_scan_options(summary, resources, databases))
    options.extend(child_option(slot, summary, resources) for slot in offered_children(summary, resources))
    return obj({'selection': {'anyOf': options}})


def offered_actions(summary, ctx):
    """The action types this decision offers, by the names a unit is recorded under (``ToolCall.name``, ``ChildCall.slot``):
    ``reason``; ``execute_selected_tool`` while the commission selects tools (every selected tool is run by this one
    tool); ``pairwise_blast`` and ``hmmer_profile_scan`` while their options are offered; and each child slot offered.
    Built from the functions ``decide`` offers the model with (``selected_tools``, ``pairwise_options``,
    ``profile_scan_options``, ``offered_children``)."""
    tools = selected_tools(ctx.settings, summary['selection'])
    resources = bound_resources(ctx)
    names = ['reason']
    if tools:
        names.append('execute_selected_tool')
    if pairwise_options(summary, resources):
        names.append(PAIRWISE_TOOL)
    if profile_scan_options(summary, resources, ctx.settings.get('profile_databases', {})):
        names.append(PROFILE_TOOL)
    return names + offered_children(summary, resources) + ([APPLY_GROUPING] if summary['grouping_owed'] else [])


def parked_jobs(summary):
    """The BV-BRC jobs of this episode's children that are parked (outstanding: launched, no closure held, not shown
    failed or lost), each as ``(slot, job row)``, from the summary's views of the job ledger rows (``bvbrc_searches``,
    ``bvbrc_msa_jobs``, ``bvbrc_metacats_jobs``)."""
    return [(slot, job) for slot, view in (('bvbrc_blast', 'bvbrc_searches'), ('bvbrc_msa', 'bvbrc_msa_jobs'),
                                           ('bvbrc_metacats', 'bvbrc_metacats_jobs'))
            for job in summary[view] if job['outstanding']]


def resume_commission(slot, job, summary):
    """The commission that resumes the parked ``job`` of ``slot``: the job's own commission again with ``until``
    ``extracted`` (the one commission of it the head's check accepts while it is outstanding; it submits nothing): for
    ``bvbrc_blast`` the search's query, program, database and resource; for ``bvbrc_msa`` the job's identity (target,
    search, candidates, sequences per candidate) and resource; for ``bvbrc_metacats`` the held alignment whose candidate
    groups the job was given (``metacats_options``' ``groups_ref``), its target and the resource."""
    if slot == 'bvbrc_blast':
        return {'query_ref': job['query_ref'], 'program': job['program'], 'database': job['database'],
                'resource_id': job['resource_id'], 'until': 'extracted'}
    if slot == 'bvbrc_msa':
        identity = job['identity']
        return {'query_ref': identity['query_ref'], 'search_ref': identity['search_ref'],
                'candidates': list(identity['candidates']), 'per_candidate': identity['per_candidate'],
                'resource_id': job['resource_id'], 'until': 'extracted'}
    (option,) = [item for item in summary['metacats_options'] if item['groups_ref'] == job['identity']['groups_ref']]
    return {'query_ref': option['query_ref'], 'alignment_ref': option['alignment_ref'], 'resource_id': job['resource_id'],
            'until': 'extracted'}


def apply_grouping(arguments, ctx):
    """Keep the grouping of this episode's candidates the commission carries (the design
    ``docs/plan/designs/a102_regrouping.md``: only the root decides which candidates are one function; the head applies
    its grouping in code, with no model decision). The grouping is kept as a record of this episode (a ``source``
    record whose artifact is the grouping): nothing held is rewritten, the candidate table is read under the grouping
    from then on (``credit.held_candidate_table``), and the credit reads every grouping kept
    (``differential_credit.grouped_credit``). The record goes back to the commissioner with the committed records and
    returns at the next commission, so a grouping given twice is known."""
    grouping = arguments['candidate_groups']
    artifact = ctx.store.artifact(canonical(grouping), 'application/json')
    source = ctx.store.put('source', {'provider': GROUPING_PROVIDER, 'accession': None, 'uri': None,
                                      'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
                                      'version': None, 'retrieved_at': None}, origin='tool')
    return {'status': 'completed',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': APPLY_GROUPING,
                                                    'arguments': grouping}),
            'record_refs': [source['id']], 'changed_record_refs': [], 'result': {'groups': len(grouping)},
            'feedback': None}


def resume_action(summary, records, ctx):
    """The resume this episode owes (``method_loop.episode_type``, step 3; the owner, 2026-11-21: "the head must finish
    parked jobs"): ``None`` while no child's BV-BRC job is parked, else the resume of one parked job as
    ``{'action_type': its slot, 'arguments': resume_commission(...), 'due': ...}``. ``due`` is True once the job's expected
    remaining seconds have passed: the estimate recorded with its launch minus the seconds from the launch to this
    decision's recorded time (the wait notice ``bvbrc_searches_view`` shows), at or below zero. The job chosen: the
    earliest launched among the due ones, else the earliest launched. While a job is parked the episode does not stop;
    once it is due its resume is the only action offered; before that the model may choose other work worth its cost,
    and when none is worth it the resume is taken in place of a stop (the system's rule). The commission passes the
    head's own check (``COMMISSION_CHECKS``), else this raises: a resume the check refuses is a fault of the episode."""
    if summary['grouping_owed']:
        return {'action_type': APPLY_GROUPING, 'arguments': {'candidate_groups': summary['candidate_groups']},
                'due': True}
    parked = parked_jobs(summary)
    if not parked:
        return None
    remaining = lambda job: job['estimated_seconds'] - seconds_between(job['launched_at'], ctx.clock.now)
    due = [(slot, job) for slot, job in parked if remaining(job) <= 0]
    slot, job = min(due or parked, key=lambda item: item[1]['launched_at'])
    arguments = resume_commission(slot, job, summary)
    problems = COMMISSION_CHECKS[slot]({'kind': 'episode_child', 'slot': slot, **arguments}, summary,
                                       bound_resources(ctx), records)
    if problems:
        raise ContractError('a101_resume_commission_refused_by_its_check:' + slot + ':' + repr(problems))
    return {'action_type': slot, 'arguments': arguments, 'due': bool(due)}


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the commission, the selected process library entries, the working
    state of the scope, its own outcomes and its children's reports, the tools and children it may use, the
    measured time and the yield table."""
    settings = ctx.settings
    library = SequenceHomologyEvidenceLibrary(settings['process_library_directory'])
    selection = summary['selection']
    _, axis_view = axis_entry(library, selection)
    thought = library.resolve(selection[selection_fields(selection)[1]])
    tools = selected_tools(settings, selection)
    resources = bound_resources(ctx)
    offered = offered_children(summary, resources)
    databases = settings.get('profile_databases', {})
    own = ([{'name': PAIRWISE_TOOL, 'description': DESCRIPTIONS[PAIRWISE_TOOL]}]
           if pairwise_options(summary, resources) else [])
    own += ([{'name': PROFILE_TOOL, 'description': DESCRIPTIONS[PROFILE_TOOL]}]
            if profile_scan_options(summary, resources, databases) else [])
    context = {
        'goal': GOAL, 'scope': summary['scope'],
        'sequence_homology_evidence': {
            'selection': selection, 'initial_selection_sha256': summary['initial_selection_sha256'],
            'evidence_axis': axis_view,
            'thought_pattern': {name: thought[name] for name in THOUGHT_FIELDS if name in thought},
            'child_tool_info': selection['child_tool_info'],
            'assignment': {'proposed_annotation_ref': summary['proposed_annotation_ref'],
                           'evidence_refs': summary['evidence_refs'], 'constraints': summary['constraints'],
                           'context': summary['context']},
            'permitted_children': offered},
        'working_state': summary['working_state'], 'visible_record_refs': summary['held_record_refs'],
        'held_source_refs': summary['held_source_refs'],
        'credit_binding': summary['credit_binding'], 'candidates': summary['candidates'], 'tests': summary['tests'],
        'differentials': summary['differentials'], 'not_asked_hit_count': summary['not_asked_hit_count'],
        'no_product_hit_count': summary['no_product_hit_count'],
        'uncharacterized_hit_count': summary['uncharacterized_hit_count'],
        'own_outcomes': summary['units'],
        'last_local_outcome': summary['last_local_outcome'], 'child_reports': summary['child_reports'],
        'handoff_refs': summary['handoff_refs'], 'bound_resources': resources,
        'organism_candidates': summary['organism_candidates'],
        'held_sequences': summary['held_sequences'], 'held_comparisons': summary['held_comparisons'],
        'held_profile_scans': summary['held_profile_scans'],
        'bvbrc_searches': bvbrc_searches_view(summary['bvbrc_searches'], ctx.clock.now),
        'msa_options': summary['msa_options'],
        'bvbrc_msa_jobs': bvbrc_searches_view(summary['bvbrc_msa_jobs'], ctx.clock.now, msa=True),
        'held_alignments': summary['held_alignments'], 'data_products': summary['data_products'],
        'metacats_options': summary['metacats_options'],
        'bvbrc_metacats_jobs': bvbrc_searches_view(summary['bvbrc_metacats_jobs'], ctx.clock.now, msa=True),
        'held_clusterings': summary['held_clusterings'],
        'held_metacats': summary['held_metacats'],
        'tools': [{'name': 'reason', 'description': DESCRIPTIONS['reason']}, *own, *tools],
        'child_options': [{'slot': slot, 'binding_path': CHILD_SLOTS[slot], 'description': CHILD_DESCRIPTIONS[slot],
                           'selectable_return_fields': SELECTABLE[slot]} for slot in offered],
        'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'revision_origin': summary.get('revision_origin')}, conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(library, selection), context,
                        generation_schema(selection_schema(summary, tools, resources, databases)))


def empty_commit(commit):
    """The old ``reasoning_has_task_content`` test: every section of the commit is empty."""
    return all(rows == [] for rows in commit.values())


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one commission, or reject it (no unit): an answer that does not
    fit the schema, a reasoning commit with every section empty (rejected before acquisition), or a pairwise request
    the check finds something to fix in (rejected with the things to fix)."""
    tools = selected_tools(ctx.settings, summary['selection'])
    resources = bound_resources(ctx)
    schema = selection_schema(summary, tools, resources, ctx.settings.get('profile_databases', {}))
    try:
        if not isinstance(response, dict) or set(response) != {'selection'}:
            raise ValueError('a101_decision_response_must_be_exactly_selection')
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'tool' and selection['tool'] == 'reason' and empty_commit(
                selection['arguments']['commit']):
            raise ValueError('empty_reasoning_commit')
        if selection['kind'] == 'tool' and selection['tool'] == PAIRWISE_TOOL:
            problems = check_pairwise_request(
                selection['arguments'], sequences=summary['held_sequences'],
                scope_subjects=summary['scope']['subject_refs'], resources=resources, made=comparisons_made(summary))
            if problems:
                raise Rejected({'status': 'invalid', 'category': 'pairwise_blast_request',
                                'detail': {'request': selection['arguments'], 'fix': problems}})
        if selection['kind'] == 'tool' and selection['tool'] == PROFILE_TOOL:
            problems = check_profile_scan_request(
                selection['arguments'], sequences=summary['held_sequences'],
                scope_subjects=summary['scope']['subject_refs'], resources=resources, made=scans_made(summary))
            if problems:
                raise Rejected({'status': 'invalid', 'category': 'hmmer_profile_scan_request',
                                'detail': {'request': selection['arguments'], 'fix': problems}})
    except (ValueError, KeyError, TypeError, ContractError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    if selection['kind'] == 'episode_child':
        problems = COMMISSION_CHECKS[selection['slot']](selection, summary, resources, records)
        if problems:
            raise Rejected({'status': 'invalid', 'category': selection['slot'] + '_commission',
                            'detail': {'commission': {key: value for key, value in selection.items()
                                                      if key not in ('kind', 'slot')}, 'fix': problems}})
        arguments = {key: value for key, value in selection.items() if key not in ('kind', 'slot')}
        return ChildCall(selection['slot'], arguments)
    scope = summary['scope']
    if selection['tool'] == 'reason':
        return ToolCall('reason', {'commit': selection['arguments']['commit'], 'scope': scope})
    if selection['tool'] in (PAIRWISE_TOOL, PROFILE_TOOL):
        return ToolCall(selection['tool'], dict(selection['arguments']))
    return ToolCall('execute_selected_tool', {'tool': selection['tool'], 'arguments': selection['arguments'],
                                              'scope': scope,
                                              'permitted_record_refs': (summary['held_record_refs']
                                                                        if selection['tool'] in RECEIVED_RECORD_READERS
                                                                        else None)})


def reason(arguments, ctx):
    """Commit the model's typed reasoning (the old ``Store.commit_reasoning`` path of ``execute``; the owner of
    interpretation accounts is named by the system). Every reference the payload names is held, else
    ``CustodyError``."""
    return ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)


async def execute_selected_tool(arguments, ctx):
    """The old ``scientific_operations.execute`` dispatch of a selected tool to the services' tool executor, over
    the library's ``ToolRegistry`` handed ``ctx.store``. An argument or reference error is an ``invalid`` outcome
    and a failed operation a ``failed`` one; both are outcomes that enter the iterator, as before. The old
    ``authenticate_source_byte_operands`` of the material and source tools was a callback of the old runner and is
    not in this episode's files."""
    registry = ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    permitted = arguments['permitted_record_refs']
    try:
        return await registry.execute_async(arguments['tool'], arguments['arguments'], scope=arguments['scope'],
                                            operation_key=ctx.operation_key,
                                            permitted_record_refs=None if permitted is None else tuple(permitted))
    except CustodyError:
        raise
    except (ContractError, ValueError, ValidationError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                             **({'detail': error.detail} if getattr(error, 'detail', None) else {})}}
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


async def pairwise_blast(arguments, ctx):
    """One pairwise comparison as one unit: run, fetch and grade, by the library's one function. The arguments are
    the model's four controlled choices."""
    return await pairwise_blast_comparison(
        ctx, program=arguments['program'], query_ref=arguments['query_ref'], reference_ref=arguments['reference_ref'],
        resource_id=arguments['resource_id'], executable_directory=ctx.settings['blast_executable_directory'])


async def profile_scan(arguments, ctx):
    """One profile scan as one unit: run, fetch and grade, by the library's one function. The arguments are the
    model's three controlled choices; the database's manifest and the programs' directory are settings."""
    return await hmmer_profile_scan(
        ctx, query_ref=arguments['query_ref'], database=arguments['database'], resource_id=arguments['resource_id'],
        executable_directory=ctx.settings['hmmer_executable_directory'],
        manifest_path=ctx.settings['profile_databases'][arguments['database']])


TOOLS = {'reason': reason, 'execute_selected_tool': execute_selected_tool, APPLY_GROUPING: apply_grouping, PAIRWISE_TOOL: pairwise_blast,
         PROFILE_TOOL: profile_scan}
