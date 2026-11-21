"""A102's one-shot tool ``partner_contacts`` (rows P2 with ligand contacts, and P4): what the solved structures that match the
target show bound to their protein, and whether the target has those contact residues in place (SOP Step 3: the model fills out
one JSON, ONE deterministic check, ONE function that runs and grades the unit).

Why: the fold search cannot tell what a matching protein does with a partner; a solved structure shows it (a methionine-bound
homolog localizes a different side-chain pocket; an arginine-bound comparator and modeled contact differences explain
recognition; CspA binds nucleic acid and has no annotated site in UniProt, but its relatives are solved with DNA and RNA).

THE REQUEST (controlled fields): ``search_ref`` (the reference of a held graded structure search of the database ``pdb100``:
the source of provider ``foldseek_search`` that ``foldseek_search.extract`` made) and ``resource_id`` (a bound local resource:
the one job per batch runs there). ``check_partner_contacts_request`` is the one check. It refuses, with the fix list (one entry
per problem: the field, a code and what to choose from): a ``search_ref`` that is not a held graded search
(``search_is_not_a_held_graded_search``); a search of a database other than ``pdb100`` (``search_database_is_not_pdb100``: only
solved structures show bound partners); a search whose raw result, sheet, hit-metadata product or model the caller does not hold
(``search_result_sheet_metadata_or_model_not_held``); a search already analysed (``search_already_analysed``); a resource that is
not a bound local one; the missing programs. A request that passes it simply works.

THE UNIT. The asked hits are the search's hits that are not a control and have a B (``partner_contacts_sheet.asked_rows``), taken
in RANK order of the sheet's B, one solved ENTRY FILE at a time (an entry with several hit chains is fetched once; the file is
the biological assembly the hit names, ``<id>-assembly<N>``), in batches of ``BATCH`` files. The rule that stops the
unit is the settling rule of ``uniprot_hit_names.name_hits``, applied to the candidates of BOTH tests: after each batch the
candidate picture of the hits done (both tests; ``partner_contacts_sheet.picture_rows`` through ``differential_credit``) is
recomputed; the unit stops when a batch, against the picture before it, admits no new candidate in either test and moves no
candidate's value by more than ``SETTLE`` (0.01), or when every file is done. The first batch has no picture before it, so a
second batch is always asked for when files remain. A hit whose file was never asked is ``not_asked`` (its partners are unknown,
not absent). Per batch: the files are fetched (``fetch_assembly``: an entry larger than ``MAX_BYTES`` is recorded ``too_large``
and not asked; at most two requests a second; no name, email or key), read (Biopython ``MMCIFParser`` and ``NeighborSearch``;
``read_assembly``), the target is aligned with every hit chain of the batch by US-align in ONE local job
(``execute_on_local_resource`` running ``usalign_driver`` over a plan of pairs), the hit chains are graded
(``partner_contacts_sheet``) and the picture is recomputed.

WHAT IS KEPT through custody, labelled as data products: every fetched file (``experimental_structure``), the alignments of every
job (``pairwise_structure_alignments``), the two retained gradings (``tool_grading_sheet``): the contacts sheet, source provider
``partner_contacts`` (test ``site_correspondence:partner_contacts@<source>``) and the partner sheet, source provider
``bound_partner`` (test ``bound_partner:pdb100@<source>``). Writes only through ``ctx.store``.

What exists and is called: ``site_correspondence.search_inputs`` (the held searches), ``foldseek_search`` (``model_positions``,
``target_sequence``, the product kinds), ``uniprot_hit_names.SETTLE``, ``differential_credit``, ``tool_grading_artifacts``,
``data_products``, ``resource_local.execute_on_local_resource``, ``target_model_sources`` (the User-Agent and the timeout)."""
import hashlib
import inspect
import io
import json
import os
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path

from Bio.PDB import MMCIFParser, NeighborSearch
from Bio.PDB.MMCIF2Dict import MMCIF2Dict

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.protein_structure.target_model_sources import (
    BROWSER_USER_AGENT, TRANSPORT_TIMEOUT_SECONDS)
from gene_annotation_episode.episodic_workflow.episode_support.forms import structural_homology_evidence as _forms
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence import partner_contacts_sheet as sheets
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.differential_credit import (
    differential_credit)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import (
    record_grading_product, retain_tool_grading, source_tool_grading_entries)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.resource_local import execute_on_local_resource
from gene_annotation_episode.episodic_workflow.episode_support.readers.protein_structure.foldseek_result import (
    parse_foldseek_result, pdb_target)
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products, record_product
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence import (
    foldseek_search, site_correspondence, usalign_driver)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.uniprot_hit_names import (
    SETTLE)

