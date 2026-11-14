"""Original operation declarations for received source-role identity evidence.

The actual A107/A110 qualification owners retain scientific execution, source
sequence witnesses and saved-result custody. This module owns only their
original shared catalog declaration and imports its original schema builder.
"""
from gene_annotation_episode.domain import obj


TOOLS = {'A107': 'partner.source_identity_evidence',
         'A110': 'chemistry.source_identity_evidence'}


def catalog(axis):
    ref = {'type': 'string', 'format': 'reference'}
    optional = {'anyOf': [ref, {'type': 'null'}]}
    return {TOOLS[axis]: {'resources': 'local', 'description':
        'Bind one original experimental role reference to an actually received '
        'protein sequence through a received source_content observation. The '
        'observation must explicitly name the role as a subject and the protein '
        'as a subject/reference_ref measurement; its exact source quote must '
        'contain the role label and a complete matching protein sequence or an '
        'actual acquired accession. For a particular experiment, explicitly link '
        'its reference from the observation. Choose whole_protein, protein_component '
        'or unspecified according to the source declaration. Component identity '
        'does not establish whole-complex identity. An accession alone retains '
        'unknown experimental sequence/construct identity and is useful as a search '
        'lead. Names alone are insufficient. Original assay roles and numbers are '
        'preserved. An explicit revision retains its predecessor and reason. '
        'This performs bounded source inspection, not an alignment, activity assay '
        'or new scalar calculation.',
        'input_schema': obj({'target_ref': ref, 'source_role_ref': ref,
            'actual_ref': ref, 'observation_ref': ref, 'experiment_ref': optional,
            'identity_scope': {'enum': ['whole_protein', 'protein_component', 'unspecified']},
            'revises_identity_ref': optional,
            'revision_reason': {'type': ['string', 'null'], 'minLength': 1}})}}


