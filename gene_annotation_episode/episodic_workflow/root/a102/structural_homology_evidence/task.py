"""The task of the A102 head: one model-chosen unit per decision. The head has two actions. The commission of its child
``structure_search``: the model chooses the controlled fields of the commission (the target, the structure database, the
Foldseek resource, the model of the target and where the commission ends) and code builds the child's assignment
(``messages/msg_to_child.py``). And its one-shot tool ``site_correspondence`` (SOP Step 3): the model fills out the two fields of
a request (``search_ref`` and ``site_source``), ONE deterministic check (``check_site_correspondence_request``) runs in ``action``
before anything runs and refuses with its fix list, and a request that passes runs as ONE unit (``site_correspondence``: ask the
source, grade, keep the sheet through custody). The tool is offered only while a (graded search, site source) pair that can
succeed is left (``credit.offered_site_pairs``: the head holds the search's raw result and model and the pair is not graded), so
a request that passes the check works. Its second tool is ``partner_contacts``: the same three things (the request ``search_ref`` and
``resource_id``, ``check_partner_contacts_request`` run in ``action``, ONE async unit ``partner_contacts`` that downloads the solved
structures of the matched entries, runs the local US-align jobs through the job service and keeps two gradings), offered only for a
graded ``pdb100`` search that can be analysed (``credit.offered_partner_searches``) and a bound local resource, and whose programs
exist (``partner_options``). Its third tool is ``ligand_transplants``: the request ``model_ref``, ``check_ligand_transplants_request``
run in ``action``, ONE unit ``ligand_transplants`` that asks AlphaFill for the ligands transplanted into an AlphaFold DB model from solved
homologs, offered only for a held model whose origin is ``alphafold_db`` and that is not yet tested (``credit.offered_transplant_models``).
For an RNA target (the molecule of the held sequence record) the head offers two other tools and none of the protein ones, and the
protein tools are offered for a protein target only. ``rna_family_scan``: the request ``query_ref``, ``database`` and ``resource_id``,
``check_rna_family_scan_request`` run in ``action``, ONE async unit that runs ``cmscan`` of Infernal over the covariance database of the
settings as a local job and grades the table; it is offered while an RNA target of the scope exists (with the ceiling 0 once every
such target is scanned, as ``structure_search`` is offered for a protein with nothing left to search: the yield controller then finds
nothing worth its cost and stops), its request options only while a target is unscanned and a local resource is bound.
``rna_structure_agreement``: the request ``scan_ref`` and ``resource_id``, ``check_rna_structure_agreement_request``, ONE async unit that
aligns the span of each family of the scan to its model (``cmfetch`` and ``cmalign`` as a local job) and grades the consensus pairs the
target can form; offered only for a held scan that lists at least two families and is not yet tested (``credit.offered_agreement_scans``).
Settings of the head: ``python_executable``, ``usalign_executable_directory``, ``infernal_executable_directory`` and
``covariance_databases`` (``{database name: manifest path}``). It never ends the
Episode: only the yield controller does. No ``reason`` action.

The child. A slot is offered while its commission can be stated from what this episode holds: a protein sequence of the scope
(a target whose molecule is not protein gets no commission) and a bound Foldseek resource (``structure_search_fields``). ONE
deterministic check of the filled commission runs in ``action`` before any child exists (``COMMISSION_CHECKS``): a search of the
same query, database and model already graded or already commissioned is refused with its fix list, except the resume of the
parked job (the same fields, ``until`` ``extracted``). A Foldseek job a child launched and returned parked is always finished
(``resume_action``: the episode does not stop while one is parked, and once it is due, or when nothing else is worth its cost,
its resume is the unit; the rule is the system's, ``method_loop.episode_type``). The service ``job_access`` is read for the bound
resources a commission may name (``bound_resources``).

Settings: ``yield_bindings`` (``yield_estimator.py``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.jobs.foldseek_job_route import DATABASES
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence import (
    foldseek_search as foldseek)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.ligand_transplants import (
    check_ligand_transplants_request, ligand_transplants)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.rna_family_scan import (
    check_rna_family_scan_request, rna_family_scan)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.rna_structure_agreement import (
    check_rna_structure_agreement_request, rna_structure_agreement)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.site_correspondence import (
    check_site_correspondence_request, site_correspondence)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.partner_contacts import (
    check_partner_contacts_request, partner_contacts)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    ROUTE_KIND, UNTIL, _choose, seconds_between)

from .credit import (OBTAIN, PARTNER_TOOL, RNA_AGREEMENT_TOOL, RNA_SCAN_TOOL, SITE_TOOL, TRANSPLANT_TOOL, agreed_scans,
                     analysed_searches, commissioned, graded_site_pairs, offered_agreement_scans, offered_partner_searches,
                     offered_site_pairs, offered_transplant_models, queries, rna_queries, scanned_targets, tested_models,
                     transplant_models, unscanned_queries)
from .goal import GOAL

CHILD_SLOTS = {'structure_search': 'structural_homology_evidence/structure_search'}
SERVICES = ('job_access',)
SLOT = 'structure_search'
LEADING = 10


def site_correspondence_tool(arguments, ctx):
    """One site test as one unit, by the library's one function. The arguments are the model's two controlled choices."""
    return site_correspondence(ctx, search_ref=arguments['search_ref'], site_source=arguments['site_source'])


async def partner_contacts_tool(arguments, ctx):
    """One partner-contacts analysis as one unit, by the library's one function (an async unit: its local alignment jobs go through
    the job service). The arguments are the model's two controlled choices; the programs' locations are settings."""
    return await partner_contacts(ctx, search_ref=arguments['search_ref'], resource_id=arguments['resource_id'])


def ligand_transplants_tool(arguments, ctx):
    """One ligand-transplants test as one unit, by the library's one function. The argument is the model's one controlled choice."""
    return ligand_transplants(ctx, model_ref=arguments['model_ref'])


async def rna_family_scan_tool(arguments, ctx):
    """One RNA family scan as one unit, by the library's one function (an async unit: its local job goes through the job service). The
    arguments are the model's three controlled choices; the programs' and the database's locations are settings."""
    return await rna_family_scan(ctx, query_ref=arguments['query_ref'], database=arguments['database'],
                                 resource_id=arguments['resource_id'])