PROVIDER = sheets.CONTACTS_PROVIDER
PARTNERS_PROVIDER = sheets.PARTNERS_PROVIDER
STRUCTURE_KIND = 'experimental_structure'
ALIGNMENTS_KIND = 'pairwise_structure_alignments'
REQUEST_FIELDS = ('search_ref', 'resource_id')
DATABASE = 'pdb100'
FILE_ROOT = 'https://files.rcsb.org/download/'
BATCH = 10
# At most two requests a second to the file service (no spacing is required for file downloads).
SPACING_SECONDS = 0.5
# The largest download of one assembly file, in bytes of the transfer (the gzip file the Foldseek database was built from,
# ``<id>-assembly<N>.cif.gz``): the machine bound of the unit (one CPU, 5 GiB of memory: a file this large unpacks to some
# 60 to 80 MB of text, about 250 thousand atoms, which Biopython holds in about 1.5 GiB). An entry over it is recorded
# ``too_large``, not asked. The same style as ``max_bytes`` of ``rcsb_acquisition``.
MAX_BYTES = 8 * 1024 * 1024
# The largest unpacked size: the same bound on what the transfer unpacks to (a gzip file can unpack to many times its size).
MAX_UNPACKED_BYTES = 128 * 1024 * 1024
# Every row of ``_atom_site`` of an assembly file has 26 columns, separated by single spaces: at least 52 bytes. So a file
# that unpacks to at most ``MAX_UNPACKED_BYTES`` has at most this many atom rows, and so at most this many molecules.
MIN_ATOM_ROW_BYTES = 52
MAX_ATOMS_PER_FILE = MAX_UNPACKED_BYTES // MIN_ATOM_ROW_BYTES
TARGET_FILE, PLAN_FILE, DRIVER_FILE = 'target.pdb', 'plan.json', 'driver.py'
DRIVER_SOURCE = Path(inspect.getsourcefile(usalign_driver)).read_bytes()
OWN_FAILURE_CODES = ('job_not_accepted', 'job_not_fetched', 'driver_exit_nonzero', 'alignment_report_missing', 'grading_refused')
WATERS = ('HOH', 'DOD')
NUCLEIC = {'polydeoxyribonucleotide': 'dna', 'polyribonucleotide': 'rna'}
HYBRID = 'polydeoxyribonucleotide/polyribonucleotide hybrid'
PROTEIN = ('polypeptide(L)', 'polypeptide(D)')
DNA_RESIDUES = ('DA', 'DC', 'DG', 'DT', 'DU', 'DI')
LONGEST_CHAIN = 9999


# -- the additive list (BioLiP's published list of ligands that are not biologically relevant) -------------------------------
def load_additive_list():
    """``({component id: name}, facts)`` of the retained copy of BioLiP's ``ligand_list`` (``forms/structural_homology_evidence/
    biolip_ligand_list``: its url, the date it was retrieved, its sha256 and the number of rows)."""
    folder = Path(_forms.__file__).parent / 'biolip_ligand_list'
    data = (folder / 'ligand_list.tsv').read_bytes()
    retrieval = json.loads((folder / 'retrieval.json').read_text())
    if hashlib.sha256(data).hexdigest() != retrieval['sha256']:
        raise ValueError('biolip_ligand_list_differs_from_its_retrieval_record')
    names = dict(line.split('\t', 1) for line in data.decode().splitlines())
    return names, {'url': retrieval['url'], 'retrieved': retrieval['retrieved'], 'sha256': retrieval['sha256'], 'count': len(names)}


ADDITIVES, ADDITIVE_FACTS = load_additive_list()


# -- the check ------------------------------------------------------------------------------------------------------------
def _choose(field, code, **detail):
    return {'field': field, 'code': code, **detail}


def partner_search_inputs(reader):
    """``site_correspondence.search_inputs`` with, per search, ``metadata_ref`` (the held ``search_hit_metadata`` product made
    from its result, or ``None``) and ``metadata_held``."""
    held = site_correspondence.search_inputs(reader)
    metadata = {tuple(row['used']): row for row in products(reader, foldseek_search.METADATA_KIND)}
    for search in held.values():
        row = metadata.get((search['result_ref'],))
        search['metadata_ref'] = None if row is None else row['artifact_ref']
        search['metadata_held'] = row is not None and reader.holds(row['artifact_ref'])
    return held


def _programs(directory, names):
    return [{'code': 'program_missing', 'field': 'settings', 'detail': name} for name in names
            if not os.access(Path(directory) / name, os.X_OK)]


