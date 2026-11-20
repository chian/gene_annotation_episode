"""The database-search kind of a BLAST use, declared in the commission and derived from the job.

A database search is one query (a sequence or a profile) against one reference set, to find what the query most
likely is. Its result is a hit list. This module holds only the kind: the controlled value a commission declares,
and the derivation of the same value from the job that was actually built. The two must agree; a commission whose
declared kind differs from the kind its job derives to is wrong and fails with its error. Nothing here repairs,
guesses or falls back, and nothing here reads a file, a record or a network.

Two jobs derive to a database search today:

* the job of the public NCBI BLAST service (``{'program', 'database', 'hitlist_size', 'query_file'}``): one staged
  query file and the name of one of the service's databases, and no subject sequence;
* a native job whose mode is ``database`` against exactly one prepared sequence database
  (``native_blast_standard_database``), or against the prepared profile databases of the profile programs
  (``native_blast_database``).

A native job whose mode is ``pairwise`` derives to ``pairwise`` so that a commission that declares the wrong one of
the two fails with a message that names both. Every other job has no derivable kind here and raises.
"""

DATABASE_SEARCH = 'database_search'
PAIRWISE = 'pairwise'
# The kinds this module can derive. The commission's controlled field of the declared kind takes its values from the
# union of the kinds every BLAST use declares (the owner's list: pairwise, database search, all-vs-all and database
# preparation), each derived by its own module.
DERIVABLE_KINDS = (PAIRWISE, DATABASE_SEARCH)

API_JOB_FIELDS = frozenset({'program', 'database', 'hitlist_size', 'query_file'})


def derive_kind_from_api_job(job):
    """The kind of a job of the public BLAST service: it names a database and one staged query file, and it has no
    subject sequence. A job that does not have exactly the service's job fields is not of the service's form."""
    if not isinstance(job, dict) or set(job) != API_JOB_FIELDS:
        raise ValueError('blast_kind_api_job_fields_invalid')
    if type(job['database']) is not str or not job['database']:
        raise ValueError('blast_kind_api_job_database_required')
    if type(job['query_file']) is not str or not job['query_file']:
        raise ValueError('blast_kind_api_job_query_file_required')
    return DATABASE_SEARCH


def derive_kind_from_native_job(requested_job):
    """The kind of a native requested job from its own declared mode and operands.

    ``native_blast_standard_database``: mode ``database``, exactly one database operand and a query of kind
    ``sequence`` or ``pssm``. ``native_blast_database``: mode ``database`` (the profile programs). ``native_blast``:
    mode ``pairwise``. The mode and the operands must agree: a database job with no database operand, or a pairwise
    job with a database operand, is not a job of any kind."""
    if not isinstance(requested_job, dict):
        raise ValueError('blast_kind_requested_job_required')
    families = [name for name in ('native_blast', 'native_blast_standard_database', 'native_blast_database')
                if name in requested_job]
    if len(families) != 1:
        raise ValueError('blast_kind_exactly_one_native_family_required')
    family = families[0]
    job = requested_job[family]
    if not isinstance(job, dict) or 'mode' not in job:
        raise ValueError('blast_kind_native_mode_required')
    if family == 'native_blast':
        if job['mode'] != 'pairwise' or 'databases' in job:
            raise ValueError('blast_kind_native_pairwise_conflict')
        return PAIRWISE
    if job['mode'] != 'database':
        raise ValueError('blast_kind_native_database_mode_required')
    if family == 'native_blast_standard_database':
        databases = job.get('databases')
        if not isinstance(databases, list) or len(databases) != 1:
            raise ValueError('blast_kind_exactly_one_database_operand_required')
        query = job.get('query')
        if not isinstance(query, dict) or query.get('kind') not in ('sequence', 'pssm'):
            raise ValueError('blast_kind_database_query_kind_required')
    return DATABASE_SEARCH


def require_declared_kind(declared, derived):
    """The commission's declared kind must be the kind derived from its job; otherwise the commission is wrong."""
    if declared not in DERIVABLE_KINDS or derived not in DERIVABLE_KINDS:
        raise ValueError('blast_analysis_kind_unknown:' + repr(declared) + ':' + repr(derived))
    if declared != derived:
        raise ValueError('blast_analysis_kind_conflict:declared:' + declared + ':derived:' + derived)
    return derived


__all__ = ['DATABASE_SEARCH', 'PAIRWISE', 'DERIVABLE_KINDS', 'derive_kind_from_api_job',
           'derive_kind_from_native_job', 'require_declared_kind']
