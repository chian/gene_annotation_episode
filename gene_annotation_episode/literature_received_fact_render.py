"""Pure presentation of selected, possessed scientific records and their links.

Local labels denote immutable record identity, never independent experiments.
The caller applies numerical-operand masking before supplying these records.
No storage, source reader, calculator or model is consulted here.
"""
from collections.abc import Mapping
import json
import re


KINDS = frozenset({'reference', 'term', 'context', 'observation', 'hypothesis', 'assessment'})
_NAMES = {'reference': 'Entity', 'term': 'Term', 'context': 'Condition',
          'observation': 'Fact', 'hypothesis': 'Claim', 'assessment': 'Assessment'}
_CUSTODY = frozenset({'id', 'record_type', 'source_ref', 'artifact_ref', 'sequence_ref',
    'key_ref', 'anchor', 'visual_anchor', 'native_record_ref', 'member_ref',
    'revision', 'created_at', 'updated_at', 'recorded_at'})
_BOUND = {'less_than': '<', 'less_or_equal': '≤', 'greater_than': '>', 'greater_or_equal': '≥'}
# Only inspected generation sites, together with their declared record origin
# and namespace, distinguish host accessions from scientific identifiers.
_REFERENCE_GENERATORS = frozenset({'source_assay', 'source_experiment', 'source_subject_token',
    'assay_literal', 'interpreted_assay', 'binding_label', 'context_literal', 'reaction_literal',
    'structure_literal', 'perturbation_literal', 'partner_literal', 'figure_literal',
    'ratio_source_meaning', 'ratio_label', 'controlled_joint_scope_witness',
    'gel_source_witness', 'gel_scientific_meaning', 'transport_curve', 'transport_quantity'})
_REFERENCE_GENERATOR_FAMILIES = ('native_rate_', 'amount_', 'optical_', 'kinetic_', 'binding_interaction_')
_TERM_GENERATORS = {'literature_endpoint': {'endpoint', 'native_rate_endpoint'},
    'literature_normalization': {'normalization', 'native_rate_normalization'},
    'literature_quantity': {'quantity'}, 'literature_analyte': {'analyte'},
    'literature_assay_endpoint': {'assay_endpoint'}, 'literature_assay_arrangement': {'assay_arrangement'},
    'literature_partner_condition_factor': {'partner_factor'}}
_TERM_GENERATOR_FAMILIES = {'literature_context_': 'context_literal',
    'literature_reaction_': 'reaction_literal', 'literature_perturbation_': 'perturbation_literal',
    'literature_partner_': 'partner_literal', 'literature_figure_': 'figure_literal'}


def _generated_accession(record):
    accession = record.get('accession')
    if not isinstance(accession, str) or '_' not in accession:
        return False
    stem, digest = accession.rsplit('_', 1)
    if not re.fullmatch(r'(?:[a-f0-9]{24}|[a-f0-9]{64})', digest):
        return False
    kind, origin = record.get('record_type'), record.get('origin')
    if origin == 'extracted':
        return (kind == 'reference' and stem == 'source_entity'
            or kind == 'term' and record.get('namespace') == 'source_local' and stem == 'source_term')
    if origin != 'tool':
        return False
    if kind == 'reference':
        return stem in _REFERENCE_GENERATORS or stem.startswith(_REFERENCE_GENERATOR_FAMILIES)
    if kind == 'term':
        namespace = record.get('namespace', '')
        return stem in _TERM_GENERATORS.get(namespace, ()) or any(
            namespace.startswith(prefix) and stem == generated
            for prefix, generated in _TERM_GENERATOR_FAMILIES.items())
    return False


def _scalar(value):
    if value is None:
        return 'unknown'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