def check_partner_contacts_request(request, *, searches, analysed, resources, usalign_directory, python):
    """The things to fix in a ``partner_contacts`` request, before anything runs; an empty list means it can run.

    ``request`` holds ``search_ref`` and ``resource_id``. ``searches`` is ``partner_search_inputs``; ``analysed`` the search
    source references already analysed (``candidate_measurements.held_partner_analyses``); ``resources`` ``{resource id: kind}``."""
    search, resource = request['search_ref'], request['resource_id']
    problems = []
    usable = [reference for reference, held in searches.items() if held['row']['database'] == DATABASE
              and held['result_held'] and held['model_held'] and held['metadata_held'] and reference not in analysed]
    if search not in searches:
        problems.append(_choose('search_ref', 'search_is_not_a_held_graded_search', choose_from=usable))
    elif searches[search]['row']['database'] != DATABASE:
        problems.append(_choose('search_ref', 'search_database_is_not_pdb100', choose_from=usable))
    elif not (searches[search]['result_held'] and searches[search]['model_held'] and searches[search]['metadata_held']):
        problems.append(_choose('search_ref', 'search_result_sheet_metadata_or_model_not_held', choose_from=usable))
    elif search in analysed:
        problems.append(_choose('search_ref', 'search_already_analysed', choose_from=usable))
    if resource not in resources:
        problems.append(_choose('resource_id', 'resource_not_bound', choose_from=[name for name, kind in resources.items() if kind == 'local']))
    elif resources[resource] != 'local':
        problems.append(_choose('resource_id', 'resource_not_local', choose_from=[name for name, kind in resources.items() if kind == 'local']))
    problems.extend(_programs(usalign_directory, ('USalign',)))
    if not os.access(python, os.X_OK):
        problems.append({'code': 'python_missing', 'field': 'settings'})
    return problems


# -- the files ------------------------------------------------------------------------------------------------------------
def file_url(entry, assembly):
    """The file the hit names: ``https://files.rcsb.org/download/<ID>-assembly<N>.cif.gz`` (upper case id)."""
    return FILE_ROOT + entry + '-assembly' + str(assembly) + '.cif.gz'


def fetch_assembly(entry, assembly):
    """One download of an assembly file: ``{'status', 'url', 'download_bytes', 'download_sha256', 'text' (the unpacked mmCIF
    bytes), 'reason'}``. Status ``ok``; ``too_large`` (the transfer is longer than ``MAX_BYTES``, known from the length the
    service states or from the bytes read, or the unpacked file is longer than ``MAX_UNPACKED_BYTES``); ``not_obtained`` (HTTP
    status other than 200, a transport failure, or a file that does not unpack: the reason names it). No redirect is followed."""
    url = file_url(entry, assembly)
    time.sleep(SPACING_SECONDS)
    out = {'status': 'not_obtained', 'url': url, 'download_bytes': None, 'download_sha256': None, 'text': None, 'reason': None}
    request = urllib.request.Request(url, headers={'User-Agent': BROWSER_USER_AGENT, 'Accept': '*/*'})
    try:
        with urllib.request.urlopen(request, timeout=TRANSPORT_TIMEOUT_SECONDS) as response:
            stated = response.headers.get('Content-Length')
            if stated is not None and int(stated) > MAX_BYTES:
                return {**out, 'status': 'too_large', 'download_bytes': int(stated)}
            data = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        return {**out, 'reason': 'rcsb_files_http_' + str(error.code)}
    except OSError as error:
        return {**out, 'reason': 'rcsb_files_request_failed:' + type(error).__name__}
    if len(data) > MAX_BYTES:
        return {**out, 'status': 'too_large', 'download_bytes': len(data)}
    out.update(download_bytes=len(data), download_sha256=hashlib.sha256(data).hexdigest())
    try:
        unpacker = zlib.decompressobj(16 + zlib.MAX_WBITS)
        text = unpacker.decompress(data, MAX_UNPACKED_BYTES + 1)
    except zlib.error:
        return {**out, 'reason': 'rcsb_files_not_gzip'}
    if len(text) > MAX_UNPACKED_BYTES:
        return {**out, 'status': 'too_large'}
    return {**out, 'status': 'ok', 'text': text}


def _rows(table, prefix, fields):
    """The rows of a loop of an mmCIF dictionary as dicts (a single-row loop gives text, not a list)."""
    columns = [table.get(prefix + '.' + field, []) for field in fields]
    columns = [[column] if isinstance(column, str) else column for column in columns]
    return [dict(zip(fields, row)) for row in zip(*columns)]


def _letter(name):
    return foldseek_search.RESIDUES.get(name, 'X')


