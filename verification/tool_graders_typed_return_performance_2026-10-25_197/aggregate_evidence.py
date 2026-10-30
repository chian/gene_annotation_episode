"""Summarize retained terminal receipts and deduplicate completed pytest cases."""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

OWN = Path(__file__).resolve().parent
invocations = []
cases = {'candidate': {}, 'frozen_baseline': {}, 'running_invocations': []}
for command in sorted(OWN.glob('*/command.json')):
    directory = command.parent
    receipt = directory / 'receipt.json'
    if receipt.exists():
        row = json.loads(receipt.read_text())
        row.update(label=directory.name, terminal_collected=True)
    else:
        row = json.loads(command.read_text())
        row.update(label=directory.name, terminal_collected=False, exit_code=None)
        cases['running_invocations'].append(directory.name)
    invocations.append(row)
    xml = directory / 'tests.xml'
    if not receipt.exists() or not xml.exists():
        continue
    group = 'frozen_baseline' if directory.name.startswith('baseline_') else 'candidate'
    for test in ET.parse(xml).getroot().iter('testcase'):
        identity = test.attrib['classname'] + '::' + test.attrib['name']
        status = ('failed' if test.find('failure') is not None else
                  'error' if test.find('error') is not None else
                  'skipped' if test.find('skipped') is not None else 'passed')
        record = {'invocation': directory.name, 'status': status,
                  'seconds': test.attrib.get('time'), 'finished_at': row['finished_at']}
        cases[group].setdefault(identity, []).append(record)
for group in ['candidate', 'frozen_baseline']:
    for records in cases[group].values():
        records.sort(key=lambda row: row['finished_at'])
summary = {}
for group in ['candidate', 'frozen_baseline']:
    summary[group] = {'unique_completed_tests': len(cases[group]),
        'latest_status_counts': dict(Counter(rows[-1]['status'] for rows in cases[group].values())),
        'ever_failed_unique': sum(any(row['status'] in {'failed', 'error'} for row in rows)
                                  for rows in cases[group].values())}
summary['running_invocations'] = cases['running_invocations']
(OWN / 'INVOCATIONS.json').write_text(json.dumps(invocations, indent=2) + '\n')
(OWN / 'UNIQUE_COMPLETED_TESTS.json').write_text(json.dumps(cases, indent=2) + '\n')
(OWN / 'TEST_SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