async def rna_structure_agreement_tool(arguments, ctx):
    """One RNA structure agreement test as one unit, by the library's one function (an async unit: its local job goes through the
    job service). The arguments are the model's two controlled choices."""
    return await rna_structure_agreement(ctx, scan_ref=arguments['scan_ref'], resource_id=arguments['resource_id'])


TOOLS = {SITE_TOOL: site_correspondence_tool, PARTNER_TOOL: partner_contacts_tool, TRANSPLANT_TOOL: ligand_transplants_tool,
         RNA_SCAN_TOOL: rna_family_scan_tool, RNA_AGREEMENT_TOOL: rna_structure_agreement_tool}

INSTRUCTIONS = (
    GOAL + '\n\n'
    'You are the head of this investigation. At each decision you choose exactly one action, from the actions offered '
    '(child_options and tool_options), by answering with the controlled fields of its commission or request; code builds '
    'everything the child is told. '
    'The child owns its own iterative work, and the configured yield controller owns continuation: you cannot end the '
    'episode. Recorded facts come from actual records and are shown to you as they are: the targets with their molecule and '
    'length, the models held (origin, residues, mean pLDDT: a model\'s own confidence, not similarity), the graded searches, '
    'the outstanding jobs with the seconds since their launch and the seconds still expected, the leading candidates with '
    'their scores and subscoring sheets (products, the partners ligand and nucleic_acid and, for an RNA target, the rna_family candidates), the site tests, partner tests, transplant tests, RNA scans and RNA agreement tests held, your earlier units and the yield table. A model that is not held is obtained by the '
    'child when the commission names obtain_one. Waiting and unchanged observations do not manufacture progress.')

# What the model is told of the child it may commission: what the child does, the controlled fields of its commission (the model
# chooses values; code builds the child's assignment) and what comes back. Facts the system enforces; no recommendation.
CREDIT_TEXT = ('Your credit counts possible annotations (candidates). A candidate found with positive evidence is admitted to the '
               'list and earns its score; a possible annotation with no positive evidence is not on the list. Applying the same '
               'test earns by how differently the two leading candidates respond: of the candidates already on the list that the '
               'test measures, the two with the highest scores earn the size of the difference of the moves of their scores in '
               'that test, and no other pair earns anything. A repeat earns nothing.')
PARKED_TEXT = ('A parked job is always finished: this episode does not end while one is parked; once its expected remaining '
               'seconds have passed, or when none of your other actions is worth its cost, code commissions its continuation '
               '(until extracted) as the next unit without asking you; before then you may do other work worth its cost.')
CHILD_DESCRIPTIONS = {
    SLOT: (
        'Search the structure of one protein sequence of your scope against one structure database on the Foldseek web server '
        '(the StructureSearch application; no key, no login), through one model of the target. The alignment mode is fixed '
        '(tmalign, a global TM-align alignment). The result is a ranked list of hits, each with its aligned residue pairs. For '
        'each hit code superposes the aligned C-alpha atoms and computes the index B = [2 n / (target length + hit length)] / '
        '[1 + (RMSD / 2 A)^2] (n the aligned pairs, RMSD in angstroms), looks up the hit\'s UniProt recommended protein name, and '
        'each distinct product name is a candidate (vocabulary product) whose value in the test is the mean B of its hits; the '
        'hit that is the target\'s own model in its own database is a control and gives no value to any candidate; a hit never '
        'asked about (the naming stops once the candidates settle) names no candidate. ' + CREDIT_TEXT + ' Fill the five fields '
        'of its commission: query_ref (a protein sequence of your scope; targets gives the molecule of each), database (the '
        'structure database; afdb-swissprot holds AlphaFold models of reviewed UniProt entries), resource_id (a foldseek '
        'resource of bound_resources), model_ref (a model of that target in held_models, passed to the child as it is, or '
        'obtain_one: the child then obtains a model itself, from a source of its own choosing) and until. Code checks the '
        'commission before the child is commissioned; if something is wrong it comes back in feedback with the things to fix and '
        'nothing was commissioned. While a child runs, you do nothing else: your next decision comes after it returns. What '
        'until means: with until launched the child estimates the duration, launches the search and returns at once; the search '
        'then keeps running at the service, you can use your other actions while it runs, and the child is said to be parked. '
        + PARKED_TEXT + ' With until extracted the child follows the search to its end, waiting between status requests for as '
        'long as the search takes, and extracts the result into the graded sheet; it is also how a parked search is continued: '
        'while structure_search_jobs shows a search of the target as outstanding, commissioning the child again with the same '
        'query, database and resource, the model that search was given and until extracted continues that search and submits '
        'nothing (code passes back the records the child returned). What comes back: the state of the search (no_model, '
        'model_held, estimated, launched, finished, extracted or failed), the model\'s origin, residues and mean pLDDT, the hit, '
        'named, not-asked and candidate counts, the seconds estimated and observed, the last failure code and the credit; the '
        'models and the graded sheet are kept as labelled data products. When the search is parked (parked true) the report is a '
        'wait notice: seconds_since_launch, estimated_seconds and expected_remaining_seconds (the estimate minus the seconds '
        'since the launch, not below zero, or the later revised figure of a status request), and structure_search_jobs keeps '
        'showing the search with the seconds since its launch and the seconds still expected as of each decision. A search of '
        'the same target, database and model that is graded, or that failed, is not commissioned again.'),
}

