"""The return. Always returned: ``credit`` (``completion['credit']``: the productivity signal, which no field restates) and
``finding``: per target of the scope its leading candidates (at most 10, the leading one first, each with its score and its
subscoring sheets), the partner candidates (ligand: its chemical component id; nucleic_acid: dna or rna; at most 20), the number of
candidates of each kind (product, ligand, nucleic_acid, rna_family), the Rfam family candidates of an RNA target (at most 20, the leading
one first, by their Rfam identifiers), the partner-contacts analyses, the ligand-transplant tests, the RNA family scans and the RNA
structure-agreement tests (counts of their sheets), the counts of the hits of the graded searches (hits, named, not asked) and the
facts of the model of the target (origin, residues, mean pLDDT 0 to 100: the model's own confidence, not similarity), and the
number of handoffs still waiting for their closure. All of it numbers, counts, values of a fixed vocabulary, the
annotation names of the candidates (names from the looked-up list of a database) and record references: no paragraph.

Selectable: ``committed_record_refs`` (the graded records this episode holds: the records its credit reads, which a parent passes
back on a later visit), ``execution_handoff_refs``, ``execution_check_refs`` and ``execution_closure_refs`` (the handoff, status
and closure records its child returned) and ``data_product_refs`` (the held data-product rows). EVERY RETURNED RECORD LIST IS
CLOSED UNDER NAMING: each is ``internal_summary``'s ``returned_refs`` entry, built with ``job_records.returned_with_names``."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.candidate_measurements import (
    LEADING_PROTEINS, VOCABULARIES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.ligand_transplants_sheet import (
    OUTCOMES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.rna_family_scan_sheet import (
    OUTCOMES as RNA_SCAN_OUTCOMES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.site_correspondence_sheet import (
    SITE_SOURCES)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.foldseek_search import (
    MODEL_ORIGINS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.uniprot_hit_names import (
    IDENTIFIER_SOURCES as ENTRY_IDENTIFIER_SOURCES, PANTHER_SUBFAMILY)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.bvbrc_family_of_proteins import (
    SOURCE as FAMILY_SOURCE)

IDENTIFIER_SOURCES = (FAMILY_SOURCE, *ENTRY_IDENTIFIER_SOURCES.values(), PANTHER_SUBFAMILY)

WAITING_FORM = RecordForm({
    'slot': ChoiceField('text', 'The child episode the job runs under', ('structure_search', 'partner_cofolding')),
    'seconds_since_launch': Field('number', 'The seconds from the launch to the latest thing the child knew'),
    'expected_remaining_seconds': Field('number', 'The seconds still expected, as the child last knew them'),
})
SHEET_FORM = RecordForm({
    'sheet': Field('text', 'The subscoring sheet: the kind of test (the part of the test name before the @)'),
    'value': Field('number', 'The candidate\'s value on the sheet: the sum of its values in the tests of that kind'),
})
FUNCTION_IDENTIFIER_FORM = RecordForm({
    'source': ChoiceField('text', 'Where the identifier is from: the BV-BRC global protein family of a matched '
                                  'protein, or a cross reference of its UniProt entry (NCBIfam, PANTHER subfamily, HAMAP rule, '
                                  'OrthoDB group, eggNOG group, PIRSF)',
                          IDENTIFIER_SOURCES),
    'identifier': Field('text', 'The identifier exactly as its source gives it'),
    'hit_count': Field('integer', 'The matched proteins of the candidate whose entry carries it'),
})
LEADING_PROTEIN_FORM = RecordForm({
    'source': ChoiceField('text', 'The database the accession is from', ('uniprot',)),
    'accession': Field('text', 'The protein\'s accession'),
    'value': Field('number', 'Its highest value (B) in the searches that matched it'),
})
CANDIDATE_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the candidate: product (the function name of a hit), ligand (a ligand bound '
                                      'to a matched protein, or placed in the model), nucleic_acid (DNA or RNA bound to it) or rna_family (a structured RNA family '
                                      'of Rfam that the target matches)', VOCABULARIES),
    'name': Field('text', 'The candidate\'s name exactly as its source gives it: for a product its UniProt recommended name, for a '
                          'ligand its chemical component id, for a nucleic acid dna or rna, for an rna_family its Rfam identifier'),
    'score': Field('number', 'The candidate\'s annotation score: the sum of its sheet values, that is, of its mean value '
                             '(0 to 1) in each test it has undergone'),
    'sheets': Field('list', 'The candidate\'s subscoring sheets, one per kind of test it has undergone', items=SHEET_FORM),
    'hit_count': Field('integer', 'For a product: the matched proteins that carry this name and have a value (a protein matched '
                                  'by several searches counts once)', required=False),
    'function_identifiers': Field('list', 'For a product: the function-level identifiers of the proteins behind it, read from '
                                          'the UniProt entries of its matched proteins, the one most of them carry first. The '
                                          'candidates are returned as found: none is merged with another',
                                  items=FUNCTION_IDENTIFIER_FORM, required=False),
    'hits_without_identifier': Field('integer', 'For a product: its matched proteins that carry no identifier of any source '
                                                'and whose BV-BRC family lookup was made', required=False),
    'hits_not_looked_up': Field('integer', 'For a product: its matched proteins whose BV-BRC family lookup was not made or failed '
                                           '(their family is unknown, not absent)', required=False),
    'leading_proteins': Field('list', 'For a product: the matched proteins behind it, the highest value first, at most '
                                      + str(LEADING_PROTEINS), items=LEADING_PROTEIN_FORM, required=False),
})
SITE_TEST_FORM = RecordForm({
    'search_ref': Field('text', 'The graded structure search whose matched proteins the test carried onto the target (a record '
                                'reference)'),
    'site_source': ChoiceField('text', 'Where the functional residues came from: annotated (UniProt active-site, binding-site and '
                                       'site features) or catalytic (M-CSA catalytic residues)', SITE_SOURCES),
    'hits_asked': Field('integer', 'The matched proteins whose residues were asked'),
    'hits_with_sites': Field('integer', 'The matched proteins that have at least one residue to carry over'),
    'candidates_measured': Field('integer', 'The candidates with at least one matched protein with residues: those the test measured'),
    'candidates_without_site': Field('integer', 'The candidates none of whose matched proteins has residues: not measured, not '
                                                'zero'),
    'absent_outside_count': Field('integer', 'The residues absent in the target because the alignment did not reach them (a part '
                                             'of the matched protein the target was not aligned to)'),
    'absent_within_count': Field('integer', 'The residues absent in the target inside the aligned span (a gap: the target lacks '
                                            'the residue there)'),
})
PARTNER_TEST_FORM = RecordForm({
    'search_ref': Field('text', 'The graded pdb100 structure search whose matched proteins were analysed (a record reference)'),
    'entries_asked': Field('integer', 'The solved structure files downloaded and read'),
    'entries_skipped_no_partner': Field('integer', 'The solved structures not downloaded because their metadata shows no ligand '
                                                   'outside the additive list and no nucleic acid'),
    'entries_too_large': Field('integer', 'The solved structure files too large to be asked'),
    'entries_not_obtained': Field('integer', 'The solved structure files that could not be obtained'),
    'entries_not_asked': Field('integer', 'The solved structures the unit never reached (it stopped once the candidates settled)'),
    'hits_with_partners': Field('integer', 'The matched proteins bound to a ligand or nucleic acid that is no additive'),
    'candidates_measured': Field('integer', 'The product candidates the test measured'),
    'partner_candidates_measured': Field('integer', 'The partner candidates (ligand, nucleic_acid) the test measured'),
})
TRANSPLANT_TEST_FORM = RecordForm({
    'model_ref': Field('text', 'The held AlphaFold DB model whose AlphaFill transplants were read (a record reference)'),
    'outcome': ChoiceField('text', 'What AlphaFill answered: transplants (hits), no_transplants (the model exists, nothing was '
                                   'transplanted) or no_alphafill_entry (AlphaFill has no entry for the accession)', OUTCOMES),
    'hit_count': Field('integer', 'The solved homologs AlphaFill transplanted from'),
    'transplant_count': Field('integer', 'The transplants AlphaFill reports'),
    'additive_count': Field('integer', 'The transplants of a ligand on the additive list: no value, no candidate'),
    'distinct_compound_count': Field('integer', 'The distinct non-additive compounds transplanted'),
    'candidates_measured': Field('integer', 'The ligand candidates the test measured'),
    'model_version_differs': Field('boolean', 'Whether the AlphaFold DB model version AlphaFill used differs from the held '
                                              'model\'s', required=False),
})
RNA_SCAN_TEST_FORM = RecordForm({
    'scan_ref': Field('text', 'The source record of the RNA family scan (a record reference)'),
    'database': Field('text', 'The covariance database scanned: its name in the settings'),
    'outcome': ChoiceField('text', 'families (at least one hit) or no_family (no model reached its gathering threshold)',
                           RNA_SCAN_OUTCOMES),
    'hit_count': Field('integer', 'The hits of the scan'),
    'overlapped_hit_count': Field('integer', 'The hits a better hit of the same clan overlaps (kept: the competing families)'),
    'candidates_measured': Field('integer', 'The family candidates the test measured'),
})
RNA_AGREEMENT_TEST_FORM = RecordForm({
    'scan_ref': Field('text', 'The RNA family scan whose families were tested (a record reference)'),
    'family_count': Field('integer', 'The families aligned'),
    'candidates_measured': Field('integer', 'The families the test measured'),
    'families_without_pairs': Field('integer', 'The families whose consensus has no base pair: not measured, not zero'),
    'consensus_pairs': Field('integer', 'The consensus base pairs of the families, summed'),
    'pairs_canonical': Field('integer', 'The consensus pairs the target can form as AU, GC or GU, summed over the families'),
})
COFOLDING_TEST_FORM = RecordForm({
    'source_ref': Field('text', 'The source record of the co-folding (a record reference)'),
    'ligand_count': Field('integer', 'The ligands co-folded with the target'),
    'candidate_count': Field('integer', 'The ligand candidates the test measured'),
})
TARGET_FORM = RecordForm({
    'target_ref': Field('text', 'The target: a subject record of the scope'),
    'molecule': ChoiceField('text', 'The molecule of the target', ('protein', 'dna', 'rna', 'unspecified')),
    'search_count': Field('integer', 'The graded structure searches of the target'),
    'hit_count': Field('integer', 'The hits of those searches'),
    'named_count': Field('integer', 'The hits that carry a product name'),
    'not_asked_count': Field('integer', 'The hits never asked about (the naming stopped once the candidates settled): their '
                                        'function is unknown, not absent'),
    'candidate_count': Field('integer', 'The product candidates (possible annotations) found for the target'),
    'ligand_candidate_count': Field('integer', 'The ligand candidates found for the target: ligands bound to its matched proteins'),
    'nucleic_acid_candidate_count': Field('integer', 'The nucleic-acid candidates found for the target: dna or rna bound to its '
                                                      'matched proteins'),
    'cofolding_tests': Field('list', 'The Chai-1 co-foldings of the target (each: its source and the counts of its sheet)',
                             items=COFOLDING_TEST_FORM),
    'candidates': Field('list', 'The leading possible annotations found for the target (at most 10), each with its score, the '
                                'leading one first', items=CANDIDATE_FORM),
    'partner_candidates': Field('list', 'The partner candidates found for the target (ligand and nucleic_acid; at most 20), each with '
                                        'its score, the leading one first', items=CANDIDATE_FORM),
    'partner_tests': Field('list', 'The partner-contacts analyses of the target (each: its search and the counts of its sheet)',
                           items=PARTNER_TEST_FORM),
    'site_tests': Field('list', 'The site tests of the target (each: its search, its site source and the counts of its sheet)',
                        items=SITE_TEST_FORM),
    'transplant_tests': Field('list', 'The ligand-transplant tests of the target (each: its model, the outcome and the counts of its '
                                      'sheet)', items=TRANSPLANT_TEST_FORM),
    'rna_family_candidate_count': Field('integer', 'The Rfam family candidates found for the target (an RNA target)'),
    'rna_family_candidates': Field('list', 'The Rfam family candidates found for the target (at most 20), each with its score, the '
                                           'leading one first', items=CANDIDATE_FORM),
    'rna_scan_tests': Field('list', 'The RNA family scans of the target (each: its database, outcome and the counts of its sheet)',
                            items=RNA_SCAN_TEST_FORM),
    'rna_agreement_tests': Field('list', 'The RNA structure-agreement tests of the target (each: its scan and the counts of its '
                                         'sheet)', items=RNA_AGREEMENT_TEST_FORM),
    'model_origin': ChoiceField('text', 'Where the model of the target came from', MODEL_ORIGINS, required=False),
    'model_residues': Field('integer', 'The residues the model covers', required=False),
    'model_mean_plddt': Field('number', 'The mean pLDDT of the model, 0 to 100: its own confidence, not similarity',
                              required=False),
})
FINDING_FORM = RecordForm({
    'evidence_axis': ChoiceField('text', 'The evidence axis', ('A102',)),
    'targets': Field('list', 'One entry per target of the scope', items=TARGET_FORM),
    'waiting_searches': Field('list', 'The structure searches and co-folding jobs launched and not extracted: for each the slot, the seconds since '
                                      'its launch and the seconds still expected, as the child last knew them',
                              items=WAITING_FORM, required=False),
    'outstanding_handoff_count': Field('integer', 'The job handoffs it holds (those its child returned) whose closure it does '
                                                  'not hold'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The leading candidates of each target with their scores and the counts of the graded searches',
                     form=FINDING_FORM),
    'committed_record_refs': Field('record_refs', 'The graded records this episode holds: what its credit reads', required=False),
    'execution_handoff_refs': Field('record_refs', 'The original handoff records its child returned', required=False),
    'execution_check_refs': Field('record_refs', 'The status records its child returned, which a later visit passes back',
                                  required=False),
    'execution_closure_refs': Field('record_refs', 'The closure records its child returned for fetched results', required=False),
    'data_product_refs': Field('record_refs', 'The data-product rows it holds (labelled files: EDAM type and format, what made '
                                              'them, where else they lie), which a later visit passes back for reuse',
                               required=False),
})


def final_to_parent(summary, completion, selection):
    waiting = [{'slot': row['slot'], 'seconds_since_launch': row['finding']['seconds_since_launch'],
                'expected_remaining_seconds': row['finding']['expected_remaining_seconds']}
               for index, row in enumerate(summary['child_reports'])
               if row['finding'].get('parked')
               and not any(later['slot'] == row['slot'] and later['finding']['state'] == 'extracted'
                           for later in summary['child_reports'][index + 1:])]
    result = {'credit': completion['credit'],
              'finding': {'evidence_axis': 'A102', 'targets': summary['findings'],
                          'outstanding_handoff_count': summary['outstanding_handoff_count'],
                          **({'waiting_searches': waiting} if waiting else {})}}
    result.update({name: refs for name, refs in summary['returned_refs'].items() if name in selection})
    return result
