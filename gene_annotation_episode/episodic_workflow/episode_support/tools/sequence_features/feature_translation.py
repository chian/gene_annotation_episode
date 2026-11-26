"""The translation of one coding feature call into its protein, tied to the positions of the original sequence: the check
of the request, and the translation as one unit.

A feature call (a ``feature`` record: the sequence it is on, ``subject_ref``; its type, ``kind``; its positions,
``segments``, zero-based, the end not included, in the order of their positions; its ``strand``) of a coding sequence
(``feature_types.CODING``) says where a protein is coded. A head that finds what a protein is takes a protein. This tool
makes that protein and keeps, with it, the mapping that leads every residue back to the three letters of the original
sequence it was read from, so that whatever is found on the protein can be placed on the original sequence.

The caller fills out one request: ``feature_ref`` (a held feature call) and ``code`` (a genetic code). Two functions of
this module do the rest, deterministically:

``check_translation_request`` examines the request against what the caller holds, before anything runs. It returns the
things to fix (one entry per problem: the field, a code and, where there is one, what to choose from); an empty list means
the request can run. The caller rejects a request with problems, so no unit is made.

``translate_feature_call`` translates a request that passed the check, as one unit. It reads the feature call and the
letters of the sequence it is on through custody and joins the letters of its segments in the order of their positions.
The translation is ``sequence_ops.translate`` (Biopython's ``Seq.translate``) over the whole joined stretch, on the
feature's strand (on ``-`` it reads the reverse complement of the joined stretch: the segments from the highest position
down), in frame 0, with ``cds`` false: every codon is translated as it stands, so a feature call that lacks a start codon
or a stop codon, or has a stop codon inside, is translated and not refused (a feature call may be wrong; that is a fact
for the caller). What the translation gives:

* A STOP CODON AT THE END (the native result ends in ``*``) is not a residue of the protein: it is left out of the
  protein and of its mapping (``translation_mapping``, ``omitted_terminal_stop``).
* AN INNER STOP CODON is a ``*`` inside the protein, kept where it is (the native result's ``internal_stop_positions``)
  and counted in the result (``inner_stops``).
* AN AMBIGUOUS CODON (IUPAC letters other than ``ACGT``) is read by Biopython's ambiguous table: one amino acid when all
  the codons it can stand for give that one; ``B``, ``Z`` or ``J`` for the two amino acids those letters stand for;
  ``X`` for any other mix, including one that may be a stop (``TAN``); ``*`` when every codon it can stand for is a stop
  (``TAR``).
* THE FIRST CODON is translated as it stands: an alternative start codon (``GTG``, ``TTG``) gives its ordinary amino
  acid, not ``M`` (``cds`` true would make it ``M``, and would refuse a call with no stop, with an inner stop or with no
  start codon).

The translation is graded in the same unit by the translation grader
(``sequence_translation_grader.grade_translation``: every codon, its positions on the original sequence, and whether the
protein's letter agrees with the frozen genetic code). Grading is not a choice of anyone: it follows the translation.

What is kept, through custody in one transaction:

1. the native result of the translation as an artifact (JSON);
2. the grading, retained beside it (``retain_tool_grading``);
3. one ``source`` record of the provider ``sequence.translate`` (the provider the Store admits a translation's mapping
   from) over the native result, with the grading as its auxiliary artifact and the feature call as its operand;
4. one ``context`` record of the translation (``processing``, ``translation_model``, the genetic code), on that source:
   the Store requires a product's mapping source to be a context of the product;
5. the protein's letters as an artifact (text) and one ``product`` record of them: ``parent_refs`` the feature call,
   ``molecule`` ``protein``, ``derivation`` ``translation``, ``context_refs`` the context, ``footprint`` the stretches of
   the original sequence its residues were read from (``footprint_from_mapping``), ``mapping`` (below) and
   ``mapping_source_ref`` the source;
6. the grading labelled as a ``tool_grading_sheet`` data product (``record_grading_product``), as the neighbours label
   theirs. The protein itself is not labelled: the one protein kind of the data products is a FASTA set
   (``protein_sequences``), and the protein is kept as its bare letters.

THE MAPPING has the form ``sequence_mapping.map_interval`` reads (``units_per_symbol`` 3, ``symbol_length`` the number of
residues, ``path`` the stretches of the original sequence in the order of reading): the mapping of the feature's
sequence (``sequence_mapping`` of the Store: the original itself, or the original a derived sequence leads back to),
cut to the feature's segments in the order of their positions (``extract_path``), then made a translation mapping on the
interval and strand the translation reports (``translation_mapping``). On ``+`` residue ``i`` is read from the letters
``3i`` to ``3i + 3`` of the joined stretch; on ``-`` the path is turned (each stretch ``-``, the highest first), so residue
``i`` lies ``3i`` to ``3i + 3`` letters below the feature's highest position. A span of residues ``[a, b)`` maps by
``map_interval(mapping, a, b)`` to the letters of the original sequence it was read from, on the strand the feature reads.

Nothing is caught: an error raised after a passed check (letters the translation does not read, a feature of one stop
codon only, which has no residue) is the unit's failure as the runner records it. Writes only through ``ctx.store``."""
from gene_annotation_episode.sequence_ops import translate, translation_codes
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    canonical)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_types import CODING
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_operations.sequence_translation_grader import (
    grade_translation)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.sequence_mapping import (
    VERSION as MAPPING_VERSION, extract_path, translation_mapping)

PROVIDER = 'sequence.translate'
STRANDS = ('+', '-')
# The genetic codes the translation function knows (``sequence_ops.translate`` takes these and refuses any other).
CODES = [row['code'] for row in translation_codes()]


