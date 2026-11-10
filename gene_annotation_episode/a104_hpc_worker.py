"""One store-free A104 scientific work unit inside an original PBS allocation.

The shared HPC episode owns submission, monitoring and original-result custody.
This leaf runs selected programs sequentially and retains native artifacts. It
does not assign functions, award episode credit, or impose research deadlines.
The file is deliberately executable without installing the application package.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import socket
import subprocess
import sys
import tarfile
import time
from urllib.request import Request, urlopen


VERSION = 'a104_native_phylogeny_work_v1'
MUSCLE_URL = 'https://github.com/rcedgar/muscle/releases/download/v5.3/muscle-linux-x86.v5.3'
IQTREE_URL = 'https://github.com/iqtree/iqtree2/releases/download/v2.4.0/iqtree-2.4.0-Linux-intel.tar.gz'
IQTREE_MEMBER = 'iqtree-2.4.0-Linux-intel/bin/iqtree2'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError(code)


def write_json(path, value):
    path.write_text(canonical(value)+'\n')


def read_fasta(text):
    rows, label, parts = {}, None, []
    for line in text.splitlines():
        if line.startswith('>'):
            if label is not None:
                require(label not in rows, 'duplicate_native_alignment_tip')
                rows[label] = ''.join(parts)
            label, parts = line[1:].split()[0], []
        elif line.strip():
            require(label is not None, 'fasta_header_required')
            parts.append(line.strip())
    if label is not None:
        require(label not in rows, 'duplicate_native_alignment_tip')
        rows[label] = ''.join(parts)
    return rows


def validate_request(value):
    require(value.get('version') == VERSION, 'a104_native_request_version')
    require(type(value.get('threads')) is int and 1 <= value['threads'] <= 8, 'a104_native_cpu_shape')
    require(type(value.get('seed')) is int and value['seed'] > 0, 'a104_native_seed')
    require(value.get('model') in {'LG', 'MFP'}, 'a104_native_model_not_selected')
    require(value.get('bootstrap_replicates') == 1000, 'a104_native_bootstrap_method')
    require(type(value.get('analyses')) is list and value['analyses'], 'a104_native_analyses_required')
    names = set()
    for analysis in value['analyses']:
        require(analysis['name'] not in names and analysis['name'].replace('_', '').isalnum(),
                'a104_native_analysis_identity')
        names.add(analysis['name'])
        require(analysis.get('model', value['model']) in {'LG', 'MFP'}, 'a104_native_analysis_model_not_selected')
        require(type(analysis.get('seed', value['seed'])) is int and analysis.get('seed', value['seed']) > 0,
                'a104_native_analysis_seed')
        require(analysis['purpose'] in {'family', 'organismal_reference', 'regional', 'sensitivity'},
                'a104_native_analysis_purpose')
        entries = analysis['entries']
        require(4 <= len(entries) <= 128, 'a104_native_panel_shape')
        labels = set()
        for row in entries:
            require(row['tip_id'] not in labels and row['tip_id'].replace('_', '').isalnum(),
                    'a104_native_unique_opaque_tip_required')
            labels.add(row['tip_id'])
            sequence = row['sequence']
            require(type(sequence) is str and sequence and set(sequence) <= set('ACDEFGHIKLMNPQRSTVWYBXZJUO'),
                    'a104_native_actual_protein_sequence_required')
            require(sha(sequence.encode()) == row['sequence_sha256'], 'a104_native_panel_sequence_digest')
            lengths = row.get('part_lengths', [len(sequence)])
            require(lengths and all(type(n) is int and n > 0 for n in lengths) and sum(lengths) == len(sequence),
                    'a104_native_marker_partition_lengths')
        require(len({len(row.get('part_lengths', [len(row['sequence'])])) for row in entries}) == 1,
                'a104_native_marker_membership_inconsistent')
    return value


def _download(url, destination):
    # Selected official release URLs only. Redirect response bytes and the final
    # URL are retained; programs are pinned to the actual acquired byte hash.
    require(url in {MUSCLE_URL, IQTREE_URL}, 'a104_native_software_url_not_selected')
    with urlopen(Request(url, headers={'User-Agent': 'gene-annotation-episode-A104/1'})) as response:
        data = response.read()
        observed = {'requested_url': url, 'resolved_url': response.url,
                    'response_headers': list(response.headers.items()), 'bytes': len(data), 'sha256': sha(data)}
    destination.write_bytes(data)
    return observed


def _command(argv, directory, stem, environment):
    start = time.monotonic()
    with (directory/(stem+'.stdout')).open('wb') as out, (directory/(stem+'.stderr')).open('wb') as err:
        process = subprocess.run(argv, cwd=directory, env=environment, stdout=out, stderr=err)
    result = {'argv': argv, 'returncode': process.returncode, 'elapsed_seconds': time.monotonic()-start,
              'stdout_path': str(directory/(stem+'.stdout')), 'stderr_path': str(directory/(stem+'.stderr'))}
    write_json(directory/(stem+'.execution.json'), result)
    require(process.returncode == 0, 'a104_native_command_failed:'+stem)
    return result


def prepare_software(directory):
    """Acquire small program assets; never execute biological software here."""
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory/'software-manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for item in manifest['files']:
            path = directory/item['name']
            require(path.is_file() and not path.is_symlink() and sha(path.read_bytes()) == item['sha256'],
                    'a104_staged_software_changed')
        return manifest
    acquisitions = {'muscle': _download(MUSCLE_URL, directory/'muscle'),
                    'iqtree_archive': _download(IQTREE_URL, directory/'iqtree.tar.gz')}
    with tarfile.open(directory/'iqtree.tar.gz', 'r:gz') as archive:
        selected = archive.getmember(IQTREE_MEMBER)
        require(selected.isfile(), 'a104_iqtree_binary_not_regular')
        (directory/'iqtree2').write_bytes(archive.extractfile(selected).read())
        # Keep only ordinary companion shared libraries under a confined flat
        # directory. No archive path is ever passed to extract/extractall.
        for member in archive.getmembers():
            basename = Path(member.name).name
            if member.isfile() and ('.so' in basename) and basename not in {'', '.', '..'}:
                (directory/basename).write_bytes(archive.extractfile(member).read())
    for name in ('muscle', 'iqtree2'):
        (directory/name).chmod(0o555)
    manifest = {'acquisitions': acquisitions, 'files': [
        {'name': path.name, 'sha256': sha(path.read_bytes()), 'size_bytes': path.stat().st_size}
        for path in sorted(directory.iterdir()) if path.is_file()]}
    write_json(manifest_path, manifest)
    return manifest


def software(directory, environment, staged_directory):
    require((staged_directory/'software-manifest.json').is_file(), 'a104_native_software_not_staged')
    manifest = prepare_software(staged_directory)
    directory.mkdir()
    for item in manifest['files']:
        shutil.copy2(staged_directory/item['name'], directory/item['name'])
    result = {}
    native_environment = {**environment, 'LD_LIBRARY_PATH': str(directory)}
    for name, executable, flag in (('muscle', directory/'muscle', '-version'),
                                    ('iqtree', directory/'iqtree2', '--version')):
        executable.chmod(0o555)
        execution = _command([str(executable), flag], directory, name+'-version', native_environment)
        version = (directory/(name+'-version.stdout')).read_text(errors='replace') + \
                  (directory/(name+'-version.stderr')).read_text(errors='replace')
        require(('5.3' if name == 'muscle' else '2.4.0') in version, 'a104_native_software_version_conflict')
        result[name] = {'path': str(executable), 'sha256': sha(executable.read_bytes()),
                        'size_bytes': executable.stat().st_size, 'version_output': version, 'execution': execution}
    return result, manifest, native_environment


def _side(labels, universe):
    first, second = tuple(sorted(labels)), tuple(sorted(universe-set(labels)))
    return min((first, second), key=lambda values: (len(values), values))


def tree_summary(text):
    from Bio import Phylo
    tree = Phylo.read(io.StringIO(text), 'newick')
    tips = [row.name for row in tree.get_terminals()]
    require(len(tips) == len(set(tips)) and all(tips), 'a104_native_tree_tip_identity')
    universe, split_rows = set(tips), {}
    for node in tree.find_clades():
        if node is tree.root:
            continue
        labels = {tip.name for tip in node.get_terminals()}
        if len(labels) < 2 or len(universe-labels) < 2:
            continue
        side = _side(labels, universe)
        row = split_rows.setdefault(side, {'side': list(side), 'complement': sorted(universe-set(side)),
            'native_support_values': [], 'native_branch_lengths': []})
        if node.confidence is not None:
            require(0 <= node.confidence <= 100, 'a104_native_branch_support_scale')
            row['native_support_values'].append(float(node.confidence))
        if node.branch_length is not None:
            row['native_branch_lengths'].append(float(node.branch_length))
    for row in split_rows.values():
        supports = set(row['native_support_values'])
        row['support_percent'] = next(iter(supports)) if len(supports) == 1 else None
        row['support_state'] = 'known' if len(supports) == 1 else 'conflict' if supports else 'unknown'
    return {'tip_ids': sorted(universe), 'splits': list(split_rows.values()),
            'biological_root': 'unestablished', 'representation_root_not_ancestry': True}


def bootstrap_counts(path, reference):
    from Bio import Phylo
    universe, counts, usable, excluded = set(reference['tip_ids']), Counter(), 0, 0
    with path.open() as stream:
        for tree in Phylo.parse(stream, 'newick'):
            labels = [row.name for row in tree.get_terminals()]
            if len(labels) != len(set(labels)) or set(labels) != universe:
                excluded += 1
                continue
            usable += 1
            observed = set()
            for node in tree.find_clades():
                side = {row.name for row in node.get_terminals()}
                if len(side) >= 2 and len(universe-side) >= 2:
                    observed.add(_side(side, universe))
            counts.update(observed)
    return {'usable_replicates': usable, 'excluded_replicates': excluded,
            'splits': [{'side': row['side'], 'matches': counts[tuple(row['side'])], 'denominator': usable,
                        'frequency': counts[tuple(row['side'])]/usable if usable else None}
                       for row in reference['splits']]}


def alignment_correspondence(aligned, entries):
    originals = {row['tip_id']: row['sequence'] for row in entries}
    require(set(aligned) == set(originals), 'a104_native_alignment_membership_conflict')
    require(len({len(sequence) for sequence in aligned.values()}) == 1, 'a104_native_alignment_not_rectangular')
    for label, sequence in aligned.items():
        require(sequence.replace('-', '').replace('.', '').upper() == originals[label],
                'a104_native_alignment_changed_original_sequence')
    rows = []
    for label, sequence in aligned.items():
        original_index, mapping = 0, []
        for column, symbol in enumerate(sequence):
            if symbol not in '-.':
                if mapping and mapping[-1][0]+mapping[-1][2] == column:
                    mapping[-1][2] += 1
                else:
                    mapping.append([column, original_index, 1])
                original_index += 1
        rows.append({'tip_id': label, 'original_length': len(originals[label]),
                     'alignment_to_residue_segments': mapping})
    return {'columns': len(next(iter(aligned.values()))), 'rows': rows}


def run_analysis(analysis, request, programs, environment, directory):
    directory.mkdir()
    fasta = ''.join('>'+row['tip_id']+'\n'+row['sequence']+'\n' for row in analysis['entries'])
    (directory/'input.fasta').write_text(fasta)
    muscle = [programs['muscle']['path'], '-align', 'input.fasta', '-output', 'aligned.fasta',
              '-threads', str(request['threads']), '-randseed', str(analysis.get('seed', request['seed'])),
              '-perturb', '0', '-perm', 'none', '-consiters', '2', '-refineiters', '100']
    partitions = []
    part_count = len(analysis['entries'][0].get('part_lengths', [1]))
    if part_count > 1:
        # Align orthologous markers separately before concatenating columns.
        # A raw concatenation must not permit alignment across gene boundaries.
        aligned_parts, executions, offset = [], [], 0
        for part_index in range(part_count):
            part_directory = directory/('marker_'+str(part_index))
            part_directory.mkdir()
            part_entries = []
            for row in analysis['entries']:
                start = sum(row['part_lengths'][:part_index])
                symbols = row['sequence'][start:start+row['part_lengths'][part_index]]
                part_entries.append({'tip_id': row['tip_id'], 'sequence': symbols})
            (part_directory/'input.fasta').write_text(''.join('>'+row['tip_id']+'\n'+row['sequence']+'\n'
                                                            for row in part_entries))
            executions.append(_command(muscle, part_directory, 'muscle', environment))
            aligned = read_fasta((part_directory/'aligned.fasta').read_text())
            alignment_correspondence(aligned, part_entries)
            aligned_parts.append(aligned)
            columns = len(next(iter(aligned.values())))
            partitions.append({'name': 'marker_'+str(part_index), 'start_1based': offset+1,
                               'end_1based_inclusive': offset+columns})
            offset += columns
        (directory/'aligned.fasta').write_text(''.join('>'+row['tip_id']+'\n'+
            ''.join(part[row['tip_id']] for part in aligned_parts)+'\n' for row in analysis['entries']))
        # An AA token in a RAxML partition is interpreted as an external
        # rate-matrix filename by IQ-TREE 2.4 when -m LG is specified. Use
        # explicit NEXUS model bindings rather than relying on that token.
        (directory/'partitions.txt').write_text('#nexus\nbegin sets;\n'+''.join(
            'charset '+row['name']+' = '+str(row['start_1based'])+'-'+str(row['end_1based_inclusive'])+';\n'
            for row in partitions)+'charpartition markers = '+', '.join(
            'LG:'+row['name'] for row in partitions)+';\nend;\n')
        alignment_execution = {'returncode': 0, 'stages': executions,
                               'elapsed_seconds': sum(row['elapsed_seconds'] for row in executions)}
    else:
        alignment_execution = _command(muscle, directory, 'muscle', environment)
    iqtree = [programs['iqtree']['path'], '-s', 'aligned.fasta', '-st', 'AA', '-m', analysis.get('model', request['model']),
              '-bb', str(request['bootstrap_replicates']), '-wbt', '-nt', str(request['threads']),
              '-seed', str(analysis.get('seed', request['seed'])), '-keep-ident', '-pre', 'result']
    if partitions:
        iqtree.extend(['-p', 'partitions.txt'])
    tree_execution = _command(iqtree, directory, 'iqtree', environment)
    aligned_text = (directory/'aligned.fasta').read_text()
    aligned = read_fasta(aligned_text)
    correspondence = alignment_correspondence(aligned, analysis['entries'])
    ml_text, consensus_text = (directory/'result.treefile').read_text(), (directory/'result.contree').read_text()
    summary = tree_summary(ml_text)
    require(set(summary['tip_ids']) == set(aligned), 'a104_native_tree_alignment_membership_conflict')
    report = (directory/'result.iqtree').read_text()
    require('ultrafast bootstrap' in report.lower() and '1000' in report, 'a104_native_support_report_missing')
    bootstraps = bootstrap_counts(directory/'result.ufboot', summary)
    require(bootstraps['usable_replicates'] == request['bootstrap_replicates'] and bootstraps['excluded_replicates'] == 0,
            'a104_native_bootstrap_population_conflict')
    files = [{'name': str(path.relative_to(directory)), 'path': str(path), 'sha256': sha(path.read_bytes()), 'size_bytes': path.stat().st_size}
             for path in sorted(directory.rglob('*')) if path.is_file()]
    return {'name': analysis['name'], 'purpose': analysis['purpose'], 'input_fasta': fasta,
        'input_sha256': sha(fasta.encode()), 'alignment_fasta': aligned_text, 'correspondence': correspondence,
        'maximum_likelihood_tree': ml_text, 'consensus_tree': consensus_text, 'native_report': report,
        'support_method': 'ultrafast_bootstrap', 'support_scale': 'percent', 'tree_summary': summary,
        'bootstrap_population': bootstraps, 'alignment_execution': alignment_execution,
        'tree_execution': tree_execution, 'marker_partitions': partitions, 'native_files': files}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 2 and args[0] == '--prepare-software':
        manifest = prepare_software(Path(args[1]).resolve())
        print(canonical({'event': 'a104_program_assets_prepared', 'files': manifest['files']}), flush=True)
        return 0
    require(len(args) == 1, 'a104_native_request_path_required')
    request_path = Path(args[0]).resolve()
    raw = request_path.read_bytes()
    request = validate_request(json.loads(raw))
    directory = Path.cwd().resolve()
    result = {'version': VERSION, 'program': 'a104_phylogeny_native', 'completed': False, 'returncode': 1,
        'case_id': request['case_id'], 'request_sha256': sha(raw), 'worker_sha256': sha(Path(__file__).read_bytes()),
        'pbs_job_id': os.environ.get('PBS_JOBID'), 'compute_hostname': socket.gethostname(),
        'platform': platform.platform(), 'analyses': [], 'failure': None}
    started = time.monotonic()
    try:
        require(result['pbs_job_id'] and not result['compute_hostname'].startswith(('aurora-uan', 'login')),
                'a104_biological_computation_requires_pbs_compute_allocation')
        require(platform.machine() == 'x86_64', 'a104_native_release_architecture')
        environment = {**os.environ, **{name: str(request['threads']) for name in
            ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}}
        for name in ('TMPDIR', 'TMP', 'TEMP', 'XDG_CACHE_HOME'):
            path = directory/name.lower()
            path.mkdir(exist_ok=True)
            environment[name] = str(path)
        programs, acquisitions, environment = software(directory/'software', environment, request_path.parent/'software')
        result.update(software=programs, acquisitions=acquisitions)
        for analysis in request['analyses']:
            result['analyses'].append(run_analysis(analysis, request, programs, environment, directory/analysis['name']))
            write_json(directory/'partial-result.json', result)
        result.update(completed=True, returncode=0)
    except Exception as error:
        result['failure'] = {'type': type(error).__name__, 'message': str(error)}
    result['elapsed_seconds'] = time.monotonic()-started
    result['native_children_peak_rss_kib'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    write_json(directory/'result.json', result)
    print(canonical({key: result[key] for key in ('program', 'case_id', 'completed', 'returncode', 'pbs_job_id', 'compute_hostname', 'failure')}), flush=True)
    return result['returncode']


if __name__ == '__main__':
    raise SystemExit(main())