def _nucleic_kind(polymer_type, names):
    """``dna`` or ``rna`` (or ``other_polymer``) of a polymer chain: from the entity's polymer type; a hybrid chain by the
    majority of its residue names."""
    if polymer_type in NUCLEIC:
        return NUCLEIC[polymer_type]
    if polymer_type == HYBRID:
        dna = sum(name in DNA_RESIDUES for name in names)
        return 'dna' if dna * 2 > len(names) else 'rna'
    return 'other_polymer'


def read_assembly(text, wanted):
    """What one assembly file (the mmCIF text, bytes) shows about the hit chains ``wanted`` (``{rank: {'chain_label': the author
    chain id as Foldseek writes it, 'entity_id': the entity RCSB gives it or ``None``}}``): ``{'chains': {rank: chain
    facts}, 'chain_files': {rank: PDB text of the chain's C-alpha atoms}}``.

    The molecules are the label asym ids (``MMCIFParser(auth_chains=False)``): every polymer chain and every ligand instance is
    one molecule, which the author chain id does not tell apart (a ligand carries the author id of its protein chain). The hit
    chain is the polymer asym id whose AUTHOR chain id is the Foldseek label (a symmetry copy ``A-2`` has that label as its
    author id too). Chain facts: ``status`` (``parsed``, ``chain_not_found``, ``chain_ambiguous``, ``chain_not_protein``,
    ``chain_entity_differs_from_rcsb``, ``chain_too_long_for_pdb_format``, ``chain_has_no_c_alpha``), ``residues`` ({ordinal:
    ``auth_seq_id``, ``insertion_code``, ``resname``, ``letter``, ``ca``}: the chain's residues that have a C-alpha, numbered 1..n in file
    order, the numbering of the chain file), ``partners`` (per key: ``kind`` (``ligand``, ``dna``, ``rna``), ``identifier``,
    ``additive``, ``additive_status``, ``instance_count``, ``ordinals``: the hit residues within ``CONTACT_A`` of a heavy
    atom of any molecule of the key), ``protein_partners`` (other protein chains and other polymers in contact: ``kind``,
    ``chain`` (the author id), ``asym_id``, ``same_entity``, ``contact_residue_count``: facts only) and ``dropped`` (contact
    residues with no C-alpha)."""
    mm = MMCIF2Dict(io.StringIO(text.decode('ascii')))
    structure = MMCIFParser(auth_residues=True, auth_chains=False, QUIET=True).get_structure('assembly', io.StringIO(text.decode('ascii')))
    model = structure[0]
    entity_of = {row['id']: row['entity_id'] for row in _rows(mm, '_struct_asym', ('id', 'entity_id'))}
    poly_type = {row['entity_id']: row['type'] for row in _rows(mm, '_entity_poly', ('entity_id', 'type'))}
    author_of = {}
    for asym, author in zip(mm['_atom_site.label_asym_id'], mm['_atom_site.auth_asym_id']):
        author_of.setdefault(asym, author)
    molecules = {}
    for chain in model:
        entity = entity_of[chain.id]
        if entity in poly_type:
            residues = [residue.get_resname() for residue in chain]
            kind = 'protein' if poly_type[entity] in PROTEIN else _nucleic_kind(poly_type[entity], residues)
            molecules[chain.id] = {'polymer': True, 'kind': kind, 'entity': entity, 'author': author_of[chain.id]}
        else:
            molecules[chain.id] = {'polymer': False, 'kind': 'ligand', 'entity': entity, 'author': author_of[chain.id]}
    heavy = [atom for atom in model.get_atoms()
             if (atom.element or '').upper() not in ('H', 'D') and atom.get_parent().get_resname() not in WATERS
             and atom.get_parent().id[0] != 'W']
    search = NeighborSearch(heavy)
    chains, chain_files = {}, {}
    for rank, want in wanted.items():
        found = [asym for asym, info in molecules.items() if info['polymer'] and info['author'] == want['chain_label']]
        blank = {'status': None, 'residues': {}, 'partners': [], 'protein_partners': [], 'dropped': []}
        if not found:
            chains[rank] = {**blank, 'status': 'chain_not_found'}
            continue
        if len(found) > 1:
            chains[rank] = {**blank, 'status': 'chain_ambiguous'}
            continue
        (asym,) = found
        info = molecules[asym]
        if info['kind'] != 'protein':
            chains[rank] = {**blank, 'status': 'chain_not_protein'}
            continue
        if want['entity_id'] is not None and info['entity'] != want['entity_id']:
            chains[rank] = {**blank, 'status': 'chain_entity_differs_from_rcsb'}
            continue
        ordinal_of, residues = {}, {}
        for residue in model[asym]:
            if 'CA' in residue:
                ordinal = len(residues) + 1
                ordinal_of[residue.id] = ordinal
                number, code = residue.id[1], residue.id[2].strip()
                residues[ordinal] = {'auth_seq_id': number, 'insertion_code': code, 'resname': residue.get_resname(),
                                     'letter': _letter(residue.get_resname()), 'ca': tuple(float(c) for c in residue['CA'].coord)}
        if not residues:
            chains[rank] = {**blank, 'status': 'chain_has_no_c_alpha'}
            continue
        if len(residues) > LONGEST_CHAIN:
            chains[rank] = {**blank, 'status': 'chain_too_long_for_pdb_format'}
            continue
        keyed, proteins, dropped = {}, {}, []
        for residue in model[asym]:
            if (residue.get_resname() in WATERS):
                continue
            ordinal = ordinal_of.get(residue.id)
            near = {}
            for atom in residue:
                if (atom.element or '').upper() in ('H', 'D'):
                    continue
                for other in search.search(atom.coord, sheets.CONTACT_A):
                    parent = other.get_parent()
                    if parent.get_parent().id != asym:
                        near[(parent.get_parent().id, parent.id)] = parent
            for (other_asym, other_id), parent in near.items():
                other = molecules[other_asym]
                if other['polymer']:
                    key = (other['kind'], other['kind'] if other['kind'] in ('dna', 'rna') else other_asym)
                    instance = other_asym
                else:
                    key = ('ligand', parent.get_resname())
                    instance = (other_asym, other_id)
                if other['kind'] in ('protein', 'other_polymer'):
                    entry = proteins.setdefault(other_asym, {'kind': other['kind'], 'chain': other['author'], 'asym_id': other_asym,
                                                             'same_entity': other['entity'] == info['entity'], 'ordinals': set()})
                    if ordinal is not None:
                        entry['ordinals'].add(ordinal)
                    continue
                entry = keyed.setdefault(key, {'kind': key[0], 'identifier': key[1], 'instances': set(), 'ordinals': set()})
                entry['instances'].add(instance)
                if ordinal is None:
                    dropped.append({'hit_author_seq_id': residue.id[1], 'reason': 'hit_residue_has_no_c_alpha',
                                    'partner': sheets.partner_key(key[0], key[1])})
                else:
                    entry['ordinals'].add(ordinal)
        partners = []
        for (kind, identifier), entry in sorted(keyed.items()):
            listed = kind == 'ligand' and identifier in ADDITIVES
            partners.append({'kind': kind, 'identifier': identifier, 'additive': listed,
                             'additive_status': ('listed_by_biolip' if listed else 'not_listed_by_biolip') if kind == 'ligand'
                             else 'not_applicable', 'instance_count': len(entry['instances']),
                             'ordinals': sorted(entry['ordinals'])})
        chains[rank] = {'status': 'parsed', 'residues': residues, 'partners': partners, 'dropped': dropped,
                        'protein_partners': [{'kind': e['kind'], 'chain': e['chain'], 'asym_id': e['asym_id'],
                                              'same_entity': e['same_entity'], 'contact_residue_count': len(e['ordinals'])}
                                             for e in sorted(proteins.values(), key=lambda e: (e['chain'], e['asym_id']))]}
        chain_files[rank] = ''.join(
            'ATOM  {:5d} {} {:>3s} A{:4d}    {:8.3f}{:8.3f}{:8.3f}  1.00  0.00           C\n'.format(
                ordinal, ' CA ', item['resname'][:3], ordinal, *item['ca']) for ordinal, item in residues.items())
    return {'chains': chains, 'chain_files': chain_files}


