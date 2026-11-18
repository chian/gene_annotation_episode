"""Private A110 Results binding_roles"""
from __future__ import annotations
VERSION = 'execution_episode_v1'
ROLES = ('launch', 'launch_local', 'launch_hpc', 'results')
KINDS = {'local': 'local', 'pbs_ssh': 'hpc'}
ROLE_KINDS = {'launch_local': 'local', 'launch_hpc': 'hpc'}
