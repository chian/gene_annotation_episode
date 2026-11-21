"""A model of the target's structure from a sequence alone (A102 ``get_model``): three requests to outside services, each a
function that makes its requests, reads the replies and returns controlled values and the model's bytes.

* ``uniprot_accessions_by_sequence(sequence)``: the UniProtKB entries whose sequence is EXACTLY the target's (UniProt
  REST, ``checksum:<CRC64>``, then the sequence compared). It returns accessions and the two controlled facts UniProt
  ranks them by (reviewed, annotation score), never a protein name: the name of an identical entry is not structural
  evidence and does not pass through this path.
* ``alphafold_model(accession)``: the AlphaFold DB model of one UniProt entry (``/api/prediction/{accession}``, then the PDB
  file that reply advertises). The URL of the prediction and the check of the advertised file address are the existing pure
  functions of ``alphafold_acquisition`` (``alphafold_prediction_url``, ``_advertised_file_url``).
* ``esmfold_model(sequence)``: a predicted model of the sequence (ESM Atlas ``foldSequence/v1/pdb/``).

A source that does not hold the model answers ``{'status': 'not_found', ...}``; nothing is raised for it. Every other
failure (a transport error, an HTTP status the service should not give, a reply that is not of the documented form)
raises, and the unit fails with it: nothing here retries or repairs.

How outside HTTP is done in a unit: as A101's ``bvbrc_hit_metadata`` does it: one plain ``urllib`` request with a socket
timeout, no redirect followed, the spacing slept before a request that follows another of the same function; the
function's returned values are what the unit's receipt keeps (nothing is re-requested on replay). The existing
``PublicClients`` of the old A102 acquisition carries a source snapshot and an old-registry host and sends its own
User-Agent, which AlphaFold DB's front refuses for a command-line client; it is not used. No request carries a name, an
email, a key or a login.

The per-residue confidence of both models is the PDB B-factor column: AlphaFold DB writes pLDDT on 0 to 100; ESM Atlas
writes pLDDT on 0 to 1 and this module returns it on 0 to 100 (``ESMFOLD_PLDDT_SCALE``). pLDDT describes the model; it is
not similarity.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.protein_structure.alphafold_acquisition import (
    _advertised_file_url, alphafold_prediction_url)

# One browser-like User-Agent for every A102 request (AlphaFold DB answers 403 to ``curl``, verified 2026-11-21:
# docs/plan/designs/a102_services.md, 1b). It names no person, project or program.
BROWSER_USER_AGENT = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/124.0.0.0 Safari/537.36')
TRANSPORT_TIMEOUT_SECONDS = 120
REQUEST_SPACING_SECONDS = 3
UNIPROT_SEARCH_URL = 'https://rest.uniprot.org/uniprotkb/search'
UNIPROT_PAGE_SIZE = 500
ESMFOLD_URL = 'https://api.esmatlas.com/foldSequence/v1/pdb/'
# UNVERIFIED: the largest sequence the ESM Atlas fold API takes. The ESM repository README (read 2026-11-21) says that
# Foldseek "provides search against the Atlas without the length limitation", so the API has a limit, but no page reached
# gives its number (https://esmatlas.com/about#api is a script page). 400 is the figure remembered from that page; 353
# residues (RecA) was folded live on 2026-11-21, nothing longer was tried.
ESMFOLD_MAX_LENGTH = 400
# The service writes pLDDT on 0 to 1 in the B-factor column of its PDB text (0.40 for residue 1 of CspA, a102_services.md 2);
# the value returned here is that times this factor.
ESMFOLD_PLDDT_SCALE = 100.0
PROTEIN_ALPHABET = re.compile(r'[ACDEFGHIKLMNPQRSTVWY]+')
_NEXT_LINK = re.compile(r'<[^>]+>;\s*rel="next"')

_CRC64_POLY = 0xD800000000000000        # the ISO 3309 polynomial, reflected: UniProt's (SwissKnife) CRC64 of the sequence text


def _crc64_table():
    table = []
    for index in range(256):
        value = index
        for _ in range(8):
            value = (value >> 1) ^ _CRC64_POLY if value & 1 else value >> 1
        table.append(value)
    return table


_CRC64_TABLE = _crc64_table()


def uniprot_crc64(sequence):
    """UniProt's CRC64 checksum of a protein sequence: 16 upper-case hex digits."""
    value = 0
    for byte in sequence.encode('ascii'):
        value = _CRC64_TABLE[(value ^ byte) & 0xFF] ^ (value >> 8)
    return '%016X' % value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _request(method, url, *, body=None, content_type=None):
    """One request: ``{'status', 'body', 'headers'}`` whatever the HTTP status; a transport failure raises."""
    headers = {'User-Agent': BROWSER_USER_AGENT, 'Accept': '*/*'}
    if content_type is not None:
        headers['Content-Type'] = content_type
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=TRANSPORT_TIMEOUT_SECONDS) as response:
            return {'status': response.status, 'body': response.read(), 'headers': response.headers}
    except urllib.error.HTTPError as error:
        return {'status': error.code, 'body': error.read(), 'headers': error.headers}


