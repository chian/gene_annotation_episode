"""Initialize a real Codex client and conversation, without a model turn."""
import asyncio
from pathlib import Path

from gene_annotation_episode.providers import _SessionConnection,load_config
from gene_annotation_episode.workflow_budget import active_budget


async def main():
    directory = Path(active_budget()['run_directory'])
    async with _SessionConnection(load_config(None),directory/'provider',directory) as provider:
        await provider._session('startup-probe', 'REASONING',
            'Validate native conversation startup; no model turn is requested.')
        print('Real Codex initialize and thread/start completed; no model turn requested.',flush=True)


if __name__=='__main__':asyncio.run(main())
