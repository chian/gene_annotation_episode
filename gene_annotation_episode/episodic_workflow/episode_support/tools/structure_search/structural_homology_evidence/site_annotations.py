"""The two sources of the residue-level functional sites of a protein, for A102's ``site_correspondence``: UniProt's site
features (``annotated``) and the M-CSA catalytic residues (``catalytic``). Each function takes accessions and returns, per
accession, rows of one shape (``feature_row``) and the replies of the service, with the request, status and checksum of each
(kept as the data product ``functional_site_annotations``). Outside HTTP is done as ``uniprot_hit_names`` does it: the same
``target_model_sources._request`` (one ``urllib`` request, no redirect followed, a socket timeout, the browser-like
User-Agent, no name, email or key) and the same spacing between two UniProt requests.

``annotated``. ``GET https://rest.uniprot.org/uniprotkb/search?query=accession:A OR accession:B OR ...&size=<n>&format=json&
fields=accession,ft_act_site,ft_binding,ft_site``, in batches of ``BATCH`` (100) accessions (verified live 2026-11-21: HTTP 200,
P00918 returned Active site 64, Binding sites 94, 96, 119 (ligand ``ChEBI:CHEBI:29105``, Zn(2+)) and 198-199 (ligand
``substrate``, no ChEBI id), Sites 7, 62, 67, 92; P0A7G6 (RecA) Binding site 67-74, ligand ATP ``ChEBI:CHEBI:30616``; P0A9X9
(CspA) no feature; every feature has ``location.start/end.value`` with ``modifier`` ``EXACT``, optional ``ligand.id`` and
``evidences[].evidenceCode``). The survey found ``ft_metal``, ``ft_np_bind`` and ``ft_ca_bind`` invalid (HTTP 400): metal and
nucleotide sites are ``Binding site`` features of ``ft_binding``. Only the three residue-level types are asked for: the region
types (DNA_BIND, ZN_FING, MOTIF, REGION) are not sites of this test. A feature range is one required residue per position.

``catalytic``. ``GET https://www.ebi.ac.uk/thornton-srv/m-csa/api/residues/?format=json``: ONE request returns every residue
of the M-CSA catalogue (5,248 residues, 5.9 MB, 4 s on 2026-11-21), each with ``residue_sequences``: ``{uniprot_id, code (three
letters), resid, is_reference}``. ``resid`` is the 1-based position in the UniProt sequence of the M-CSA reference entry
(verified 2026-11-21 against the UniProt sequences of P00918 (carbonic anhydrase 2: His64, His94, His96, Glu106, His119,
Thr198) and P00720 (T4 lysozyme: Glu11, Asp20): the letter at ``resid`` is the three-letter ``code`` in all eight). The
filtered form ``entries/?entries.proteins.sequences.uniprot_ids=<id>`` gives the same residues for one accession, but with
several accessions in one request it returned the entries WITHOUT ``residue_sequences`` and ``is_reference_uniprot_id``
false (checked on P00918, P00720, P00915), so the filter cannot be batched; the catalogue request does not depend on the
number of hits. An accession is a source of catalytic sites only when it is the ``uniprot_id`` of a ``residue_sequences``
entry with ``is_reference`` true: M-CSA's homologue lists are not used (an accession that is not an M-CSA reference entry
has no catalytic sites from this source).

A service that does not answer 200, or whose reply is not of the documented form, is a failure of the whole fetch (a hit
whose sites were not asked is unknown, not siteless)."""
import hashlib
import json
import time
import urllib.parse

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.protein_structure.target_model_sources import (
    _request)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.uniprot_hit_names import (
    BATCH, SPACING_SECONDS, SEARCH_URL as UNIPROT_URL)