SITE_DESCRIPTION = (
    'Test whether the target has, in place, the functional residues of the proteins that one graded structure search matched. '
    'For each matched protein of the search that has a product name and a value, code asks one source for the protein\'s '
    'annotated functional residues and carries each residue through the search\'s structural alignment onto the target model '
    '(the alignment and the superposition are the search\'s; the residues never enter the fit). Per residue the score is a '
    'class match (1 when the target\'s residue at the aligned position equals the matched protein\'s residue or shares its '
    'role class: acidic DE, basic KR, aromatic FWY, hydroxyl STY, amide NQ, sulfur CM, small AGS; else 0) times the kernel '
    '1 / (1 + (d / 1 A)^2) of the distance d in angstroms between the two C-alpha atoms after the search\'s superposition. A '
    'residue the alignment does not align to the target is absent in the target: its score is 0 and it stays in the average; '
    'the sheet records where it is absent, outside_the_alignment (a part of the matched protein the target was not aligned to, '
    'for example another domain) or within_the_alignment (a gap inside the aligned span). A residue code cannot read (an '
    'isoform model of the matched protein, a position beyond its sequence, a letter that differs from the source, no model '
    'coordinate) is dropped with its reason and out of the average. A matched protein with no annotated residue gives no '
    'measurement. The value of a matched protein is B (its index in the search) times the mean of its residue scores; the '
    'value of a candidate (a product name) in this test is the mean of that over its matched proteins that have residues. A '
    'candidate none of whose matched proteins has a residue is not measured: that is not a value of zero. Two site sources: '
    'annotated (UniProt active-site, binding-site and site features of the matched proteins\' accessions) and catalytic (M-CSA '
    'catalytic residues of the matched proteins that are M-CSA reference entries). What it needs: a graded structure search '
    'that you hold with its raw result and model. Fill out the two fields of its request: search_ref (a graded search, '
    'graded_searches gives each with its source_ref) and site_source. Only pairs not yet graded are offered; the same search '
    'and site source are not run again. Code checks the request before anything runs; if something is wrong it comes back in '
    'feedback with the things to fix and nothing ran. A request that passes runs as one unit with no second call: code asks the '
    'source for every matched protein of the search (UniProt in batches of 100, M-CSA in one request), grades, and keeps the '
    'sheet. The grading is automatic: each measured candidate\'s value is counted as soon as the unit completes. site_tests shows '
    'the tests held: for each its search, its site source, the matched proteins asked, those with residues, the candidates '
    'measured and those without a residue, and the residues absent outside and within the alignment. ' + CREDIT_TEXT +
    ' A failed outcome is a fault of the environment and the same request is not made again.')


PARTNER_DESCRIPTION = (
    'For the proteins that one graded pdb100 structure search matched in solved structures, show what is bound to them, a ligand or '
    'DNA or RNA, and test whether the target has the contacting residues in place. What it needs: a graded pdb100 search that you '
    'hold with its raw result, model and hit metadata (graded_searches gives each with its source_ref; searches of another '
    'database are not offered), and a local resource of bound_resources for the alignment jobs. Fill out the two fields of its '
    'request: search_ref and resource_id. What code does: it takes the matched proteins of the search in rank order, one solved '
    'structure file at a time (the biological assembly the hit names, from files.rcsb.org; no name, email or key). A structure '
    'whose entry the hit metadata shows to hold no ligand outside the list of crystallization and buffer components (BioLiP) and '
    'no DNA or RNA is not downloaded (recorded no_partner_in_entry). The structure files it does download are kept as '
    'experimental_structure products; one larger than 8 MiB is recorded too_large and not asked. A partner of the matched protein '
    'is every other molecule of the structure with a heavy atom within 4.0 A of a heavy atom of the matched chain: a ligand '
    '(by chemical component id; water is not a partner), a DNA or RNA chain; other protein chains and glycans are recorded as '
    'facts only. A ligand on the BioLiP list of crystallization and buffer components is recorded as additive and is no '
    'candidate and gives no contact residue. One local job per batch of ten structure files aligns the target model with each '
    'matched chain by US-align; the alignments are kept as products. Per contact residue of the matched chain the score is the '
    'class match times the kernel 1 / (1 + (d / 1 A)^2) of the distance d between the aligned target residue and the matched '
    'residue after the superposition (a contact residue the alignment does not align to the target is absent: score 0, '
    'recorded outside_the_alignment or within_the_alignment); F is the mean of the residue scores, E = B F with B the search\'s '
    'index of the matched protein. The unit stops when a batch admits no new candidate in either test and moves no value by '
    'more than 0.01, after at least two batches, or when every structure is done; matched proteins of structures never reached '
    'are not_asked. It grades two tests and keeps both sheets: the matched proteins by their binding machinery '
    '(site_correspondence:partner_contacts, candidates are the products, the value of a product is the mean E over its '
    'matched proteins that have a ligand or nucleic-acid partner; a product none of whose matched proteins has one is not '
    'measured, not zero) and the bound partners themselves (bound_partner:pdb100, candidates are ligand:<chemical component '
    'id> and nucleic_acid:dna or nucleic_acid:rna; the value is the mean E of the matched proteins bound to it). Code checks the '
    'request before anything runs; if something is wrong it comes back in feedback with the things to fix and nothing ran. A '
    'request that passes runs as one unit with no second call; the same search is not analysed again. partner_tests shows the '
    'analyses held: for each its search, the structure files asked, skipped without a partner, too large, not obtained, the '
    'matched proteins with partners, the products measured and the partners measured. candidates shows the leading products '
    'and the partner candidates, each with its score and subscoring sheets. ' + CREDIT_TEXT + ' A failed outcome is a fault of '
    'the environment and the same request is not made again.')

