"""The program the ``rna_structure_agreement`` job runs on its resource: ``python driver.py plan.json``.

Standard library only (like ``usalign_driver``): the job stages this file, its plan and the spans of the target beside each other. It
decides nothing. The plan is ``{'cmfetch': <executable>, 'cmalign': <executable>, 'database': <Rfam.cm>, 'families': [{'accession',
'span', 'model', 'alignment'}]}``: for each family it runs ``cmfetch -o <model> <database> <accession>`` (the family's covariance
model out of the pressed database) and ``cmalign --cpu 1 -o <alignment> <model> <span>`` (the span of the target, one FASTA record;
the default local alignment, Stockholm output) and writes ONE JSON, ``alignments.json``, with one entry per family, in plan order:
the accession, the alignment file, the two return codes and the status.

Status of a family: ``aligned``, ``cmfetch_exit_nonzero`` or ``cmalign_exit_nonzero``. Exit status 0 when the plan was read and every
family was run (a family's own status is in the JSON); exit status 2: the plan is not what this driver reads."""
import json
import subprocess
import sys

OUTPUT_FILE = 'alignments.json'
PLAN_KEYS = {'cmfetch', 'cmalign', 'database', 'families'}
FAMILY_KEYS = {'accession', 'span', 'model', 'alignment'}


def main(argv):
    if len(argv) != 2:
        return 2
    plan = json.load(open(argv[1]))
    if not isinstance(plan, dict) or set(plan) != PLAN_KEYS or any(set(item) != FAMILY_KEYS for item in plan['families']):
        return 2
    results = []
    for family in plan['families']:
        entry = {'accession': family['accession'], 'alignment': family['alignment']}
        fetched = subprocess.run([plan['cmfetch'], '-o', family['model'], plan['database'], family['accession']],
                                 stdin=subprocess.DEVNULL, capture_output=True, text=True)
        if fetched.returncode != 0:
            results.append({**entry, 'status': 'cmfetch_exit_nonzero', 'cmfetch_returncode': fetched.returncode,
                            'cmalign_returncode': None})
            continue
        aligned = subprocess.run([plan['cmalign'], '--cpu', '1', '-o', family['alignment'], family['model'], family['span']],
                                 stdin=subprocess.DEVNULL, capture_output=True, text=True)
        results.append({**entry, 'status': 'aligned' if aligned.returncode == 0 else 'cmalign_exit_nonzero',
                        'cmfetch_returncode': 0, 'cmalign_returncode': aligned.returncode})
    json.dump({'families': results}, open(OUTPUT_FILE, 'w'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
