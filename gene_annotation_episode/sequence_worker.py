"""Store-free native sequence worker, launched only through local_jobs.

The selected algorithm and complete operands are preserved. Operational limits
belong to the caller's process boundary; this worker makes no follow-up decision.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys


def main() -> int:
    request_path, output_path = map(Path, sys.argv[1:])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    # Native computation receives only copied operands; no Store is imported.
    try:
        if request["operation"] == "arsenic_speciation":
            from .arsenic_speciation_tools import run_arsenic_speciation_tool_request
            result = run_arsenic_speciation_tool_request(**request["arguments"])
        elif request["operation"] == "protein_disorder":
            from .protein_disorder_tools import run_disorder_tool_request
            result = run_disorder_tool_request(**request["arguments"])
        elif request["operation"] == "itc_binding":
            from .molecular_measurement_tools import run_itc_tool_request
            result = run_itc_tool_request(**request["arguments"], output_directory=output_path.parent)
        elif request["operation"] == "liftover_point":
            from .liftover_measurements import run_liftover_tool_request
            result = run_liftover_tool_request(**request["arguments"], output_directory=output_path.parent)
        elif request["operation"] == "circular_dichroism":
            from .circular_dichroism_tools import run_circular_dichroism_tool_request
            result = run_circular_dichroism_tool_request(**request["arguments"], output_directory=output_path.parent)
        elif request["operation"] == "macs2_peak_result":
            from .macs2_peak_result_worker import run_macs2_peak_result_job
            result = run_macs2_peak_result_job(**request["arguments"], output_directory=output_path.parent)
        else:
            from .sequence_ops import align_pair, predict_genes
            operations = {"align_pair": align_pair, "predict_genes": predict_genes}
            result = operations[request["operation"]](**request["arguments"])
    except ValueError as error:
        output_path.write_text(json.dumps({"code": str(error), "exception_type": "ValueError"}), encoding="utf-8")
        return 2
    except MemoryError:
        output_path.write_text(json.dumps({"code": "native_memory_allocation_failed", "exception_type": "MemoryError"}), encoding="utf-8")
        return 3
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, allow_nan=False, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