TRANSPLANT_DESCRIPTION = (
    'Ask AlphaFill (alphafill.eu) which ligands and cofactors have a place in one AlphaFold DB model of the target, as they sit in '
    'solved homologs. What it needs: a held model whose origin is alphafold_db (held_models; a model of another origin is not '
    'offered, and a model already tested is not offered again). Fill out the one field of its request: model_ref. What code does: one '
    'request to AlphaFill for the model\'s accession. AlphaFill superposes the surroundings of each ligand of a solved homolog '
    '(more than 25% identity over at least 85 aligned residues) onto the model and reports, per transplant, local_rmsd (how well the '
    'ligand\'s surroundings fit, angstroms) and the clash score (how much the placed ligand collides with the model, angstroms). Per '
    'transplant the sheet keeps these facts (with the donor entry and chain, the donor\'s ligand and the ligand AlphaFill placed, the '
    'alignment identity and length, the global RMSD, the clash count and atom count, the mean PAE and the model residues near the '
    'ligand) and two degrees, each 1 / (1 + (x / s)^2): fit of local_rmsd with s = 0.92 A and no_clash of the clash score with s = '
    '0.64 A (AlphaFill\'s own boundaries between high and medium confidence); the transplant\'s value is fit times no_clash, 0 to 1. '
    'A ligand on the BioLiP list of crystallization and buffer components is recorded as additive, has no value and is no '
    'candidate. A candidate is ligand:<chemical component id of the solved donor> (the same name partner_contacts gives a ligand); '
    'its value in the test is the value of its best transplant and the sheet shows how many transplants it has. A model AlphaFill '
    'holds with no transplant (no_transplants) or has no entry for (no_alphafill_entry) gives no candidate; both count as the test '
    'run. The model the numbers are for is the AlphaFold DB model AlphaFill used (a version that may differ from the model you hold: '
    'recorded as model_version_differs); only AlphaFill\'s numbers are used. Code checks the request before anything runs; if '
    'something is wrong it comes back in feedback with the things to fix and nothing ran. A request that passes runs as one unit '
    'with no second call. transplant_tests shows the tests held: for each its model, the outcome, the hits and transplants, the '
    'additive transplants and the candidates measured. candidates shows the ligand candidates with their scores and subscoring '
    'sheets. ' + CREDIT_TEXT + ' An answer of another shape, or an HTTP status other than 200 and 404, fails the run.')


RNA_SCAN_DESCRIPTION = (
    'Find which structured RNA family (Rfam) the RNA target is, by Infernal\'s covariance models: a family\'s consensus sequence and its '
    'consensus base pairs. For an RNA target only (a protein target is not offered it). What it needs: an RNA sequence of your scope '
    'that is not yet scanned (targets gives the molecule of each), a covariance database of the settings and a local resource of '
    'bound_resources. Fill out the three fields of its request: query_ref, database and resource_id. What code does: one local job, '
    'cmscan over every model of the database by Rfam\'s own command for annotating a sequence (each family\'s own gathering threshold '
    'GA decides what is reported; one CPU; Z as Rfam defines it, the nucleotides searched in millions times two for the two strands). '
    'Per hit the sheet keeps the family, its clan, the bit score, the E-value (it depends on Z and weighs nothing), the model and '
    'sequence spans, the strand, the truncation and whether a better hit of the same clan overlaps it (such a hit is kept: it is the '
    'competing family), and the family\'s GA. A hit\'s value is x^2 / (1 + x^2) with x the bit score over GA (a hit at GA has value one '
    'half, a hit at twice GA 0.8, and it rises gradually towards 1). A candidate is rna_family:<Rfam accession> (its name is the '
    'family\'s Rfam identifier); its value in the test is the value of its best hit. A sequence with no hit gives no candidate '
    '(no_family) and counts as the test run. One scan of a target is made; code checks the request before anything runs, and if '
    'something is wrong it comes back in feedback with the things to fix and nothing ran. A request that passes runs as one unit with '
    'no second call. rna_scan_tests shows the scans held: for each its target, database, outcome, hits, hits overlapped by a better hit '
    'of the clan and families measured. candidates shows the rna_family candidates with their scores and subscoring sheets. '
    + CREDIT_TEXT + ' A failed outcome is a fault of the environment and the same request is not made again.')

