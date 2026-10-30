"""Synthetic adversarial observation, not an adopted cross-family policy.

Reproduce a completion endpoint witness containing product fraction operands
when the requested product component is only their derived sum.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_a105_partition_time_joined_149 import synthetic_inputs, TEXT, TIME_REQUEST, PARTITION_REQUEST
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_completion_time_storage import LiteratureCompletionTimeRepository
from gene_annotation_episode.literature_completion_time_render import render_received
from gene_annotation_episode.literature_product_partition_storage import LiteratureProductPartitionRepository
from gene_annotation_episode.state import Store


def run(directory):
    with Store(directory / "cross_family_probe_state") as store:
        store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        source, artifact, times, partition = synthetic_inputs(store)
        quote = "Single mixture has component A 71.234567% and component B 28.765433%"
        start = TEXT.index(quote)
        times["quantities"]["numerator"]["endpoint"] = {"source_ref": source,
            "representation": "original", "start": start, "end": start + len(quote), "quote": quote}
        context = BindingContext("cross-family-probe", "child", "literature", (("literature", "child"),),
            store.validate_scope(), {"requested_completion_time_components": TIME_REQUEST,
                "requested_product_partition_components": PARTITION_REQUEST}, {}, [source])
        time_repo = LiteratureCompletionTimeRepository(store, context.run_id)
        time_outcome = time_repo.populate(context, times, "time")
        product_outcome = LiteratureProductPartitionRepository(store, context.run_id).populate(context, partition, "partition")
        rows = time_repo.project_cells([time_outcome["result"]["sheet_ref"]],
            permitted_record_refs=time_outcome["record_refs"], components=TIME_REQUEST)
        parts = []
        render_received(parts, rows, section=lambda p, title, value: p.append(title + "\n" + str(value)),
                        table=lambda headers, body: str(headers) + str(list(body)))
        rendered = "\n".join(parts)
        result = {"kind": "synthetic_adversarial_observation", "requested_completion": TIME_REQUEST,
            "requested_product": PARTITION_REQUEST, "completion_rows": rows,
            "product_rows": product_outcome["result"]["cells"],
            "native_product_operands_present_in_completion_return": all(x in json.dumps(rows) for x in ("71.234567", "28.765433")),
            "native_product_operands_present_in_completion_render": all(x in rendered for x in ("71.234567", "28.765433")),
            "scope_question": "Should cross-family unrequested native operands be withheld when contained in another requested family's scientifically meaningful source witness?",
            "source_hashes": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
                "gene_annotation_episode/literature_completion_time_storage.py",
                "gene_annotation_episode/literature_completion_time_render.py",
                "gene_annotation_episode/literature_product_partition_storage.py")}}
        (directory / "CROSS_FAMILY_MEANING_PROBE_001.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({k: result[k] for k in ("native_product_operands_present_in_completion_return",
            "native_product_operands_present_in_completion_render", "scope_question")}))


if __name__ == "__main__":
    run(Path(__file__).resolve().parent)
