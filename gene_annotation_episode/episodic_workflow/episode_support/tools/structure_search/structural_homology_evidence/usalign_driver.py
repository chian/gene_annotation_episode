"""The program the ``partner_contacts`` job runs on its resource: ``python driver.py plan.json``.

Standard library only (like ``all_vs_all_driver``): the job stages this file, its plan, the target's model and the hit chains
beside each other. It decides nothing. The plan is ``{'usalign': <the USalign executable>, 'pairs': [{'id', 'first',
'second'}]}``: for each pair it runs ``USalign <first> <second> -m -`` (the default alignment of the first chain of each file,
sequence-independent; ``-m -`` prints the rotation matrix to standard output) and writes ONE JSON, ``alignments.json``, with
one entry per pair, in plan order.

THE PROGRAM'S OUTPUT, read faithfully (``a102_structural_aligners.md``, "US-align installed locally"; the forms are those of
Version 20261019)::

    Length of Structure_1: 70 residues
    Length of Structure_2: 69 residues
    Aligned length= 69, RMSD=   0.82, Seq_ID=n_identical/n_aligned= 1.000
    TM-score= 0.92809 (normalized by length of Structure_1: L=70, d0=2.92)
    TM-score= 0.94064 (normalized by length of Structure_2: L=69, d0=2.89)
    (":" denotes residue pairs of d < 5.0 Angstrom, "." denotes other aligned residues)
    <the aligned sequence of structure 1, '-' for a gap>
    <the marker line>
    <the aligned sequence of structure 2>
    ------ The rotation matrix to rotate Structure_1 to Structure_2 ------
    m   t[m]   u[m][0]   u[m][1]   u[m][2]        (three rows)

THE ALIGNED RESIDUE PAIRS. The program prints no residue numbers. Its i-th residue of a structure is the i-th C-alpha atom
line (``ATOM``, atom name `` CA ``) of the file, so the pairs are read from the two aligned sequences column by column
(a column with a letter on both sides is one pair) against the residue identifiers this driver reads from the two files
(residue number and insertion code, columns 23 to 27, of the C-alpha lines): the pair is given in the files' own residue
identifiers. The number of residues the driver reads from each file must equal the program's ``Length of Structure_n`` and the
number of pairs its ``Aligned length``; otherwise the pair's status is ``output_does_not_match_the_files``.

THE TRANSFORM. ``X = t[0] + u[0][0] x + u[0][1] y + u[0][2] z`` (and rows 1 and 2) rotates structure 1 onto structure 2; the
driver gives ``rotation`` (rows ``u``) and ``translation`` (``t``) as the program printed them.

Status of a pair: ``aligned``, ``usalign_exit_nonzero`` or ``output_does_not_match_the_files``. Exit status 0 when the plan
was read and every pair was run (a pair's own status is in the JSON); exit status 2: the plan is not what this driver reads."""
import json
import re
import subprocess
import sys

OUTPUT_FILE = 'alignments.json'
LENGTH = re.compile(r'^Length of Structure_([12]):\s*(\d+) residues')
ALIGNED = re.compile(r'^Aligned length=\s*(\d+), RMSD=\s*([0-9.]+), Seq_ID=n_identical/n_aligned=\s*([0-9.]+)')
TM_SCORE = re.compile(r'^TM-score=\s*([0-9.]+) \(normalized by length of Structure_([12]): L=(\d+), d0=([0-9.]+)\)')
MATRIX_ROW = re.compile(r'^([012])\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s*$')
MARKER = '(":" denotes residue pairs of'


def residue_identifiers(path):
    """The residue identifiers (``resSeq`` + insertion code, columns 23 to 27) of the C-alpha lines of a PDB file, in file order."""
    return [line[22:27].strip() for line in open(path) if line.startswith('ATOM') and line[12:16] == ' CA ']


def parse_output(text, first_ids, second_ids):
    """The facts of one USalign output (see the module), or ``None`` for a field that does not read as stated."""
    lines = text.splitlines()
    lengths, scores, rows = {}, {}, {}
    aligned = None
    for line in lines:
        found = LENGTH.match(line)
        if found:
            lengths[found.group(1)] = int(found.group(2))
        found = ALIGNED.match(line)
        if found:
            aligned = {'aligned_length': int(found.group(1)), 'rmsd_A': float(found.group(2)), 'seq_id': float(found.group(3))}
        found = TM_SCORE.match(line)
        if found:
            scores[found.group(2)] = {'tm_score': float(found.group(1)), 'normalized_by_length': int(found.group(3)),
                                      'd0_A': float(found.group(4))}
        found = MATRIX_ROW.match(line)
        if found:
            rows[int(found.group(1))] = [float(found.group(index)) for index in range(2, 6)]
    marker = [index for index, line in enumerate(lines) if line.startswith(MARKER)]
    if (set(lengths) != {'1', '2'} or aligned is None or set(scores) != {'1', '2'} or len(marker) != 1 or set(rows) != {0, 1, 2}
            or lengths['1'] != len(first_ids) or lengths['2'] != len(second_ids)):
        return None
    block = lines[marker[0] + 1:marker[0] + 4]
    if len(block) != 3 or len(block[0]) != len(block[2]):
        return None
    first_line, second_line = block[0], block[2]
    pairs, i, j = [], 0, 0
    for a, b in zip(first_line, second_line):
        if a != '-' and b != '-':
            pairs.append([first_ids[i], second_ids[j]])
        i += a != '-'
        j += b != '-'
    if (i, j) != (len(first_ids), len(second_ids)) or len(pairs) != aligned['aligned_length']:
        return None
    return {**aligned, 'length_1': lengths['1'], 'length_2': lengths['2'], 'tm_score_1': scores['1'], 'tm_score_2': scores['2'],
            'aligned': pairs, 'translation': [rows[m][0] for m in range(3)], 'rotation': [rows[m][1:] for m in range(3)]}


def main(argv):
    if len(argv) != 2:
        return 2
    plan = json.load(open(argv[1]))
    if not isinstance(plan, dict) or set(plan) != {'usalign', 'pairs'}:
        return 2
    results = []
    for pair in plan['pairs']:
        done = subprocess.run([plan['usalign'], pair['first'], pair['second'], '-m', '-'], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True)
        entry = {'id': pair['id'], 'first': pair['first'], 'second': pair['second'], 'returncode': done.returncode}
        if done.returncode != 0:
            results.append({**entry, 'status': 'usalign_exit_nonzero'})
            continue
        parsed = parse_output(done.stdout, residue_identifiers(pair['first']), residue_identifiers(pair['second']))
        results.append({**entry, 'status': 'output_does_not_match_the_files'} if parsed is None
                       else {**entry, 'status': 'aligned', **parsed})
    json.dump({'pairs': results}, open(OUTPUT_FILE, 'w'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