RNA_AGREEMENT_DESCRIPTION = (
    'Test whether the RNA target can form the consensus base pairs of each family that one held scan listed. What it needs: a held '
    'rna_family_scan that lists at least two families (rna_scan_tests gives each with its source_ref; with one family there is no '
    'other family to tell it from, so it is not offered) and is not yet tested, and a local resource. Fill out the two fields of its '
    'request: scan_ref and resource_id. What code does, for every family of the scan: one local job fetches the family\'s model and '
    'aligns the span of the target the scan\'s best hit of the family covers to it (cmalign, local mode, one CPU); the base pairs are '
    'the matched brackets of the alignment\'s consensus structure. Per family the sheet counts the consensus pairs, the pairs whose two '
    'positions both hold a residue of the target, and of those the canonical ones (AU, GC, GU either way); the family\'s value is the '
    'canonical pairs over the consensus pairs, 0 to 1: the share of the family\'s base pairs this sequence can form. A family whose '
    'consensus has no base pair is not measured (not zero). The sheet keeps, as facts that weigh nothing, each consensus stem with its '
    'pairs, pairs present and pairs canonical, the counts of stems wholly, partly and not formable, the target\'s residues inserted '
    'relative to the model and the consensus positions with no residue. The candidates are the scan\'s rna_family candidates, so the '
    'test measures the candidates already on the list and earns the differential of the top two. Code checks the request before '
    'anything runs; if something is wrong it comes back in feedback with the things to fix and nothing ran. A request that passes runs '
    'as one unit with no second call. rna_agreement_tests shows the tests held: for each its scan, the families aligned, those '
    'measured and the consensus pairs and canonical pairs summed. ' + CREDIT_TEXT + ' A failed outcome is a fault of the '
    'environment and the same request is not made again.')


def bound_resources(ctx):
    """The resources bound to the job service, each with its kind, which a commission may name (read through the service's read
    handle, so the read is recorded with the decision)."""
    return {resource['resource_id']: resource['kind'] for resource in ctx.services['job_access'].read('resources')}


def structure_search_fields(summary, resources):
    """What the model supplies to commission ``structure_search``, as ``(properties, required)``: controlled values only. ``None`` while
    this episode holds nothing the commission could be chosen from (no protein sequence in the scope, or no bound Foldseek
    resource): the slot is then not offered. The model is one of the held models of the targets, or ``obtain_one`` while a target
    has none."""
    targets = queries(summary)
    services = [name for name, kind in resources.items() if kind == ROUTE_KIND]
    if not targets or not services:
        return None
    models = [row['id'] for row in summary['model_rows'] if row['query_ref'] in targets]
    if any(all(row['query_ref'] != target for row in summary['model_rows']) for target in targets):
        models.append(OBTAIN)
    properties = {'query_ref': {'type': 'string', 'enum': targets}, 'database': {'type': 'string', 'enum': list(DATABASES)},
                  'resource_id': {'type': 'string', 'enum': services}, 'model_ref': {'type': 'string', 'enum': models},
                  'until': {'type': 'string', 'enum': list(UNTIL)}}
    return properties, list(properties)


def check_structure_search(commission, summary, resources, records):
    """The things to fix in a commission of ``structure_search``: the child's own commission check
    (``foldseek_search.check_commission``: the query is a protein sequence of the scope, the database is offered, the model is a
    held model product, the resource is a bound Foldseek service, an outstanding job of this search is continued with ``until``
    ``extracted`` and another one blocks it, a search of the same query, database and model graded, or commissioned and not
    outstanding, is not commissioned again), over the graded searches the credit's own reader gives (``held_searches``) and the
    jobs read from the job ledger rows the head holds; and that the model is of the query."""
    model_ref = None if commission['model_ref'] == OBTAIN else commission['model_ref']
    request = {'query_ref': commission['query_ref'], 'database': commission['database'],
               'resource_id': commission['resource_id'], 'until': commission['until'], 'model_ref': model_ref}
    searches = [{'query_ref': target, 'database': database, 'model_sha256': sha}
                for target, pairs in summary['held_searches'].items() for database, sha in pairs]
    problems = foldseek.check_commission(
        request, scope_subjects=summary['scope']['subject_refs'], sequences=summary['held_sequences'], resources=resources,
        jobs=summary['structure_search_jobs'],
        commissioned=[(query, database, None if model == OBTAIN else model) for query, database, model in commissioned(summary)],
        models={row['id']: row for row in summary['model_rows']}, searches=searches)
    mine = [row['id'] for row in summary['model_rows'] if row['query_ref'] == commission['query_ref']]
    if model_ref is not None and mine and model_ref not in mine:
        problems.append(_choose('model_ref', 'model_is_not_of_the_query', choose_from=mine))
    if model_ref is None and mine:
        problems.append(_choose('model_ref', 'a_model_of_the_query_is_held', choose_from=mine))
    return problems


def site_options(summary):
    """The request of the ``site_correspondence`` tool as the model fills it out: one option per graded search that still has a
    site source to grade (``credit.offered_site_pairs``), the search and the site sources left for it. Empty while no pair can
    succeed (no graded search with its raw result and model held, or every pair graded)."""
    pairs = offered_site_pairs(summary)
    return [{'type': 'object', 'additionalProperties': False, 'required': ['name', 'search_ref', 'site_source'],
             'properties': {'name': {'type': 'string', 'enum': [SITE_TOOL]}, 'search_ref': {'type': 'string', 'enum': [search]},
                            'site_source': {'type': 'string', 'enum': [source for found, source in pairs if found == search]}}}
            for search in dict.fromkeys(search for search, _ in pairs)]


def check_site_request(request, summary):
    """The things to fix in a request of ``site_correspondence``: the library's one check
    (``check_site_correspondence_request``) over the searches the head holds with their raw result and model
    (``site_correspondence.search_inputs`` as ``internal_summary`` reads it) and the site tests already graded."""
    return check_site_correspondence_request(request, searches=summary['search_inputs'], graded=graded_site_pairs(summary))


