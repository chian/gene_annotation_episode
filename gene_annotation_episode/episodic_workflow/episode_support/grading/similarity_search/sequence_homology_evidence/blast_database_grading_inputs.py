"""The inputs a BLAST database grading needs besides the native result, built from records the caller holds.

``build_database_sheet`` takes the native result and three further inputs that only the caller can know: the
identity of the searched database and the facts of how the result was reported (``calculation_context``), how often
each function occurs in that database (``database_profile``), and the target's own taxon where it is known
independently of the search (``target_context``). The grader rejects each of them unless it has an exact shape.
These functions build the shapes. They read no file, record or network: the caller reads the records through
custody and hands the values in, so nothing here can reach a record the caller does not hold.

They also account for the reference metadata. A hit with no metadata record is counted as missing, not as a hit
with no function: a metadata set that does not cover the hit list is ``complete: False`` and names what is missing.
Nothing is defaulted, and an incomplete or absent hit list is never reported as zero hits.
"""


def _text(value, code):
    if type(value) is not str or not value:
        raise ValueError(code)
    return value


def _optional_text(value, code):
    if value is not None:
        _text(value, code)
    return value


def _optional_count(value, code):
    if value is not None and (type(value) is not int or value < 0):
        raise ValueError(code)
    return value


def database_identity(*, namespace, value, version, release, scope, source_ref, pointer):
    """The identity of a searched sequence database, as the grader's calculation context requires it.

    ``value`` is the database's name as the service or the prepared-database record spells it, ``release`` the
    release the counts of a profile must match, ``scope`` what the database holds (for example every sequence or
    one clade), and ``source_ref`` and ``pointer`` the place the identity was read from (a record reference and an
    RFC 6901 pointer into it). A missing release or scope makes the representation adjustment unavailable; the
    grader says so in its reasons."""
    _text(namespace, 'blast_database_identity_namespace_required')
    _text(value, 'blast_database_identity_value_required')
    for field, item in (('version', version), ('release', release), ('scope', scope)):
        _optional_text(item, 'blast_database_identity_' + field + '_invalid')
    _text(source_ref, 'blast_database_identity_source_ref_required')
    if type(pointer) is not str or not (pointer == '' or pointer.startswith('/')):
        raise ValueError('blast_database_identity_pointer_invalid')
    return {'namespace': namespace, 'value': value, 'version': version, 'release': release, 'scope': scope,
            'preparation_type': 'sequence_database', 'source': {'source_ref': source_ref, 'pointer': pointer}}


def calculation_context(normalized, identity, *, requested_hit_limit, requested_hsp_limit=None,
                        native_returncode=None, producer_complete=None):
    """The reporting facts of a native result and the database identity, as the grader's calculation context.

    The hit array's presence and the number of hits come from the normalized result itself. The limits the search
    was asked for are the request's, so the caller passes them (for the public service, the job's hit-list size); a
    limit the caller does not know is ``None`` and the sheet then cannot say whether the limit was reached. A
    producer that is not known to have completed is ``None``, never ``True``."""
    search = normalized['search']
    present = search.get('hit_array_present')
    if type(present) is not bool:
        raise ValueError('blast_database_hit_array_presence_required')
    _optional_count(requested_hit_limit, 'blast_database_requested_hit_limit_invalid')
    _optional_count(requested_hsp_limit, 'blast_database_requested_hsp_limit_invalid')
    if native_returncode is not None and type(native_returncode) is not int:
        raise ValueError('blast_database_native_returncode_invalid')
    if producer_complete is not None and type(producer_complete) is not bool:
        raise ValueError('blast_database_producer_complete_invalid')
    return {'reporting': {'native_hit_array_present': present,
                          'native_hit_count': search.get('reported_hit_count'),
                          'requested_hit_limit': requested_hit_limit, 'requested_hsp_limit': requested_hsp_limit,
                          'native_returncode': native_returncode, 'producer_complete': producer_complete},
            'database_identity': identity}


def database_profile(identity, *, count_unit, total_count, function_counts, source):
    """How often each function occurs in the searched database, built on the identity it describes.

    The profile carries the identity's name, release and scope, so it is for exactly that database and that release;
    a profile made for another release is the grader's ``database_profile_release_unmatched`` and the adjustment
    stays unavailable. ``function_counts`` maps each function identifier to the number of database sequences that
    carry it, counted in ``count_unit`` (``unique_sequences`` or ``sequence_groups``), and ``total_count`` is the
    size of the whole database in the same unit."""
    if count_unit not in ('unique_sequences', 'sequence_groups'):
        raise ValueError('blast_database_profile_count_unit_invalid')
    if type(total_count) is not int or total_count <= 0:
        raise ValueError('blast_database_profile_total_count_invalid')
    if not isinstance(function_counts, dict) or any(
            type(key) is not str or not key or type(count) is not int or count < 0 or count > total_count
            for key, count in function_counts.items()):
        raise ValueError('blast_database_profile_function_counts_invalid')
    _text(source, 'blast_database_profile_source_required')
    return {'database': identity['value'], 'release': identity['release'], 'scope': identity['scope'],
            'count_unit': count_unit, 'source': source, 'total_count': total_count,
            'function_counts': dict(function_counts)}


def target_context(*, taxid, lineage, source, independent_of_search):
    """The target's own taxon, for the sheet's agreement of the hits' taxa with it.

    ``independent_of_search`` states that the taxon was established without using this search; a taxon read from the
    search's own best hit is not independent, and the caller says so (``False``). ``lineage`` is the ordered list of
    ``{'taxid', 'rank', 'name'}`` of the taxon. A target whose taxon is unknown is not given a context: the sheet then
    has no target agreement, and the features for it are absent."""
    if type(taxid) is not int or taxid <= 0:
        raise ValueError('blast_database_target_taxid_invalid')
    if not isinstance(lineage, list) or any(
            not isinstance(node, dict) or type(node.get('taxid')) is not int or node['taxid'] <= 0
            or type(node.get('rank')) is not str or not node['rank'] for node in lineage):
        raise ValueError('blast_database_target_lineage_invalid')
    _text(source, 'blast_database_target_source_required')
    if type(independent_of_search) is not bool:
        raise ValueError('blast_database_target_independence_required')
    return {'taxid': taxid, 'lineage': lineage, 'source': source, 'independent_of_search': independent_of_search}


def metadata_accounting(normalized, rows):
    """What the supplied reference metadata covers of the hit list.

    ``hit_list_present`` is false when the result has no hit array (a result that reported none is not a result of
    zero hits). The hit accessions are those the native result gives; the covered ones are those a metadata row
    names. ``complete`` is true only when a hit list is present, has at least one accession, and every accession is
    covered. Rows that match no hit are listed too, since a row that matches nothing may be a wrong join."""
    present = normalized['search'].get('hit_array_present') is True
    accessions = set()
    for hit in normalized.get('hits', []):
        for description in hit.get('descriptions', []):
            accession = description.get('accession')
            if type(accession) is str and accession:
                accessions.add(accession)
    named = {row['accession'] for row in rows if type(row.get('accession')) is str and row['accession']}
    missing = sorted(accessions - named)
    return {'hit_list_present': present, 'hit_accession_count': len(accessions),
            'covered_count': len(accessions & named), 'missing_accessions': missing,
            'rows_without_hit': sorted(named - accessions),
            'complete': present and bool(accessions) and not missing}


__all__ = ['database_identity', 'calculation_context', 'database_profile', 'target_context', 'metadata_accounting']
