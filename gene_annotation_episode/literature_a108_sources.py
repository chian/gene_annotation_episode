"""Source-specific A108 context selections over already possessed bytes.

These readers authenticate the selected source statement and retain native
qualifications. They neither decide contextual fit nor assign evidence scores.
"""
from copy import deepcopy
import io
import json
import xml.etree.ElementTree as ET

from .domain import REF, ContractError, obj, validate_schema
from .literature_assay_inputs import _Sources, _witness_schema


SOURCE_QUALIFIERS = ('organism', 'strain', 'isolate', 'host', 'isolation_source',
    'collection_date', 'country', 'geo_loc_name', 'lat_lon', 'environmental_sample',
    'db_xref', 'note')
IDENTITY_QUALIFIERS = {'organism', 'strain', 'isolate', 'db_xref'}
UNIPROT_COMMENTS = ('SUBCELLULAR LOCATION', 'TISSUE SPECIFICITY',
    'DEVELOPMENTAL STAGE', 'INDUCTION', 'BIOPHYSICOCHEMICAL PROPERTIES')


def source_selector_schema():
    index = {'type': 'integer', 'minimum': 0}
    native = {'source_ref': deepcopy(REF)}
    return {'oneOf': [
        {**obj({'kind': {'const': 'literature_passage'}, 'witness': _witness_schema()}),
         'description': (
             'An exact passage in an acquired literature source. For UniProt, '
             'GenBank and taxonomy records, select their native fields with the '
             'corresponding source selector so their evidence and context metadata '
             'remain attached to the statement.')},
        {**obj({'kind': {'const': 'uniprot_context'}, **deepcopy(native),
            'accession': {'type': 'string', 'minLength': 1},
            'field': {'enum': ['organism', *UNIPROT_COMMENTS]},
            'occurrence': deepcopy(index)}),
         'description': (
             'Select one organism field or comment from the received UniProt '
             'record, including prose within that comment. This selection retains '
             'the full selected field, its native evidence codes, organism and '
             'cited references. occurrence is the zero-based index among comments '
             'of the selected field type; organism uses occurrence 0.')},
        obj({'kind': {'const': 'genbank_source_qualifier'}, **deepcopy(native),
            'record_accession': {'type': 'string', 'minLength': 1},
            'source_feature_index': deepcopy(index),
            'qualifier': {'enum': list(SOURCE_QUALIFIERS)},
            'value_index': deepcopy(index)}),
        obj({'kind': {'const': 'supplied_genbank_qualifier'}, **deepcopy(native),
            'record_ordinal': deepcopy(index), 'feature_index': deepcopy(index),
            'qualifier': {'enum': list(SOURCE_QUALIFIERS)},
            'value_index': deepcopy(index)}),
        obj({'kind': {'const': 'taxonomy_identity'}, **deepcopy(native),
            'taxon_id': {'type': 'string', 'pattern': '^[0-9]+$'}}),
    ]}


def _fail(reason):
    raise ContractError('a108_source_' + reason)


def _at(values, index):
    if type(index) is not int or index < 0 or index >= len(values):
        _fail('selected_native_position_unavailable')
    return values[index]


