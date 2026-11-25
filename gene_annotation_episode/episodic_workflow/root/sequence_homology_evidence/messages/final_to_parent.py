"""The return. Always returned: ``credit`` (``completion['credit']``: the productivity signal, which no field restates)
and ``finding``: the controlled features code read from the A101 axis sheet of each target of the scope
(``INVESTIGATION_FINDING_FEATURES_a101.md`` sections 2.3 and 10) and the number of handoffs still waiting for their
results. No held-record lists, no per-child rows and no prose: the root decides which axis to commission next and
whether to come back for an outstanding job, and that is what it needs.

Selectable: ``committed_record_refs`` (the records this episode committed through its reasoning units and the graded
records of its comparisons: the records its credit reads, which a parent passes back on a later visit) and
``execution_handoff_refs`` (the handoff records its launches returned), ``execution_check_refs`` and
``execution_closure_refs`` (the status and closure records its children returned) and ``data_product_refs`` (the held
data-product rows). EVERY RETURNED RECORD LIST IS CLOSED UNDER NAMING: each is ``internal_summary``'s ``returned_refs`` entry, built with
``job_records.returned_with_names`` (the records chosen with everything they name among the records held), so the parent holds
whatever a returned record names.

Also selectable: ``candidate_hit_organisms`` (controlled data, no records): for each target of the scope, in the order
of ``finding.targets``, the organisms of the database hits behind each candidate a database search named: per candidate
its vocabulary and name, one entry per NCBI taxon id with the number of its hits of that taxon, and the number of its
hits whose feature carries no taxon id (``candidate_measurements._hit_organisms``). Ids and counts only.

And ``candidate_hit_feature_kinds`` (controlled data, no records), in the same arrangement: per candidate a database
search named, the number of its hits per feature type (a type of the one list ``feature_types.KINDS``, matched from the
database's own feature type of each hit by ``database_feature_types``), the number of its hits whose database value has
no type of ours yet, and the number of its hits whose feature carries no feature type
(``candidate_measurements._hit_feature_kinds``). The database's own values are not returned: they stay in this
episode's records."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_types import KINDS
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.axis_features import (
    FEATURES, MEANINGS)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    FAMILY_SOURCE, VOCABULARIES)

FIELD_TYPES = {'number': 'number', 'count': 'integer', 'boolean': 'boolean'}


def feature_field(name, rule):
    if rule[0] == 'choice':
        return ChoiceField('text', MEANINGS[name], rule[1])
    return Field(FIELD_TYPES[rule[0]], MEANINGS[name], required=rule[-1] != 'optional')


WAITING_FORM = RecordForm({
    'slot': ChoiceField('text', 'The child episode the job runs under', ('bvbrc_blast', 'bvbrc_msa', 'bvbrc_metacats')),
    'seconds_since_launch': Field('number', 'The seconds from the launch to the latest thing the child knew'),
    'expected_remaining_seconds': Field('number', 'The seconds still expected, as the child last knew them'),
})
CANDIDATE_REFERENCE_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the candidate: product (a database search\'s function), '
                                      'profile_family (a family of a profile database) or reference_sequence (a '
                                      'sequence record it was compared with)', VOCABULARIES),
    'name': Field('text', 'The candidate\'s name exactly as its source gives it'),
    'identifier': Field('text', 'The candidate\'s identifier exactly as its source gives it (a family accession or '
                                'a record reference; a product has none)', required=False),
})
SHEET_FORM = RecordForm({
    'sheet': Field('text', 'The subscoring sheet: the kind of test (the part of the test name before the @)'),
    'value': Field('number', 'The candidate\'s value on the sheet: the sum of its values in the tests of that kind'),
})
FUNCTION_IDENTIFIER_FORM = RecordForm({
    'source': ChoiceField('text', 'Where the identifier is from: the global protein family of the hit\'s BV-BRC feature',
                          (FAMILY_SOURCE,)),
    'identifier': Field('text', 'The identifier exactly as its source gives it'),
    'hit_count': Field('integer', 'The hits of the candidate that carry it'),
})
IDENTIFIER_SOURCE_FORM = RecordForm({
    'source': ChoiceField('text', 'A source of function-level identifiers', (FAMILY_SOURCE,)),
    'protein_count': Field('integer', 'The hits of the candidate that carry any identifier of that source'),
})
UNCHARACTERIZED_FAMILY_FORM = RecordForm({
    'source': ChoiceField('text', 'Where the identifier is from', (FAMILY_SOURCE,), required=False),
    'identifier': Field('text', 'The family identifier of the hits (absent: their features carry none)', required=False),
    'hit_count': Field('integer', 'The uncharacterized hits of that family'),
    'best_value': Field('number', 'The highest value among them, 0 to 1'),
})
CANDIDATE_FORM = RecordForm({
    **CANDIDATE_REFERENCE_FORM.fields,
    'function_identifiers': Field('list', 'For a candidate a database search named: the function-level identifiers of '
                                          'the proteins behind it, read from its hits, the one most hits carry first',
                                  items=FUNCTION_IDENTIFIER_FORM, required=False),
    'identifier_sources': Field('list', 'Per source of those identifiers, the hits that carry any identifier of it',
                                items=IDENTIFIER_SOURCE_FORM, required=False),
    'hits_without_identifier': Field('integer', 'Its hits whose feature carries no such identifier', required=False),
    'score': Field('number', 'The candidate\'s annotation score: the sum of its sheet values, that is, of its mean '
                             'value (0 to 1) in each test it has undergone'),
    'sheets': Field('list', 'The candidate\'s subscoring sheets, one per kind of test it has undergone', items=SHEET_FORM),
    'tests': Field('list', 'The tests the candidate has undergone, each as the controlled test name'),
    'measurement_count': Field('integer', 'The measurements of the candidate over all its tests'),
    'best_value': Field('number', 'The highest single value of the candidate, 0 to 1'),
})
DIFFERENTIAL_FORM = RecordForm({
    'test': Field('text', 'The test the top two listed candidates both underwent'),
    'first': Field('record', 'The first candidate', form=CANDIDATE_REFERENCE_FORM),
    'second': Field('record', 'The second candidate', form=CANDIDATE_REFERENCE_FORM),
    'value': Field('number', 'The credit the test earned by differentiating the top two: the difference of the moves of their '
                             'scores over the test times the weaker evidence of the two (1 except in a cluster test, where '
                             'a candidate with n sequences in the set has evidence n/(n+4))'),
})
MEMBER_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the candidate', VOCABULARIES),
    'name': Field('text', 'Its name exactly as it was found'),
    'identifier': Field('text', 'Its own identifier, when it has one', required=False),
})
GROUP_FORM = RecordForm({
    'members': Field('list', 'The candidates of the group', items=MEMBER_FORM),
})
GROUPED_CANDIDATE_FORM = RecordForm({
    'members': Field('list', 'The candidates read as this one (a candidate in no group: itself)', items=MEMBER_FORM),
    'score': Field('number', 'Its annotation score under the grouping in force: the measurements of all its members '
                             'read as one candidate\'s'),
    'sheets': Field('list', 'Its subscoring sheets under the grouping in force', items=SHEET_FORM),
})
TARGET_FORM = RecordForm({
    **{name: feature_field(name, rule) for name, rule in FEATURES.items()},
    'candidates': Field('list', 'The possible annotations found for the target, each with its score, the leading one '
                                'first', items=CANDIDATE_FORM),
    'candidate_count': Field('integer', 'The number of possible annotations found'),
    'not_asked_hit_count': Field('integer', 'The hits of database searches whose function was not asked: the naming of the '
                                            'hits stopped once the candidates settled, so their function is unknown, not absent'),
    'no_product_hit_count': Field('integer', 'The hits of database searches whose function was asked and that carry no '
                                             'product: they name no candidate'),
    'uncharacterized_hit_count': Field('integer', 'The hits of database searches whose every function is a label of '
                                                  'ignorance (hypothetical protein, uncharacterized protein): they '
                                                  'name no candidate'),
    'uncharacterized_best_value': Field('number', 'The highest value among those hits, on the scale of a candidate\'s '
                                                  'best_value: how close the target is to a protein nobody has '
                                                  'characterized (absent when there is no such hit)', required=False),
    'uncharacterized_families': Field('list', 'Those hits by family, the family with the highest value first',
                                      items=UNCHARACTERIZED_FAMILY_FORM),
    'differentials': Field('list', 'The tests that differentiated the top two listed candidates they measured (one per test)', items=DIFFERENTIAL_FORM),
    'grouped_candidates': Field('list', 'With a grouping of the candidates in force (the commissioner\'s): every '
                                        'candidate rescored under it, the leading one first',
                                items=GROUPED_CANDIDATE_FORM, required=False),
    'grouping_in_force': Field('list', 'The grouping in force, as the commission gave it', items=GROUP_FORM,
                               required=False),
})
HIT_ORGANISM_FORM = RecordForm({
    'taxon_id': Field('integer', 'The taxon the hits are from (NCBI taxonomy id), as the database gives it for each '
                                 'hit\'s feature'),
    'hit_count': Field('integer', 'The hits of the candidate that are from that taxon'),
})
CANDIDATE_HIT_ORGANISMS_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the candidate: product (a database search\'s function)',
                              ('product',)),
    'name': Field('text', 'The candidate\'s name exactly as its source gives it'),
    'organisms': Field('list', 'The taxa the candidate\'s hits are from, the taxon of most hits first',
                       items=HIT_ORGANISM_FORM),
    'hits_without_taxon': Field('integer', 'Its hits whose feature carries no taxon id'),
})
TARGET_HIT_ORGANISMS_FORM = RecordForm({
    'candidates': Field('list', 'One row per candidate of the target that a database search named, in the order of the '
                                'target\'s candidates', items=CANDIDATE_HIT_ORGANISMS_FORM),
})
HIT_FEATURE_KIND_FORM = RecordForm({
    'kind': ChoiceField('text', 'The type of feature the hits are, in this code base\'s list of feature types, matched '
                                'from the database\'s own feature type of each hit', KINDS),
    'hit_count': Field('integer', 'The hits of the candidate that are features of that type'),
})
CANDIDATE_HIT_FEATURE_KINDS_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the candidate: product (a database search\'s function)',
                              ('product',)),
    'name': Field('text', 'The candidate\'s name exactly as its source gives it'),
    'feature_kinds': Field('list', 'The types of feature the candidate\'s hits are, the type of most hits first',
                           items=HIT_FEATURE_KIND_FORM),
    'hits_with_unmapped_feature_type': Field('integer', 'Its hits whose feature type in the database is matched to '
                                                        'no type of this code base yet'),
    'hits_without_feature_type': Field('integer', 'Its hits whose feature carries no feature type'),
})
TARGET_HIT_FEATURE_KINDS_FORM = RecordForm({
    'candidates': Field('list', 'One row per candidate of the target that a database search named, in the order of the '
                                'target\'s candidates', items=CANDIDATE_HIT_FEATURE_KINDS_FORM),
})
FINDING_FORM = RecordForm({
    'evidence_axis': ChoiceField('text', 'The evidence axis', ('A101',)),
    'targets': Field('list', 'One entry per target of the scope: the features of its axis sheet', items=TARGET_FORM),
    'waiting_searches': Field('list', 'The BV-BRC jobs (searches, alignments) launched and not extracted: for each the slot, the seconds since '
                                      'its launch and the seconds still expected, as the child last knew them',
                              items=WAITING_FORM, required=False),
    'outstanding_handoff_count': Field('integer', 'The job handoffs it holds (its own and those its children returned) '
                                                  'whose closure it does not hold'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled features of the A101 axis sheet of each target', form=FINDING_FORM),
    'committed_record_refs': Field('record_refs', 'The records this episode committed or graded: what its credit '
                                                  'reads', required=False),
    'execution_handoff_refs': Field('record_refs', 'The original handoff records its launches returned',
                                    required=False),
    'execution_check_refs': Field('record_refs', 'The status records its children returned for their searches, which a '
                                                'later visit passes back', required=False),
    'execution_closure_refs': Field('record_refs', 'The closure records its children returned for fetched reports',
                                    required=False),
    'data_product_refs': Field('record_refs', 'The data-product rows it holds (labelled files: EDAM type and format, what '
                                              'made them, where else they lie), which a later visit passes back for reuse',
                               required=False),
    'candidate_hit_organisms': Field('list', 'For each target of the scope, in the order of the finding\'s targets: the '
                                             'organisms of the database hits behind each candidate a database search '
                                             'named (taxon ids and hit counts)',
                                     items=TARGET_HIT_ORGANISMS_FORM, required=False),
    'candidate_hit_feature_kinds': Field('list', 'For each target of the scope, in the order of the finding\'s targets: '
                                                 'the feature types of the database hits behind each candidate a '
                                                 'database search named (types of the fixed list and hit counts)',
                                         items=TARGET_HIT_FEATURE_KINDS_FORM, required=False),
})


def final_to_parent(summary, completion, selection):
    waiting = [{'slot': row['slot'], 'seconds_since_launch': row['finding']['seconds_since_launch'],
                'expected_remaining_seconds': row['finding']['expected_remaining_seconds']}
               for index, row in enumerate(summary['child_reports'])
               if row['slot'] in ('bvbrc_blast', 'bvbrc_msa', 'bvbrc_metacats') and row['finding'].get('parked')
               and not any(later['slot'] == row['slot'] and later['finding']['state'] == 'extracted'
                           for later in summary['child_reports'][index + 1:])]
    result = {'credit': completion['credit'],
              'finding': {'evidence_axis': 'A101', 'targets': summary['axis_findings'],
                          'outstanding_handoff_count': summary['outstanding_handoff_count'],
                          **({'waiting_searches': waiting} if waiting else {})}}
    result.update({name: refs for name, refs in summary['returned_refs'].items() if name in selection})
    if 'candidate_hit_organisms' in selection:
        result['candidate_hit_organisms'] = summary['candidate_hit_organisms']
    if 'candidate_hit_feature_kinds' in selection:
        result['candidate_hit_feature_kinds'] = summary['candidate_hit_feature_kinds']
    return result