def _refused(service, reply):
    return RuntimeError('model_source_http_' + str(reply['status']) + ':' + service)


def _protein(sequence):
    if type(sequence) is not str or PROTEIN_ALPHABET.fullmatch(sequence) is None:
        raise ValueError('target_sequence_must_be_upper_case_standard_amino_acids')
    return sequence


def uniprot_accessions_by_sequence(sequence):
    """The UniProtKB entries whose sequence equals ``sequence`` exactly, reviewed first, then by annotation score
    (highest first), then by accession: ``{'status': 'found'|'not_found', 'crc64', 'accessions': [{'accession',
    'reviewed' (bool), 'annotation_score' (number)}], 'truncated' (bool: UniProt had more rows than one page of
    ``UNIPROT_PAGE_SIZE``), 'rows_seen', 'collisions' (rows of the checksum whose sequence differs)}``. No name."""
    _protein(sequence)
    crc = uniprot_crc64(sequence)
    query = urllib.parse.urlencode({'query': 'checksum:' + crc, 'format': 'json', 'size': UNIPROT_PAGE_SIZE,
                                    'fields': 'accession,reviewed,annotation_score,length,sequence'})
    reply = _request('GET', UNIPROT_SEARCH_URL + '?' + query)
    if reply['status'] != 200:
        raise _refused('uniprot', reply)
    rows = json.loads(reply['body'])['results']
    exact = [row for row in rows if row['sequence']['value'] == sequence and row['sequence']['length'] == len(sequence)]
    found = sorted(({'accession': row['primaryAccession'], 'reviewed': row['entryType'].startswith('UniProtKB reviewed'),
                     'annotation_score': row['annotationScore']} for row in exact),
                   key=lambda item: (not item['reviewed'], -item['annotation_score'], item['accession']))
    return {'status': 'found' if found else 'not_found', 'crc64': crc, 'accessions': found,
            'truncated': _NEXT_LINK.search(reply['headers'].get('Link', '')) is not None, 'rows_seen': len(rows),
            'collisions': len(rows) - len(exact)}


def pdb_ca_confidence(pdb_bytes):
    """``[(residue number, B-factor)]`` of the C-alpha atoms of a PDB text, in file order, one per residue (the first
    alternate location only is not distinguished: both models have none)."""
    seen, rows = set(), []
    for line in pdb_bytes.decode('ascii').splitlines():
        if line.startswith('ATOM') and line[12:16].strip() == 'CA':
            key = (line[21], int(line[22:26]), line[26])
            if key in seen:
                raise ValueError('pdb_model_has_a_residue_twice:' + repr(key))
            seen.add(key)
            rows.append((int(line[22:26]), float(line[60:66])))
    if not rows:
        raise ValueError('pdb_model_has_no_c_alpha_atoms')
    return rows


