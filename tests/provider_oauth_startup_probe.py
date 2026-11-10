"""Verify real OAuth and role selection without starting a model turn."""
import argparse
import asyncio
import json
from pathlib import Path

from gene_annotation_episode.providers import _SessionConnection, load_config
from gene_annotation_episode.workflow_budget import active_budget


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-config', required=True)
    args = parser.parse_args()
    directory = Path(active_budget()['run_directory'])
    config = load_config(args.model_config)
    async with _SessionConnection(config, directory/'provider', directory) as provider:
        assert provider.authentication is not None
        for role in ('FAST', 'REASONING'):
            await provider._session('oauth-startup-'+role, role,
                'Check the selected OAuth transport; no inference is requested.')
        print(json.dumps({'authentication': provider.authentication,
            'role_models': {role: config[role]['model'] for role in ('FAST', 'REASONING')},
            'native_threads_created': 2, 'model_turns_requested': 0}), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
