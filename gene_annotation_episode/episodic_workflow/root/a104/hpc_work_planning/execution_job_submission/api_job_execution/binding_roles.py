"""Private A104 API binding roles."""
from __future__ import annotations
from pathlib import Path
VERSION = 'execution_episode_v1'
ROLES = ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results')
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
ROLE_KINDS = {'launch_api': 'api', 'launch_local': 'local', 'launch_hpc': 'hpc'}