def _confidence(pdb_bytes, scale):
    rows = pdb_ca_confidence(pdb_bytes)
    values = [round(value * scale, 2) for _, value in rows]
    return {'residue_start': rows[0][0], 'residue_end': rows[-1][0], 'residue_count': len(rows),
            'plddt_per_residue': values, 'plddt_mean': round(sum(values) / len(values), 2)}


def alphafold_model(accession):
    """The AlphaFold DB model of the UniProt entry ``accession``: ``{'status': 'found'|'not_found', 'accession',
    'entry_id', 'model_version', 'sequence' (the model's), 'residue_start', 'residue_end', 'residue_count',
    'plddt_mean' (0 to 100, from the file's per-residue values), 'plddt_reported' (the service's global figure),
    'plddt_per_residue', 'model_url', 'model_bytes' (PDB text)}``. An accession AlphaFold DB has no model for (HTTP 404)
    is ``{'status': 'not_found', 'accession'}``."""
    url = alphafold_prediction_url(accession)
    reply = _request('GET', url)
    if reply['status'] == 404:
        return {'status': 'not_found', 'accession': accession}
    if reply['status'] != 200:
        raise _refused('alphafold_prediction', reply)
    predictions = json.loads(reply['body'])
    if type(predictions) is not list or len(predictions) != 1 or predictions[0]['uniprotAccession'] != accession:
        raise ValueError('alphafold_prediction_reply_is_not_one_entry_of_the_accession')
    entry = predictions[0]
    model_url = _advertised_file_url(entry['pdbUrl'], 'pdb_3x_text')
    time.sleep(REQUEST_SPACING_SECONDS)
    file_reply = _request('GET', model_url)
    if file_reply['status'] != 200:
        raise _refused('alphafold_file', file_reply)
    facts = _confidence(file_reply['body'], 1.0)
    if facts['residue_count'] != len(entry['sequence']):
        raise ValueError('alphafold_model_residues_differ_from_its_sequence')
    return {'status': 'found', 'accession': accession, 'entry_id': entry['entryId'],
            'model_version': entry['latestVersion'], 'sequence': entry['sequence'], **facts,
            'plddt_reported': entry['globalMetricValue'], 'model_url': model_url, 'model_bytes': file_reply['body']}


def esmfold_model(sequence):
    """A predicted model of ``sequence`` (ESM Atlas): ``{'status': 'found', 'sequence', 'residue_start', 'residue_end',
    'residue_count', 'plddt_mean' (0 to 100: the service's 0 to 1 times ``ESMFOLD_PLDDT_SCALE``), 'plddt_per_residue',
    'model_bytes' (PDB text)}``. A sequence longer than ``ESMFOLD_MAX_LENGTH`` is refused with ``ValueError`` (a tool's
    check does not offer it)."""
    _protein(sequence)
    if len(sequence) > ESMFOLD_MAX_LENGTH:
        raise ValueError('esmfold_sequence_longer_than_the_limit:' + str(ESMFOLD_MAX_LENGTH))
    reply = _request('POST', ESMFOLD_URL, body=sequence.encode('ascii'),
                     content_type='application/x-www-form-urlencoded')
    if reply['status'] != 200:
        raise _refused('esmfold', reply)
    facts = _confidence(reply['body'], ESMFOLD_PLDDT_SCALE)
    if facts['residue_count'] != len(sequence):
        raise ValueError('esmfold_model_residues_differ_from_the_sequence')
    return {'status': 'found', 'sequence': sequence, **facts, 'model_bytes': reply['body']}


__all__ = ['BROWSER_USER_AGENT', 'ESMFOLD_MAX_LENGTH', 'ESMFOLD_PLDDT_SCALE', 'alphafold_model', 'esmfold_model',
           'pdb_ca_confidence', 'uniprot_accessions_by_sequence', 'uniprot_crc64']