def check_translation_request(request, *, features, made):
    """The things to fix in a translation request, before anything runs; an empty list means it can run.

    ``request`` holds ``feature_ref`` and ``code``. ``features`` is ``{feature_ref: {'kind', 'strand', 'segments',
    'subject_ref'}}`` of the feature calls the caller holds, and ``made`` the ``(feature_ref, code)`` pairs already
    translated. The conditions:

    1. the feature call is one the caller holds;
    2. it is a coding sequence (``CODING``);
    3. its strand is ``+`` or ``-`` (a call with no strand, ``.``, has no reading direction);
    4. the number of its letters is a multiple of three (the whole call is read in codons);
    5. the code is one the translation knows (``CODES``);
    6. the same translation (feature call, code) is not already made."""
    feature_ref, code = request['feature_ref'], request['code']
    problems = []
    if feature_ref not in features:
        problems.append({'field': 'feature_ref', 'code': 'feature_call_not_held', 'choose_from': sorted(
            ref for ref, feature in features.items() if feature['kind'] == CODING)})
    else:
        feature = features[feature_ref]
        if feature['kind'] != CODING:
            problems.append({'field': 'feature_ref', 'code': 'translation_takes_a_coding_sequence',
                             'feature_kind': feature['kind'], 'choose_from': sorted(
                                 ref for ref, held in features.items() if held['kind'] == CODING)})
        if feature['strand'] not in STRANDS:
            problems.append({'field': 'feature_ref', 'code': 'translation_needs_the_strand_plus_or_minus',
                             'strand': feature['strand']})
        length = sum(segment['end'] - segment['start'] for segment in feature['segments'])
        if length % 3:
            problems.append({'field': 'feature_ref', 'code': 'coding_sequence_length_not_a_multiple_of_three',
                             'length': length})
    if code not in CODES:
        problems.append({'field': 'code', 'code': 'genetic_code_not_known_to_the_translation', 'choose_from': CODES})
    if (feature_ref, code) in made:
        problems.append({'field': 'code', 'code': 'translation_already_held'})
    return problems


def translate_feature_call(ctx, *, feature_ref, code):
    """Translate the coding feature call ``feature_ref`` under the genetic code ``code`` and keep the protein with the
    mapping of its residues to the original sequence (see the module). ``ctx`` is the tool's ``UnitContext``. Returns
    ``{'product_ref', 'length', 'inner_stops', 'refs'}``: the protein's product record, its number of residues, the number
    of stop codons inside it, and every record kept."""
    store = ctx.store
    feature = store.get(feature_ref)
    subject = store.get(feature['subject_ref'])
    letters = store.get_artifact(subject['sequence_ref']).decode('ascii')
    joined = ''.join(letters[segment['start']:segment['end']] for segment in feature['segments'])
    subject_mapping = store.sequence_mapping(feature['subject_ref'])
    scale = subject_mapping['units_per_symbol']
    # The joined stretch's own mapping: every letter of it on the original sequence, in the order of their positions.
    joined_mapping = {'version': MAPPING_VERSION, 'units_per_symbol': scale, 'symbol_length': len(joined),
                      'path': extract_path(subject_mapping['path'],
                                           [{'start': segment['start'] * scale, 'end': segment['end'] * scale}
                                            for segment in feature['segments']], strand='+')}
    native = translate(joined, code=code, strand=feature['strand'])
    request = {'code': code, 'strand': feature['strand'], 'frame': 0, 'start': 0, 'end': len(joined), 'cds': False}
    grading = grade_translation(native, input_sequence=joined, subject_ref=feature_ref, parent_mapping=joined_mapping,
                                request=request, genetic_code=native['genetic_code_snapshot'])
    terminal_stop = native['terminal_stop']
    protein = native['sequence'][:-1] if terminal_stop else native['sequence']
    start, end = native['translated_interval']
    mapping = translation_mapping(joined_mapping['path'], start=start, end=end, strand=native['strand'],
                                  protein_length=len(protein), omitted_terminal_stop=terminal_stop)
    with store.transaction():
        native_ref = store.artifact(canonical(native), 'application/json')
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=native_ref, grading=grading)
        source = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': native_ref, 'text_ref': None,
            'request_ref': None, 'version': native['biopython_version'], 'retrieved_at': None,
            'auxiliary_artifact_refs': [grading_ref], 'operand_refs': [feature_ref]}, origin='tool')
        context = store.put('context', {
            'context_type': 'processing', 'name': 'translation_model', 'source_ref': source['id'],
            'attributes': [{'name': 'genetic_code', 'value': {'type': 'number', 'value': code, 'unit_ref': None}}],
            'related_refs': [feature_ref]}, origin='tool')
        sequence_ref = store.artifact(protein, 'text/plain')
        product = store.put('product', {
            'parent_refs': [feature_ref], 'molecule': 'protein', 'sequence_ref': sequence_ref,
            'derivation': 'translation', 'context_refs': [context['id']],
            'footprint': store.footprint_from_mapping(mapping), 'mapping': mapping,
            'mapping_source_ref': source['id']}, origin='tool')
        grading_product = record_grading_product(store, grading_ref=grading_ref, grading=grading, provider=PROVIDER,
                                                 source_ref=source['id'], used=[native_ref])
    return {'product_ref': product['id'], 'length': len(protein), 'inner_stops': len(native['internal_stop_positions']),
            'refs': [product['id'], sequence_ref, source['id'], context['id'], native_ref, grading_ref,
                     grading_product['id']]}


__all__ = ['CODES', 'PROVIDER', 'STRANDS', 'check_translation_request', 'translate_feature_call']
