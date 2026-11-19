"""Typed finding identity; no scientific verdict, score or continuation rule.

Episodes supply source-claim meaning, qualifications and explicit equivalence
or correction. The host checks references and declared relationships. Canonical
keys remove quotation/registration identity; they do not prove that a biological
interpretation is true or recognize arbitrary synonyms automatically.
"""
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import canonical, identity


IDENTITY_VERSION = 'typed_source_claim_question_qualification_v2'


def finding_target_roots(store, assessment):
    if 'context_account_scope' in assessment:
        # Clearing a revisable allocation does not change the original target
        # domain or cancel a legitimately owned correction declaration.
        return set(assessment['context_account_scope']['subject_refs'])
    return set(store._record_roots('assessment', assessment))


class FindingIdentity:
    """A projection-local, metadata-only normalizer of declared semantics."""

    def __init__(self, store):
        self.store = store
        self._entities = {}
        self._sources = {}
        self._claims = {}

    def source(self, ref):
        if ref in self._sources:
            return self._sources[ref]
        row = self.store.get(ref)
        if (row.get('origin') == 'tool' and row.get('provider') == 'xlsx.rows'
                and row.get('version') == 'xlsx_selected_cells_v1'
                and len(row.get('parent_source_refs', ())) == 1):
            # This adapter only decodes retained original cells/formula caches;
            # its page/filter/header selection is not a new biological source.
            # Keep the exact input workbook, not its article's DOI (which could
            # combine different supplements) or the selected-page artifact.
            workbook = self.store.get(row['parent_source_refs'][0])
            value = {'original_xlsx_workbook_artifact': workbook['artifact_ref'],
                     'representation': 'original_cells_and_formula_caches_v1'}
            self._sources[ref] = value
            return value
        identifiers = {}
        for item in row.get('publication_identifiers', ()):
            identifiers.setdefault(item['namespace'], set()).add(item['value'])
        ids = {namespace: next(iter(values)) for namespace, values in identifiers.items()
               if len(values) == 1}
        # Identity asserted by actual primary metadata, never bibliography text
        # or a source record's registration/quotation window.
        if any(len(values) > 1 for values in identifiers.values()):
            value = {'conflicting_publication_metadata': {
                key: sorted(values) for key, values in identifiers.items()},
                **{key: row.get(key) for key in ('provider', 'accession', 'version', 'artifact_ref')}}
        elif ids.get('doi'):
            value = {'publication': {'doi': ids['doi'].lower()}}
        elif ids.get('pmcid'):
            value = {'publication': {'pmcid': ids['pmcid']}}
        elif ids.get('pmid'):
            value = {'publication': {'pmid': ids['pmid']}}
        else:
            # A routing/request accession is not necessarily an identity the
            # source asserts. Without primary identity retain content as well;
            # explicit episode equivalence can connect other representations.
            value = {key: row.get(key) for key in ('provider', 'accession', 'version', 'artifact_ref')}
        self._sources[ref] = value
        return value

    def ordered(self, values):
        return sorted({canonical(value): value for value in values}.values(), key=canonical)

    def value(self, value):
        if isinstance(value, dict):
            return {key: (self.entity(child) if key == 'ref' or key.endswith('_ref')
                else self.ordered(self.entity(ref) for ref in child) if key.endswith('_refs')
                else self.ordered(self.value(item) for item in child) if key in {'roles', 'attributes'}
                else self.value(child)) for key, child in value.items()}
        if isinstance(value, list):
            # Mapping paths and compound construct order are meaningful.
            return [self.value(child) for child in value]
        if isinstance(value, float) and value.is_integer():
            # JSON 1 and 1.0 do not state different scientific precision.
            return int(value)
        return value

    def entity(self, ref):
        if ref is None:
            return None
        if ref in self._entities:
            return self._entities[ref]
        row = self.store.get(ref)
        kind = row['record_type']
        if kind in {'input', 'read_subject'}:
            # Fixed original identity/member identity is meaningful. Two equal
            # sequences or coordinate extents do not imply the same material.
            body = {'record_type': kind, 'original_identity': ref}
        elif kind == 'term':
            body = ({'record_type': kind, 'source': self.source(row['source_ref']),
                     'term_type': row['term_type'], 'label': row['label']}
                if row['namespace'] == 'source_local' else
                {'record_type': kind, 'namespace': row['namespace'],
                 'accession': row['accession'], 'term_type': row['term_type']})
        elif kind == 'reference':
            body = {'record_type': kind, 'reference_type': row['reference_type'],
                'source': self.source(row['source_ref']), 'molecule': row.get('molecule'),
                'sequence_ref': row.get('sequence_ref'), 'length': row.get('length'),
                **self.value({key: row[key] for key in ('term_refs', 'context_refs')})}
            if row.get('origin') == 'extracted':
                body['label'] = row['label']
            else:
                body['accession'] = row['accession']
                if row.get('member_ref') is not None:
                    body['member_ref'] = row['member_ref']
        elif kind == 'feature':
            body = {'record_type': kind, **self.value({key: row[key] for key in
                ('subject_ref', 'kind', 'segments', 'strand', 'context_refs')})}
        elif kind == 'product':
            # Same original coverage is insufficient: preserve actual derived
            # sequence identity, molecule, parents and mapping/construct path.
            body = {'record_type': kind, **self.value({key: row[key] for key in
                ('sequence_ref', 'molecule', 'derivation', 'context_refs', 'footprint', 'mapping')
                if key in row}), 'parent_refs': [self.entity(ref) for ref in row['parent_refs']]}
        elif kind == 'context':
            body = {'record_type': kind, 'source': self.source(row['source_ref']),
                **self.value({key: row[key] for key in
                    ('context_type', 'name', 'attributes', 'related_refs')})}
        elif kind == 'hypothesis':
            body = {'record_type': kind, **self.value({key: row[key] for key in
                ('subject_refs', 'predicate', 'value', 'context_refs')})}
        elif kind == 'artifact':
            # Sequence/unit identity is content-addressed; bytes stay on disk.
            body = {'record_type': kind, 'content_ref': ref}
        else:
            # Unsupported semantic entities retain their actual identity rather
            # than acquiring guessed equality from display wording.
            body = {'record_type': kind, 'reference': ref}
        self._entities[ref] = body
        return body

    def source_claim(self, assessment):
        chain, current = [], assessment
        while True:
            ref = current['id']
            if ref in self._claims:
                value = self._claims[ref]
                break
            chain.append(ref)
            finding = current['investigation_finding']
            previous = finding['same_source_claim_as_ref']
            if previous is None:
                observation = self.store.get(current['observation_ref'])
                value = {'source': self.source(observation['source_ref']),
                         'assertion': self.value(finding['source_claim'])}
                break
            # Store references point to already existing immutable records.
            # Equivalence chains therefore form a DAG; iterative resolution
            # does not impose a scientific chain-length or iteration limit.
            current = self.store.get(previous)
        for ref in chain:
            self._claims[ref] = value
        return value

    def finding(self, assessment):
        body = {'question': self.entity(assessment['hypothesis_ref']),
            'source_claim': self.source_claim(assessment),
            'qualification': self.value(assessment['investigation_finding']['qualification'])}
        # Relation, applicability, disposition, revision, account, episode and
        # quotation identity are not extra information units.
        return {'finding_key': identity('scientific_finding', {'version': IDENTITY_VERSION, **body}),
                'identity_version': IDENTITY_VERSION, 'meaning': body}