# -- the files of a search, the job, the settling rule ------------------------------------------------------------------------
def entry_files(search_sheet, expected_entities):
    """The solved entry files of the asked hits in rank order of their first hit: ``[{'entry', 'assembly', 'ranks': [...],
    'wanted': {rank: {'chain_label', 'entity_id'}}}]``. ``expected_entities``: the entity id of each hit's chain as RCSB gave it
    (the held hit metadata), ``{rank: entity id}``."""
    files = {}
    for row in sheets.asked_rows(search_sheet):
        target = pdb_target(row['target_id'])
        entry = files.setdefault((target['entry'], target['assembly']), {'entry': target['entry'], 'assembly': target['assembly'],
                                                                      'ranks': [], 'wanted': {}})
        entry['ranks'].append(row['rank'])
        entry['wanted'][row['rank']] = {'chain_label': target['chain_label'], 'entity_id': expected_entities.get(row['rank'])}
    return list(files.values())


class JobFailed(Exception):
    """A job of the unit that did not end well: ``code`` is one of ``OWN_FAILURE_CODES``."""

    def __init__(self, code, record_refs=()):
        super().__init__(code)
        self.code, self.record_refs = code, list(record_refs)


async def align_batch(ctx, resource_id, model_ref, chain_files, batch_number):
    """The ONE local job of a batch: ``usalign_driver`` over the plan of pairs (the target model with each hit chain of
    ``chain_files``, ``{rank: PDB text}``), through ``execute_on_local_resource``. Returns ``{'alignments': {rank: driver pair},
    'plan_ref', 'report_ref', 'handoff_ref', 'closure_ref'}`` or raises ``JobFailed``."""
    store = ctx.store
    plan = {'usalign': str((Path(ctx.settings['usalign_executable_directory']) / 'USalign').resolve()),
            'pairs': [{'id': 'r' + str(rank), 'first': TARGET_FILE, 'second': 'h' + str(rank) + '.pdb'} for rank in sorted(chain_files)]}
    with store.transaction():
        plan_ref = store.artifact(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode(), 'application/json')
        driver_ref = store.artifact(DRIVER_SOURCE, 'text/x-python')
        staged = {'h' + str(rank) + '.pdb': store.artifact(text.encode('ascii'), 'chemical/x-pdb') for rank, text in chain_files.items()}
    ran = await execute_on_local_resource(
        ctx, resource_id, [ctx.settings['python_executable'], DRIVER_FILE, PLAN_FILE], {}, wait=True,
        inputs={PLAN_FILE: plan_ref, DRIVER_FILE: driver_ref, TARGET_FILE: model_ref, **staged}, name='usalign_batch_' + str(batch_number))
    if ran['status'] != 'completed':
        raise JobFailed('job_not_accepted' if ran['launch']['status'] != 'completed' else 'job_not_fetched', [plan_ref])
    if ran['returncode'] != 0:
        raise JobFailed('driver_exit_nonzero', [plan_ref])
    found = [item['ref'] for item in ran['fetch']['results'] if item['name'] == usalign_driver.OUTPUT_FILE]
    if len(found) != 1:
        raise JobFailed('alignment_report_missing', [plan_ref])
    report = json.loads(store.get_artifact(found[0]))
    return {'alignments': {int(pair['id'][1:]): pair for pair in report['pairs']}, 'plan_ref': plan_ref, 'report_ref': found[0],
            'handoff_ref': ran['launch']['handoff_ref'], 'closure_ref': ran['fetch']['closure_ref'],
            'staged_refs': sorted(staged.values())}