SITE_SOURCES = ('annotated', 'catalytic')
UNIPROT_FIELDS = 'accession,ft_act_site,ft_binding,ft_site'
MCSA_URL = 'https://www.ebi.ac.uk/thornton-srv/m-csa/api/residues/?format=json'
# UniProt feature type text of the reply -> the feature type kept
UNIPROT_TYPES = {'Active site': 'ACT_SITE', 'Binding site': 'BINDING', 'Site': 'SITE'}
FEATURE_TYPES = ('ACT_SITE', 'BINDING', 'SITE', 'CATALYTIC')
THREE_LETTER = {'Ala': 'A', 'Arg': 'R', 'Asn': 'N', 'Asp': 'D', 'Cys': 'C', 'Gln': 'Q', 'Glu': 'E', 'Gly': 'G', 'His': 'H',
                'Ile': 'I', 'Leu': 'L', 'Lys': 'K', 'Met': 'M', 'Phe': 'F', 'Pro': 'P', 'Ser': 'S', 'Thr': 'T', 'Trp': 'W',
                'Tyr': 'Y', 'Val': 'V', 'Sec': 'U'}


def feature_row(*, type, start, end, ligand_chebi, evidence, residue):
    """One site feature in the shape the grader reads: ``type`` (``FEATURE_TYPES``), the 1-based ``start`` and ``end`` (equal for
    one residue; ``None`` both when the position is not exact), the ChEBI id of the ligand (``CHEBI:<n>``) or ``None``, the
    sorted distinct evidence codes (ECO ids; empty for M-CSA) and ``residue`` (the one-letter residue the source states at
    the position: M-CSA only, else ``None``)."""
    return {'type': type, 'start': start, 'end': end, 'ligand_chebi': ligand_chebi, 'evidence': evidence, 'residue': residue}


def _failure(code):
    return {'failure': code, 'sites': {}, 'replies': [], 'not_returned': []}


def _reply(request, url, reply, body):
    return {'request': request, 'url': url, 'status': reply['status'],
            'sha256': hashlib.sha256(reply['body']).hexdigest(), 'bytes': len(reply['body']),
            'media_type': reply['headers'].get('Content-Type', 'application/json'), 'body': body}


def _chebi(ligand):
    """``CHEBI:<n>`` of a UniProt ligand (``{'name', 'id': 'ChEBI:CHEBI:<n>'}``), or ``None`` when it has no id."""
    if ligand is None or 'id' not in ligand:
        return None
    identifier = ligand['id']
    if not identifier.startswith('ChEBI:CHEBI:'):
        raise ValueError('uniprot_ligand_id_is_not_chebi:' + identifier)
    return identifier[len('ChEBI:'):]


def uniprot_feature(feature):
    """The ``feature_row`` of one UniProt JSON feature. A type that was not asked for raises; a position that is not exact
    (``modifier`` other than ``EXACT``) gives ``start`` and ``end`` ``None``."""
    if feature['type'] not in UNIPROT_TYPES:
        raise ValueError('uniprot_feature_type_not_asked:' + feature['type'])
    start, end = feature['location']['start'], feature['location']['end']
    exact = start['modifier'] == 'EXACT' and end['modifier'] == 'EXACT'
    return feature_row(type=UNIPROT_TYPES[feature['type']], start=start['value'] if exact else None,
                       end=end['value'] if exact else None, ligand_chebi=_chebi(feature.get('ligand')),
                       evidence=sorted({item['evidenceCode'] for item in feature.get('evidences', ())}), residue=None)