def partner_options(summary, resources, settings):
    """The request of the ``partner_contacts`` tool as the model fills it out: one option per graded ``pdb100`` search that can be
    analysed now (``credit.offered_partner_searches``), with the bound local resources. Only searches whose request passes the
    library's check are offered, so a request taken from the schema works (the check also needs the programs and the python of
    the settings). Empty while none can succeed."""
    local = [name for name, kind in resources.items() if kind == 'local']
    return [{'type': 'object', 'additionalProperties': False, 'required': ['name', 'search_ref', 'resource_id'],
             'properties': {'name': {'type': 'string', 'enum': [PARTNER_TOOL]}, 'search_ref': {'type': 'string', 'enum': [search]},
                            'resource_id': {'type': 'string', 'enum': local}}}
            for search in offered_partner_searches(summary)
            if local and not check_partner_request({'search_ref': search, 'resource_id': local[0]}, summary, resources, settings)]


def check_partner_request(request, summary, resources, settings):
    """The things to fix in a request of ``partner_contacts``: the library's one check (``check_partner_contacts_request``) over the
    searches the head holds with their raw result, model, hit metadata and partner metadata (``partner_contacts.
    partner_search_inputs`` as ``internal_summary`` reads it), the searches already analysed, the bound resources and the
    programs of the settings."""
    return check_partner_contacts_request(
        request, searches=summary['search_inputs'], analysed=analysed_searches(summary), resources=resources,
        usalign_directory=settings['usalign_executable_directory'], python=settings['python_executable'])

def transplant_options(summary):
    """The request of the ``ligand_transplants`` tool as the model fills it out: one option per held AlphaFold DB model not yet
    tested (``credit.offered_transplant_models``). Empty while none is."""
    return [{'type': 'object', 'additionalProperties': False, 'required': ['name', 'model_ref'],
             'properties': {'name': {'type': 'string', 'enum': [TRANSPLANT_TOOL]}, 'model_ref': {'type': 'string', 'enum': [model]}}}
            for model in offered_transplant_models(summary)]


def check_transplant_request(request, summary):
    """The things to fix in a request of ``ligand_transplants``: the library's one check (``check_ligand_transplants_request``) over
    the held models and the models already tested."""
    return check_ligand_transplants_request(request, models=transplant_models(summary), tested=tested_models(summary))


def rna_scan_options(summary, resources, settings):
    """The request of the ``rna_family_scan`` tool as the model fills it out: one option per RNA sequence of the scope not yet scanned,
    with the databases of the settings and the bound local resources. Only options whose request passes the library's check are
    offered, so a request taken from the schema works. Empty while no target is left, or no local resource or database is bound."""
    targets = unscanned_queries(summary)
    if not targets:
        return []
    local = [name for name, kind in resources.items() if kind == 'local']
    databases = sorted(settings['covariance_databases'])
    return [{'type': 'object', 'additionalProperties': False, 'required': ['name', 'query_ref', 'database', 'resource_id'],
             'properties': {'name': {'type': 'string', 'enum': [RNA_SCAN_TOOL]}, 'query_ref': {'type': 'string', 'enum': [query]},
                            'database': {'type': 'string', 'enum': databases}, 'resource_id': {'type': 'string', 'enum': local}}}
            for query in targets
            if local and databases and not check_rna_scan_request(
                {'query_ref': query, 'database': databases[0], 'resource_id': local[0]}, summary, resources, settings)]


def rna_scan_offered(summary, resources, settings):
    """Whether ``rna_family_scan`` is an offered action: an RNA target of the scope exists and either its request can be stated now
    (``rna_scan_options``) or every such target is already scanned (the action is then offered with the ceiling 0, as
    ``structure_search`` is for a protein with nothing left to search, and the yield controller stops the episode)."""
    return bool(rna_queries(summary)) and (bool(rna_scan_options(summary, resources, settings)) or not unscanned_queries(summary))


def check_rna_scan_request(request, summary, resources, settings):
    """The things to fix in a request of ``rna_family_scan``: the library's one check (``check_rna_family_scan_request``) over the
    sequences the head holds, the targets already scanned, the bound resources and the databases and programs of the settings."""
    return check_rna_family_scan_request(
        request, sequences=summary['held_sequences'], scope_subjects=summary['scope']['subject_refs'], resources=resources,
        scanned=scanned_targets(summary), databases=settings['covariance_databases'],
        executable_directory=settings['infernal_executable_directory'])


def rna_agreement_options(summary, resources, settings):
    """The request of the ``rna_structure_agreement`` tool as the model fills it out: one option per held scan that lists at least two
    families and is not yet tested (``credit.offered_agreement_scans``), with the bound local resources. Only requests that pass the
    library's check are offered. Empty while none can succeed."""
    local = [name for name, kind in resources.items() if kind == 'local']
    return [{'type': 'object', 'additionalProperties': False, 'required': ['name', 'scan_ref', 'resource_id'],
             'properties': {'name': {'type': 'string', 'enum': [RNA_AGREEMENT_TOOL]}, 'scan_ref': {'type': 'string', 'enum': [scan]},
                            'resource_id': {'type': 'string', 'enum': local}}}
            for scan in offered_agreement_scans(summary)
            if local and not check_rna_agreement_request({'scan_ref': scan, 'resource_id': local[0]}, summary, resources, settings)]


def check_rna_agreement_request(request, summary, resources, settings):
    """The things to fix in a request of ``rna_structure_agreement``: the library's one check
    (``check_rna_structure_agreement_request``) over the scans the head holds (``rna_family_scan.rna_scan_inputs`` as
    ``internal_summary`` reads it), the scans already tested, the bound resources and the programs of the settings."""
    return check_rna_structure_agreement_request(
        request, scans=summary['rna_scan_inputs'], tested=agreed_scans(summary), resources=resources,
        executable_directory=settings['infernal_executable_directory'], python=settings['python_executable'])


COMMISSIONS = {SLOT: structure_search_fields}
COMMISSION_CHECKS = {SLOT: check_structure_search}


