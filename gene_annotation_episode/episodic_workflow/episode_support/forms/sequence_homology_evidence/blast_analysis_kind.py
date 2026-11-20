"""The analysis kind of a BLAST job: what the search or preparation is for, which decides how its result is graded.

A commission declares the kind (a value of ``ANALYSIS_KINDS``) and the kind is derived again, by this one function,
from the validated job itself, from what the job is; the two must agree. There is one recognizer per kind and each
recognizes only the job form of its own contract:

* ``pairwise``: one query sequence against one subject sequence (A101's pairwise job, or a native job whose mode is
  ``pairwise``);
* ``database_search``: one query against one reference set (the job of the public NCBI BLAST service, or a native job
  whose mode is ``database``);
* ``all_vs_all``: a set of sequences against the same set (the all-vs-all job);
* ``database_build`` and ``masking``: a preparation plan whose first step runs ``makeblastdb`` or a masking program.

A job of none of these forms has no kind and raises, a job of two forms is an error, and a declared kind that is not
the derived one is an error. Nothing is repaired and nothing falls back, and nothing here reads a file, a record or a
network."""
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_all_vs_all_job import (
    validate_requested_job as validate_all_vs_all_requested_job)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_pairwise_job import (
    validate_pairwise_requested_job)

PAIRWISE = 'pairwise'
DATABASE_SEARCH = 'database_search'
ALL_VS_ALL = 'all_vs_all'
DATABASE_BUILD = 'database_build'
MASKING = 'masking'
PREPARATION_KINDS = (DATABASE_BUILD, MASKING)
ANALYSIS_KINDS = (PAIRWISE, DATABASE_SEARCH, ALL_VS_ALL, DATABASE_BUILD, MASKING)

# The public service's job fields, and the preparation plan's version and programs (the plan is read by the
# preparation job's compiler and by the job-side driver; the program of its first step is what the kind is read from).
API_JOB_FIELDS = frozenset({'program', 'database', 'hitlist_size', 'query_file'})
PREPARATION_PLAN_VERSION = 'blast_preparation_job_v1'
KIND_OF_PROGRAM = {'makeblastdb': DATABASE_BUILD, 'dustmasker': MASKING, 'segmasker': MASKING}
NATIVE_FAMILIES = ('native_blast', 'native_blast_standard_database', 'native_blast_database')


def _pairwise_job(job):
    """``pairwise`` for A101's pairwise job; ``None`` when the job is not of that form."""
    if 'blast_pairwise' not in job:
        return None
    validate_pairwise_requested_job(job)
    return PAIRWISE


def _native_job(job):
    """``pairwise`` or ``database_search`` for a native requested job, from its own declared mode and operands;
    ``None`` when the job names none of the native families. The mode and the operands must agree: a database job with
    no database operand, or a pairwise job with a database operand, is not a job of any kind."""
    families = [name for name in NATIVE_FAMILIES if name in job]
    if not families:
        return None
    if len(families) != 1:
        raise ValueError('blast_kind_exactly_one_native_family_required')
    family = families[0]
    native = job[family]
    if not isinstance(native, dict) or 'mode' not in native:
        raise ValueError('blast_kind_native_mode_required')
    if family == 'native_blast':
        if native['mode'] != 'pairwise' or 'databases' in native:
            raise ValueError('blast_kind_native_pairwise_conflict')
        return PAIRWISE
    if native['mode'] != 'database':
        raise ValueError('blast_kind_native_database_mode_required')
    if family == 'native_blast_standard_database':
        databases = native.get('databases')
        if not isinstance(databases, list) or len(databases) != 1:
            raise ValueError('blast_kind_exactly_one_database_operand_required')
        query = native.get('query')
        if not isinstance(query, dict) or query.get('kind') not in ('sequence', 'pssm'):
            raise ValueError('blast_kind_database_query_kind_required')
    return DATABASE_SEARCH


def _api_job(job):
    """``database_search`` for a job of the public BLAST service: it names a database and one staged query file and has
    no subject sequence; ``None`` when the job has not the service's job fields."""
    if set(job) != API_JOB_FIELDS:
        return None
    if type(job['database']) is not str or not job['database']:
        raise ValueError('blast_kind_api_job_database_required')
    if type(job['query_file']) is not str or not job['query_file']:
        raise ValueError('blast_kind_api_job_query_file_required')
    return DATABASE_SEARCH


def _all_vs_all_job(job):
    """``all_vs_all`` for the all-vs-all job; ``None`` when the job is not of that form."""
    if 'native_blast_all_vs_all' not in job:
        return None
    validate_all_vs_all_requested_job(job)
    return ALL_VS_ALL


def _preparation_plan(job):
    """``database_build`` or ``masking`` for a preparation plan, read from the program its first step runs and never
    from the declared field; ``None`` when the job is not a preparation plan."""
    if job.get('version') != PREPARATION_PLAN_VERSION:
        return None
    if type(job.get('steps')) is not list or not job['steps']:
        raise ValueError('blast_preparation_plan_has_no_steps')
    program = job['steps'][0]['argv'][0].rsplit('/', 1)[-1]
    if program not in KIND_OF_PROGRAM:
        raise ValueError('blast_preparation_program_not_a_preparation_program')
    return KIND_OF_PROGRAM[program]


RECOGNIZERS = (_pairwise_job, _native_job, _api_job, _all_vs_all_job, _preparation_plan)


def derived_analysis_kind(job):
    """The kind of the job, read from what the job is. Exactly one recognizer must recognize it."""
    if not isinstance(job, dict):
        raise ValueError('analysis_kind_not_derivable:job_must_be_a_record')
    kinds = []
    for recognize in RECOGNIZERS:
        try:
            kind = recognize(job)
        except (TypeError, KeyError, ValueError) as error:
            raise ValueError('analysis_kind_not_derivable:' + str(error)) from error
        if kind is not None:
            kinds.append(kind)
    if len(kinds) != 1:
        raise ValueError('analysis_kind_not_derivable:' + ('no_blast_job_of_a_known_form' if not kinds
                                                           else 'the_job_is_of_more_than_one_form'))
    return kinds[0]


def checked_analysis_kind(declared, job):
    """The derived kind of the job, after the declared one is shown to be it."""
    if declared not in ANALYSIS_KINDS:
        raise ValueError('analysis_kind_not_declared_or_unknown:' + repr(declared))
    derived = derived_analysis_kind(job)
    if declared != derived:
        raise ValueError('analysis_kind_conflict:declared:' + declared + ':derived:' + derived)
    return derived


__all__ = ['ALL_VS_ALL', 'ANALYSIS_KINDS', 'DATABASE_BUILD', 'DATABASE_SEARCH', 'KIND_OF_PROGRAM', 'MASKING',
           'PAIRWISE', 'PREPARATION_KINDS', 'PREPARATION_PLAN_VERSION', 'checked_analysis_kind',
           'derived_analysis_kind']
