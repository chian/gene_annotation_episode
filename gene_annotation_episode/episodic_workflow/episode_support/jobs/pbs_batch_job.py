"""The batch job of a command for a PBS resource: the job a ``JobAccess`` route of kind ``pbs`` submits with ``qsub``.

A job of the PBS route is ``{'mode', 'script', 'arguments', 'env'}`` (``pbs_job_route``). ``pbs_batch_job`` builds the
batch one: a script that runs ``command`` in the directory the job was submitted from, and the ``qsub`` operands of the
allocation the caller supplies (``account``, ``queue``, ``select``, ``walltime``, ``filesystems``, each a plain
operand). The allocation is passed through and never chosen here, and nothing is defaulted: a missing, an unknown or a
malformed operand is a wrong commission and fails with its error. The walltime is a scheduler operand, separate from
any Episode's continuation, which belongs to its yield estimator alone. Nothing here submits, reads or writes a file."""
import re
import shlex

PBS_FIELDS = ('account', 'queue', 'select', 'walltime', 'filesystems')
_OPERAND = re.compile(r'^[A-Za-z0-9_.:=+@,-]+$')


def pbs_batch_job(command, allocation, *, env=None):
    """The PBS batch job that runs ``command`` (the argv tokens) under ``allocation``."""
    if type(command) is not list or not command or any(type(token) is not str or not token for token in command):
        raise ValueError('pbs_batch_command_invalid')
    if type(allocation) is not dict or set(allocation) != set(PBS_FIELDS):
        raise ValueError('pbs_allocation_fields')
    for name in PBS_FIELDS:
        if type(allocation[name]) is not str or not _OPERAND.match(allocation[name]):
            raise ValueError('pbs_allocation_operand:' + name)
    script = '#!/bin/bash\ncd "$PBS_O_WORKDIR" || exit 2\n' + ' '.join(shlex.quote(token) for token in command) + '\n'
    arguments = ['-A', allocation['account'], '-q', allocation['queue'], '-l', 'select=' + allocation['select'],
                 '-l', 'walltime=' + allocation['walltime'], '-l', 'filesystems=' + allocation['filesystems']]
    return {'mode': 'batch', 'script': script, 'arguments': arguments, 'env': dict(env or {})}


__all__ = ['PBS_FIELDS', 'pbs_batch_job']
