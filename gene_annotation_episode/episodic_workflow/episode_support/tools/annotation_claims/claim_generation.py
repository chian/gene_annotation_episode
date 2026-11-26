"""The claims a candidate annotation makes: one set workflow, called once for an annotation.

The owner, 2026-11-23: "annotations generate claims for A105 to check"; "it is a set path. you find all the info, you
reason about it and add anything else to the list. that's it. done. there is no iteration, and there is no need to
separate the database finding from the llm reasoning about claims"; the caller "does not need to know anything but the
claims themselves and does not need to know the process".

A claim says that the annotated protein binds, catalyzes or transports one named molecule: a ``hypothesis`` record of
the system's ordinary form (``domain.RECORD_SCHEMAS['hypothesis']``), which any evidence head that can check its
predicate reads as it reads a proposed annotation. The workflow (``generate_claims``), in this order and nothing else:

1. Find what the public record states about proteins of the annotation: one UniProt search (by protein name; by the
   Pfam cross-reference for a profile family), read for the names, functions, subunit statements, catalytic
   activities, cofactors, interaction partners and complexes of the entries found. A search by name matches loosely
   (found in the real run ``root_a101_a105_04``: "hypothetical protein" returned 25 unrelated proteins that carry those
   words in a synonym), so of a name search only the entries one of whose names is exactly the annotation's name (case
   apart) are read.
2. One model call reads the annotation, what was found and the rival annotations, and writes the list of claims: what
   the record states and whatever else it knows the annotation to mean, the claims that set this annotation apart from
   its rivals first. It also gives the name the literature uses for the protein.
3. A claim is written only when its molecule is found by lookup under the name given (a protein in UniProt by gene or
   protein name, a small molecule in ChEBI by name), so every name in a claim record is a looked-up name, never text a
   model wrote. The name the literature uses is taken the same way; when it is not found the annotation's own name
   stands. A claim that the protein binds itself (it forms oligomers) is a claim like any other: the molecule is then the
   looked-up protein of the same name, a record of its own beside the subject's (the first form of this workflow
   dropped such a claim, found in the real runs ``root_a101_a105_06`` and ``_09``: "binds PopZ" was proposed and lost).
   The list the model writes differs from run to run (four runs gave ParB with ChpT and ZitP; ParB, ChpT, CckA and
   PopZ; ParB, CckA, DivL and ChpT; ParB and PopZ), so the model is asked for every claim it knows of.

What is written, through the scoped store handed in: the sources of the lookups; when the annotation has a claim, one
``reference`` record for the subject under the annotation (the subject's own sequence, carrying the protein name of
the annotation, so that a head searches under that name and compares what it finds with the subject's sequence; its
accession is the subject's record reference); one ``reference`` record per admitted molecule; one ``hypothesis`` record
per claim; and one ``source`` record whose artifact holds everything the
workflow read, what the model answered, the subject and the claims written (the trace: an episode that holds it knows
which annotations it made claims for and what they are). Returned: the claims only.

A lookup that fails raises (a failed lookup is not an absent molecule). A protein subject is required."""
import json

from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.domain import canonical, identity

TOOL_NAME = 'make_claims'
PREDICATES = ('binds', 'catalyzes', 'transports')
PARTNER_KINDS = ('protein', 'chemical')
TRACE_PROVIDER = 'annotation_claims'
# The largest page the UniProt search of this project reads (as ``literature_subject_resolution.UNIPROT_NAME_RESULTS``).
UNIPROT_ROWS = 25
# One page of ChEBI's name search, at the size the project's ChEBI client asks by default.
CHEBI_ROWS = 10