def picture(rank_rows, hit_chains, alignments, target_ca, target_sequence):
    """The candidate picture of the hits done so far (both tests): ``{candidate: value}``, as ``differential_credit`` admits them."""
    rows = [sheets.grade_chain(row, hit_chains[row['rank']], alignments.get(row['rank']), target_ca, target_sequence)
            for row in rank_rows if row['rank'] in hit_chains]
    return differential_credit(sheets.picture_rows(rows))['scores']


def settled(before, after, batches):
    """The rule: after the second batch, no new candidate in either test and no candidate's value moved by more than SETTLE."""
    return batches > 1 and set(after) <= set(before) and all(abs(after[name] - before[name]) <= SETTLE for name in after)


async def analyse(ctx, resource_id, search_sheet, model_ref, model_ca, target_sequence, files):
    """Walk the entry ``files`` in order, in batches of ``BATCH``, by the settling rule (the module). Returns ``{'file_rows',
    'hit_chains', 'alignments', 'jobs', 'stopped' ('settled' or 'all_done'), 'batches', 'not_reached' (files never asked)}``;
    ``file_rows`` follow ``partner_contacts_sheet.grade_partner_contacts``, with ``file_ref`` the held artifact of the unpacked file."""
    store = ctx.store
    rank_rows = {row['rank']: row for row in sheets.asked_rows(search_sheet)}
    ordered = [rank_rows[rank] for file in files for rank in file['ranks']]
    file_rows, hit_chains, alignments, jobs = [], {}, {}, []
    before, batches, stopped = {}, 0, 'all_done'
    for start in range(0, len(files), BATCH):
        part = files[start:start + BATCH]
        chain_files = {}
        for file in part:
            got = fetch_assembly(file['entry'], file['assembly'])
            row = {'entry': file['entry'], 'assembly': file['assembly'], 'url': got['url'], 'status': None, 'reason': got['reason'],
                   'download_bytes': got['download_bytes'], 'download_sha256': got['download_sha256'], 'unpacked_bytes': None,
                   'file_ref': None, 'hit_count': len(file['ranks'])}
            if got['status'] != 'ok':
                row['status'] = got['status'] if got['status'] == 'too_large' else 'not_obtained'
                for rank in file['ranks']:
                    hit_chains[rank] = 'file_too_large' if got['status'] == 'too_large' else 'file_not_obtained'
            else:
                with store.transaction():
                    row.update(unpacked_bytes=len(got['text']), file_ref=store.artifact(got['text'], 'chemical/x-mmcif'))
                try:
                    read = read_assembly(got['text'], file['wanted'])
                except (ValueError, KeyError, OSError) as error:
                    row.update(status='unreadable', reason=type(error).__name__ + ':' + str(error)[:120])
                    for rank in file['ranks']:
                        hit_chains[rank] = 'file_unreadable'
                else:
                    row['status'] = 'parsed'
                    hit_chains.update(read['chains'])
                    chain_files.update(read['chain_files'])
            file_rows.append(row)
        if chain_files:
            ran = await align_batch(ctx, resource_id, model_ref, chain_files, batches + 1)
            alignments.update(ran['alignments'])
            jobs.append(ran)
        batches += 1
        after = picture(ordered, hit_chains, alignments, model_ca, target_sequence)
        done = batches * BATCH >= len(files)
        if not done and settled(before, after, batches):
            stopped = 'settled'
            break
        before = after
    return {'file_rows': file_rows, 'hit_chains': hit_chains, 'alignments': alignments, 'jobs': jobs, 'stopped': stopped,
            'batches': batches, 'not_reached': len(files) - len(file_rows)}


