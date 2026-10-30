"""Direct retained-byte replay against staged public code, before installation."""
from pathlib import Path
import runpy

import gene_annotation_episode

packet = Path(__file__).resolve().parent
gene_annotation_episode.__path__.insert(0, str(packet / "candidate"))
runpy.run_path(str(packet / "reproduce_public.py"), run_name="__main__")
