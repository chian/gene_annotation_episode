"""Consume exact experimental reference links from existing A105 returns.

This is a receiving adapter, not a new experimental-evidence subtree. Copied
names, an assessment alone, and an unreceived literature return cannot supply
an experimentally characterized clade member.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from .domain import canonical
from .episode_return_records import EpisodeReturnRecords
from .literature_a105_worksheet import VERSION, VERSION_V2, validate_a105_worksheet_links


def native_assay_qualification(store, form, schema, assertion, source, known, *, run_id):
    """Read the particular delivered A105 judgments, never an axis scalar."""
    rows = []
    for field, node in schema.get('properties', {}).items():
        if node.get('x-source') == 'literature_assay_grading_cells':
            rows.extend(form[field])
        elif node.get('x-source') == 'literature_a105_aggregation_cells':
            rows.extend(row for cell in form[field] for row in cell['selected_components'])
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
        grant = store.get(sheet)
        if grant.get('provider') != 'literature.a105.assay_grading' or grant['origin'] != 'tool':
            continue
        from .literature_assay_grading_storage import LiteratureAssayGradingRepository
        repository = LiteratureAssayGradingRepository(store, run_id)
        saved = repository.read(sheet)
        originals = {canonical(row) for row in repository.rows(saved, sheet,
                     list(dict.fromkeys(row['component'] for row in parts)))}
        if not all(canonical(row) in originals for row in parts):
            raise ValueError('a104_characterization_native_assay_cells_changed')
        interpretations = {key: value for row in parts for key, value in row.get('interpretations', {}).items()}
        required = set(common)
        assay_type = parts[0]['assay_type']
        required.update({'transport_response': {'membrane_system', 'transport_endpoint',
            'transport_driving_force', 'transport_specificity'},
            'ligand_binding': {'binding_species', 'binding_controls', 'binding_regime'},
            'endpoint_conversion': {'product_identity'}, 'product_distribution': {'species_identity'},
            'reaction_coupling': {'product_identity', 'stoichiometry', 'reporter_specificity'}}.get(assay_type, ()))
        if not all(interpretations.get(name, {}).get('status') == 'supported' for name in required):
            continue
        supports = {reference for name in required for reference in interpretations[name]['support_refs']}
        if not supports <= set(known):
            continue
        result.append({'grading_sheet_ref': sheet, 'assay_type': assay_type,
            'quantity_kind': parts[0]['quantity_kind'], 'required_supported_criteria': sorted(required),
            'support_record_refs': sorted(supports), 'scope': 'this_assayed_subject_and_molecular_endpoint'})
    return result


def received_links(store, context, known):
    if context is None:
        return []
    reader = EpisodeReturnRecords(store, context.run_id, failure_prefix='a104_characterization_')

    def public(reference):
        if reference not in known:
            raise ValueError('a104_characterization_operand_not_received')
        return store.get(reference)

    assessments = defaultdict(list)
    for reference in known:
        record = store.get(reference)
        if record['record_type'] == 'assessment' and record['relation'] == 'strengthens' \
                and record['applicability'] == 'direct' and record['extent_basis'] == 'observed_extent':
            assessments[record['hypothesis_ref']].append(record)
    links = []
    for child, form, schema in reader.received_attempts(context):
        if child.role != 'literature':
            continue
        contexts = [value for value in form.values() if isinstance(value, Mapping)
                    and value.get('version') in {VERSION, VERSION_V2}]
        if not contexts:
            continue
        try:
            validate_a105_worksheet_links(form, schema, child.assignment, read_public_record=public)
        except ValueError as error:
            if str(error) == 'a104_characterization_operand_not_received':
                continue
            raise
        for worksheet in contexts:
            for link in worksheet['assertion_links']:
                if link['relation'] != 'measures_asserted_endpoint' or link['assertion_ref'] not in known:
                    continue
                hypothesis = store.get(link['assertion_ref'])
                if hypothesis['record_type'] != 'hypothesis' or hypothesis['predicate'] not in {'catalyzes', 'transports', 'binds'}:
                    continue
                selector = link['selector']
                cells = [row for row in form[selector['field']] if row['sheet_ref'] == selector['sheet_ref']
                         and row['component'] == selector['component']]
                if len(cells) != 1 or cells[0].get('status') != 'populated':
                    continue
                cell = cells[0]
                qualification = native_assay_qualification(store, form, schema, hypothesis,
                    cell.get('evidence_source_ref'), known, run_id=context.run_id)
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
                        if subject not in known or store.get(subject)['record_type'] not in {'reference', 'feature', 'product'}:
                            continue
                        value = hypothesis['value']
                        identity, identity_status = value, 'source_local_assertion'
                        if value.get('type') == 'term_ref' and value['ref'] in known:
                            term = store.get(value['ref'])
                            if term['record_type'] == 'term' and term['namespace'] != 'local':
                                identity = {key: term[key] for key in ('namespace', 'accession', 'term_type')}
                                identity_status = 'received_term_identifier'
                        links.append({'reference_ref': subject, 'function_key': canonical([
                            hypothesis['predicate'], identity]), 'predicate': hypothesis['predicate'],
                            'function_value': hypothesis['value'], 'hypothesis_ref': hypothesis['id'],
                            'function_identity_status': identity_status,
                            'assessment_ref': assessment['id'], 'observation_ref': observation['id'],
                            'sheet_ref': selector['sheet_ref'], 'component': selector['component'],
                            'evidence_source_ref': observation['source_ref'],
                            'condition_refs': list(assessment['condition_refs']),
                            'native_assay_qualification': qualification,
                            'basis': 'received_A105_native_cells_and_direct_observed_assayed_subject'})
    return [dict(value) for _, value in sorted({canonical(row): row for row in links}.items())]


def exact_reference_correspondence(store, subjects, links, known):
    """Attach an assayed construct only through received identical AA bytes.

    Nonidentical or unknown sequences remain an explicit correspondence need.
    The original assayed subject and observation are never replaced by the
    panel label, and repeated uses remain one original experimental assay.
    """
    from .a104_hpc import sequence, sha
    result = list(links)
    for row in links:
        assayed = row['reference_ref']
        if assayed in subjects or assayed not in known:
            continue
        try:
            original = sequence(store, assayed)
        except ValueError:
            continue
        if not original or set(original)-set('ACDEFGHIKLMNPQRSTVWYUO'):
            continue
        for subject in sorted(set(subjects) & set(known)):
            try:
                candidate = sequence(store, subject)
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
