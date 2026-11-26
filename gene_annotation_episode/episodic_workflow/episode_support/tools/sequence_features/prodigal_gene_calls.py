"""One run of the gene finder Prodigal (Pyrodigal) on one nucleotide sequence: the check of the request, and the run as
one unit.

The episode's model fills out one request: ``searched_ref`` (a held sequence) and ``code`` (a genetic code). Two
functions of this module do the rest, deterministically:

``check_prodigal_request`` examines the request against what the episode holds, before anything runs. It returns the
things to fix (one entry per problem: the field, a code and, where there is one, what to choose from); an empty list means
the request can run. The episode's ``action`` rejects a request with problems, so no unit is made.

``prodigal_gene_calls`` runs a request that passed the check, as one unit: it reads the searched sequence through custody,
calls the finder in process (``sequence_ops.predict_genes``; on the 614-letter piece of 2026-11-25 the whole launch,
imports included, took 0.65 seconds, ``runs/feature_calling_20261125/pyrodigal_facts/workflow-result.json``: no job),
grades the native result (``prodigal_grader.grade_prodigal``), turns the graded genes into
statements about the sequence's features (``prodigal_calls.prodigal_call_sheet``) and keeps, through custody in one
transaction:

1. the native result as an artifact (JSON);
2. the grading, retained beside it (``retain_tool_grading``);
3. the call sheet, retained as a second grading beside the native result;
5. one ``source`` record of the provider ``native.pyrodigal.find_genes`` over the native result, whose operand is the
   sequence the statements are about and whose auxiliary artifacts are the two gradings (the sheet of feature calls
   reads it: ``feature_candidates.feature_tests``);
6. both gradings labelled as ``tool_grading_sheet`` data products (``record_grading_product``), the call sheet derived
   from the grading.

Grading is not a choice of anyone: it follows the run in the same unit.

THE MODE is not a choice: it follows from the length of the searched sequence by Prodigal's own rule. Training the
finder on the sequence itself (``single``) needs at least ``pyrodigal.MIN_SINGLE_GENOME`` = 20,000 letters
(``pyrodigal/lib.pyx`` line 170, exported at line 205 and in ``pyrodigal/__init__.py`` line 20; ``GeneFinder.train``
raises a ``ValueError`` below it, lines 5546-5549, and warns below 100,000, ``IDEAL_SINGLE_GENOME``, lines 5550-5553; the
length is that of the letters given, line 576). Below it the finder uses its pre-trained models (``meta``).

THE CODES each mode can take:

* ``meta``: the genetic codes of the pre-trained models, ``pyrodigal.METAGENOMIC_BINS`` (built from Prodigal's compiled
  training data, ``lib.pyx`` line 5069): 4 and 11, as read from the installed package on 2026-11-25
  (``runs/feature_calling_20261125/pyrodigal_facts/stdout.log``). The list is read from the package when this module is
  imported, not written here.
* ``single``: the translation tables Prodigal can train with, ``pyrodigal.TRANSLATION_TABLES`` (``lib.pyx`` line 172:
  1 to 6, 9 to 16, 21 to 26, 29, 30, 32, 33; checked by ``GeneFinder.train``, line 5528).

Both are kept to the codes ``predict_genes`` takes (the tables of Biopython, ``sequence_ops.py`` line 86), which hold
every one of them.

THE LETTERS: the finder reads DNA letters only (``predict_genes`` refuses any other letter, ``U`` included,
``sequence_ops.py`` lines 90-91). That is this tool's own knowledge of what it takes, stated in its check.

The searched sequence can be a product derived from another (an extracted stretch, a reverse complement: its record has a
``mapping``). The statements are then about the sequence its mapping leads back to, as in
``blast_claim_keeping.keep_blast_claims``: the source names that sequence, and the positions are
carried back by the mapping (``prodigal_calls``). The feature records of the candidates are then settled
(``feature_record_keeping.settle_feature_records``).

The outcome has the shape of every tool outcome of an episode. ``completed``: ``record_refs`` are the source, the native
result, the two gradings, their product rows and the feature records; ``result`` holds the mode, the code, the gene count
and the counts of genes with both ends (feature calls), with one end and with none (claims). A sequence with no gene is
completed with no statement. Nothing is caught: an error raised after a passed check is the unit's failure as the runner
records it."""
import pyrodigal
from Bio.Data import CodonTable

from gene_annotation_episode.prodigal_grader import grade_prodigal
from gene_annotation_episode.sequence_ops import predict_genes
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    canonical)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.prodigal_calls import (
    prodigal_call_sheet)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_features.feature_record_keeping import (
    settle_feature_records)

