"""Initialize and close one real capped Codex client, without a model turn."""
import asyncio
from pathlib import Path

from gene_annotation_episode.providers import _SessionConnection,load_config
from gene_annotation_episode.workflow_budget import active_budget


async def main():
    directory = Path(active_budget()['run_directory'])
    async with _SessionConnection(load_config(None),directory/'provider',directory):
        print('Real Codex initialize handshake completed.',flush=True)


if __name__=='__main__':asyncio.run(main())