class ReceivedFactDisplay:
    def __init__(self, records, *, subjects=(), revision_status=(), received_refs=()):
        self.records = {row['id']: row for row in records}
        self.subjects = {row['id']: row for row in subjects if isinstance(row, Mapping) and 'id' in row}
        self.revision_status = {row['record_ref']: row['is_current_revision'] for row in revision_status}
        self.labels = {}
        self.unresolved_labels = {}
        self.known_refs = set(received_refs) | set(self.records) | set(self.subjects)
        self.source_labels = {}
        self.sequence_labels = {}
        self.passages = {}
        counts = {}
        for reference, row in self.records.items():
            name = _NAMES.get(row.get('record_type'), 'Record')
            counts[name] = counts.get(name, 0) + 1
            self.labels[reference] = name + ' ' + str(counts[name])
            if row.get('source_ref') is not None:
                self.identity_ref(row['source_ref'], 'source')
            if row.get('sequence_ref') is not None:
                self.identity_ref(row['sequence_ref'], 'sequence')

    def identity_ref(self, reference, category):
        """Preserve a received association without hydrating its contents."""
        if isinstance(reference, (Mapping, tuple, list)):
            return self.inline(reference)
        if reference is None:
            return 'unknown'
        labels = self.source_labels if category == 'source' else self.sequence_labels
        if reference not in labels:
            labels[reference] = category.capitalize() + ' handle ' + str(len(labels) + 1)
        return labels[reference]

    def ref(self, reference):
        # Canonical finding meanings can expand typed atom, unit and relation
        # links into semantic records. Display those supplied meanings directly;
        # only actual handles belong in the local label dictionaries.
        if isinstance(reference, (Mapping, tuple, list)):
            return self.inline(reference)
        if reference is None:
            return 'unknown'
        if reference in self.labels:
            return self.labels[reference]
        if reference in self.source_labels:
            return self.source_labels[reference]
        if reference in self.sequence_labels:
            return self.sequence_labels[reference]
        if reference in self.subjects:
            row = self.subjects[reference]
            return 'supplied material: ' + str(row.get('name', row.get('label', 'unnamed')))
        # Do not infer a missing definition from the spelling of a host ID.
        if reference not in self.unresolved_labels:
            self.unresolved_labels[reference] = 'Unresolved link ' + str(len(self.unresolved_labels) + 1)
        return self.unresolved_labels[reference] + ' (meaning unavailable in this scoped display)'

    def atom(self, value):
        if not isinstance(value, Mapping):
            return _scalar(value)
        kind = value.get('type')
        if kind == 'number':
            text = ('≈' if value.get('qualifier') == 'approximate' else '')
            text += _BOUND.get(value.get('bound'), '') + _scalar(value.get('value'))
            uncertainty = value.get('uncertainty')
            if isinstance(uncertainty, Mapping):
                text += ' ± ' + _scalar(uncertainty.get('magnitude')) + ' (statistic: ' + str(uncertainty.get('statistic', 'unknown')) + ')'
            if value.get('unit_ref') is not None:
                text += ' ' + self.ref(value['unit_ref'])
            return text
        if kind == 'enum':
            return _scalar(value.get('value'))
        if kind in {'reference', 'term_ref'}:
            return self.ref(value.get('ref'))
        if kind == 'relation':
            return '; '.join(str(row['role']) + '=' + self.ref(row['ref']) for row in value['roles'])
        return self.inline(value)

    def project(self, value):
        """Keep generic admitted field meanings while resolving their references."""
        if isinstance(value, Mapping):
            if value.get('type') in {'number', 'enum', 'reference', 'term_ref', 'relation'}:
                return self.atom(value)
            result = {}
            for name, child in value.items():
                if name == 'id':
                    continue
                if name in {'source_ref', 'sequence_ref'}:
                    result[name] = self.identity_ref(child, name.removesuffix('_ref'))
                elif name == 'ref' or name.endswith('_ref'):
                    result[name] = self.ref(child) if isinstance(child, str) or child is None else self.project(child)
                elif name == 'partial_record_refs' and isinstance(child, (tuple, list)):
                    # Failure receipts carry recovery addresses, not admitted
                    # scientific meanings. Keep the actual handles selectable
                    # without hydrating or interpreting the retained records.
                    result[name] = [ref if isinstance(ref, str) else self.project(ref) for ref in child]
                elif name.endswith('_refs') or name == 'dependencies':
                    if isinstance(child, (tuple, list)):
                        links = [self.ref(ref) if isinstance(ref, str) or ref is None
                                 else self.project(ref) for ref in child]
                        # Some admitted results expand these links into records.
                        # Keep that structure instead of using it as a label key.
                        result[name] = ('; '.join(links) if all(
                            isinstance(ref, str) or ref is None for ref in child) else links)
                    else:
                        result[name] = self.project(child)
                elif name == 'accession' and _generated_accession(value):
                    continue
                else:
                    result[name] = self.project(child)
            return result
        if isinstance(value, (tuple, list)):
            return [self.project(item) for item in value]
        if isinstance(value, str) and value in self.known_refs:
            return self.ref(value)
        return value

    def inline(self, value):
        if isinstance(value, Mapping):
            if value.get('type') in {'number', 'enum', 'reference', 'term_ref', 'relation'}:
                return self.atom(value)
            items = []
            for key, child in value.items():
                if key == 'accession' and _generated_accession(value):
                    continue
                if key == 'ref' or key.endswith('_ref'):
                    text = self.ref(child) if isinstance(child, str) or child is None else self.inline(child)
                elif key.endswith('_refs') or key == 'dependencies':
                    text = ('; '.join(self.ref(ref) if isinstance(ref, str) or ref is None
                                     else self.inline(ref) for ref in child)
                            if isinstance(child, (tuple, list)) else self.inline(child))
                    text = text or 'none supplied'
                else:
                    text = self.inline(child)
                items.append(str(key) + '=' + text)
            return '; '.join(items) or 'none supplied'
        if isinstance(value, (tuple, list)):
            return '; '.join(self.inline(item) for item in value) or 'none supplied'
        return _scalar(value)

    def _passage(self, row):
        anchor = row.get('anchor')
        if not isinstance(anchor, Mapping) or not isinstance(anchor.get('quote'), str):
            return 'no selected text excerpt'
        key = json.dumps([anchor.get(name) for name in ('source_ref', 'artifact_ref', 'start', 'end', 'quote')], ensure_ascii=False)
        if key not in self.passages:
            self.passages[key] = ('Passage ' + str(len(self.passages) + 1), anchor['quote'])
        return self.passages[key][0]

    def render_records(self, *, table):
        rows = []
        for reference, row in self.records.items():
            kind = row.get('record_type')
            fields = {key: child for key, child in row.items() if key not in _CUSTODY}
            if kind not in KINDS:
                fields = {'unrecognized record type': kind, **fields}
            # Native generated accessions are custody; scientific accessions
            # and classification namespaces remain available in this row.
            if _generated_accession(row):
                fields.pop('accession')
            if 'source_ref' in row:
                fields['source identity'] = self.identity_ref(row['source_ref'], 'source')
            if 'sequence_ref' in row:
                fields['sequence association'] = self.identity_ref(row['sequence_ref'], 'sequence')
            if row.get('revision') is not None or reference in self.revision_status:
                current = self.revision_status.get(reference)
                fields['received revision state'] = 'current' if current is True else 'stale' if current is False else 'unknown'
            rows.append((self.labels[reference], kind or 'unrecognized', self.inline(fields), self._passage(row)))
        return table(('Record', 'Scientific type', 'Received scientific meaning and relationships', 'Selected excerpt'), rows)

    def render_passages(self, *, table):
        return table(('Excerpt', 'Already received source text'), self.passages.values()) if self.passages else None


__all__ = ['KINDS', 'ReceivedFactDisplay']
