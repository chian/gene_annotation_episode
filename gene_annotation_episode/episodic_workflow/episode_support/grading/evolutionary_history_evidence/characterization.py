"""Consume exact experimental reference links from received A105 assay-grading sheets.

This is a receiving adapter, not a new experimental-evidence subtree. Copied
names, an assessment alone, and an unreceived literature return cannot supply
an experimentally characterized clade member.

Restored from ``root/a104/a104_characterization.py`` at ``60889621e``. The owner's qualification rules are kept
verbatim (rows 11 to 14 of ``LOST_CONTENT_a104.md``). What changed is where a link is read from: the old adapter read
the A105 worksheet that a literature child's return form carried (``EpisodeReturnRecords.received_attempts``, an
old-runner reader). A child now returns no form text, only its credit, controlled features and the references of
its saved sheets, which this episode then holds. So a link is read from each held A105 assay-grading sheet itself:
the sheet's own ``assertion_ref`` is the asserted endpoint its populated ``measured_effect`` cell measures (the old
``measures_asserted_endpoint`` link selected exactly that cell), read through ``A104AssayGradingReader``. ``reader``
is ``ctx.store`` or ``records``."""
from __future__ import annotations

from collections import defaultdict

from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.grading.assay_grading_read import A104AssayGradingReader
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence.hpc import sequence, sha

ASSAY_PROVIDER = 'literature.a105.assay_grading'
LINK_COMPONENT = 'measured_effect'


def held_assay_sheets(reader, known):
    """The A105 assay-grading sheets among the held records, each read and authenticated once."""
    repository = A104AssayGradingReader(reader)
    sheets = {}
    for reference in sorted(known):
        record = reader.get(reference)
        if record['record_type'] == 'source' and record.get('provider') == ASSAY_PROVIDER and record['origin'] == 'tool':
            saved = repository.read(reference)
            sheets[reference] = repository.rows(saved, reference, list(saved['sheet']['cells']))
    return sheets


def native_assay_qualification(sheets, assertion, source, known):
    """Read the particular delivered A105 judgments, never an axis scalar."""
    rows = [row for cells in sheets.values() for row in cells]
    common = {'measurement_identity', 'attribution_supported', 'assertion_relevance',
              'condition_scope', 'background_alternatives'}
    kinds = {'catalyzes': {'activity_rate', 'endpoint_conversion', 'product_distribution', 'reaction_coupling'},
             'transports': {'transport_response'}, 'binds': {'ligand_binding'}}
    candidates = [row for row in rows if row.get('assertion_ref') == assertion['id']
                  and row.get('evidence_source_ref') == source and row.get('assay_type') in kinds[assertion['predicate']]]
    groups = defaultdict(list)
    for row in candidates:
        groups[row['sheet_ref']].append(row)
    result = []
    for sheet, parts in groups.items():
        if sheet not in known:
            continue
        interpretations = {key: value for row in parts for key, value in row.get('interpretations', {}).items()}
        required = set(common)
        assay_type = parts[0]['assay_type']
        required.update({'transport_response': {'membrane_system', 'transport_endpoint',
            'transport_driving_force', 'transport_specificity'},
            'ligand_binding': {'binding_species', 'binding_controls', 'binding_regime'},
            'endpoint_conversion': {'product_identity'}, 'product_distribution': {'species_identity'},
            'reaction_coupling': {'product_identity', 'stoichiometry', 'reporter_specificity'}}.get(assay_type, ()))
        # A member counts as characterized only when every common criterion and every criterion of its assay type
        # is supported, read cell by cell.
        if not all(interpretations.get(name, {}).get('status') == 'supported' for name in required):
            continue
        supports = {reference for name in required for reference in interpretations[name]['support_refs']}
        if not supports <= set(known):
            continue
        result.append({'grading_sheet_ref': sheet, 'assay_type': assay_type,
            'quantity_kind': parts[0]['quantity_kind'], 'required_supported_criteria': sorted(required),
            'support_record_refs': sorted(supports), 'scope': 'this_assayed_subject_and_molecular_endpoint'})
    return result


