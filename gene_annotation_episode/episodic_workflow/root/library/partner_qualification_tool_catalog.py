"""Original partner qualification operation declarations for the shared registry."""
from gene_annotation_episode.domain import obj


def catalog():
    ref = {'type': 'string', 'format': 'reference'}
    nullable = {'anyOf': [ref, {'type': 'null'}]}
    from .literature_partner_return_contracts import COMPONENTS
    definitions = {
        'partner.component_correspondence': ('Measure this particular actual/reference protein or region correspondence from received native alignments or exact peptide identity. For a protein feature, positions use its local protein coordinates; native reuse requires its actually received parent sequence frame. Return native maps, coordinate paths, distance, extent, unresolved competing maps and their sources. This runs no search and establishes no functional requirement or new scalar score.',
            obj({'target_ref': ref, 'actual_ref': ref, 'component_ref': ref,
                'positions': {'type': ['array', 'null'], 'items': {'type': 'integer', 'minimum': 0},
                    'uniqueItems': True, 'minItems': 1}, 'alignment_ref': nullable})),
        'partner.requirement_evidence': ('Retain a received source-backed requires/partner_dependence finding and its exact partner, direction, actual subject and conditions. Optionally attach actually delivered native omission/addback components from that same experiment. The finding observation must explicitly link the sheet experiment_ref in its subject_refs, source_subject_refs or dependencies. A shared paper alone does not establish that experiment link; missing linkage retains the numerical components with unresolved application. A source interpretation does not create target transfer or prove necessity. No model-authored numerical values are accepted.',
            obj({'target_ref': ref, 'assessment_ref': ref, 'component_ref': ref,
                'sheet_ref': nullable, 'components': {'type': 'array', 'items': {'enum': list(COMPONENTS)},
                    'uniqueItems': True}})),
        'partner.detection_evidence': ('Read an actual received native A103 detector inventory or authenticated A107 HPC search/detector publication using the exact required-component query sequence. Distinguish exact peptide detection, a homologous match, scoped no included hit and incomplete detection. New detector results retain the original computed reference-CDS translations, nucleotide sequences, record-local coordinates and all sequence-matched locus candidates; reuse those saved witnesses before seeking a new translation or placement calculation. A verified reference correspondence does not establish submitted target/sample genomic origin. Historical results without these witnesses retain their original meanings. Preserve original records, examined CDS, native statistics and unknown identity. This runs no detector/search and makes no whole-genome or functional-partner absence claim.',
            obj({'target_ref': ref, 'detection_ref': ref, 'component_ref': ref})),
        'partner.expression_evidence': ('Attach one actually received expression-table feature to a particular supplied target or required component using its declared measured-molecule sequence identity and received native correspondence. For measured RNA to a protein, supply the actual received native translation product and its original mapping witnesses. Positions then refer to that encoded product. Keep measured transcript, protein or reporter, whole-feature quantity, selected condition and local correspondence distinct. Missing measured-feature identity does not become target coexpression.',
            obj({'target_ref': ref, 'expression_ref': ref, 'feature_side': {'enum': ['left', 'right']},
                'actual_ref': ref, 'component_ref': ref,
                'encoded_product_ref': nullable,
                'require_detection_criterion': {'type': 'boolean', 'description':
                    'Request qualified source-criterion information for this measured feature. '
                    'Omit or use false for correspondence/coexpression alone.'},
                'positions': {'type': ['array', 'null'], 'items': {'type': 'integer', 'minimum': 0},
                    'uniqueItems': True, 'minItems': 1}, 'alignment_ref': nullable},
                required=['target_ref', 'expression_ref', 'feature_side', 'actual_ref', 'component_ref',
                    'encoded_product_ref', 'positions', 'alignment_ref'])),
        'partner.expression_locus_evidence': ('Attach a gene-ID-level RNA measurement to an actually received native genomic locus. Require the measured feature entity_id to match its exact locus tag and retain each selected sample\'s declared reference-genome accession. Reuse the original verified CDS translation and received protein/region correspondence when available. A reference-locus assignment is not verification of the assay sample genotype, transcript isoform or protein abundance.',
            obj({'target_ref': ref, 'expression_ref': ref, 'feature_side': {'enum': ['left', 'right']},
                'locus_binding_ref': ref, 'component_ref': ref,
                'require_detection_criterion': {'type': 'boolean'},
                'positions': {'type': ['array', 'null'], 'items': {'type': 'integer', 'minimum': 0},
                    'uniqueItems': True, 'minItems': 1}, 'alignment_ref': nullable},
                required=['target_ref', 'expression_ref', 'feature_side', 'locus_binding_ref',
                    'component_ref', 'positions', 'alignment_ref'])),
    }
    entries = {name: {'description': text, 'resources': 'local', 'input_schema': schema}
        for name, (text, schema) in definitions.items()}
    from .component_source_identity import catalog as identity_catalog
    entries.update(identity_catalog('A107'))
    # Optional associations extend the existing tools without changing the
    # required arguments or meaning of historical requests.
    entries['partner.requirement_evidence']['input_schema']['properties'].update(
        component_identity_ref=nullable, subject_identity_ref=nullable,
        subject_alignment_ref=nullable)
    entries['partner.requirement_evidence']['description'] += (
        ' Optional component_identity_ref and subject_identity_ref select actual '
        'source_identity_evidence results for the original partner/subject roles. '
        'Their protein references remain separate from the immutable assay roles; '
        'subject correspondence does not create a new regional measurement.')
    for name in ('partner.detection_evidence', 'partner.expression_evidence',
                 'partner.expression_locus_evidence'):
        entries[name]['input_schema']['properties']['requirement_ref'] = nullable
        entries[name]['description'] += (
            ' Optional requirement_ref selects the actual qualified source '
            'requirement whose identified component is being examined. The '
            'original component query/measurement must match that particular '
            'declared sequence; homologs do not automatically acquire its role.')
    return entries


