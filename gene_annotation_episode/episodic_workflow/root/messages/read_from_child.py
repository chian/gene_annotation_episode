"""What the root takes from an axis head's return: controlled data only.

- ``credit``: the credit the head returned (never bounded, clamped or rescaled). What it measures is the head's own
  (``CREDIT_RETURNED``): the axis credit as it stands over every record the head holds, or the rise since the sheet
  the head was given. ``messages/internal_summary.py`` makes the axis credit from it.
- ``sheet_state_refs``: the subscoring-sheet states the head returned (``SHEET_FIELDS``), which go back to it as the
  sheet it is given at its next commission.
- ``finding``: the numbers and flags of the head's finding, under the head's own field names. Text, lists and
  nested records of a finding stay with the head that wrote them and are not read, except the annotation rows below:
  nothing a model wrote reaches the root's summary or the root's model.
- ``annotation_rows``: the score channel of a head that scores annotations it finds (``ANNOTATION_ROWS``). One row per
  candidate annotation: which annotation (``vocabulary``, and the ``name`` and ``identifier`` its source gives it), the
  ``status`` of the evidence (``ROW_STATUS``) and its ``score``: the one number that head's scoring sheet gives the
  annotation, on that head's own scale, never bounded, clamped or rescaled here. With them, where the head returns
  them, the function-level identifiers of the proteins behind the candidate, and the organisms of the database hits
  behind it (``hit_organisms``: NCBI taxon ids with hit counts; ``hits_without_taxon``) and the feature types of
  those hits (``hit_feature_kinds``: types of the head's fixed list with hit counts;
  ``hits_with_unmapped_feature_type``; ``hits_without_feature_type``), which enter no score.
- ``grouped_rows`` and ``grouping_in_force``: for a head that applies the root's grouping of its candidates
  (``GROUPED_ROWS``), its candidates rescored under the grouping it was last given, and that grouping.
- ``claim_rows``: the score channel of a head that checks claims (``CLAIM_ROWS``). One row per claim its sheet scored:
  the claim (the hypothesis record the root made from an annotation and commissioned the head on), the ``status`` and
  the ``support`` and ``opposition`` of the head's sheet (absent when the status is unknown, never written as 0).
  ``messages/internal_summary.py`` puts each claim's row on the line of the annotation the claim was made from.
  The score never reads a credit, and the credit never reads a score.
- ``record_refs``: the records the head returned in the fields the root selected (``RECORD_FIELDS``), which the
  root now holds and passes back to that head at its next commission.
- ``outstanding_job_refs``: the job records the head returned (``JOB_FIELDS``).
- ``outstanding_jobs``: how many jobs the head left running when it ended its turn, by the head's own count
  (``OUTSTANDING_JOBS``). A head that left none ran fully: its own yield estimator ended it because nothing more was
  worth doing with what it held.

Each head's fields are named here against its own ``messages/final_to_parent.py``, read as data."""

# The record-reference fields of each head's return the root reads.
RECORD_FIELDS = {
    'sequence_homology_evidence': ('committed_record_refs', 'execution_handoff_refs'),
    'structural_homology_evidence': ('committed_record_refs',),
    'gene_context_evidence': ('committed_record_refs',),
    'evolutionary_history_evidence': ('committed_record_refs',),
    'experimental_activity_evidence': ('committed_record_refs',),
    'perturbation_evidence': ('committed_record_refs',),
    'partner_presence_evidence': ('committed_record_refs',),
    'sample_context_evidence': ('committed_record_refs',),
    'biochemical_feasibility_evidence': ('committed_record_refs',),
}
# What the credit of each head's return measures, read from its own ``credit.py``. ``standing``: the credit over every
# record the head holds, so with its earlier records passed back it continues from where it stood (A101: the differential
# credit of the held graded sources). ``rise``: the rise since the sheet the head was given, so each return adds to the
# axis credit (A105: the strongest evidence on its latest sheet minus that on the sheet it was given). The heads that
# are not linked yet (``task.CHILD_SLOTS``) stand as the root first assumed them and are to be read when they are linked.
CREDIT_RETURNED = {
    'sequence_homology_evidence': 'standing',
    'structural_homology_evidence': 'standing',
    'gene_context_evidence': 'standing',
    'evolutionary_history_evidence': 'standing',
    'experimental_activity_evidence': 'rise',
    'perturbation_evidence': 'standing',
    'partner_presence_evidence': 'standing',
    'sample_context_evidence': 'standing',
    'biochemical_feasibility_evidence': 'standing',
}
# The fields of a head's return that hold its subscoring-sheet states, for the heads that take them back as a field of
# their own (``sheet_state_refs`` of the A105 assignment).
SHEET_FIELDS = {
    'sequence_homology_evidence': (),
    'structural_homology_evidence': (),
    'gene_context_evidence': (),
    'evolutionary_history_evidence': (),
    'experimental_activity_evidence': ('sheet_state_refs',),
    'perturbation_evidence': (),
    'partner_presence_evidence': (),
    'sample_context_evidence': (),
    'biochemical_feasibility_evidence': (),
}
# Of the record fields, the ones that name the records of jobs a head left outstanding.
JOB_FIELDS = {
    'sequence_homology_evidence': ('execution_handoff_refs',),
    'structural_homology_evidence': (),
    'gene_context_evidence': (),
    'evolutionary_history_evidence': (),
    'experimental_activity_evidence': (),
    'perturbation_evidence': (),
    'partner_presence_evidence': (),
    'sample_context_evidence': (),
    'biochemical_feasibility_evidence': (),
}


