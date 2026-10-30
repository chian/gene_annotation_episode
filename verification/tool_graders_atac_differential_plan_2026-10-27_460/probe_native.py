"""Explicit synthetic native cases; no production grader or biological claim."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys

ATTEMPT = Path(os.environ['ATAC_NATIVE_ATTEMPT'])
MACS = Path(sys.executable).parent / 'macs2'
commands = []


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def execute(name, args):
    out, err = ATTEMPT / (name + '.stdout.txt'), ATTEMPT / (name + '.stderr.txt')
    argv = [str(MACS), *list(map(str, args))]
    with out.open('wb') as stdout, err.open('wb') as stderr:
        result = subprocess.run(argv, cwd=ATTEMPT, stdout=stdout, stderr=stderr, check=False)
    commands.append({'name': name, 'argv': argv, 'cwd': str(ATTEMPT), 'returncode': result.returncode,
                     'stdout': str(out), 'stderr': str(err)})
    save(ATTEMPT / 'commands.json', commands)
    if result.returncode:
        raise SystemExit(result.returncode)


tracks = ATTEMPT / 'explicit_tracks'
tracks.mkdir()
values = {'t1': [0, 20, 10, 2, 0], 'c1': [1, 1, 1, 1, 1],
          't2': [0, 2, 20, 40, 0], 'c2': [2, 2, 2, 2, 2]}
for name, numbers in values.items():
    (tracks / (name + '.bdg')).write_text(''.join(
        f'chrToy\t{i * 100}\t{(i + 1) * 100}\t{number}\n' for i, number in enumerate(numbers)))
save(tracks / 'INPUT.json', {'origin': 'explicit synthetic fixture, not observed biology',
    'coordinate_convention': 'zero_based_half_open', 'reference': {'chrToy': 500},
    'tracks': values, 'declared_depth_millions': [1, 2],
    'parameters': {'cutoff': 3, 'minlen_bp': 50, 'maxgap_bp': 0, 'native_pseudocount': 0.01}})
execute('explicit_bdgdiff', ['bdgdiff', '--t1', tracks / 't1.bdg', '--c1', tracks / 'c1.bdg',
    '--t2', tracks / 't2.bdg', '--c2', tracks / 'c2.bdg', '--d1', '1', '--d2', '2',
    '-C', '3', '-l', '50', '-g', '0', '--outdir', tracks,
    '-o', 'condition1.bed', 'condition2.bed', 'common.bed'])

# A separately selected diagnostic calculation exports full native arrays.
import numpy as np
from MACS2.IO import BedGraphIO, ScoreTrack
inputs = [BedGraphIO.bedGraphIO(str(tracks / (name + '.bdg'))).build_bdgtrack()
          for name in ('t1', 'c1', 't2', 'c2')]
native = ScoreTrack.TwoConditionScores(*inputs, 1.0, 0.5)
native.build()
native.finalize()
diagnostic = []
for ordinal, chrom in enumerate(sorted(native.get_chr_names())):
    arrays = native.get_data_by_chr(chrom)
    filenames = []
    for label, array in zip(('positions', 'condition1_vs_background', 'condition2_vs_background', 'condition1_vs_condition2'), arrays):
        filename = f'native_{ordinal}_{label}.npy'
        np.save(tracks / filename, array, allow_pickle=False)
        filenames.append(filename)
    diagnostic.append({'chromosome': chrom.decode(), 'native_positions': arrays[0].tolist(),
        'native_condition1_vs_background': arrays[1].tolist(),
        'native_condition2_vs_background': arrays[2].tolist(),
        'native_condition1_vs_condition2': arrays[3].tolist(), 'array_files': filenames})
save(tracks / 'NATIVE_DIAGNOSTIC.json', {'operation': 'explicit separate native TwoConditionScores build/finalize/export',
    'source_values': values, 'condition_factors': [1, 0.5], 'native_pseudocount': 0.01, 'arrays': diagnostic})

import pysam
reads = ATTEMPT / 'bam_inputs'
reads.mkdir()
header = {'HD': {'VN': '1.6', 'SO': 'coordinate'}, 'SQ': [{'SN': 'chrToy', 'LN': 12000}]}
positions = {'condition1': list(range(1000, 1050)) + [6000 + i * 40 for i in range(50)] + [1000] * 5,
             'condition2': list(range(3000, 3100)) + [6000 + i * 40 for i in range(100)]}
for name, starts in positions.items():
    with pysam.AlignmentFile(reads / (name + '.bam'), 'wb', header=header) as output:
        for i, start in enumerate(sorted(starts)):
            row = pysam.AlignedSegment(output.header)
            row.query_name = f'{name}_synthetic_{i}'
            row.query_sequence = 'A' * 30
            row.flag = 0
            row.reference_id = 0
            row.reference_start = start
            row.mapping_quality = 60
            row.cigar = [(0, 30)]
            row.query_qualities = pysam.qualitystring_to_array('I' * 30)
            output.write(row)
save(reads / 'INPUT.json', {'origin': 'explicit coordinate-sorted synthetic BAMs, not biological observations',
    'header': header, 'coordinate_convention': 'zero_based_half_open', 'read_length_bp': 30,
    'single_end_starts': positions, 'selected_format': 'BAM', 'selected_keep_dup': 1,
    'declared_unique_start_counts': {k: len(set(v)) for k, v in positions.items()}})
depths = []
outputs = ATTEMPT / 'bam_outputs'
outputs.mkdir()
for name in positions:
    execute(name + '_callpeak', ['callpeak', '-t', reads / (name + '.bam'), '-f', 'BAM', '-g', '12000',
        '--keep-dup', '1', '--nomodel', '--shift', '-100', '--extsize', '200', '-q', '0.05',
        '-B', '-n', name, '--outdir', outputs, '--tempdir', ATTEMPT / 'temporary'])
    xls = outputs / (name + '_peaks.xls')
    found = re.findall(r'^# tags after filtering in treatment: ([0-9]+)$', xls.read_text(), re.MULTILINE)
    assert len(found) == 1 and int(found[0]) > 0, 'actual nonredundant native tag count required'
    depths.append({'condition': name, 'count': int(found[0]), 'units': 'tags_after_filtering',
                   'count_source_file': str(xls), 'depth_millions': int(found[0]) / 1000000})
save(outputs / 'DEPTH_INPUTS.json', depths)
execute('bam_bdgdiff', ['bdgdiff', '--t1', outputs / 'condition1_treat_pileup.bdg',
    '--c1', outputs / 'condition1_control_lambda.bdg', '--t2', outputs / 'condition2_treat_pileup.bdg',
    '--c2', outputs / 'condition2_control_lambda.bdg', '--d1', str(depths[0]['depth_millions']),
    '--d2', str(depths[1]['depth_millions']), '-C', '3', '-l', '50', '-g', '0', '--outdir', outputs,
    '-o', 'condition1_differential.bed', 'condition2_differential.bed', 'common.bed'])
files = []
for folder in (tracks, reads, outputs):
    for path in sorted(folder.iterdir()):
        if path.is_file():
            data = path.read_bytes()
            files.append({'path': str(path.relative_to(ATTEMPT)), 'size_bytes': len(data),
                          'sha256': hashlib.sha256(data).hexdigest()})
save(ATTEMPT / 'NATIVE_FILES.json', {'biological_validation': False, 'production_grader': False,
    'native_cli_commands': len(commands), 'separate_native_score_export': True, 'files': files})
