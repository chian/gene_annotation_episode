"""Run one probe plan in a process of its own, so that a test can have it cut.

``python -m episode_runtime.tests.cut_run <directory> <run id> <entry input as JSON>`` opens the Store, the journal
and the services below ``directory`` (the ones the test's ``world`` fixture opened, ``probe_world.open_world``),
links the probe run and runs it. A tool of the plan ends the process (``os._exit``) where the test wants the cut:
nothing after that point runs, as when a process is killed."""
import asyncio
import json
from pathlib import Path
import sys

from episode_runtime import link

from .probe_world import collaborators, open_world, registry


def main(directory, run_id, entry_input):
    world = open_world(Path(directory), calls='model_calls_of_the_cut_process')
    linked = link(registry(), 'probe', json.loads(entry_input), run_id=run_id, journal=world['journal'],
                  collaborators=collaborators(world))
    asyncio.run(linked.run())


if __name__ == '__main__':
    main(*sys.argv[1:])