# The status of the evidence of a row, as the heads' scoring sheets name it.
ROW_STATUS = ('measured', 'measured_zero', 'unknown')
# The vocabularies of a candidate annotation, as the sequence-homology head names its candidates: a database search's
# function, a family of a profile database, a sequence record it was compared with.
VOCABULARIES = ('product', 'profile_family', 'reference_sequence')
# The sources of function-level identifiers a head may return with a candidate (read from the proteins behind it): the
# global protein family of a BV-BRC feature (the sequence-homology head), and the identifiers of a UniProt entry (the
# structural-homology head, when it is linked).
FUNCTION_SOURCES = ('bvbrc_global_family', 'hamap', 'ncbifam', 'panther_subfamily', 'orthodb', 'eggnog', 'pirsf')
# The sources that decide whether two annotations are one function. The orthologous-group sources (OrthoDB, eggNOG,
# PIRSF) are recorded and decide nothing until they have been measured: on the one case checked (the cold shock
# proteins CspA and CspC, 2026-11-23) they join what the BV-BRC family and NCBIfam keep apart.
DECIDING_SOURCES = ('bvbrc_global_family', 'hamap', 'ncbifam', 'panther_subfamily')


def sequence_homology_rows(result):
    """A101. The finding holds one entry per target of the scope, and the root annotates one subject: one target. Each
    of its candidates (the possible annotations found, each with its annotation score: the sum of its values on the
    head's subscoring sheets, never negative) is a row with that score. This head's sheets hold no evidence against a
    candidate, so its rows have no support and opposition apart from the score. A candidate a database search named
    carries the function-level identifiers of the proteins behind it (``function_identifiers``: source, identifier and
    the number of its hits that carry it; ``identifier_sources``: per source, the number of its hits that carry any
    identifier of it) and ``hits_without_identifier``; the root decides with them which names are
    one function (``internal_summary.same_function``). Such a candidate also carries the organisms of the database hits
    behind it, from the field the root selects (``candidate_hit_organisms``, one entry per target as the finding):
    ``hit_organisms`` (one entry per NCBI taxon id with the number of its hits of that taxon, the taxon of most hits
    first) and ``hits_without_taxon``; and, from the field ``candidate_hit_feature_kinds`` (arranged the same), the
    feature types of those hits: ``hit_feature_kinds`` (one entry per type of the head's fixed list with the number of
    its hits of that type), ``hits_with_unmapped_feature_type`` (its hits whose database feature type is matched to no
    type yet) and ``hits_without_feature_type``. They are kept on the row and enter no score."""
    (target,) = result['finding']['targets']
    (organisms,) = result['candidate_hit_organisms']
    (feature_kinds,) = result['candidate_hit_feature_kinds']
    behind = {(row['vocabulary'], row['name']): {'hit_organisms': row['organisms'],
                                                 'hits_without_taxon': row['hits_without_taxon']}
              for row in organisms['candidates']}
    kinds = {(row['vocabulary'], row['name']): {
        'hit_feature_kinds': row['feature_kinds'],
        'hits_with_unmapped_feature_type': row['hits_with_unmapped_feature_type'],
        'hits_without_feature_type': row['hits_without_feature_type']} for row in feature_kinds['candidates']}
    return [{'vocabulary': candidate['vocabulary'], 'name': candidate['name'],
             **{name: candidate[name] for name in ('identifier', 'function_identifiers', 'identifier_sources',
                                                    'hits_without_identifier') if name in candidate},
             **behind.get((candidate['vocabulary'], candidate['name']), {}),
             **kinds.get((candidate['vocabulary'], candidate['name']), {}),
             'status': 'measured' if candidate['score'] else 'measured_zero', 'score': candidate['score']}
            for candidate in target['candidates']]


def no_groups(finding):
    return {'grouped_rows': [], 'grouping_in_force': []}


