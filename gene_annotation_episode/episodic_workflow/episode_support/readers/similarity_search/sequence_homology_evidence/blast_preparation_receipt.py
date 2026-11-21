"""What a finished preparation job's receipt establishes: its state, its checked facts and whether the product is
usable. A pure function over three things the coordinator holds: the plan the job ran, the receipt the driver wrote,
and the result listing the route gave for the job's directory. It reads no file, runs no program and writes no
record, and it is the only place that decides ``usable``.

**Usable** means every one of these facts holds, each checked from the receipt and the listing and none assumed:

- the plan the receipt names is the plan that was run, and the staged input was verified against its digest;
- every step of the plan ran and returned 0 (a database build: build, native summary);
- the produced files are present and the route's listing agrees with the receipt on each file's size;
- a database: the native summary parses and its sequence and letter counts equal the input's, and the files of the
  database (each volume the alias names, or the single set) are all there; a mask: the output parses and, for a
  masked FASTA, its record and residue counts equal the input's.

**States.** ``usable``; ``failed`` (a step returned nonzero, or a fact contradicts the plan); ``incomplete`` (no
receipt, an unreadable one, or steps the job never ran for a reason other than an earlier failure). An incomplete
preparation is never read as a finished one: nothing is inferred from absence.
"""
from __future__ import annotations

import re

FAILURE_CODES = ('receipt_missing', 'receipt_plan_conflict', 'input_unverified', 'native_nonzero_exit',
                 'native_not_run', 'output_missing', 'inventory_incomplete', 'info_unparsed', 'counts_mismatch',
                 'listing_conflict', 'mask_unparsed', 'mask_counts_conflict')
BASE = {'protein': ('phr', 'pin', 'psq'), 'nucleotide': ('nhr', 'nin', 'nsq')}
ALIAS = {'protein': 'pal', 'nucleotide': 'nal'}
SUPPORT_SUFFIXES = ('.stdout', '.stderr')


def _database_inventory(molecule, prefix, names):
    """Whether the files of the database are all there: the single set, or every volume of the alias."""
    base, alias = BASE[molecule], ALIAS[molecule]
    if all(prefix + '.' + ext in names for ext in base):
        return True
    volumes = {}
    pattern = re.compile(re.escape(prefix) + r'\.(\d\d)\.(' + '|'.join(base) + ')$')
    for name in names:
        match = pattern.match(name)
        if match:
            volumes.setdefault(match.group(1), set()).add(match.group(2))
    return (prefix + '.' + alias in names and bool(volumes)
            and all(found == set(base) for found in volumes.values()))


def evaluate(plan, plan_sha256, receipt, catalog, *, ended):
    """``{'state', 'usable', 'failure_codes', 'facts', 'files'}`` for one preparation job.

    ``plan``: the validated plan. ``plan_sha256``: the digest of the plan bytes that were staged. ``receipt``: the
    parsed receipt or ``None`` when it is absent or unreadable. ``catalog``: the route's listing,
    ``[{'name', 'bytes'}]``. ``ended``: whether the job has ended; an ended job with no receipt is ``failed`` (the
    driver refused its plan or its input), a job still running or unobserved is ``incomplete``."""
    codes, facts, files = [], {}, []
    if receipt is None or type(receipt) is not dict:
        return {'state': 'failed' if ended else 'incomplete', 'usable': False, 'failure_codes': ['receipt_missing'],
                'facts': facts, 'files': files}
    if receipt.get('plan_sha256') != plan_sha256:
        codes.append('receipt_plan_conflict')
    if receipt.get('input_verified') is not True:
        codes.append('input_unverified')
    steps = {step['name']: step for step in receipt.get('steps', [])}
    wanted = [step['name'] for step in plan['steps']]
    failed_step, never_ran = False, False
    for name in wanted:
        step = steps.get(name)
        if step is None or step.get('ran') is not True:
            never_ran = True
        elif step.get('returncode') != 0:
            failed_step = True
    if failed_step:
        codes.append('native_nonzero_exit')
    listed = {item['name']: item['bytes'] for item in catalog}
    files = [{'name': item['name'], 'bytes': item['bytes'], 'sha256': item['sha256']}
             for item in receipt.get('files', [])]
    for item in files:
        if listed.get(item['name']) != item['bytes']:
            codes.append('listing_conflict')
            break
    names = {item['name'] for item in files}
    stated = plan['input']
    if plan['kind'] == 'database_build':
        operation = plan['operation']
        facts['files_count'] = len(files)
        facts['bytes_total'] = sum(item['bytes'] for item in files)
        facts['inventory_complete'] = _database_inventory(operation['molecule'], operation['output_prefix'], names)
        info = receipt.get('info')
        facts['info_parsed'] = info is not None
        facts['sequences'] = None if info is None else info['sequences']
        facts['letters'] = None if info is None else info['letters']
        facts['counts_match'] = (info is not None and info['sequences'] == stated['records']
                                 and info['letters'] == stated['residues'])
        if not failed_step and not never_ran:
            if not facts['inventory_complete']:
                codes.append('inventory_incomplete')
            if info is None:
                codes.append('info_unparsed')
            elif not facts['counts_match']:
                codes.append('counts_mismatch')
    else:
        mask = receipt.get('mask')
        output = plan['operation']['output_name']
        facts['files_count'] = len(files)
        facts['bytes_total'] = sum(item['bytes'] for item in files)
        facts['output_present'] = output in names
        facts['mask_parsed'] = bool(mask and mask.get('parsed'))
        masked = None if not facts['mask_parsed'] else mask['masked_residues']
        facts['masked_residues'] = masked
        facts['masked_fraction'] = None if masked is None else masked / stated['residues']
        if not failed_step and not never_ran:
            if not facts['output_present']:
                codes.append('output_missing')
            elif not facts['mask_parsed']:
                codes.append('mask_unparsed')
            else:
                if plan['operation']['output_format'] == 'fasta' and (
                        mask['records'] != stated['records'] or mask['residues'] != stated['residues']):
                    codes.append('mask_counts_conflict')
                if masked > stated['residues']:
                    codes.append('mask_counts_conflict')
    if never_ran and not failed_step:
        codes.append('native_not_run')
    codes = sorted(set(codes), key=FAILURE_CODES.index)
    if not codes:
        state = 'usable'
    elif never_ran and not failed_step and all(code == 'native_not_run' for code in codes):
        state = 'incomplete'
    else:
        state = 'failed'
    return {'state': state, 'usable': state == 'usable', 'failure_codes': codes, 'facts': facts, 'files': files}


__all__ = ['FAILURE_CODES', 'evaluate']
