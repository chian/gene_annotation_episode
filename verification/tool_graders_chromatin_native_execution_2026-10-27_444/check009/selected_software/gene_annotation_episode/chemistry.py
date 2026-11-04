"""Source-faithful chemical/reaction projections; no target-function inference.

Rhea equation sides are source left/right, not inferred substrates/products.
Stoichiometric expressions remain expressions; blank Rhea coefficients denote
one by the documented notation. ChEBI search summaries and compound records
retain distinct completeness. Complete native responses remain source artifacts.
"""
from __future__ import annotations

from html.parser import HTMLParser
import json
import re

from .domain import ContractError

VERSION = 'rhea_chebi_source_projection_v1'
RHEA_ID = re.compile(r'^(?:RHEA:)?([0-9]+)$', re.I)
CHEBI_ID = re.compile(r'^(?:CHEBI:)?([0-9]+)$', re.I)
DIRECTIONS = {'=': 'undefined', '=>': 'left_to_right', '<=': 'right_to_left', '<=>': 'bidirectional'}


def accession(value, database):
    pattern = RHEA_ID if database == 'RHEA' else CHEBI_ID
    match = pattern.fullmatch(str(value))
    if not match:
        raise ContractError('invalid_'+database.lower()+'_accession')
    return database+':'+match[1]


class _Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return ''.join(child.text() if isinstance(child, _Node) else child for child in self.children)

    def nodes(self):
        yield self
        for child in self.children:
            if isinstance(child, _Node):
                yield from child.nodes()


class _Equation(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {'br', 'img', 'hr', 'input'}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if len(self.stack) < 2 or self.stack[-1].tag != tag:
            raise ContractError('unbalanced_rhea_equation_markup')
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def rhea_equation(markup):
    """Use native participant boundaries; '+' inside a name is not a separator."""
    if not isinstance(markup, str):
        raise ContractError('rhea_equation_markup_unavailable')
    parser = _Equation()
    parser.feed(markup)
    parser.close()
    if len(parser.stack) != 1:
        raise ContractError('unbalanced_rhea_equation_markup')
    side, arrow, participants = 'left', None, []
    for child in parser.root.children:
        if isinstance(child, str):
            text = child.strip()
            if text in {'', '+'}:
                continue
            if text not in DIRECTIONS or arrow is not None:
                raise ContractError('unrecognized_rhea_equation_separator')
            arrow, side = text, 'right'
            continue
        if 'participant' not in child.attrs.get('class', '').split():
            raise ContractError('unrecognized_rhea_equation_element')
        links = [n for n in child.nodes() if n.tag == 'a' and 'data-molid' in n.attrs]
        if len(links) != 1:
            raise ContractError('rhea_participant_identity_unavailable')
        def part(name):
            nodes = [n for n in child.nodes() if name in n.attrs.get('class', '').split()]
            if len(nodes) > 1:
                raise ContractError('ambiguous_rhea_participant_'+name)
            return nodes[0].text().strip() if nodes else ''
        coefficient = part('stoichiometry')
        participants.append({'ordinal': len(participants), 'side': side,
            'source_accession': links[0].attrs['data-molid'], 'source_name': links[0].text(),
            'coefficient_expression': coefficient or '1', 'source_coefficient_text': coefficient,
            'coefficient_basis': 'source_explicit' if coefficient else 'implicit_unit_rhea_notation',
            'source_location': part('location')})
    if arrow is None or not participants or not any(p['side'] == 'right' for p in participants):
        raise ContractError('rhea_equation_sides_unavailable')
    return arrow, DIRECTIONS[arrow], participants


def rhea_response(content):
    body = json.loads(content)
    if not isinstance(body, dict) or not isinstance(body.get('results'), list):
        raise ContractError('invalid_rhea_response')
    return body


def rhea_row(row):
    if not isinstance(row, dict) or not isinstance(row.get('equation'), str):
        raise ContractError('invalid_rhea_reaction_row')
    rid = accession(row['id'], 'RHEA')
    arrow, direction, participants = rhea_equation(row.get('htmlequation'))
    return {'accession': rid, 'source_equation': row['equation'], 'source_arrow': arrow,
        'source_direction': direction, 'source_status': row.get('status'),
        'source_balanced': row.get('balanced'), 'source_transport': row.get('transport'),
        'source_comment': row.get('comment'), 'participants': participants}


def chebi_response(content, *, search):
    body = json.loads(content)
    if not isinstance(body, dict) or (search and not isinstance(body.get('results'), list)):
        raise ContractError('invalid_chebi_response')
    return body


def chemical_row(row, *, search):
    if search:
        row = row.get('_source') if isinstance(row, dict) else None
    if not isinstance(row, dict) or not isinstance(row.get('name'), str):
        raise ContractError('invalid_chebi_compound_row')
    cid = accession(row['chebi_accession'], 'CHEBI')
    data = row if search else (row.get('chemical_data') or {})
    structure = row if search else (row.get('default_structure') or {})
    if not isinstance(data, dict) or not isinstance(structure, dict):
        raise ContractError('invalid_chebi_chemical_structure')
    relations=[]
    if not search:
        ontology = row.get('ontology_relations') or {}
        if not isinstance(ontology, dict):
            raise ContractError('invalid_chebi_ontology_relations')
        for orientation, rows in ontology.items():
            if orientation not in {'incoming_relations','outgoing_relations'} or not isinstance(rows, list):
                raise ContractError('invalid_chebi_ontology_relations')
            for item in rows:
                relations.append({'orientation': orientation,
                    'initial_accession': accession(item['init_id'], 'CHEBI'),
                    'initial_name': item['init_name'], 'source_relation': item['relation_type'],
                    'final_accession': accession(item['final_id'], 'CHEBI'), 'final_name': item['final_name']})
    return {'accession': cid, 'source_name': row['name'], 'source_definition': row.get('definition'),
        'representation': 'search_summary' if search else 'compound_detail',
        'formula': data.get('formula'), 'charge': data.get('charge'), 'mass': data.get('mass'),
        'monoisotopic_mass': data.get('monoisotopicmass' if search else 'monoisotopic_mass'),
        'smiles': structure.get('smiles'), 'inchi': structure.get('inchi' if search else 'standard_inchi'),
        'inchikey': structure.get('inchikey' if search else 'standard_inchi_key'),
        'wurcs': structure.get('wurcs'), 'is_r_group': structure.get('is_r_group'),
        'source_structure_id': row.get('default_structure') if search else structure.get('id'),
        'secondary_accessions': row.get('secondary_ids', []), 'ontology_relations': relations,
        'source_modified_on': row.get('modified_on'), 'source_stars': row.get('stars'),
        'source_is_released': row.get('is_released')}