def annotated_sites(accessions):
    """The residue-level UniProt features of ``accessions`` (batches of ``BATCH``, one request each, ``SPACING_SECONDS`` between
    two requests). Returns ``{'failure': None, 'sites': {accession: [feature_row]}, 'replies': [...], 'not_returned': [accessions
    UniProt did not return]}`` or ``{'failure': code, ...}`` (``uniprot_http_<status>``, ``uniprot_request_failed:<type>``,
    ``uniprot_reply_invalid``). An entry is matched to the accession asked by its primary or a secondary accession; an entry
    with no feature has an empty list."""
    accessions = list(dict.fromkeys(accessions))
    sites, replies = {}, []
    for start in range(0, len(accessions), BATCH):
        part = accessions[start:start + BATCH]
        if start:
            time.sleep(SPACING_SECONDS)
        params = {'query': ' OR '.join('accession:' + accession for accession in part), 'size': len(part),
                  'format': 'json', 'fields': UNIPROT_FIELDS}
        url = UNIPROT_URL + '?' + urllib.parse.urlencode(params)
        try:
            reply = _request('GET', url)
        except OSError as error:
            return _failure('uniprot_request_failed:' + type(error).__name__)
        if reply['status'] != 200:
            return _failure('uniprot_http_' + str(reply['status']))
        try:
            body = json.loads(reply['body'])
            asked = set(part)
            for entry in body['results']:
                rows = [uniprot_feature(feature) for feature in entry.get('features', ())]
                for accession in [entry['primaryAccession'], *entry.get('secondaryAccessions', ())]:
                    if accession in asked:
                        sites[accession] = rows
        except (KeyError, TypeError, ValueError):
            return _failure('uniprot_reply_invalid')
        replies.append(_reply(params, url, reply, body))
    return {'failure': None, 'sites': sites, 'replies': replies,
            'not_returned': [accession for accession in accessions if accession not in sites]}


def catalytic_sites(accessions):
    """The M-CSA catalytic residues of ``accessions`` from the one catalogue request (see the module): per accession that is the
    ``uniprot_id`` of a reference ``residue_sequences`` entry, a ``feature_row`` of type ``CATALYTIC`` per residue (the position
    in UniProt numbering, the residue letter M-CSA states, no ligand, no evidence code). An accession with none has an empty
    list. The reply kept is the rows of the asked accessions (``body``: ``[{'mcsa_id', 'uniprot_id', 'code', 'resid'}]``) with
    the checksum and size of the whole reply. Returns the shape of ``annotated_sites`` (``failure`` codes ``mcsa_http_<status>``,
    ``mcsa_request_failed:<type>``, ``mcsa_reply_invalid``)."""
    accessions = list(dict.fromkeys(accessions))
    try:
        reply = _request('GET', MCSA_URL)
    except OSError as error:
        return _failure('mcsa_request_failed:' + type(error).__name__)
    if reply['status'] != 200:
        return _failure('mcsa_http_' + str(reply['status']))
    asked = set(accessions)
    sites = {accession: [] for accession in accessions}
    rows = []
    try:
        for residue in json.loads(reply['body']):
            for entry in residue['residue_sequences']:
                if entry['is_reference'] and entry['uniprot_id'] in asked:
                    letter = THREE_LETTER[entry['code']]
                    rows.append({'mcsa_id': residue['mcsa_id'], 'uniprot_id': entry['uniprot_id'], 'code': entry['code'],
                                 'resid': entry['resid']})
                    sites[entry['uniprot_id']].append(feature_row(
                        type='CATALYTIC', start=entry['resid'], end=entry['resid'], ligand_chebi=None, evidence=[],
                        residue=letter))
    except (KeyError, TypeError, ValueError):
        return _failure('mcsa_reply_invalid')
    return {'failure': None, 'sites': sites, 'replies': [_reply({'catalogue': 'residues'}, MCSA_URL, reply, rows)],
            'not_returned': []}


def site_annotations(site_source, accessions):
    """``annotated_sites`` or ``catalytic_sites`` of ``accessions`` by ``site_source``."""
    return {'annotated': annotated_sites, 'catalytic': catalytic_sites}[site_source](accessions)


__all__ = ['BATCH', 'FEATURE_TYPES', 'MCSA_URL', 'SITE_SOURCES', 'UNIPROT_FIELDS', 'annotated_sites', 'catalytic_sites',
           'feature_row', 'site_annotations', 'uniprot_feature']
