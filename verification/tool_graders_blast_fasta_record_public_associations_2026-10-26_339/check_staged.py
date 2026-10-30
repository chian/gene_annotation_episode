"""Test only staged v2 changes while E retains original production source pins."""
from pathlib import Path
import shutil
import sys

import gene_annotation_episode
import pytest

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
candidate = PACKET / "candidate"
# Only these two modules are overlaid; their actual names and dependencies are
# unchanged. This establishes staged behavior, not installed production status.
gene_annotation_episode.__path__.insert(0, str(candidate))
staged_root = Path.cwd() / "temporary/staged"
(staged_root / "tests").mkdir(parents=True)
(staged_root / "verification").symlink_to(ROOT / "verification", target_is_directory=True)
for name in ("test_blast_explicit_associations.py", "test_blast_sequence_database.py"):
    shutil.copyfile(candidate / name, staged_root / "tests" / name)
raise SystemExit(pytest.main(["-q", "-p", "no:cacheprovider", "--basetemp", str(Path.cwd()/"temporary/pytest"),
    "-k", "v2 or locator or implicit_matcher or saved_generic_v1 or null_and_absent",
    str(staged_root / "tests/test_blast_explicit_associations.py"),
    str(staged_root / "tests/test_blast_sequence_database.py")]))
