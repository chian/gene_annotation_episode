"""Caller-side retained fixture/example creation, separate from pure graders."""
from pathlib import Path
import hashlib
import json
import shutil

from gene_annotation_episode.cmalign_inputs import populate_cmalign_sheet
from gene_annotation_episode.cmalign_grader import calculate_cmalign_scores

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXTURES = ROOT / 'tests/fixtures/cmalign_graders'

def fasta(path):
    rows = []
    for line in path.read_text().splitlines():
        if line.startswith('>'):
            rows.append({'name': line[1:].split()[0], 'sequence': '', 'origin': 'newly_aligned'})
        elif line.strip():
            rows[-1]['sequence'] += line.strip()
    return rows

def main():
    receipts = json.loads((HERE / 'NATIVE_RECEIPTS.json').read_text())
    examples, hashes = {}, {}
    for run in receipts['runs']:
        if run['returncode']:
            continue
        name = run['case']
        source = HERE / 'native' / name
        dest = FIXTURES / 'native' / name
        dest.mkdir(parents=True, exist_ok=True)
        artifacts = []
        for file, fmt in [('alignment.sto','stockholm'),('scores.txt','cmalign_sfile'),
                          ('inserts.txt','cmalign_ifile'),('local_ends.txt','cmalign_elfile')]:
            if not (source / file).exists():
                continue
            shutil.copyfile(source / file, dest / file)
            raw = (source / file).read_bytes()
            hashes[str((dest/file).relative_to(FIXTURES))] = hashlib.sha256(raw).hexdigest()
            artifacts.append({'artifact_id': name+'/'+file, 'format':fmt, 'content':raw.decode(), 'complete':True})
        args = run['argv']
        model_file, sequence_file = Path(args[-2]), Path(args[-1])
        model_fields = dict(line.split(None,1) for line in model_file.read_text().splitlines()
                            if line.startswith(('NAME ', 'CLEN ')))
        settings = {'algorithm':'sample' if '--sample' in args else 'cyk' if '--cyk' in args else 'optacc',
            'global':'-g' in args, 'notrunc':'--notrunc' in args, 'matchonly':'--matchonly' in args,
            'sub':'--sub' in args,
            'noprob':'--noprob' in args, 'miss':'--miss' in args, 'mapali':'--mapali' in args,
            'banding':'nonbanded' if '--nonbanded' in args else 'hbanded',
            'cpu':int(args[args.index('--cpu')+1]), 'mxsize_mb':256, 'verbose':'--verbose' in args}
        if '--seed' in args:
            settings['seed'] = int(args[args.index('--seed')+1])
        metadata = {'operation':{'program':'cmalign','native_version':'1.1.5','settings':settings},
            'sequences':fasta(sequence_file),
            'model':{'name':model_fields['NAME'].strip(),'consensus_length':int(model_fields['CLEN'])}}
        if name in ('mapali', 'mapali_collision'):
            metadata['inherited_alignment'] = {'artifact_id':'tRNA5-training', 'format':'stockholm',
                'content':(HERE/'native/inputs/tRNA5.sto').read_text(),'complete':True}
        if name == 'mapali_collision':
            metadata['sequences'][0]['occurrence'] = 1
        (dest/'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
        sheet = populate_cmalign_sheet(artifacts, **metadata)
        scores = calculate_cmalign_scores(sheet)
        output = HERE/'examples'/name
        output.mkdir(parents=True, exist_ok=True)
        (output/'sheet.json').write_text(json.dumps(sheet, indent=2, allow_nan=False)+'\n')
        (output/'scores.json').write_text(json.dumps(scores, indent=2, allow_nan=False)+'\n')
        examples[name] = {'status':scores['status'], 'sequences':[{k:r[k] for k in
            ('name','origin','retained_nucleotides','model_match_nucleotides','model_gap_positions','deleted_model_positions',
             'missing_model_positions','total_insert_nucleotides','total_local_end_nucleotides','omitted_nucleotides',
             'original_length','model_length','model_occupancy','sequence_matched_coverage',
             'native_bit_score','native_avg_pp','posterior_lower_mean','posterior_upper_mean',
             'posterior_available_count','posterior_unavailable_count')} for r in scores['sequences']],
             'pairs':scores['summary']['pair_totals']}
    (FIXTURES/'NATIVE_SHA256.json').write_text(json.dumps(hashes, indent=2)+'\n')
    (HERE/'NUMERICAL_EXAMPLES.json').write_text(json.dumps(examples, indent=2)+'\n')
    print(json.dumps(examples, indent=2))

if __name__ == '__main__':
    main()
