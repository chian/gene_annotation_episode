"""Print the reconciled inventory; retained history is available explicitly."""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', action='store_true', help='Print category counts only.')
    parser.add_argument('--history', action='store_true', help='Also print historical rows, aliases and bindings.')
    args = parser.parse_args()
    scope = json.loads((HERE / 'SCOPE.json').read_text())
    progress = json.loads((HERE / 'WORK_STATUS.json').read_text())
    coverage = json.loads((HERE / 'COVERAGE.json').read_text())
    listing = coverage['active_listing']
    rows = {r['id']: r for r in scope['rows']}
    states = {r['id']: r for r in progress['rows']}
    labels = {
        'molecular_scientific_operations': 'Molecular scientific operations',
        'restriction_site_support_operation': 'Restriction-site support operation',
        'new_bvbrc_application_bindings': 'Additional BV-BRC application bindings',
        'bvbrc_data_collections': 'BV-BRC data collections',
        'molecular_provider_bindings': 'Molecular provider bindings, including Addgene',
        'blast_support_operations': 'BLAST preparation and inspection operations',
    }
    out = [
        '# Reconciled tool inventory', '',
        'Counts describe entries in the corrected list. They do not assert how many new graders are needed or how many entries are complete. Existing-family repairs and integration gaps remain separate.', '',
        '| Category | Entries |', '| --- | ---: |',
    ]
    for group, ids in listing['entries'].items():
        assert listing['counts'][group] == len(ids)
        out.append(f'| {labels[group]} | {len(ids)} |')
    out += ['', 'Aliases, lifecycle steps, formats, resource subrows and tests are not added to an algorithm total. Recorded verification status is retained; scope reconciliation does not mark scientific work complete.', '']
    if args.summary:
        print('\n'.join(out))
        return
    columns = ['overall', 'production_result_binding', 'integration_verification', 'live_resource_verification']

    def table(ids):
        result = ['| ID | Operation or resource | Recorded status | Result binding | Episode verification | Live resource |',
                  '| --- | --- | --- | --- | --- | --- |']
        for identity in ids:
            row = rows[identity]
            name = listing.get('display_names', {}).get(identity, row['name'])
            result.append('| ' + ' | '.join([cell(identity), cell(name)] + [cell(states[identity][key]) for key in columns]) + ' |')
        return result

    for group, ids in listing['entries'].items():
        out += ['## ' + labels[group], ''] + table(ids) + ['']

    out += ['## Existing-family repairs and integration', '',
            'Shared-scoring consumer repairs cover BLAST publication/HSP reading, HMMER publication and Biopython alignment publication. Their completion requires their own verification evidence.', '']
    for label, ids in listing['existing_family_rows'].items():
        out += ['### ' + label, ''] + table(ids) + ['']

    if args.history:
        out += ['## Consolidated aliases and helpers', '',
                '| Historical entry | Canonical operation or responsibility | Disposition |',
                '| --- | --- | --- |']
        for row in scope['rows']:
            if row['scope_disposition'] not in {'alias_of_existing_operation', 'part_of_existing_operation', 'helper_only_if_needed', 'removed'}:
                continue
            targets = ', '.join(row.get('canonical_row_ids', [])) or row.get('shared_implementation_relationship', 'Conditional helper')
            out.append(f"| {cell(row['name'])} | {cell(targets)} | {row['scope_disposition']} |")
        selected = {identity for ids in listing['entries'].values() for identity in ids}
        out += ['', '## Other retained inventory rows', ''] + table([r['id'] for r in scope['rows'] if r['id'] not in selected])
        bindings = {r['id']: r for r in progress['resource_bindings']}
        out += ['', '## Retained resource bindings', '',
                '| ID | Route status | Result binding | Integration | Live resource |',
                '| --- | --- | --- | --- | --- |']
        for row in scope['resource_bindings']:
            state = bindings[row['id']]
            values = [row['id'], row['route_status']] + [state[k] for k in ('production_result_binding', 'integration_verification', 'live_resource_verification')]
            out.append('| ' + ' | '.join(cell(v) for v in values) + ' |')
        sources = json.loads((HERE / 'SOURCE_ALIASES.json').read_text())
        out += ['', '## Historical source mappings', '',
                '| Source ID | Source name | Linked inventory IDs | Disposition |',
                '| --- | --- | --- | --- |']
        for row in sources['rows']:
            out.append('| ' + ' | '.join(cell(v) for v in (row['id'], row['name'], ', '.join(row['requirement_row_ids']), row['disposition'])) + ' |')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