def jobs_view(jobs, now):
    """The searches this episode's child launched as the model sees them at ``now`` (the decision's recorded time): each with
    its state, whether it is outstanding, and for an outstanding one the seconds since its launch and the seconds still
    expected: the estimate recorded with its launch minus those seconds, not below zero. Facts, never a deadline."""
    shown = []
    for job in jobs:
        row = {'handoff_ref': job['handoff_ref'], 'query_ref': job['identity']['query_ref'],
               'database': job['identity']['database'], 'resource_id': job['resource_id'], 'latest_state': job['latest_state'],
               'outstanding': job['outstanding'], 'closed': job['closed'], 'estimated_seconds': job['estimated_seconds']}
        if job['outstanding']:
            elapsed = seconds_between(job['launched_at'], now)
            row.update(seconds_since_launch=elapsed, expected_remaining_seconds=max(job['estimated_seconds'] - elapsed, 0.0))
        shown.append(row)
    return shown


def offered_children(summary, resources):
    """The children this decision offers: those whose commission this episode can state now."""
    return [slot for slot in CHILD_SLOTS if COMMISSIONS[slot](summary, resources) is not None]


def child_option(slot, summary, resources):
    """One child the model may commission: its name and the controlled fields of its commission."""
    properties, required = COMMISSIONS[slot](summary, resources)
    properties = {'name': {'type': 'string', 'enum': [slot]}, **properties}
    return {'type': 'object', 'additionalProperties': False, 'required': ['name', *required], 'properties': properties}


def selection_schema(summary, resources, settings):
    """What the model answers with: one commission of one offered child, or one request of the tool."""
    return {'type': 'object', 'additionalProperties': False, 'required': ['action'],
            'properties': {'action': {'anyOf': [child_option(slot, summary, resources)
                                                for slot in offered_children(summary, resources)] + site_options(summary)
                                  + partner_options(summary, resources, settings) + transplant_options(summary)
                                  + rna_scan_options(summary, resources, settings)
                                  + rna_agreement_options(summary, resources, settings)}}}


def offered_actions(summary, ctx):
    """The action types this decision offers, by the names a unit is recorded under (``ChildCall.slot``, ``ToolCall.name``): each
    child slot whose commission can be stated (``offered_children``, the function ``decide`` offers the model with) and
    ``site_correspondence``, ``partner_contacts`` and ``ligand_transplants`` while a request of it can succeed (``site_options``,
    ``partner_options``, ``transplant_options``), ``rna_family_scan`` while an RNA target of the scope exists (its ceiling is 0 once
    every such target is scanned) and ``rna_structure_agreement`` while a request of it can succeed (``rna_agreement_options``)."""
    resources = bound_resources(ctx)
    return (offered_children(summary, resources) + ([SITE_TOOL] if site_options(summary) else [])
            + ([PARTNER_TOOL] if partner_options(summary, resources, ctx.settings) else [])
            + ([TRANSPLANT_TOOL] if transplant_options(summary) else [])
            + ([RNA_SCAN_TOOL] if rna_scan_offered(summary, resources, ctx.settings) else [])
            + ([RNA_AGREEMENT_TOOL] if rna_agreement_options(summary, resources, ctx.settings) else []))


def parked_jobs(summary):
    """The jobs of this episode's child that are parked (outstanding: launched, no closure held, not shown failed or lost),
    from the summary's view of the job ledger rows."""
    return [job for job in summary['structure_search_jobs'] if job['outstanding']]


def resume_commission(job, summary):
    """The commission that resumes the parked ``job``: the job's own commission again with ``until`` ``extracted`` (the one
    commission of it the head's check accepts while it is outstanding; it submits nothing): the search's query, database and
    resource and the model the job was given (the held model row of its SHA-256)."""
    identity = job['identity']
    model = next(row['id'] for row in summary['model_rows'] if row['settings']['sha256'] == identity['model_sha256'])
    return {'query_ref': identity['query_ref'], 'database': identity['database'], 'resource_id': job['resource_id'],
            'model_ref': model, 'until': 'extracted'}


def resume_action(summary, records, ctx):
    """The resume this episode owes (``method_loop.episode_type``; the owner, 2026-11-21: "the head must finish parked jobs"):
    ``None`` while no job is parked, else the resume of one parked job as ``{'action_type': its slot, 'arguments':
    resume_commission(...), 'due': ...}``. ``due`` is True once the job's expected remaining seconds have passed: the estimate
    recorded with its launch minus the seconds from the launch to this decision's recorded time (the wait notice ``jobs_view``
    shows), at or below zero. The job chosen: the earliest launched among the due ones, else the earliest launched. The
    commission passes the head's own check (``COMMISSION_CHECKS``), else this raises: a resume the check refuses is a fault of
    the episode."""
    parked = parked_jobs(summary)
    if not parked:
        return None
    remaining = lambda job: job['estimated_seconds'] - seconds_between(job['launched_at'], ctx.clock.now)
    due = [job for job in parked if remaining(job) <= 0]
    job = min(due or parked, key=lambda item: item['launched_at'])
    arguments = resume_commission(job, summary)
    problems = COMMISSION_CHECKS[SLOT](arguments, summary, bound_resources(ctx), records)
    if problems:
        raise ContractError('a102_resume_commission_refused_by_its_check:' + SLOT + ':' + repr(problems))
    return {'action_type': SLOT, 'arguments': arguments, 'due': bool(due)}


