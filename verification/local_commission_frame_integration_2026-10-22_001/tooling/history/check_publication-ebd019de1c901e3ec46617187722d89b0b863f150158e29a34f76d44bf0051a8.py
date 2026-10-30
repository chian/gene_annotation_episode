"""Independent stdlib-only verification of the fixed factual-frame007 capsule.

This checker imports no builder or application, opens no database, invokes no
tests or programs, and follows no filesystem alias.  --check-originals reads
only originals declared by the finalized inputs and their finite tree controls.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import xml.etree.ElementTree as ET


HISTORICAL_INTERFACE_PIN = "d39a6756507bacd8e9ba90f75912cc01822a316f766cc72764154b7205ba81e3"
BASELINE_SHA = "98f81ab1cbcf4576d4a3604e9a91f223d247fa7b1333311fb78d2e6c5d882983"
SCOPE_SHA = "639a5bc3833be3a74b457afc92e5214788e0c91a8f6360b05da51fbb9a9cc256"
PARENT_SHA = "d402530d46239223f6dc1e59b81169d4da1a623e5b66c1126c9532bfde08c8b4"
FRAME_SHA = "395fb421829fa90f0fe2d232c7b146718f67519018eff853cee56e4e6b44727c"
SOURCE_CHANGES = {"gene_annotation_episode/runtime.py", "gene_annotation_episode/waiting.py",
                  "gene_annotation_episode/wait_estimation_inputs.py"}
REQUIRED = {"MANIFEST.json", "REPORT.md", "RESULTS_FINAL.json", "INPUTS_FINAL.json",
            "COPY_CONTROLS.json", "BASELINE_COMPARISON.json", "EXTERNAL_REFERENCES.json",
            "lineage/parent006-MANIFEST.json", "lineage/original-frame-MANIFEST.json",
            "source/GENERATION_BASELINE_007.json"}
WITNESS_KEYS = {"sha256", "bytes", "mode", "mtime_ns", "inode", "device"}
META_KEYS = {"mode", "mtime_ns", "inode", "device"}
SHA = re.compile(r"[0-9a-f]{64}\Z")


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def integer(value):
    return type(value) is int and value >= 0


def absolute(value):
    require(isinstance(value, str) and value.startswith("/"), "expected absolute path")
    require(os.path.normpath(value) == value, "absolute path must be normalized")
    return Path(value)


def relative(value, *, dot=False):
    require(isinstance(value, str) and value and "\\" not in value, "invalid relative member")
    if dot and value == ".":
        return value
    parts = PurePosixPath(value).parts
    require(not value.startswith("/") and parts and all(part not in {".", ".."} for part in parts)
            and str(PurePosixPath(value)) == value, "unsafe relative member: "+value)
    return value


def open_directory(path):
    """Open each absolute component using O_NOFOLLOW, closing predecessors."""
    path = absolute(str(path))
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def open_regular(path):
    path = absolute(str(path))
    parent = open_directory(path.parent)
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
    finally:
        os.close(parent)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise Invalid("not a nofollow regular file: "+str(path))
    return os.fdopen(descriptor, "rb")


def metadata(value):
    return {"mode": format(stat.S_IMODE(value.st_mode), "04o"),
            "mtime_ns": value.st_mtime_ns, "inode": value.st_ino, "device": value.st_dev}


def stream_witness(stream):
    before = os.fstat(stream.fileno())
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024*1024), b""):
        digest.update(block)
    after = os.fstat(stream.fileno())
    require(metadata(before) == metadata(after) and before.st_size == after.st_size,
            "file changed while hashing")
    return {"sha256": digest.hexdigest(), "bytes": after.st_size, **metadata(after)}


def file_witness(path):
    with open_regular(path) as stream:
        return stream_witness(stream)


def read_bytes(path):
    with open_regular(path) as stream:
        return stream.read()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "duplicate JSON object key: "+key)
        value[key] = item
    return value


def load_json(path):
    return json.loads(read_bytes(path), object_pairs_hook=unique_object,
        parse_constant=lambda value: (_ for _ in ()).throw(Invalid("nonfinite JSON: "+value)))


def tree_snapshot(path):
    descriptor = open_directory(path)
    result = {"root": metadata(os.fstat(descriptor)), "directories": {}, "files": {}, "aliases": {}}
    def visit(parent, prefix):
        with os.scandir(parent) as scan:
            names = sorted(entry.name for entry in scan)
        for name in names:
            member = name if not prefix else prefix+"/"+name
            relative(member)
            value = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if stat.S_ISDIR(value.st_mode):
                result["directories"][member] = metadata(value)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                try:
                    visit(child, member)
                finally:
                    os.close(child)
            elif stat.S_ISREG(value.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
                with os.fdopen(child, "rb") as stream:
                    result["files"][member] = stream_witness(stream)
            elif stat.S_ISLNK(value.st_mode):
                result["aliases"][member] = {"target": os.readlink(name, dir_fd=parent), **metadata(value)}
            else:
                raise Invalid("special filesystem member not traversed: "+member)
    try:
        visit(descriptor, "")
    finally:
        os.close(descriptor)
    return result


def valid_witness(value):
    require(isinstance(value, dict) and set(value) == WITNESS_KEYS, "invalid original witness shape")
    require(isinstance(value["sha256"], str) and SHA.fullmatch(value["sha256"]), "invalid witness sha256")
    require(integer(value["bytes"]) and re.fullmatch(r"[0-7]{4}", value["mode"] or ""), "invalid witness bytes/mode")
    require(all(integer(value[key]) for key in ("mtime_ns", "inode", "device")), "invalid witness metadata")


def valid_metadata(value):
    require(isinstance(value, dict) and set(value) == META_KEYS, "invalid directory metadata shape")
    require(isinstance(value["mode"], str) and re.fullmatch(r"[0-7]{4}", value["mode"]), "invalid directory metadata mode")
    require(all(integer(value[key]) for key in ("mtime_ns", "inode", "device")), "invalid directory metadata types")


def validate_snapshot(value):
    require(isinstance(value, dict) and set(value) == {"root", "directories", "files", "aliases"},
            "invalid tree snapshot shape")
    valid_metadata(value["root"])
    for name, row in value["files"].items():
        relative(name)
        valid_witness(row)
    for name, row in value["directories"].items():
        relative(name)
        valid_metadata(row)
    for name, row in value["aliases"].items():
        relative(name)
        require(set(row) == META_KEYS | {"target"} and isinstance(row["target"], str),
                "invalid original alias metadata")
        valid_metadata({key: row[key] for key in META_KEYS})
    groups = [set(value[key]) for key in ("directories", "files", "aliases")]
    require(sum(len(group) for group in groups) == len(set.union(*groups)), "mixed original tree membership")


def xml_facts(data):
    require(b"<!DOCTYPE" not in data.upper(), "XML document type is not accepted")
    root = ET.fromstring(data)
    tag = lambda item: item.tag.rsplit("}", 1)[-1]
    cases = [item for item in root.iter() if tag(item) == "testcase"]
    counts = {"cases": len(cases), "failed": 0, "errors": 0, "skipped": 0}
    nodeids = []
    for case in cases:
        states = {tag(child) for child in case} & {"failure", "error", "skipped"}
        require(len(states) <= 1, "XML testcase has conflicting outcome children")
        if states:
            counts[{"failure": "failed", "error": "errors", "skipped": "skipped"}[states.pop()]] += 1
        require(case.attrib.get("name"), "XML testcase has no name")
        nodeids.append(case.attrib.get("classname", "")+"."+case.attrib["name"])
    suites = [item for item in root.iter() if tag(item) == "testsuite"
              and not any(tag(child) == "testsuite" for child in item)]
    seconds = sum(float(item.attrib.get("time", "0")) for item in suites)
    require(math.isfinite(seconds) and seconds >= 0, "invalid XML suite duration")
    if root.attrib.get("tests") is not None:
        require(int(root.attrib["tests"]) == counts["cases"], "XML aggregate test count differs from cases")
    return counts, seconds, nodeids


def apply_unified_patch(original, patch):
    """Verify one recorded textual test amendment without running patch/git."""
    old = original.decode("utf-8").splitlines(keepends=True)
    lines = patch.decode("utf-8").splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.startswith("--- ")), None)
    require(start is not None and start+1 < len(lines) and lines[start+1].startswith("+++ "),
            "test amendment is not one unified patch")
    position, index, output, hunks = 0, start+2, [], 0
    while index < len(lines):
        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[index])
        require(match is not None, "unexpected amendment patch body")
        old_start, old_count = int(match[1]), int(match[2] or 1)
        new_count = int(match[4] or 1)
        target = old_start-1 if old_start else 0
        require(target >= position and target <= len(old), "overlapping or out-of-range patch hunk")
        output.extend(old[position:target])
        position, index = target, index+1
        removed = added = 0
        while index < len(lines) and not lines[index].startswith("@@ "):
            line = lines[index]
            require(line and line[0] in " +-", "unexpected patch line")
            marker, text = line[0], line[1:]
            if index+1 < len(lines) and lines[index+1].startswith("\\ No newline at end of file"):
                text = text.rstrip("\r\n")
                index += 1
            if marker in " -":
                require(position < len(old) and old[position] == text, "patch original context differs")
                position += 1
                removed += 1
            if marker in " +":
                output.append(text)
                added += 1
            index += 1
        require((removed, added) == (old_count, new_count), "patch hunk counts differ")
        hunks += 1
    require(hunks > 0, "empty amendment patch")
    output.extend(old[position:])
    return "".join(output).encode("utf-8")


def check(capsule, report, check_originals):
    actual = tree_snapshot(capsule)
    files, aliases = actual["files"], actual["aliases"]
    require(REQUIRED <= set(files), "required capsule regular files missing")
    manifest = load_json(capsule/"MANIFEST.json")
    inputs = load_json(capsule/"INPUTS_FINAL.json")
    require(inputs["version"] == "factual_frame007_build_inputs_v1" and inputs["ready"] is True,
            "inputs were not explicitly finalized")
    expected_pin = inputs["runtime_pin"]
    require(isinstance(expected_pin, str) and SHA.fullmatch(expected_pin), "invalid final input runtime pin")
    require(manifest["version"] == "local_commission_frame_integration_capsule_v1", "wrong manifest version")
    members = manifest["members"]
    require(set(members) == set(files)-{"MANIFEST.json"}, "manifest regular membership is not exact")
    require(set(manifest["aliases"]) == set(aliases), "manifest alias membership is not exact")
    directories = manifest["directories"]
    require(isinstance(directories, list) and len(directories) == len(set(directories))
            and set(directories) == {".", *actual["directories"]}, "manifest directory membership differs")
    require(manifest["manifest_self_excluded"] is True, "manifest self-exclusion missing")
    require(manifest["regular_file_mode"] == "0444" and manifest["directory_mode"] == "0555", "wrong seal mode declaration")
    require(all(row["mode"] == "0444" for row in files.values()), "unsealed capsule regular file")
    require(actual["root"]["mode"] == "0555" and all(row["mode"] == "0555" for row in actual["directories"].values()),
            "unsealed capsule directory")
    for name, row in members.items():
        relative(name)
        require(set(row) == {"sha256", "bytes", "mode", "kind"}, "invalid manifest member shape: "+name)
        require(isinstance(row["kind"], str) and row["kind"], "missing manifest member kind")
        require(integer(row["bytes"]) and isinstance(row["sha256"], str) and SHA.fullmatch(row["sha256"]),
                "invalid member size/digest types")
        require(all(row[key] == files[name][key] for key in ("sha256", "bytes", "mode")), "member digest/size/mode mismatch: "+name)
    require(integer(manifest["file_count_excluding_manifest"])
            and manifest["file_count_excluding_manifest"] == len(members), "manifest file count differs")
    require(integer(manifest["content_bytes_excluding_manifest"])
            and manifest["content_bytes_excluding_manifest"] == sum(row["bytes"] for row in members.values()), "manifest content bytes differ")
    require(manifest["parent006_extent"] == "MANIFEST ONLY", "parent006 extent expanded")
    require(manifest["original_frame_extent"] == "MANIFEST ONLY; separately pinned authority scopes/report may be copied", "original frame extent expanded")
    require(files["lineage/parent006-MANIFEST.json"]["sha256"] == PARENT_SHA, "wrong copied parent006 manifest")
    require(files["lineage/original-frame-MANIFEST.json"]["sha256"] == FRAME_SHA, "wrong copied original-frame manifest")
    require({name for name in files if name.startswith("lineage/")} == {"lineage/parent006-MANIFEST.json", "lineage/original-frame-MANIFEST.json"}, "unexpected lineage payload")
    results = load_json(capsule/"RESULTS_FINAL.json")
    controls = load_json(capsule/"COPY_CONTROLS.json")
    comparison = load_json(capsule/"BASELINE_COMPARISON.json")
    require(inputs["version"] == "factual_frame007_build_inputs_v1" and inputs["ready"] is True, "inputs were not explicitly finalized")
    require(results["version"] == "local_commission_frame_integration_results_v1", "wrong results version")
    require(controls["version"] == "factual_frame007_copy_controls_v1", "wrong copy controls version")
    for document in (manifest, results, inputs):
        require(document["runtime_pin"] == expected_pin, "runtime pin declaration differs from finalized inputs")
    for document in (manifest, results):
        require(document["runtime_files"] == 137 and document["test_files"] == 222, "wrong source/test count declaration")
    source = inputs["source_inventory"]
    require("GENERATION_BASELINE_007.json" in source, "baseline absent from source inventory")
    expected_source = {"source/"+relative(name) for name in source} | {"source/GENERATION_BASELINE_007.json"}
    require({name for name in files if name.startswith("source/")} == expected_source, "source inventory membership differs")
    for name, row in source.items():
        require(set(row) == {"source", "sha256", "bytes", "kind"}, "invalid source inventory row")
        absolute(row["source"])
        require(integer(row["bytes"]) and isinstance(row["kind"], str) and row["kind"], "invalid source inventory types")
        require(row["sha256"] == files["source/"+name]["sha256"] and row["bytes"] == files["source/"+name]["bytes"], "source inventory bytes differ: "+name)
    runtime = sorted(name.removeprefix("source/") for name in files
        if name.endswith(".py") and (name.startswith("source/gene_annotation_episode/") or name.startswith("source/method_loop/")))
    tests = sorted(name for name in files if name.startswith("source/tests/") and name.endswith(".py"))
    digest = hashlib.sha256()
    for name in runtime:
        digest.update(name.encode("utf-8")+b"\0")
        digest.update(bytes.fromhex(files["source/"+name]["sha256"]))
    require(len(runtime) == 137 and len(tests) == 222 and digest.hexdigest() == expected_pin, "recomputed source/test counts or runtime pin differ")
    require(files["source/GENERATION_BASELINE_007.json"]["sha256"] == BASELINE_SHA, "wrong baseline original bytes")
    require(inputs["baseline"]["sha256"] == BASELINE_SHA and inputs["integration_scope"]["sha256"] == SCOPE_SHA, "wrong baseline/scope input authority")
    baseline = load_json(capsule/"source/GENERATION_BASELINE_007.json")["files"]
    require(len(baseline) == 690 and set(baseline) <= set(source), "baseline original690 coverage differs")
    checkout = absolute(inputs["checkout"])
    require(all(source[name]["source"] == str(checkout/name) for name in baseline),
            "baseline original source paths differ from the declared checkout")
    require(comparison["baseline_member"] == "source/GENERATION_BASELINE_007.json"
            and comparison["baseline_sha256"] == BASELINE_SHA and comparison["original_file_count"] == 690,
            "baseline comparison authority differs")
    require(set(comparison["authorized_source_changes"]) == SOURCE_CHANGES
            and len(comparison["authorized_source_changes"]) == 3, "original source-change scope differs")
    amendments = comparison["test_amendments"]
    require(amendments == inputs["test_amendments"], "test amendments differ from finalized inputs")
    amendment_by_path = {}
    for row in amendments:
        path = relative(row["path"])
        require(path.startswith("tests/") and path in baseline and path not in amendment_by_path, "invalid scoped original-test amendment")
        require(row["baseline_sha256"] == baseline[path]["sha256"]
                and row["final_sha256"] == files["source/"+path]["sha256"], "test amendment endpoint digests differ")
        for key in ("scope_member", "original_member", "patch_member"):
            require(relative(row[key]) in files, "test amendment custody missing: "+key)
        require(files[row["original_member"]]["sha256"] == row["baseline_sha256"], "wrong amendment original bytes")
        require(apply_unified_patch(read_bytes(capsule/row["original_member"]), read_bytes(capsule/row["patch_member"]))
                == read_bytes(capsule/("source/"+path)), "recorded test patch does not produce final bytes")
        amendment_by_path[path] = row
    rows = comparison["comparisons"]
    require(set(rows) == set(baseline), "baseline comparisons do not cover exactly690 originals")
    changed_source = set()
    for name, old in baseline.items():
        final = {key: files["source/"+name][key] for key in ("sha256", "bytes")}
        require(set(rows[name]["baseline"]) == set(rows[name]["final"]) == {"sha256", "bytes"}
                and integer(rows[name]["baseline"]["bytes"]) and integer(rows[name]["final"]["bytes"]),
                "invalid baseline comparison row")
        require(rows[name]["baseline"] == old and rows[name]["final"] == final, "baseline comparison bytes differ: "+name)
        if old == final:
            expected = "unchanged"
        elif name in SOURCE_CHANGES:
            expected = "authorized_source_change"
            changed_source.add(name)
        else:
            require(name in amendment_by_path, "unscoped original file changed: "+name)
            expected = "scoped_test_amendment"
        require(rows[name]["classification"] == expected, "incorrect original classification: "+name)
    require(changed_source == SOURCE_CHANGES and comparison["all_other_original_files_equal"] is True, "source changes or original equality declaration differs")
    known_originals = {row["source"] for row in source.values()}
    for key in ("baseline", "integration_scope", "report_template", "builder", "checker", "plan"):
        known_originals.add(str(absolute(inputs[key]["path"])))
    external = load_json(capsule/"EXTERNAL_REFERENCES.json")
    require(external["version"] == "factual_frame007_external_references_v1", "wrong external reference version")
    require(external["references"] == inputs["external_refs"], "external reference inventory differs")
    for row in inputs["external_refs"]:
        known_originals.add(str(absolute(row["path"])))
        require(isinstance(row["sha256"], str) and SHA.fullmatch(row["sha256"]), "invalid external identity")
        if row["copy_member"] is not None:
            require(relative(row["copy_member"]) in files and files[row["copy_member"]]["sha256"] == row["sha256"], "external authority copy differs")
    require(controls["aliases"] == manifest["aliases"], "copy-control alias rows differ")
    mapped_sources = {}
    for name, row in controls["files"].items():
        require(set(row) == {"source", "before", "after", "copy_equals_source"}, "invalid copy-control file shape")
        require(relative(name) in members, "copy control names missing member")
        original = str(absolute(row["source"]))
        valid_witness(row["before"])
        valid_witness(row["after"])
        require(row["before"] == row["after"] and row["copy_equals_source"] is True, "copied original changed: "+name)
        require(all(row["before"][key] == files[name][key] for key in ("sha256", "bytes")), "copy differs from source witness: "+name)
        mapped_sources.setdefault(original, []).append(name)
    for key in ("baseline", "integration_scope", "report_template", "builder", "checker", "plan"):
        authority = inputs[key]
        require(any(files[member]["sha256"] == authority["sha256"]
                    for member in mapped_sources.get(authority["path"], [])),
                "explicit authority original is not copied exactly: "+key)
    require(all("source/"+name in controls["files"] for name in source), "source copies lack original controls")
    original_tree_checks = []
    evidence_prefixes = {}
    mapped_directories = {}
    known_aliases = {}
    require(set(controls["trees"]) == set(inputs["evidence_roots"]), "evidence tree controls differ from finalized roots")
    for name, row in controls["trees"].items():
        require(set(row) == {"source_root", "prefix", "before", "after"}, "invalid tree control shape")
        configured = inputs["evidence_roots"][name]
        require(configured["final"] is True and configured["synthetic_engineering_only"] is True, "unfinished/nonfixture evidence root")
        root = absolute(row["source_root"])
        require(str(root) == configured["path"], "evidence source root differs")
        prefix = relative(row["prefix"])
        evidence_prefixes[name] = prefix
        validate_snapshot(row["before"])
        validate_snapshot(row["after"])
        require(row["before"] == row["after"], "evidence tree changed during copy")
        before = row["before"]
        mapped_directories.setdefault(str(root), []).append(prefix)
        for path in before["directories"]:
            mapped_directories.setdefault(str(root/path), []).append(prefix+"/"+path)
        for path, alias in before["aliases"].items():
            known_aliases[str(root/path)] = alias
        require({path for path in members if path.startswith(prefix+"/")} == {prefix+"/"+path for path in before["files"]}, "copied evidence file membership differs")
        require({path for path in aliases if path.startswith(prefix+"/")} == {prefix+"/"+path for path in before["aliases"]}, "copied evidence alias membership differs")
        require({path for path in actual["directories"] if path == prefix or path.startswith(prefix+"/")}
                == {prefix, *(prefix+"/"+path for path in before["directories"])}, "copied evidence directory membership differs")
        for path, witness in before["files"].items():
            member = prefix+"/"+path
            original = str(root/path)
            known_originals.add(original)
            require(controls["files"][member]["source"] == original
                    and controls["files"][member]["before"] == witness, "tree/file original witness differs")
        original_tree_checks.append((root, before))
        authority = configured["manifest"]
        known_originals.add(str(absolute(authority["path"])))
        require(any(files[member]["sha256"] == authority["sha256"] for member in mapped_sources.get(authority["path"], [])), "evidence manifest original is not copied exactly")
    for name, row in manifest["aliases"].items():
        require(set(row) == {"original_path", "original_target", "published_target", "target_member", "mapping_kind", "authority"}, "invalid alias mapping shape")
        require(row["published_target"] == aliases[name]["target"] and not row["published_target"].startswith("/"), "alias not rebased relatively")
        target = relative(row["target_member"], dot=True)
        require((target in members or target in directories)
                and os.path.normpath(os.path.join(str(PurePosixPath(name).parent), row["published_target"])) == target,
                "alias target escapes or differs")
        original = str(absolute(row["original_path"]))
        require(original in known_aliases and known_aliases[original]["target"] == row["original_target"],
                "alias original absent from finite nofollow controls")
        mapping = inputs["alias_mappings"][original]
        require(mapping["original_target"] == row["original_target"] and mapping["authority"] == row["authority"], "alias source mapping authority differs")
        target_source = str(absolute(mapping["target_source"]))
        require(target in mapped_sources.get(target_source, []) or target in mapped_directories.get(target_source, []),
                "alias target lacks known copied original file/directory")
        require(isinstance(row["mapping_kind"], str) and row["mapping_kind"], "alias mapping kind is missing")
        if row["authority"] is not None:
            authority = row["authority"]
            known_originals.add(str(absolute(authority["path"])))
            require(any(files[member]["sha256"] == authority["sha256"] for member in mapped_sources.get(authority["path"], [])), "alias authority copy differs")
    selected_inputs = {row["id"]: row for row in inputs["selected_invocations"]}
    selected = results["selected_invocations"]
    require(len(selected_inputs) == len(inputs["selected_invocations"]) and len(selected) == len(selected_inputs)
            and {row["id"] for row in selected} == set(selected_inputs), "selected invocation identities differ")
    verified_invocations = []
    for row in selected:
        expected = selected_inputs[row["id"]]
        for key in ("evidence_name", "expected_counts", "runtime_pin", "classification", "passed_at_final_pin"):
            require(row[key] == expected[key], "selected invocation declaration differs: "+key)
        for key in ("xml", "log"):
            member = relative(row[key+"_member"])
            require(row["evidence_name"] in evidence_prefixes and member.startswith(evidence_prefixes[row["evidence_name"]]+"/"),
                    "selected XML/log is outside its declared evidence tree")
            require(member in members and files[member]["sha256"] == expected[key]["sha256"], "selected XML/log bytes differ")
            require(controls["files"][member]["source"] == expected[key]["path"], "selected XML/log original differs")
        counts, seconds, nodeids = xml_facts(read_bytes(capsule/row["xml_member"]))
        require(set(row["expected_counts"]) == {"cases", "failed", "errors", "skipped"}
                and all(integer(value) for value in row["expected_counts"].values()), "invalid expected XML counts")
        require(counts == row["expected_counts"] == row["actual_counts"], "selected XML counts differ")
        require(all(integer(value) for value in row["actual_counts"].values()), "invalid recorded actual XML count types")
        require(seconds == row["suite_seconds"] and nodeids == row["nodeids"], "selected XML duration/node identities differ")
        require(type(row["passed_at_final_pin"]) is bool, "final-pin flag is not boolean")
        if row["passed_at_final_pin"]:
            require(row["runtime_pin"] == expected_pin and counts["cases"] > 0 and counts["failed"] == counts["errors"] == 0, "failed/different-pin invocation marked final")
        verified_invocations.append({"id": row["id"], "counts": counts, "runtime_pin": row["runtime_pin"], "passed_at_final_pin": row["passed_at_final_pin"]})
    require(results["counting"] == "no sum across overlapping invocations or different pins", "overlap counting declaration differs")
    report_row = manifest["report"]
    require(report_row == {"path": str(report), "member": "REPORT.md", "sha256": files["REPORT.md"]["sha256"]}, "manifest report authority differs")
    report_before = file_witness(report)
    report_bytes = read_bytes(report)
    require(report_bytes == read_bytes(capsule/"REPORT.md"), "published report is not an exact byte copy")
    require(b"RESULTS_FINAL.json" in report_bytes and files["RESULTS_FINAL.json"]["sha256"].encode() in report_bytes,
            "report does not name exact RESULTS_FINAL.json and digest")
    original_file_count = 0
    if check_originals:
        for name, row in controls["files"].items():
            require(row["source"] in known_originals, "unknown original not read: "+row["source"])
            require(file_witness(absolute(row["source"])) == row["before"], "original nofollow witness changed: "+name)
            original_file_count += 1
        for root, before in original_tree_checks:
            require(tree_snapshot(root) == before, "original nofollow tree membership/metadata changed: "+str(root))
    require(tree_snapshot(capsule) == actual, "sealed capsule changed while checking")
    require(file_witness(report) == report_before, "published report changed while checking")
    return {"status": "passed", "runtime_pin": expected_pin, "historical_interface_pin": HISTORICAL_INTERFACE_PIN,
        "runtime_files": len(runtime), "test_files": len(tests),
        "baseline_original_files": len(baseline), "original_source_changes": sorted(changed_source),
        "scoped_test_amendments": sorted(amendment_by_path),
        "manifest_sha256": files["MANIFEST.json"]["sha256"],
        "results_final_member": "RESULTS_FINAL.json", "results_final_sha256": files["RESULTS_FINAL.json"]["sha256"],
        "report_sha256": files["REPORT.md"]["sha256"], "member_count_excluding_manifest": len(members),
        "content_bytes_excluding_manifest": sum(row["bytes"] for row in members.values()),
        "directory_count": len(directories), "alias_count": len(aliases),
        "capsule_unchanged_during_check": True, "report_unchanged_during_check": True,
        "selected_invocations": verified_invocations, "invocations_not_summed": True,
        "original_files_checked": original_file_count, "original_trees_checked": len(original_tree_checks) if check_originals else 0,
        "no_alias_following": True, "application_or_tests_executed": False,
        "limits": results["limits"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capsule", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--check-originals", action="store_true")
    args = parser.parse_args()
    capsule, report, output = (absolute(value) for value in (args.capsule, args.report, args.output))
    require(not output.is_relative_to(capsule), "checker output must be outside the sealed capsule")
    parent = open_directory(output.parent)
    try:
        descriptor = os.open(output.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
    finally:
        os.close(parent)
    result = {"version": "factual_frame007_independent_check_v1", "capsule": str(capsule),
        "report": str(report), "check_originals": args.check_originals,
        "started_at": datetime.now(timezone.utc).isoformat()}
    try:
        result.update(check(capsule, report, args.check_originals))
    except Exception as error:
        result.update(status="failed", error_type=type(error).__name__, error=str(error))
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": result["status"], "output": str(output), "sha256": file_witness(output)["sha256"]}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