INSTRUCTIONS = """You are given one candidate annotation of a protein, what a public protein database states about proteins of that annotation, and the rival annotations of the same protein.

`organism`, when it is given, is the organism the protein is from: a taxon of the NCBI taxonomy with its name, its rank and a score of how well it is supported. The database entries shown are then those of that organism, and the claims are about this protein in that organism: a capsid protein of one virus does not bind what the capsid protein of another binds. When `organism` is empty the organism is not known.

Write the claims this annotation makes that an experiment could check. Each claim says that the annotated protein does one of three things to one named molecule:
- `binds`: it binds that molecule (a specific protein, or a specific small molecule or ion);
- `catalyzes`: it catalyzes a reaction of that molecule (name one substrate or product);
- `transports`: it moves that molecule across a membrane.

Use what the database states and add what you know this annotation to mean beyond it. Write every such claim you know of, not a selection: each one is a separate thing an experiment can check, and a protein that binds copies of itself is one of them. Name each molecule by the one name a database would list it under: a gene or protein symbol for a protein (`partner_kind` `protein`), a compound name for a small molecule or ion (`partner_kind` `chemical`). Never name a class of molecules. Put first the claims that set this annotation apart from the rival annotations: what it would do and they would not.

An annotation that states no function (a hypothetical protein, a domain or family of unknown function) makes no claims: answer with an empty list.

`literature_name` is the short name under which the literature writes about this protein (its gene or protein symbol), or an empty text when the annotation gives none."""

OUTPUT_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['literature_name', 'claims'],
    'properties': {
        'literature_name': {'type': 'string'},
        'claims': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['predicate', 'partner_name', 'partner_kind'],
            'properties': {'predicate': {'type': 'string', 'enum': list(PREDICATES)},
                           'partner_name': {'type': 'string'},
                           'partner_kind': {'type': 'string', 'enum': list(PARTNER_KINDS)}}}}}}


def _quoted(text):
    return '"' + text.replace('"', ' ').strip() + '"'


def _same(first, second):
    return first.strip().casefold() == second.strip().casefold()


def _source(store, snapshot):
    """The record of one lookup: the response and the request, as the acquisition tools keep a provider request."""
    request = store.artifact(canonical({'request': snapshot.request, 'transport': snapshot.transport}), 'application/json')
    return store.put('source', {'provider': snapshot.service, 'accession': None, 'uri': snapshot.url,
                                'artifact_ref': store.artifact(snapshot.content, snapshot.media_type), 'text_ref': None,
                                'request_ref': request, 'version': None, 'retrieved_at': snapshot.retrieved_at},
                     origin='external')


def _uniprot(store, query):
    """One UniProt search: its source record and the entries found."""
    snapshot = PublicClients().uniprot_search(query, size=UNIPROT_ROWS)
    return _source(store, snapshot), json.loads(snapshot.content)['results']


def _protein_names(row):
    """The names UniProt gives one entry: its gene names and its protein names (full and short)."""
    names = []
    for gene in row.get('genes', ()):
        names.extend(part['value'] for part in (gene.get('geneName'), *gene.get('synonyms', ())) if part)
    description = row.get('proteinDescription', {})
    for entry in (description.get('recommendedName'), *description.get('submissionNames', ()),
                  *description.get('alternativeNames', ())):
        if entry:
            names.extend(part['value'] for part in (entry.get('fullName'), *entry.get('shortNames', ())) if part)
    return list(dict.fromkeys(names))


def _texts(row, comment_type):
    return [text['value'] for comment in row.get('comments', ()) if comment.get('commentType') == comment_type
            for text in comment.get('texts', ())]


def _unique(rows):
    return [json.loads(text) for text in dict.fromkeys(json.dumps(row, sort_keys=True) for row in rows)]