def outcome_row(row):
    """One earlier unit as the model sees it: a child commission (its slot, state and credit) or a tool request (its name, status and
    the counts of its result)."""
    if row['kind'] == 'tool':
        return {'position': row['position'], 'tool': row['tool'], 'arguments': row['arguments'], 'status': row['status'],
                **row['result']}
    return {key: row[key] for key in ('position', 'slot', 'arguments', 'child_state', 'credit', 'parked')}


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the commission's scope (the targets), the resources, the models, the graded
    searches, the jobs, the leading candidates, its own outcomes, the child it may use, the measured time and the yield table."""
    resources = bound_resources(ctx)
    offered = offered_children(summary, resources)
    context = {
        'goal': GOAL, 'scope': summary['scope'], 'targets': summary['targets'], 'bound_resources': resources,
        'held_models': [{'row_ref': row['id'], 'query_ref': row['query_ref'], 'origin': row['settings']['origin'],
                         'residues': row['settings']['residues_covered'], 'mean_plddt': row['settings']['mean_plddt']}
                        for row in summary['model_rows']],
        'graded_searches': [{key: row[key] for key in ('source_ref', 'query_ref', 'database', 'hit_count', 'named_count',
                                                       'candidate_count')} for row in summary['graded_searches']],
        'structure_search_jobs': jobs_view(summary['structure_search_jobs'], ctx.clock.now),
        'candidates': [{'target_ref': ref, 'candidate_counts': row['candidate_counts'], 'leading_products': row['products'],
                        'partners': row['partners'], 'rna_families': row['rna_families']}
                       for ref, row in summary['credit_table'].items()],
        'site_tests': summary['site_test_rows'], 'partner_tests': summary['partner_test_rows'],
        'transplant_tests': summary['transplant_test_rows'], 'rna_scan_tests': summary['rna_scan_test_rows'],
        'rna_agreement_tests': summary['rna_agreement_test_rows'],
        'own_outcomes': [outcome_row(row) for row in summary['units']],
        'child_options': [{'slot': slot, 'binding_path': CHILD_SLOTS[slot], 'description': CHILD_DESCRIPTIONS[slot]}
                          for slot in offered],
        'tool_options': ([{'name': SITE_TOOL, 'description': SITE_DESCRIPTION}] if site_options(summary) else [])
                        + ([{'name': PARTNER_TOOL, 'description': PARTNER_DESCRIPTION}]
                           if partner_options(summary, resources, ctx.settings) else [])
                        + ([{'name': TRANSPLANT_TOOL, 'description': TRANSPLANT_DESCRIPTION}] if transplant_options(summary) else [])
                        + ([{'name': RNA_SCAN_TOOL, 'description': RNA_SCAN_DESCRIPTION}]
                           if rna_scan_options(summary, resources, ctx.settings) else [])
                        + ([{'name': RNA_AGREEMENT_TOOL, 'description': RNA_AGREEMENT_DESCRIPTION}]
                           if rna_agreement_options(summary, resources, ctx.settings) else [])
                        or None,
        'yield_table': summary['yield_table'], 'time_accounting': time_accounting(ctx.clock.progress_time),
        'feedback': feedback}
    return ModelRequest('REASONING', INSTRUCTIONS, {key: value for key, value in context.items() if value is not None},
                        selection_schema(summary, resources, ctx.settings))


def action(response, summary, records, ctx):
    """Turn the model's answer into one commission, or reject it (no unit): an answer that does not fit the schema, or a
    commission the check finds something to fix in (rejected with the things to fix)."""
    resources = bound_resources(ctx)
    try:
        Draft202012Validator(selection_schema(summary, resources, ctx.settings)).validate(response)
    except (ValueError, KeyError, TypeError, ContractError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    chosen = response['action']
    slot = chosen['name']
    commission = {key: value for key, value in chosen.items() if key != 'name'}
    if slot == SITE_TOOL:
        problems = check_site_request(commission, summary)
        if problems:
            raise Rejected({'status': 'invalid', 'category': SITE_TOOL + '_request',
                            'detail': {'request': commission, 'fix': problems}})
        return ToolCall(SITE_TOOL, commission)
    if slot == PARTNER_TOOL:
        problems = check_partner_request(commission, summary, resources, ctx.settings)
        if problems:
            raise Rejected({'status': 'invalid', 'category': PARTNER_TOOL + '_request',
                            'detail': {'request': commission, 'fix': problems}})
        return ToolCall(PARTNER_TOOL, commission)
    if slot == TRANSPLANT_TOOL:
        problems = check_transplant_request(commission, summary)
        if problems:
            raise Rejected({'status': 'invalid', 'category': TRANSPLANT_TOOL + '_request',
                            'detail': {'request': commission, 'fix': problems}})
        return ToolCall(TRANSPLANT_TOOL, commission)
    if slot == RNA_SCAN_TOOL:
        problems = check_rna_scan_request(commission, summary, resources, ctx.settings)
        if problems:
            raise Rejected({'status': 'invalid', 'category': RNA_SCAN_TOOL + '_request',
                            'detail': {'request': commission, 'fix': problems}})
        return ToolCall(RNA_SCAN_TOOL, commission)
    if slot == RNA_AGREEMENT_TOOL:
        problems = check_rna_agreement_request(commission, summary, resources, ctx.settings)
        if problems:
            raise Rejected({'status': 'invalid', 'category': RNA_AGREEMENT_TOOL + '_request',
                            'detail': {'request': commission, 'fix': problems}})
        return ToolCall(RNA_AGREEMENT_TOOL, commission)
    problems = COMMISSION_CHECKS[slot](commission, summary, resources, records)
    if problems:
        raise Rejected({'status': 'invalid', 'category': slot + '_commission',
                        'detail': {'commission': commission, 'fix': problems}})
    return ChildCall(slot, commission)