def sequence_homology_groups(finding):
    """A101. With a grouping in force its one target carries ``grouped_candidates`` (every candidate rescored under
    it: members and score) and ``grouping_in_force``; without one, neither."""
    (target,) = finding['targets']
    return {'grouped_rows': [{'members': group['members'], 'score': group['score']}
                             for group in target.get('grouped_candidates', ())],
            'grouping_in_force': target.get('grouping_in_force', [])}


# How the candidates of a head that applies the root's grouping are read once a grouping is in force (the design
# ``docs/plan/designs/a102_regrouping.md``, agreed between the sessions on 2026-11-23): ``grouped_rows``, one per group
# of the head's table under that grouping (``members``, each named exactly as the head returned it, and the group's
# ``score``, rescored by the head from its own records), and ``grouping_in_force``, the grouping it applied. A head is
# listed with its own reader when it takes a grouping (``task.TAKES_GROUPING``); until then it has none in force.
GROUPED_ROWS = {
    'sequence_homology_evidence': sequence_homology_groups,
    'experimental_activity_evidence': no_groups,
}


def experimental_activity_rows(finding):
    """A105. The finding holds one score per candidate of the head's main scoring sheet: the hypothesis record it is
    about (``assertion_ref``: the claim the head was commissioned on), the status, and the summed support and opposition
    (omitted by the head when the status is unknown)."""
    return [{'claim_ref': score['assertion_ref'], 'status': score['status'],
             **{name: score[name] for name in ('support', 'opposition') if name in score}}
            for score in finding['scores']]


def no_rows(finding):
    return []


def no_annotation_rows(result):
    return []


# How the rows of each linked head's return are read, written against that head's own ``messages/final_to_parent.py``.
# A head is listed here when it is linked (``task.CHILD_SLOTS``): a head that scores the annotations it finds gives
# annotation rows (read from its return: its finding and the fields the root selected), a head that checks claims
# gives claim rows (read from its finding).
ANNOTATION_ROWS = {
    'sequence_homology_evidence': sequence_homology_rows,
    'experimental_activity_evidence': no_annotation_rows,
}
CLAIM_ROWS = {
    'sequence_homology_evidence': no_rows,
    'experimental_activity_evidence': experimental_activity_rows,
}


def sequence_homology_outstanding(finding):
    """A101. The job handoffs it holds whose closure it does not hold, as its finding counts them."""
    return finding['outstanding_handoff_count']


def none_outstanding(finding):
    return 0


# How many jobs each linked head left running at its return, read from its own finding.
OUTSTANDING_JOBS = {
    'sequence_homology_evidence': sequence_homology_outstanding,
    'experimental_activity_evidence': none_outstanding,
}


def references(result, fields):
    """The references of the named fields of a return, in order, each once."""
    return list(dict.fromkeys(ref for field in fields for ref in result[field]))


ORGANISM_FINDER = 'organism_identification'


def organism_report(result):
    """The return of the organism identification head, which is not an evidence axis: the candidate taxa of the one DNA
    sequence it was commissioned on (taxon id, the taxonomy's name, rank code, the ids of its lineage, score; the leading
    one first), the leading candidate, its leading rival and the deepest taxon the two share, and the records it
    committed. It leaves no job running."""
    (target,) = result['finding']['targets']
    return {'credit': result['credit'],
            'organism_rows': [{'taxon_id': row['taxon_id'], 'name': row['name'], 'rank_code': row['rank_code'],
                               'lineage_taxon_ids': [item['taxon_id'] for item in row['lineage']], 'score': row['score']}
                              for row in target['candidates']],
            'placement': {name: target[name] for name in ('leader_taxon_id', 'rival_taxon_id', 'agreed_taxon_id')
                          if name in target},
            'test_count': target['test_count'], 'record_refs': list(result['record_refs']), 'outstanding_jobs': 0}


def read_from_child(slot, result, summary, records):
    if slot == ORGANISM_FINDER:
        return organism_report(result)
    return {'credit': result['credit'],
            'finding': {name: value for name, value in result['finding'].items()
                        if type(value) in (bool, int, float)},
            'annotation_rows': ANNOTATION_ROWS[slot](result),
            'claim_rows': CLAIM_ROWS[slot](result['finding']),
            **GROUPED_ROWS[slot](result['finding']),
            'record_refs': references(result, (*RECORD_FIELDS[slot], *SHEET_FIELDS[slot])),
            'sheet_state_refs': references(result, SHEET_FIELDS[slot]),
            'outstanding_job_refs': references(result, JOB_FIELDS[slot]),
            'outstanding_jobs': OUTSTANDING_JOBS[slot](result['finding'])}