def received_links(reader, known):
    known = set(known)

    def public(reference):
        if reference not in known:
            raise ValueError('a104_characterization_operand_not_received')
        return reader.get(reference)

    assessments = defaultdict(list)
    for reference in known:
        record = reader.get(reference)
        if record['record_type'] == 'assessment' and record['relation'] == 'strengthens' \
                and record['applicability'] == 'direct' and record['extent_basis'] == 'observed_extent':
            assessments[record['hypothesis_ref']].append(record)
    sheets = held_assay_sheets(reader, known)
    links = []
    for sheet_ref, cells in sheets.items():
        selected = [row for row in cells if row['component'] == LINK_COMPONENT]
        if len(selected) != 1 or selected[0].get('status') != 'populated':
            continue
        cell = selected[0]
        if cell['assertion_ref'] not in known:
            continue
        hypothesis = reader.get(cell['assertion_ref'])
        if hypothesis['record_type'] != 'hypothesis' or hypothesis['predicate'] not in {'catalyzes', 'transports', 'binds'}:
            continue
        qualification = native_assay_qualification(sheets, hypothesis, cell.get('evidence_source_ref'), known)
        if not qualification:
            continue
        for assessment in assessments[hypothesis['id']]:
            if assessment['observation_ref'] not in known:
                continue
            observation = public(assessment['observation_ref'])
            if observation['record_type'] != 'observation' or observation.get('kind', '').startswith('visual'):
                continue
            if observation['source_ref'] != cell.get('evidence_source_ref'):
                continue
            measured_subjects = set(observation.get('source_subject_refs', [])) or set(observation.get('subject_refs', []))
            # An assay of an unresolved multi-protein preparation is
            # not a component-specific molecular activity measurement.
            if len(measured_subjects) != 1:
                continue
            for subject in set(hypothesis['subject_refs']) & measured_subjects:
                if subject not in known or reader.get(subject)['record_type'] not in {'reference', 'feature', 'product'}:
                    continue
                value = hypothesis['value']
                identity, identity_status = value, 'source_local_assertion'
                if value.get('type') == 'term_ref' and value['ref'] in known:
                    term = reader.get(value['ref'])
                    if term['record_type'] == 'term' and term['namespace'] != 'local':
                        identity = {key: term[key] for key in ('namespace', 'accession', 'term_type')}
                        identity_status = 'received_term_identifier'
                links.append({'reference_ref': subject, 'function_key': canonical([
                    hypothesis['predicate'], identity]), 'predicate': hypothesis['predicate'],
                    'function_value': hypothesis['value'], 'hypothesis_ref': hypothesis['id'],
                    'function_identity_status': identity_status,
                    'assessment_ref': assessment['id'], 'observation_ref': observation['id'],
                    'sheet_ref': sheet_ref, 'component': LINK_COMPONENT,
                    'evidence_source_ref': observation['source_ref'],
                    'condition_refs': list(assessment['condition_refs']),
                    'native_assay_qualification': qualification,
                    'basis': 'received_A105_native_cells_and_direct_observed_assayed_subject'})
    return [dict(value) for _, value in sorted({canonical(row): row for row in links}.items())]


def exact_reference_correspondence(reader, subjects, links, known):
    """Attach an assayed construct only through received identical AA bytes.

    Nonidentical or unknown sequences remain an explicit correspondence need.
    The original assayed subject and observation are never replaced by the
    panel label, and repeated uses remain one original experimental assay.
    """
    result = list(links)
    for row in links:
        assayed = row['reference_ref']
        if assayed in subjects or assayed not in known:
            continue
        try:
            original = sequence(reader, assayed)
        except ValueError:
            continue
        if not original or set(original)-set('ACDEFGHIKLMNPQRSTVWYUO'):
            continue
        for subject in sorted(set(subjects) & set(known)):
            try:
                candidate = sequence(reader, subject)
            except ValueError:
                continue
            if candidate == original:
                result.append({**row, 'reference_ref': subject, 'assayed_reference_ref': assayed,
                    'sequence_correspondence': {'method': 'exact_received_amino_acid_bytes',
                        'assayed_sha256': sha(original.encode()), 'reference_sha256': sha(candidate.encode()),
                        'aligned_residues': len(original), 'identity': 1., 'both_sequence_coverage': 1.}})
    return result


def clade_sheet(subjects, links):
    selected = [row for row in links if row['reference_ref'] in subjects]
    keys = {canonical(row): row for row in selected}
    selected = [keys[key] for key in sorted(keys)]
    characterized = {row['reference_ref'] for row in selected}
    functions = defaultdict(set)
    for row in selected:
        functions[row['function_key']].add(row['reference_ref'])
    unknown = sorted(set(subjects)-characterized)
    identities_unresolved = len(functions) > 1 and any(row.get('function_identity_status') == 'source_local_assertion' for row in selected)
    return {'reference_subject_refs': sorted(subjects), 'characterized_subject_refs': sorted(characterized),
        'unknown_subject_refs': unknown, 'links': selected,
        'function_rows': [{'function_key': key, 'reference_subject_refs': sorted(members)}
                          for key, members in sorted(functions.items())],
        'characterized_fraction': len(characterized)/len(subjects) if subjects else 0.,
        'independent_assay_observation_count': len({row['observation_ref'] for row in selected}),
        'status': 'function_identity_mapping_unresolved' if identities_unresolved else
                  'mixed_characterized_functions' if len(functions) > 1 else 'uncharacterized' if not functions
                  else 'partially_characterized' if unknown else 'uniform_observed_activity_in_sampled_references',
        'all_sampled_references_have_one_observed_activity': len(functions) == 1 and not unknown,
        'evidence_refs': sorted({row[field] for row in selected for field in
            ('reference_ref', 'hypothesis_ref', 'assessment_ref', 'observation_ref', 'sheet_ref', 'evidence_source_ref')}
            | {row['assayed_reference_ref'] for row in selected if row.get('assayed_reference_ref')}
            | {proof['grading_sheet_ref'] for row in selected for proof in row.get('native_assay_qualification', [])}
            | {ref for row in selected for proof in row.get('native_assay_qualification', []) for ref in proof['support_record_refs']}),
        'interpretation': 'sampled_reference_activities_with_assayed_subject_and_conditions; target_activity_separate'}
