"""Measure retained A104 prompt construction without a model or biological job."""
from __future__ import annotations

import argparse
import ctypes
import gc
import json
from pathlib import Path

from gene_annotation_episode.workflow_budget import active_budget
from gene_annotation_episode.providers import _SessionConnection, load_config


def memory():
    fields = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    return int(fields['VmRSS'].split()[0])*1024


def main():
    run = Path(active_budget()['run_directory'])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider-directory', type=Path, required=True)
    args = parser.parse_args()
    connection = _SessionConnection(load_config(), run/'presentation', Path.cwd())
    trim = ctypes.CDLL(None).malloc_trim
    for path in sorted(args.provider_directory.glob('session-*/call-*/request.json')):
        if not path.stat().st_size:
            continue
        try:
            request = json.loads(path.read_text())
        except ValueError:
            continue
        before = memory()
        rendered, _ = connection._presentation(request['episode_id'], request['role'], request['instructions'], request['context'])
        after = memory()
        size = len(rendered)
        del rendered, request
        collected = gc.collect()
        trim(0)
        print(json.dumps({'call': path.parent.name, 'retained_request_bytes': path.stat().st_size,
            'rss_before_render': before, 'rss_after_render': after, 'rss_after_collection': memory(),
            'rendered_characters': size, 'collected_objects': collected}), flush=True)


if __name__ == '__main__':
    main()
