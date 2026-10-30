"""Verify staged providers with the actual corrected production calculator.

The filesystem overlay links unmodified staged dependencies and links exactly
one corrected production dependency. No scientific implementation is mocked.
Run with the project's absolute venv Python and the staging working directory.
"""
from pathlib import Path
import hashlib
import json
import sys

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STAGING = HERE.parent / "staging"
OVERLAY = HERE / "dependency-overlay"
PACKAGE = OVERLAY / "gene_annotation_episode"
CORRECTED = ROOT / "gene_annotation_episode" / "bvbrc_codon_tree_calculators.py"
EXPECTED = "e8eeab6a379af3cf80b0c92089df13a8c06630abf8baabe04593d94aaab87d54"


def establish_overlay():
    assert hashlib.sha256(CORRECTED.read_bytes()).hexdigest() == EXPECTED
    PACKAGE.mkdir(parents=True, exist_ok=True)
    for original in sorted((STAGING / "gene_annotation_episode").iterdir()):
        if original.name == "__pycache__":
            continue
        target = CORRECTED if original.name == CORRECTED.name else original
        link = PACKAGE / original.name
        if link.is_symlink():
            assert link.resolve() == target.resolve()
        else:
            assert not link.exists()
            link.symlink_to(target, target_is_directory=target.is_dir())
    sys.path.insert(0, str(OVERLAY))
    from gene_annotation_episode import bvbrc_codon_tree_inputs, bvbrc_codon_tree_grader
    from gene_annotation_episode import bvbrc_codon_tree_calculators
    from gene_annotation_episode import bvbrc_phylogeny_common_inputs, bvbrc_phylogeny_common_contracts, bvbrc_phylogeny_common_grader
    from gene_annotation_episode import bvbrc_codon_tree_native, phylogeny_formats, phylogeny_raxml_inputs
    from gene_annotation_episode import phylogeny_calculators, phylogeny_calculation_contracts
    modules = (bvbrc_codon_tree_inputs, bvbrc_codon_tree_grader, bvbrc_codon_tree_calculators,
        bvbrc_phylogeny_common_inputs, bvbrc_phylogeny_common_contracts, bvbrc_phylogeny_common_grader,
        bvbrc_codon_tree_native, phylogeny_formats, phylogeny_raxml_inputs, phylogeny_calculators, phylogeny_calculation_contracts)
    imports = [{"module": module.__name__, "resolved_path": str(Path(module.__file__).resolve()),
        "sha256": hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()} for module in modules]
    assert Path(bvbrc_codon_tree_calculators.__file__).resolve() == CORRECTED
    assert all(Path(m.__file__).resolve().parent == STAGING / "gene_annotation_episode"
               for m in modules if m is not bvbrc_codon_tree_calculators)
    return imports


if __name__ == "__main__":
    imports = establish_overlay()
    (HERE / "verified-imports.json").write_text(json.dumps(imports, indent=2) + "\n")
    print(json.dumps({"imports_verified": len(imports), "corrected_calculator_sha256": EXPECTED}))
    raise SystemExit(pytest.main(sys.argv[1:]))
