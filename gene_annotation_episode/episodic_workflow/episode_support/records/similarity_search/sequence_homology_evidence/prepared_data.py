"""The prepared-data record: what a preparation job built, held under custody by the Episode that established it.

A database or a mask built for later work is one row of the declared work table ``PREPARED_DATA``. Later searches
and clustering name the row by its reference (a ``record_refs`` field); they never receive its files. The row says
what was built, from which input digests, by which program, where the files live and what was checked. The files
of a database stay on the resource that built them (``placement``): the row names the resource, the job and the
path prefix inside that job's directory, and every file's size and digest. Only the small records (the plan, the
receipt, the job's handoff and closure rows) are artifacts or rows the Episode holds.

Library functions here never write the Store directly: ``put_prepared`` writes through the tool's scoped store
(``ctx.store.table``), in one transaction with the records written beside it, and the system fills the writing
Episode, unit and operation key.

Credit: a usable prepared record is progress, earned once per distinct record (``data_key``, derived from the input
digest, the kind and every option). A record that is not usable, a repeat of a held key, and a failed build earn
nothing. The unit comes from the commission.
"""
from __future__ import annotations

from episode_runtime.work_tables import TableDeclaration

PREPARED_DATA = TableDeclaration(
    name='prepared_data',
    columns=('data_key', 'prepared_kind', 'state', 'usable', 'molecule', 'input_ref', 'input_sha256',
             'input_records', 'input_residues', 'program', 'executable_sha256', 'resource_id', 'job',
             'placement_prefix', 'files', 'facts', 'failure_codes', 'plan_ref', 'receipt_ref', 'handoff_ref',
             'closure_ref'),
    key=('data_key',),
    record_refs=('input_ref', 'plan_ref', 'receipt_ref', 'handoff_ref', 'closure_ref'))
STATES = ('usable', 'failed', 'incomplete')


def prepared_values(plan, evaluation, *, resource_id, job, plan_ref, receipt_ref, handoff_ref, closure_ref):
    """The columns of one prepared-data row, from the plan that ran, the receipt's evaluation and the references
    of the records the Episode holds. ``receipt_ref`` is ``None`` when the job left no receipt."""
    build = plan['steps'][0]
    operation = plan['operation']
    prefix = operation['output_prefix'] if plan['kind'] == 'database_build' else operation['output_name']
    return {'data_key': plan['key'], 'prepared_kind': plan['prepared_kind'], 'state': evaluation['state'],
            'usable': evaluation['usable'], 'molecule': operation['molecule'],
            'input_ref': plan['input']['artifact_ref'], 'input_sha256': plan['input']['sha256'],
            'input_records': plan['input']['records'], 'input_residues': plan['input']['residues'],
            'program': build['argv'][0].rsplit('/', 1)[-1], 'executable_sha256': build['software']['sha256'],
            'resource_id': resource_id, 'job': job, 'placement_prefix': prefix, 'files': evaluation['files'],
            'facts': evaluation['facts'], 'failure_codes': evaluation['failure_codes'], 'plan_ref': plan_ref,
            'receipt_ref': receipt_ref, 'handoff_ref': handoff_ref, 'closure_ref': closure_ref}


def put_prepared(ctx, values):
    """Write the row through the tool's scoped store, in its own transaction; returns the row (``row['id']`` is
    its reference). The same key written again is the next revision of the same row."""
    return ctx.store.table(PREPARED_DATA).put(values)


def prepared_rows(reader, *, usable=None):
    """The prepared-data rows the reader holds, in receipt order; only usable ones (or only the others) when
    ``usable`` is a boolean."""
    where = None if usable is None else {'usable': usable}
    return reader.table(PREPARED_DATA).select(where)


def prepared_credit(reader, unit, *, known_keys=()):
    """The credit of the held prepared-data records: ``unit`` for each distinct usable record whose key is not one
    the parent already held (``known_keys``: a repeat earns nothing)."""
    return unit * len({row['data_key'] for row in prepared_rows(reader, usable=True)} - set(known_keys))


def prepared_features(row):
    """The controlled features of one prepared-data row, read by code: numbers, booleans and fixed values (no
    paths, no text). A fact the receipt did not establish is absent, never defaulted."""
    facts = row['facts']
    features = {'prepared_kind': row['prepared_kind'], 'state': row['state'], 'usable': row['usable'],
                'input_records': row['input_records'], 'input_residues': row['input_residues'],
                'files_count': facts.get('files_count'), 'bytes_total': facts.get('bytes_total')}
    for name in ('sequences', 'letters', 'integrity_ok', 'counts_match', 'inventory_complete', 'masked_residues',
                 'masked_fraction'):
        if facts.get(name) is not None:
            features[name] = facts[name]
    return {name: value for name, value in features.items() if value is not None}


__all__ = ['PREPARED_DATA', 'STATES', 'prepared_values', 'put_prepared', 'prepared_rows', 'prepared_credit',
           'prepared_features']