def stated(rows):
    """What the entries found state, each kind of statement once: read as data, nothing interpreted."""
    activities, cofactors, partners, complexes = [], [], [], []
    for row in rows:
        for comment in row.get('comments', ()):
            kind = comment.get('commentType')
            if kind == 'CATALYTIC ACTIVITY':
                reaction = comment['reaction']
                activities.append({'reaction': reaction['name'], **({'ec': reaction['ecNumber']}
                                                                    if 'ecNumber' in reaction else {})})
            elif kind == 'COFACTOR':
                cofactors.extend({'name': cofactor['name']} for cofactor in comment.get('cofactors', ()))
            elif kind == 'INTERACTION':
                for interaction in comment.get('interactions', ()):
                    for side in ('interactantOne', 'interactantTwo'):
                        partner = interaction[side]
                        if partner.get('uniProtKBAccession') != row['primaryAccession'] and 'geneName' in partner:
                            partners.append({'gene': partner['geneName']})
        complexes.extend({'complex': reference['id']} for reference in row.get('uniProtKBCrossReferences', ())
                         if reference['database'] == 'ComplexPortal')
    return {'entries_found': len(rows),
            'names': list(dict.fromkeys(name for row in rows for name in _protein_names(row))),
            'functions': list(dict.fromkeys(text for row in rows for text in _texts(row, 'FUNCTION'))),
            'subunit_statements': list(dict.fromkeys(text for row in rows for text in _texts(row, 'SUBUNIT'))),
            'catalytic_activities': _unique(activities), 'cofactors': _unique(cofactors),
            'interaction_partners': _unique(partners), 'complexes': _unique(complexes)}


def of_annotation(rows, annotation):
    """The entries a search found that are of the annotation: every entry of a profile family's cross-reference search;
    of a name search, the entries one of whose names is exactly the annotation's name (case apart)."""
    if annotation['vocabulary'] == 'profile_family':
        return rows
    return [row for row in rows if any(_same(name, annotation['name']) for name in _protein_names(row))]


def annotation_query(annotation, organism=None):
    """The UniProt search for one annotation: the entries cross-referenced to the Pfam family of a profile family
    (its accession without the version), else the entries of that protein name; within the taxon of ``organism`` (its
    NCBI taxon id: the taxon and everything below it) when the caller knows the organism. A name such as "capsid
    protein" is carried by the proteins of many unrelated organisms, and only the organism says which are meant."""
    if annotation['vocabulary'] == 'profile_family':
        query = '(xref:pfam-' + annotation['identifier'].split('.')[0] + ') AND (reviewed:true)'
    else:
        query = 'protein_name:' + _quoted(annotation['name'])
    return query if organism is None else '(' + query + ') AND (taxonomy_id:' + str(int(organism['taxon_id'])) + ')'


def find_protein(store, name):
    """A protein by its name: the UniProt entries whose gene or protein name is exactly ``name`` (case apart), the
    reviewed ones first. Returns ``(source record, entry, the name as UniProt spells it)`` or None when there is none."""
    source, rows = _uniprot(store, '(gene_exact:' + _quoted(name) + ') OR (protein_name:' + _quoted(name) + ')')
    for row in sorted(rows, key=lambda row: not row['entryType'].startswith('UniProtKB reviewed')):
        spelled = next((given for given in _protein_names(row) if _same(given, name)), None)
        if spelled is not None:
            return source, row, spelled
    return None


def find_chemical(store, name):
    """A small molecule by its name: the ChEBI entry whose name is exactly ``name`` (case apart). Returns ``(source
    record, accession, the name as ChEBI spells it)`` or None when there is none."""
    snapshot = PublicClients().chebi_search(name, size=CHEBI_ROWS)
    source = _source(store, snapshot)
    for hit in json.loads(snapshot.content)['results']:
        entry = hit['_source']
        if _same(entry['name'], name):
            accession = str(entry['chebi_accession'])
            return source, accession if accession.upper().startswith('CHEBI:') else 'CHEBI:' + accession, entry['name']
    return None


