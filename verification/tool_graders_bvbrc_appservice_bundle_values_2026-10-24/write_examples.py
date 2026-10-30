"""Write explicitly synthetic pure-constructor examples; make no native calls."""
from contextlib import contextmanager
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from test_bvbrc_appservice_bundle_values import (  # noqa: E402
    acquisition, bundle, dependency, fixture, harness, selector,
)


def main():
    with TemporaryDirectory(prefix="appservice-bundle-fixture-") as directory:
        with contextmanager(harness.__wrapped__)(Path(directory)) as host:
            first = fixture(host, selected=selector(two=True))
            first_acquisition = dependency(first)
            second = fixture(host, selected=selector(two=True), number=2,
                requirement_ids=["r2"], role="sidecar", prior=[first_acquisition["receipt_ref"]])
            ignored_range = fixture(host, byte_range=[2, 4])
            incomplete = fixture(host, content=b"cd", byte_range=[2, 4], status=206,
                complete=False, headers={"Content-Length": "3", "Content-Range": "bytes 2-4/6"})
            empty = fixture(host, content=b"", metadata_size=0)
            examples = {
                "evidence_kind": "synthetic fixtures through actual C4b prepare/decode and pure constructors",
                "native_calls": host.client.calls,
                "native_bodies": {"complete_utf8": "abcdef", "incomplete_utf8": "cd", "empty_utf8": ""},
                "ignored_range_acquisition": acquisition(ignored_range),
                "incomplete_206_acquisition": acquisition(incomplete),
                "complete_empty_bundle": bundle(empty),
                "missing_artifact_bundle": bundle(empty, []),
                "first_required_output_bundle": bundle(first, [first_acquisition]),
                "two_required_outputs_bundle": bundle(second, [first_acquisition, dependency(second)]),
            }
            assert not host.client.calls
            path = Path(__file__).with_name("EXAMPLES.json")
            path.write_text(json.dumps(examples, indent=2, allow_nan=False) + "\n")
            print(json.dumps({"path": str(path), "evidence_kind": examples["evidence_kind"],
                "native_calls": 0, "first_bundle_status": examples["first_required_output_bundle"]["status"],
                "second_bundle_status": examples["two_required_outputs_bundle"]["status"]}))


if __name__ == "__main__":
    main()
