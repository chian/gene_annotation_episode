"""Optional log diagnostic. Do not run against real logs without user permission.

The parser necessarily reads log bytes, which may contain private model content.
Its output contains only the fixed lifecycle fields below. It neither prints nor
saves messages, reasoning, tool arguments, error messages or arbitrary strings.
It does not contact a provider, change a run, retry a request or alter credit.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


METHODS = {'turn/started', 'turn/completed', 'error', 'item/started',
           'item/completed', 'thread/status/changed'}
ITEMS = {'userMessage', 'agentMessage', 'reasoning', 'contextCompaction'}
STATUSES = {'completed', 'failed', 'interrupted', 'inProgress'}
MAX_LINE = 16 * 1024 * 1024


def inspect(path, expected_thread):
    counts = Counter()
    methods, items, statuses, retries = Counter(), Counter(), Counter(), Counter()
    started, completed = set(), set()
    size = path.stat().st_size
    with path.open('rb') as stream:
        remaining = size
        while remaining:
            line = stream.readline(min(MAX_LINE + 1, remaining))
            remaining -= len(line)
            if not line:
                break
            if len(line) > MAX_LINE:
                while not line.endswith(b'\n') and remaining:
                    line = stream.readline(min(MAX_LINE + 1, remaining))
                    remaining -= len(line)
                counts['oversized_lines_skipped'] += 1
                continue
            if not line.endswith(b'\n'):
                counts['partial_trailing_lines_skipped'] += 1
                break
            try:
                event = json.loads(line)
            except (ValueError, UnicodeError):
                counts['invalid_json_lines'] += 1
                continue
            counts['complete_json_lines'] += 1
            if not isinstance(event, dict):
                counts['non_object_events'] += 1
                continue
            raw_method = event.get('method')
            method = raw_method if isinstance(raw_method, str) and raw_method in METHODS else 'other'
            methods[method] += 1
            params = event.get('params')
            if not isinstance(params, dict):
                continue
            if params.get('threadId') != expected_thread:
                counts['other_or_missing_thread_events'] += 1
                continue
            counts['matching_thread_events'] += 1
            if method in {'item/started', 'item/completed'}:
                item = params.get('item')
                kind = item.get('type') if isinstance(item, dict) else None
                items[kind if isinstance(kind, str) and kind in ITEMS else 'other'] += 1
            if method == 'error':
                retry = params.get('willRetry')
                retries['true' if retry is True else 'false' if retry is False else 'absent_or_invalid'] += 1
            if method not in {'turn/started', 'turn/completed'}:
                continue
            turn = params.get('turn')
            if not isinstance(turn, dict):
                counts['invalid_turn_envelopes'] += 1
                continue
            identity = turn.get('id')
            if isinstance(identity, str) and len(identity) <= 256:
                target = started if method == 'turn/started' else completed
                if len(target) < 8:
                    target.add(hashlib.sha256(identity.encode(errors='surrogatepass')).hexdigest())
                else:
                    counts['turn_digest_capacity_reached'] += 1
            if method == 'turn/completed':
                status = turn.get('status')
                statuses[status if isinstance(status, str) and status in STATUSES else 'other'] += 1
    return {'version': 'allowlisted_provider_lifecycle_metadata_v1',
        'bytes_at_scan_start': size, 'counts': dict(counts),
        'event_method_counts': dict(methods), 'matching_thread_item_type_counts': dict(items),
        'matching_thread_completion_status_counts': dict(statuses),
        'matching_thread_error_retry_counts': dict(retries),
        'started_turn_sha256': sorted(started), 'completed_turn_sha256': sorted(completed),
        'private_text_returned_or_saved': False, 'run_modified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', type=Path, required=True)
    parser.add_argument('--thread', required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.events, args.thread), sort_keys=True))


if __name__ == '__main__':
    main()
