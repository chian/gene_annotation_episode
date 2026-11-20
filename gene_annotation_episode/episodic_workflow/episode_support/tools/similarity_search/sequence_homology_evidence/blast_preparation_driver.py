"""The program a BLAST data-preparation job runs on its resource: ``python driver.py plan.json``.

Standard library only, on purpose: the job stages this file and its plan beside the input, so it runs the same on a
local resource and on a cluster that has Python and the BLAST+ programs and none of this repository. It decides
nothing. It reads the plan (``blast_preparation_job_v1``, written by ``compile_preparation``), checks the staged
input against the plan's digest, runs the plan's argv steps in order, and writes one receipt, ``receipt.json``,
last and atomically. The receipt is facts: what each step ran and returned, every produced file with its size and
digest (computed here, where the files are), the native database summary, and for a mask the masked residues
counted from the produced output. Whether those facts make the product usable is decided by code on the
coordinator (``readers/.../blast_preparation_receipt.py``), never here.

Exit status: 0 when every step of the plan returned 0; 1 when a step did not (the receipt is still written);
2 when the plan or the staged input is not what the plan says (no step is run).
"""
import hashlib
import json
import os
import re
import subprocess
import sys

CHUNK = 1024 * 1024
INFO = re.compile(r'([\d,]+) sequences; ([\d,]+) total (residues|bases)')


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        while True:
            block = stream.read(CHUNK)
            if not block:
                return digest.hexdigest()
            digest.update(block)


def count_fasta(path):
    records, residues = 0, 0
    with open(path, 'r', errors='replace') as stream:
        for line in stream:
            line = line.strip()
            if line.startswith('>'):
                records += 1
            elif line:
                residues += len(line)
    return records, residues


def write_receipt(path, value):
    with open(path + '.writing', 'w') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(path + '.writing', path)


def inventory(root):
    found = []
    for directory, _, names in os.walk(root):
        for name in sorted(names):
            path = os.path.join(directory, name)
            if os.path.isfile(path) and not os.path.islink(path):
                found.append({'name': os.path.relpath(path, '.').replace(os.sep, '/'),
                              'bytes': os.path.getsize(path), 'sha256': sha256_of(path)})
    return sorted(found, key=lambda item: item['name'])


def union_length(intervals):
    """The residues covered by inclusive intervals, each counted once."""
    total, end = 0, -1
    for first, last in sorted(intervals):
        if last <= end:
            continue
        first = max(first, end + 1)
        total += last - first + 1
        end = last
    return total


def mask_facts(operation):
    """Masked residues counted from the produced output (intervals, or lower-case letters of a soft-masked FASTA)."""
    name, form = operation['output_name'], operation['output_format']
    if not os.path.isfile(name):
        return None
    if form == 'interval':
        per_record, current, ordered = {}, None, []
        for line in open(name, errors='replace'):
            line = line.strip()
            if line.startswith('>'):
                current = line[1:].split()[0] if line[1:].split() else ''
                per_record.setdefault(current, [])
                ordered.append(current)
            elif line and current is not None:
                match = re.fullmatch(r'(\d+)\s*-\s*(\d+)', line)
                if match is None:
                    return {'parsed': False, 'masked_residues': None, 'records': None, 'residues': None}
                per_record[current].append((int(match.group(1)), int(match.group(2))))
        masked = sum(union_length(value) for value in per_record.values())
        return {'parsed': True, 'masked_residues': masked, 'records': len(ordered), 'residues': None}
    records, residues, masked = 0, 0, 0
    for line in open(name, errors='replace'):
        line = line.rstrip('\n')
        if line.startswith('>'):
            records += 1
        else:
            residues += len(line.strip())
            masked += sum(1 for letter in line if letter.islower() or letter in 'nNxX')
    return {'parsed': True, 'masked_residues': masked, 'records': records, 'residues': residues}


def main(argv):
    if len(argv) != 2:
        return 2
    try:
        plan = json.load(open(argv[1]))
        stated = plan['input']
        if (os.path.getsize(stated['name']) != stated['size_bytes'] or sha256_of(stated['name']) != stated['sha256']
                or count_fasta(stated['name']) != (stated['records'], stated['residues'])):
            return 2
    except (OSError, KeyError, ValueError, TypeError):
        return 2
    receipt = {'version': 'blast_preparation_receipt_v1', 'plan_sha256': sha256_of(argv[1]), 'steps': [],
               'files': [], 'info': None, 'readback': None, 'mask': None, 'input_verified': True}
    failed = False
    for step in plan['steps']:
        if failed:
            receipt['steps'].append({'name': step['name'], 'ran': False, 'returncode': None})
            continue
        if step['name'] == 'build' and plan['kind'] == 'database_build':
            os.makedirs(os.path.dirname(plan['operation']['output_prefix']), exist_ok=True)
        stdout_path, stderr_path = step['name'] + '.stdout', step['name'] + '.stderr'
        with open(stdout_path, 'wb') as out, open(stderr_path, 'wb') as err:
            try:
                done = subprocess.run(step['argv'], stdout=out, stderr=err, stdin=subprocess.DEVNULL)
                code = done.returncode
            except OSError:
                code = 127
        receipt['steps'].append({'name': step['name'], 'ran': True, 'returncode': code})
        if code != 0:
            failed = True
        elif step['name'] == 'check':
            entries, letters = 0, 0
            for line in open(stdout_path, errors='replace'):
                parts = line.split()
                if len(parts) == 2 and parts[1].isdigit():
                    entries, letters = entries + 1, letters + int(parts[1])
            receipt['readback'] = {'entries': entries, 'letters': letters}
        elif step['name'] == 'info':
            match = INFO.search(open(stdout_path, errors='replace').read())
            receipt['info'] = (None if match is None else
                               {'sequences': int(match.group(1).replace(',', '')),
                                'letters': int(match.group(2).replace(',', '')), 'unit': match.group(3)})
    if plan['kind'] == 'database_build':
        receipt['files'] = inventory(os.path.dirname(plan['operation']['output_prefix']))
    else:
        receipt['mask'] = mask_facts(plan['operation'])
        name = plan['operation']['output_name']
        if os.path.isfile(name):
            receipt['files'] = [{'name': name, 'bytes': os.path.getsize(name), 'sha256': sha256_of(name)}]
    write_receipt(plan['receipt'], receipt)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