PROVIDER = 'native.pyrodigal.find_genes'
SEARCHED_MOLECULES = ('dna',)
MIN_TRAINING_LETTERS = pyrodigal.MIN_SINGLE_GENOME
# The genetic codes each mode can take (the module's description).
MODE_CODES = {
    'meta': sorted({item.training_info.translation_table for item in pyrodigal.METAGENOMIC_BINS}
                   & set(CodonTable.unambiguous_dna_by_id)),
    'single': sorted(set(pyrodigal.TRANSLATION_TABLES) & set(CodonTable.unambiguous_dna_by_id))}


def prodigal_mode(length):
    """The mode of a run on a sequence of ``length`` letters: ``single`` (trained on the sequence) from
    ``MIN_TRAINING_LETTERS`` letters, ``meta`` (the pre-trained models) below."""
    return 'single' if length >= MIN_TRAINING_LETTERS else 'meta'


def check_prodigal_request(request, *, sequences, lengths, made):
    """The things to fix in a gene finding request, before anything runs; an empty list means it can run.

    ``request`` holds ``searched_ref`` (a key of ``sequences``) and ``code`` (a genetic code); the caller's schema has
    already bound each to its set. ``sequences`` is ``{record: its letters}`` (``dna``, ``rna``, ``protein``, ...) of the
    sequences the episode holds, ``lengths`` ``{record: its length}`` of the same sequences, and ``made``
    ``{(searched_ref, code): 'completed' | 'failed'}`` of the runs the episode already holds or already saw fail. The
    conditions:

    1. the searched sequence is of DNA letters (the finder reads no other);
    2. the code is one the mode the sequence's length gives can use (``prodigal_mode``, ``MODE_CODES``);
    3. the same run (searched sequence, code) is not already held;
    4. the same run has not already failed."""
    searched, code = request['searched_ref'], request['code']
    problems = []
    if sequences[searched] not in SEARCHED_MOLECULES:
        problems.append({'field': 'searched_ref', 'code': 'prodigal_takes_dna_letters',
                         'searched_letters': sequences[searched],
                         'choose_from': [ref for ref, letters in sequences.items() if letters in SEARCHED_MOLECULES]})
    mode = prodigal_mode(lengths[searched])
    if code not in MODE_CODES[mode]:
        problems.append({'field': 'code', 'code': 'genetic_code_not_taken_in_the_mode_of_this_length', 'mode': mode,
                         'choose_from': MODE_CODES[mode]})
    if (searched, code) in made:
        problems.append({'field': 'code', 'code': {
            'completed': 'gene_finding_already_held',
            'failed': 'gene_finding_already_failed_and_cannot_be_retried'}[made[searched, code]]})
    return problems


def prodigal_gene_calls(ctx, *, searched_ref, code):
    """Find the genes of the searched sequence ``searched_ref`` under the genetic code ``code`` and keep the graded
    statements (see the module). ``ctx`` is the tool's ``UnitContext``."""
    store = ctx.store
    record = store.get(searched_ref)
    mapping = record.get('mapping')
    subject_ref = searched_ref if mapping is None else mapping['path'][0]['subject_ref']
    letters = store.get_artifact(record['sequence_ref']).decode('ascii')
    mode = prodigal_mode(len(letters))
    native = predict_genes(letters, code=code, mode=mode)
    grading = grade_prodigal(native, input_length=len(letters))
    sheet = prodigal_call_sheet(grading, code=code, mode=mode, searched_mapping=mapping)
    with store.transaction():
        native_ref = store.artifact(canonical(native), 'application/json')
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=native_ref, grading=grading)
        kept = {**sheet, 'searched_ref': searched_ref, 'subject_ref': subject_ref}
        call_grading = {'sheet': kept}
        call_sheet_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=native_ref,
                                             grading=call_grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': native_ref, 'text_ref': None,
            'request_ref': None, 'version': native['pyrodigal_version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref, call_sheet_ref], 'operand_refs': [subject_ref]}, origin='tool')
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[native_ref])
        call_product = record_grading_product(store, grading_ref=call_sheet_ref, grading=call_grading,
                                              provider=PROVIDER, source_ref=source['id'], used=[native_ref],
                                              derived_from=[grading_product['id']])
    refs = [source['id'], native_ref, grading_ref, call_sheet_ref, grading_product['id'], call_product['id'],
            *settle_feature_records(ctx, subject_ref=subject_ref, source_ref=source['id'])]
    ends = [gene['claims_start'] + gene['claims_end'] for gene in sheet['genes']]
    return {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs,
            'result': {'mode': mode, 'code': code, 'grading_ref': grading_ref, 'call_sheet_ref': call_sheet_ref,
                       'gene_count': len(ends), 'with_both_ends': ends.count(2), 'with_one_end': ends.count(1),
                       'with_no_end': ends.count(0)}, 'feedback': None}


__all__ = ['MIN_TRAINING_LETTERS', 'MODE_CODES', 'PROVIDER', 'check_prodigal_request', 'prodigal_gene_calls',
           'prodigal_mode']
