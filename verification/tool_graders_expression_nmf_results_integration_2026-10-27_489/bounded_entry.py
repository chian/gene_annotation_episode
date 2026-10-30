from pathlib import Path
import json
import os
import sys
import importlib

root = Path(sys.argv[1])
for name in ("expression_nmf_result_contracts", "expression_nmf_return_views", "expression_nmf_returns",
        "expression_nmf_result_receipts", "expression_nmf_result_worker", "native_expression_nmf_preparation",
        "native_expression_nmf_capture", "native_expression_nmf_results"):
    importlib.import_module("gene_annotation_episode." + name)
import pytest
status = pytest.main([str(root / "source_snapshot/tests"), "-q", "-p", "no:cacheprovider", "--basetemp=" + str(root / "test-work")])
(root / "test-result.json").write_text(json.dumps({"returncode": status}) + "\n")
raise SystemExit(status)