class ContextSources:
    """Read literal passages and native context fields, with original custody."""
    def __init__(self, read_source, read_record):
        self.sources = _Sources(read_source)
        self.read_record = read_record
        self.selected = []

    def _native(self, selection, providers):
        ref = selection['source_ref']
        record = self.read_record(ref)
        if record.get('record_type') != 'source' or record.get('provider') not in providers:
            _fail('native_provider_mismatch')
        source = self.sources.source(ref, 'original')
        return record, source

    def select(self, selection):
        validate_schema(selection, source_selector_schema())
        kind = selection['kind']
        if kind == 'literature_passage':
            witness = self.sources.witness(selection['witness'], 'context_observation')
            record = self.read_record(witness['source_ref'])
            if record.get('provider') in {'literature.a108.context_grading', 'literature.a108.aggregation'}:
                _fail('computed_sheet_is_not_original_context_source')
            if record.get('provider') in {'uniprot', 'material.genbank'}:
                _fail('native_context_selector_required')
            if record.get('provider') == 'ncbi_entrez':
                original = self.sources.source(witness['source_ref'], 'original')['content'].lstrip()
                if original.startswith(b'LOCUS ') or b'<TaxaSet' in original[:512]:
                    _fail('native_context_selector_required')
            row = {'source_ref': witness['source_ref'], 'artifact_ref': witness['artifact_ref'],
                'representation': witness['representation'], 'selector': deepcopy(selection),
                'value': witness['quote'], 'qualifications': [], 'identity_only': False,
                'native_context': None}
        elif kind == 'uniprot_context':
            row = self._uniprot(selection)
        elif kind == 'genbank_source_qualifier':
            row = self._genbank(selection)
        elif kind == 'supplied_genbank_qualifier':
            row = self._supplied_genbank(selection)
        else:
            row = self._taxonomy(selection)
        self.selected.append(row)
        return deepcopy(row)

    @staticmethod
    def _result(selection, source, value, context, qualifications=(), identity_only=False):
        return {'source_ref': selection['source_ref'], 'artifact_ref': source['artifact_ref'],
            'representation': 'original', 'selector': deepcopy(selection),
            'value': deepcopy(value), 'native_context': deepcopy(context),
            'qualifications': list(qualifications), 'identity_only': identity_only}

    def _uniprot(self, selection):
        _, source = self._native(selection, {'uniprot'})
        try:
            data = json.loads(source['content'])
        except (UnicodeDecodeError, ValueError) as error:
            raise ContractError('a108_source_uniprot_json_required') from error
        entries = data.get('results', [data]) if isinstance(data, dict) else []
        matches = [entry for entry in entries if isinstance(entry, dict)
            and entry.get('primaryAccession') == selection['accession']]
        if len(matches) != 1:
            _fail('uniprot_accession_not_unique')
        entry = matches[0]
        field = selection['field']
        if field == 'organism':
            if selection['occurrence'] != 0 or 'organism' not in entry:
                _fail('uniprot_organism_unavailable')
            selected = entry['organism']
        else:
            selected = _at([comment for comment in entry.get('comments', ())
                if comment.get('commentType') == field], selection['occurrence'])
        # Evidence references and native evidence codes remain paired with the
        # selected comment. A database location label is not presumed measured.
        citations = set()
        pending = [selected]
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                if item.get('source') == 'PubMed' and item.get('id') is not None:
                    citations.add(str(item['id']))
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
        references = [reference for reference in entry.get('references', ())
            if any(str(cross.get('id')) in citations and cross.get('database') == 'PubMed'
                for cross in reference.get('citation', {}).get('citationCrossReferences', ()))]
        return self._result(selection, source, selected,
            {'accession': entry['primaryAccession'], 'organism': entry.get('organism'),
             'entry_audit': entry.get('entryAudit'), 'cited_references': references},
            ('native_evidence_codes_require_scientific_interpretation',), field == 'organism')

    def _genbank(self, selection):
        _, source = self._native(selection, {'ncbi_entrez'})
        from Bio import SeqIO
        try:
            records = [record for record in SeqIO.parse(io.StringIO(source['content'].decode('utf-8')), 'genbank')
                if record.id == selection['record_accession']]
        except (UnicodeDecodeError, ValueError) as error:
            raise ContractError('a108_source_genbank_required') from error
        if len(records) != 1:
            _fail('genbank_accession_not_unique')
        record = records[0]
        feature = _at(record.features, selection['source_feature_index'])
        if feature.type != 'source':
            _fail('genbank_source_feature_required')
        value = _at(feature.qualifiers.get(selection['qualifier'], []), selection['value_index'])
        return self._result(selection, source, value,
            {'accession': record.id, 'source_qualifiers': feature.qualifiers,
             'feature_location': str(feature.location)},
            ('submitted_source_qualifier_not_current_function_annotation',),
            selection['qualifier'] in IDENTITY_QUALIFIERS)

    def _supplied_genbank(self, selection):
        _, source = self._native(selection, {'material.genbank'})
        matches = []
        try:
            for line in source['content'].splitlines():
                if not line.strip():
                    continue
                entry = json.loads(line)
                feature = entry.get('feature')
                if not isinstance(feature, dict):
                    continue
                if (entry.get('record_ordinal') == selection['record_ordinal']
                        and feature.get('native_feature_index') == selection['feature_index']):
                    matches.append(entry)
        except (UnicodeDecodeError, ValueError, AttributeError) as error:
            raise ContractError('a108_source_supplied_genbank_projection_required') from error
        if len(matches) != 1:
            _fail('supplied_genbank_feature_not_unique')
        entry = matches[0]
        feature = entry['feature']
        if feature.get('type') != 'source':
            _fail('genbank_source_feature_required')
        value = _at(feature.get('qualifiers', {}).get(selection['qualifier'], []), selection['value_index'])
        return self._result(selection, source, value, entry,
            ('normalized_native_source_qualifier_not_original_genbank_byte_coordinates',),
            selection['qualifier'] in IDENTITY_QUALIFIERS)

    def _taxonomy(self, selection):
        _, source = self._native(selection, {'ncbi_entrez'})
        try:
            root = ET.fromstring(source['content'])
        except ET.ParseError as error:
            raise ContractError('a108_source_taxonomy_xml_required') from error
        if root.tag != 'TaxaSet':
            _fail('taxonomy_taxaset_required')
        taxa = [taxon for taxon in root.findall('Taxon')
            if taxon.findtext('TaxId') == selection['taxon_id']]
        if len(taxa) != 1:
            _fail('taxonomy_id_not_unique')
        value = ET.tostring(taxa[0], encoding='unicode')
        return self._result(selection, source, value,
            {'taxon_id': selection['taxon_id'], 'scientific_name': taxa[0].findtext('ScientificName')},
            ('taxonomic_identity_does_not_establish_physiology',), True)


__all__ = ['ContextSources', 'source_selector_schema', 'SOURCE_QUALIFIERS', 'UNIPROT_COMMENTS']