def _failed(code, retryable=False, record_refs=(), **detail):
    """The outcome of a unit that failed after its check passed (the code is one of ``OWN_FAILURE_CODES``)."""
    return {'status': 'failed', 'failure_code': code, 'retryable': retryable, 'record_refs': list(record_refs), 'graded_refs': [],
            'detail': detail}


def _expected_entities(metadata):
    """``{rank: entity id}`` of the hit chains as RCSB gave them (the held hit metadata: ``chain_service.chains`` in rank order)."""
    return {index: chain['entity_id'] for index, chain in enumerate(metadata['chain_service']['chains'], 1)
            if chain.get('entity_id') is not None}


async def partner_contacts(ctx, *, search_ref, resource_id):
    """Run and grade ``partner_contacts`` for the held search ``search_ref`` and keep the two gradings through custody (see the
    module). ``ctx`` is the tool's ``UnitContext``; ``ctx.settings`` holds ``python_executable`` and
    ``usalign_executable_directory``."""
    store = ctx.store
    source = store.get(search_ref)
    query_ref = source['operand_refs'][0]
    inputs = partner_search_inputs(store)[search_ref]
    result_ref, model_ref = inputs['result_ref'], inputs['model_ref']
    (entry,) = source_tool_grading_entries(store, search_ref)
    search_sheet = entry['grading']['sheet']
    result_row = {row['artifact_ref']: row for row in products(store, foldseek_search.RESULTS_KIND)}[result_ref]
    try:
        sequence = foldseek_search.target_sequence(store, query_ref)
        model_ca = foldseek_search.model_positions(store.get_artifact(model_ref), sequence)
        target_sequence = parse_foldseek_result(json.loads(store.get_artifact(result_ref)), DATABASE)['query_sequence']
        files = entry_files(search_sheet, _expected_entities(json.loads(store.get_artifact(inputs['metadata_ref']))))
    except (ValueError, KeyError) as error:
        return _failed('grading_refused', reason=str(error))
    try:
        walked = await analyse(ctx, resource_id, search_sheet, model_ref, model_ca, target_sequence, files)
    except JobFailed as error:
        return _failed(error.code, record_refs=error.record_refs)
    try:
        contacts, bound = sheets.grade_partner_contacts(
            search_sheet, walked['file_rows'], walked['hit_chains'], walked['alignments'], model_ca, target_sequence,
            search_source_ref=search_ref, additive_list=ADDITIVE_FACTS, files_not_reached=walked['not_reached'])
    except (ValueError, KeyError) as error:
        return _failed('grading_refused', reason=str(error))
    settings = {'service': 'rcsb_files', 'url_form': FILE_ROOT + '<ID>-assembly<N>.cif.gz', 'batch': BATCH, 'settle': SETTLE,
                'contact_A': sheets.CONTACT_A, 'max_bytes': MAX_BYTES, 'program': 'USalign', 'additive_list': ADDITIVE_FACTS}
    record = {**settings, 'entries': [{key: row[key] for key in ('entry', 'assembly', 'url', 'status', 'download_bytes',
                                                                 'download_sha256', 'unpacked_bytes', 'file_ref')}
                                      for row in walked['file_rows']],
              'jobs': [{key: job[key] for key in ('plan_ref', 'report_ref', 'handoff_ref', 'closure_ref')} for job in walked['jobs']],
              'stopped': walked['stopped'], 'batches': walked['batches']}
    with store.transaction():
        record_ref = store.artifact(canonical(record), 'application/json')
        grading_ref = retain_tool_grading(store, provider=PROVIDER, native_artifact_ref=record_ref, grading={'sheet': contacts})
        first = store.put('source', {
            'provider': PROVIDER, 'accession': None, 'uri': FILE_ROOT, 'artifact_ref': record_ref, 'text_ref': None,
            'request_ref': None, 'version': None, 'retrieved_at': None, 'auxiliary_artifact_refs': [grading_ref],
            'operand_refs': [query_ref]}, origin='tool')
        bound = {**bound, 'contacts_source_ref': first['id']}
        bound_ref = retain_tool_grading(store, provider=PARTNERS_PROVIDER, native_artifact_ref=record_ref, grading={'sheet': bound})
        second = store.put('source', {
            'provider': PARTNERS_PROVIDER, 'accession': None, 'uri': FILE_ROOT, 'artifact_ref': record_ref, 'text_ref': None,
            'request_ref': None, 'version': None, 'retrieved_at': None, 'auxiliary_artifact_refs': [bound_ref],
            'operand_refs': [query_ref]}, origin='tool')
        structures = [record_product(
            store, artifact_ref=row['file_ref'], kind=STRUCTURE_KIND, generated_by=first['id'], used=[result_ref],
            derived_from=[result_row['id']],
            settings={'entry': row['entry'], 'assembly': row['assembly'], 'url': row['url'], 'download_bytes': row['download_bytes'],
                      'download_sha256': row['download_sha256'], 'unpacked_bytes': row['unpacked_bytes']})
            for row in walked['file_rows'] if row['file_ref'] is not None]
        alignments = [record_product(
            store, artifact_ref=job['report_ref'], kind=ALIGNMENTS_KIND, generated_by=job['handoff_ref'],
            used=[model_ref, job['plan_ref'], *job['staged_refs']], derived_from=[result_row['id']],
            settings={'program': 'USalign', 'batch': number}) for number, job in enumerate(walked['jobs'], 1)]
        derived = [row['id'] for row in structures + alignments]
        first_grading = record_grading_product(store, grading_ref=grading_ref, grading={'sheet': contacts}, provider=PROVIDER,
                                               source_ref=first['id'], used=[record_ref, result_ref, model_ref],
                                               derived_from=[result_row['id'], *derived])
        second_grading = record_grading_product(store, grading_ref=bound_ref, grading={'sheet': bound}, provider=PARTNERS_PROVIDER,
                                                source_ref=second['id'], used=[record_ref, result_ref, model_ref],
                                                derived_from=[result_row['id'], *derived])
    graded = [first['id'], grading_ref, first_grading['id'], second['id'], bound_ref, second_grading['id'],
              *derived]
    jobs = [ref for job in walked['jobs'] for ref in (job['handoff_ref'], job['closure_ref'])]
    return {'status': 'completed', 'failure_code': None, 'retryable': False, 'graded_refs': graded, 'record_refs': [*graded, *jobs],
            'source_ref': first['id'], 'bound_partner_source_ref': second['id'],
            'entries_asked': contacts['entries_asked'], 'entries_too_large': contacts['entries_too_large'],
            'entries_not_asked': contacts['entries_not_asked'], 'hits_with_partners': contacts['hits_with_partners'],
            'product_candidates_measured': contacts['candidates_measured'], 'partner_candidates_measured': bound['candidates_measured'],
            'stopped': walked['stopped'], 'batch_count': walked['batches']}


__all__ = ['ADDITIVES', 'ADDITIVE_FACTS', 'ALIGNMENTS_KIND', 'BATCH', 'DATABASE', 'MAX_ATOMS_PER_FILE', 'MAX_BYTES',
           'MAX_UNPACKED_BYTES', 'OWN_FAILURE_CODES', 'PARTNERS_PROVIDER', 'PROVIDER', 'REQUEST_FIELDS', 'STRUCTURE_KIND',
           'align_batch', 'analyse', 'check_partner_contacts_request', 'entry_files', 'fetch_assembly', 'file_url',
           'load_additive_list', 'partner_contacts', 'partner_search_inputs', 'picture', 'read_assembly', 'settled']
