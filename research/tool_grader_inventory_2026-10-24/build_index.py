"""Assemble the source inventory; never execute a scientific tool or service."""
from collections import Counter
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
sources = {name: json.loads((ROOT / (name + '.json')).read_text())
           for name in ('current', 'bvbrc', 'gentner', 'providers')}
rows = []


def add(source, key, name, kind, details, resources=None):
    rows.append(dict(source=source, source_key=key, name=name, kind=kind,
                     details=details, resource_information=resources))


for row in sources['current']['entries']:
    add('current', 'entries/' + row['name'] + '/' + row['resources'],
        row['name'], row['category'], row['inventory_group'], row['resources'])
for row in sources['current']['conditional_entries']:
    add('current', 'conditional_entries/' + row['name'], row['name'],
        'infrastructure', 'Optional caller-bound execution timing estimate', row.get('resources'))
for row in sources['bvbrc']['registered_tools']:
    add('bvbrc', 'registered_tools/' + row['name'], row['name'],
        row['category'], row['actual_operation'], row['resource'])
for row in sources['bvbrc']['service_families']:
    add('bvbrc', 'service_families/' + row['name'], row['name'],
        row['category'], row['description'], row['resource'])
for section in ('biomni_entries', 'gentner_owned_entries'):
    for row in sources['gentner'][section]:
        add('gentner', section + '/' + row['id'], row['name'],
            row['classification'], row['description'], row.get('execution_routes'))
for row in sources['providers']['entries']:
    add('providers', 'entries/' + row['name'], row['name'],
        row['inventory_kind'], row['description'], row['resources'])

# Filesystem presence is separate from a catalog binding and from a successful
# native run. Package test executables are accounted for without calling them
# scientific tools. Preparation helpers also do not gain an invented score.
native_analyses = set('''cmalign cmbuild cmcalibrate cmemit cmscan cmsearch cmstat
blastn blastp blastx tblastn tblastx blastn_vdb tblastn_vdb psiblast deltablast
rpsblast rpstblastn dustmasker segmasker windowmasker alimask hmmalign hmmbuild
hmmemit hmmscan hmmsearch hmmsim hmmstat jackhmmer nhmmer nhmmscan phmmer
hmmerfm-exactmatch'''.split())
native_preparation = set('''cmconvert cmfetch cmpress blast_formatter blast_formatter_vdb
blast_vdb_cmd blastdb_aliastool blastdbcheck blastdbcmd convert2blastmask makeblastdb
makembindex makeprofiledb hmmconvert hmmfetch hmmlogo hmmpress makehmmerdb'''.split())
for folder, items in sources['current']['deployment']['local']['binary_directory_facts'].items():
    for item in items:
        name = Path(item['path']).name
        kind = ('native_analysis_or_model_program' if name in native_analyses else
                'native_preparation_or_reader_program' if name in native_preparation else
                'package_test_or_internal_helper')
        add('current', 'deployment/local/binary_directory_facts/' + folder + '/' + name,
            name, kind, item['scope'], {'local': 'file and executable bit present; binding/run not inferred'})

identity = [(r['source'], r['source_key']) for r in rows]
assert len(identity) == len(set(identity))
assert len(sources['gentner']['biomni_entries']) == 222
assert sum(r['registered_in_biomni_catalog'] for r in sources['gentner']['biomni_entries']) == 218
assert len(sources['bvbrc']['service_families']) == 31
assert len(sources['current']['entries']) == 115

index = {
    'inventory_date': '2026-10-24',
    'scope': 'Source inventory, not an availability assertion or a unique-algorithm count. '
             'Every observation preserves its source. Mode/format and true equivalence are '
             'established in per-tool contracts; wrappers are not independent evidence.',
    'sources': {name: {'file': name + '.json',
                      'sha256': hashlib.sha256((ROOT / (name + '.json')).read_bytes()).hexdigest(),
                      'counts': value['counts']} for name, value in sources.items()},
    'source_observation_count': len(rows),
    'source_observations_by_kind': dict(sorted(Counter(r['kind'] for r in rows).items())),
    'entries': rows,
}
(ROOT / 'index.json').write_text(json.dumps(index, indent=2) + '\n')
print(json.dumps({'source_observations': len(rows), 'source_observations_by_kind': index['source_observations_by_kind']}))