def admit(store, name, kind):
    """The ``reference`` record of a named molecule that was found by lookup, or None when it was not found."""
    if kind == 'protein':
        found = find_protein(store, name)
        if found is None:
            return None
        source, row, spelled = found
        sequence = row['sequence']['value']
        return store.put('reference', {
            'reference_type': 'protein', 'source_ref': source['id'], 'accession': row['primaryAccession'],
            'label': spelled, 'sequence_ref': store.artifact(sequence, 'text/plain'), 'molecule': 'protein',
            'length': len(sequence), 'term_refs': [], 'context_refs': []}, origin='external')
    found = find_chemical(store, name)
    if found is None:
        return None
    source, accession, spelled = found
    return store.put('reference', {
        'reference_type': 'chemical', 'source_ref': source['id'], 'accession': accession, 'label': spelled,
        'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []}, origin='external')


async def generate_claims(store, model, operation_key, *, annotation, rivals, subject_ref, organism=None):
    """The set workflow of the module text for one annotation of the subject ``subject_ref``. ``annotation`` is
    ``{'vocabulary', 'name'?, 'identifier'?}``; ``rivals`` the other candidate annotations in the same form;
    ``organism`` the organism the subject is from when the caller knows it (``{'taxon_id', 'name', 'rank_code',
    'score'}``: the leading candidate taxon and how well it is supported), else ``None``."""
    subject = store.get(subject_ref)
    if subject['molecule'] != 'protein':
        raise ValueError('annotation_claims_need_a_protein_subject:' + repr(subject['molecule']))
    written = []
    # 1. what the public record states
    source, rows = _uniprot(store, annotation_query(annotation, organism))
    written.append(source['id'])
    found = stated(of_annotation(rows, annotation))
    # 2. the claims, by one model call
    answer = await model.complete('REASONING', INSTRUCTIONS,
                                  {'annotation': annotation, 'organism': organism, 'database': found,
                                   'rival_annotations': rivals},
                                  OUTPUT_SCHEMA)
    # 3. only looked-up names are written
    label = annotation.get('name') or annotation['identifier']
    if answer['literature_name'].strip():
        named = find_protein(store, answer['literature_name'])
        if named is not None:
            written.append(named[0]['id'])
            label = named[2]
    admitted, seen, not_found = [], set(), 0
    for proposed in answer['claims']:
        partner = admit(store, proposed['partner_name'], proposed['partner_kind'])
        if partner is None:
            not_found += 1
        elif (proposed['predicate'], partner['id']) not in seen:
            seen.add((proposed['predicate'], partner['id']))
            admitted.append((proposed, partner))
    claims = []
    if admitted:
        under = store.put('reference', {
            'reference_type': 'protein', 'source_ref': source['id'], 'accession': subject_ref, 'label': label,
            'sequence_ref': subject['sequence_ref'], 'molecule': 'protein', 'length': store.subject_length(subject_ref),
            'term_refs': [], 'context_refs': []}, origin='tool')
        written.append(under['id'])
        for proposed, partner in admitted:
            claim = store.put('hypothesis', {'subject_refs': [under['id']], 'predicate': proposed['predicate'],
                                             'value': {'type': 'reference', 'ref': partner['id']},
                                             'context_refs': []}, origin='tool')
            written.extend([partner['source_ref'], partner['id'], claim['id']])
            claims.append({'claim_ref': claim['id'], 'predicate': proposed['predicate'], 'partner': partner['label'],
                           'partner_kind': proposed['partner_kind'],
                           'record_refs': [under['id'], partner['id'], claim['id']]})
    trace = store.artifact(canonical({'annotation': annotation, 'rival_annotations': rivals, 'database': found,
                                      'answer': answer, 'subject_name': label, 'not_found': not_found,
                                      'subject_ref': subject_ref, 'claims': claims}),
                           'application/json')
    written.append(store.put('source', {'provider': TRACE_PROVIDER, 'accession': None, 'uri': None,
                                        'artifact_ref': trace, 'text_ref': None, 'request_ref': None, 'version': None,
                                        'retrieved_at': None}, origin='tool')['id'])
    return {'status': 'completed',
            'operation_ref': identity('operation', {'key': operation_key, 'name': TOOL_NAME, 'arguments': annotation}),
            'record_refs': list(dict.fromkeys(written)), 'changed_record_refs': [],
            'result': {'subject_name': label, 'claims': claims, 'proposed': len(answer['claims']),
                       'not_found': not_found},
            'feedback': None}
