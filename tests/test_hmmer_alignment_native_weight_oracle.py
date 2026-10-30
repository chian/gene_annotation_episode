"""Authentic source-linked Easel conformance, executed only by root's job.

No native output is embedded in these tests. Explicit constructed inputs are
written in the selected job, real retained C is compiled there, and complete
native outputs are compared with the existing Python helpers/common normalizer.
The three HMMER_NATIVE_ORACLE_* environment paths are mandatory. Missing inputs
fail verification; there is no host search, download, or skip-as-success path.

Root must use its frozen native_lifecycle/local_jobs runner with 20 GiB RAM,
4 GiB scratch, no swap and no wall-time cap, and retain pytest's --basetemp tree.
This diagnostic does not run alimask or establish a Workflow/child-return path.
The unchanged packet 525 sampler harness exercises an explicit positive-seed
API, independently of alimask's retained effective PB seed 42.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

import pytest

from gene_annotation_episode.hmmer_alignment_preparation_calculations import (
    _normalize_easel_weights,
)
from gene_annotation_episode.hmmer_alignment_tree_weights import (
    blosum_raw_weights,
    gsc_raw_weights,
)
from gene_annotation_episode import hmmer_alignment_pb_sampling as sampling


_REPO = Path(__file__).resolve().parents[1]
_PACKET = _REPO / "verification/tool_graders_hmmer_native_weight_oracles_2026-10-28_528"
_ALIMASK_SHA256 = "4cf273b7b4b52363468b758a39bedf8f00540b01983bf6641ffd36140afad547"
_SYMBOLS = {
    "dna": "ACGTRYMKSWHBVDN",
    "rna": "ACGURYMKSWHBVDN",
    "amino": "ACDEFGHIKLMNPQRSTVWYBJZOUX",
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _required_path(variable, *, directory=False):
    supplied = os.environ.get(variable)
    if not supplied:
        pytest.fail(f"{variable} must name an explicitly staged native verification input")
    path = Path(supplied).resolve(strict=True)
    assert path.is_dir() if directory else path.is_file(), (variable, str(path))
    return path


def _check_pin(path, pin):
    assert path.is_file(), f"missing staged native/support input: {path}"
    assert path.stat().st_size == pin["size_bytes"], str(path)
    assert _sha256(path) == pin["sha256"], f"staged input digest changed: {path}"


def _run_recorded(argv, directory, label, *, env):
    """Retain the real command and both byte streams before checking success."""
    argv = [str(value) for value in argv]
    _write_json(directory / f"{label}.argv.json", argv)
    completed = subprocess.run(argv, cwd=directory, env=env, capture_output=True, check=False)
    (directory / f"{label}.stdout").write_bytes(completed.stdout)
    (directory / f"{label}.stderr").write_bytes(completed.stderr)
    _write_json(directory / f"{label}.exit.json", {"returncode": completed.returncode})
    assert completed.returncode == 0, (
        f"{label} exited {completed.returncode}; retained output: {directory}"
    )
    return completed.stdout


class _NativeOracles:
    def __init__(self, root, env, weights, sampler):
        self.root = root
        self.env = env
        self.weights = weights
        self.sampler = sampler

    def case(self, name, *, inputs):
        directory = self.root / name
        directory.mkdir()
        _write_json(directory / "constructed_input.json", inputs)
        return directory

    def call(self, executable, arguments, directory):
        data = _run_recorded([executable, *arguments], directory, "native", env=self.env)
        return json.loads(data.decode("ascii"))


@pytest.fixture(scope="module")
def native_oracles(tmp_path_factory):
    easel = _required_path("HMMER_NATIVE_ORACLE_EASEL_DIR", directory=True)
    compiler = _required_path("HMMER_NATIVE_ORACLE_CC")
    alimask = _required_path("HMMER_NATIVE_ORACLE_ALIMASK")
    pins = json.loads((_PACKET / "SOURCE_PINS.json").read_text())
    assert pins["profile"]["executable_sha256"] == _ALIMASK_SHA256
    for relative, pin in pins["easel_files"].items():
        source = (easel / relative).resolve(strict=True)
        assert source.is_relative_to(easel), f"native input escapes staged Easel: {relative}"
        _check_pin(source, pin)
    _check_pin(alimask, pins["alimask_executable"])
    # Root stages this source beside the selected binary; neither is executed.
    _check_pin(alimask.with_name("alimask.c"), pins["alimask_source"])
    for relative, pin in pins["diagnostic_sources"].items():
        _check_pin(_REPO / relative, pin)

    root = tmp_path_factory.mktemp("hmmer_native_weight_oracle")
    temporary = root / "compiler_tmp"
    temporary.mkdir()
    env = os.environ.copy()
    env.update(TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary), LC_ALL="C")
    _write_json(root / "verified_source_pins.json", pins)
    _write_json(root / "selected_paths.json", {
        "easel": str(easel), "compiler": str(compiler), "compiler_sha256": _sha256(compiler),
        "alimask": str(alimask), "alimask_executed": False,
        "evidence_kind": "source_linked_native_diagnostic_not_alimask_cli",
    })
    _run_recorded([compiler, "--version"], root, "compiler_version", env=env)
    flags = ["-std=c99", "-O2", "-fno-fast-math", "-ffp-contract=off", "-I", str(easel)]
    objects = {}
    for filename in pins["compile_native_sources"]:
        name = Path(filename).stem
        destination = root / f"{name}.o"
        _run_recorded([
            compiler, *flags, "-MMD", "-MF", root / f"{name}.d",
            "-c", easel / filename, "-o", destination,
        ], root, f"compile_{name}", env=env)
        objects[filename] = destination
    binaries = {}
    for name, relative in pins["harnesses"].items():
        harness_object = root / f"{name}_harness.o"
        _run_recorded([
            compiler, *flags, "-MMD", "-MF", root / f"{name}_harness.d",
            "-c", _REPO / relative, "-o", harness_object,
        ], root, f"compile_{name}_harness", env=env)
        sources = pins["weight_link_sources"] if name == "weights" else ["esl_rand64.c"]
        binary = root / f"{name}_oracle"
        _run_recorded([
            compiler, harness_object, *(objects[source] for source in sources),
            easel / "libeasel.a", "-lm", "-lpthread", "-o", binary,
        ], root, f"link_{name}", env=env)
        binaries[name] = binary
    _write_json(root / "built_binaries.json", {
        name: {"path": str(path), "sha256": _sha256(path), "size_bytes": path.stat().st_size}
        for name, path in binaries.items()
    })
    return _NativeOracles(root, env, binaries["weights"], binaries["sampler"])


def _exact_doubles(actual, native_hex, *, field):
    assert len(actual) == len(native_hex), field
    for index, (number, token) in enumerate(zip(actual, native_hex)):
        observed = float.fromhex(token)
        assert math.isfinite(number) and math.isfinite(observed), (field, index)
        assert float(number).hex() == observed.hex(), (field, index, float(number).hex(), token)


def _native_weight_case(oracles, method, case_id, alphabet, sequences, cutoff=None):
    directory = oracles.case(f"{method}_{case_id}", inputs={
        "basis": "explicit_constructed_alignment", "alphabet": alphabet,
        "sequences_in_original_order": sequences, "identity_cutoff": cutoff,
    })
    alignment = directory / "input.sto"
    alignment.write_text("# STOCKHOLM 1.0\n" + "".join(
        f"row_{index} {sequence}\n" for index, sequence in enumerate(sequences)
    ) + "//\n", encoding="ascii")
    arguments = [method, alphabet, alignment]
    if cutoff is not None:
        arguments.append(float(cutoff).hex())
    native = oracles.call(oracles.weights, arguments, directory)
    assert native["kind"] == "diagnostic_easel_msaweight"
    assert native["easel_version"] == "0.49"
    assert native["method"] == method and native["alphabet"] == alphabet
    assert native["digitized_sequences"] == list(sequences)
    assert native["sequence_count"] == len(sequences)
    assert native["alignment_width"] == len(sequences[0])
    assert native["normalization_calls"] == (0 if len(sequences) == 1 else 1)
    assert native["raw_basis"] == (
        "native_singleton_early_return" if len(sequences) == 1 else "copy_before_original_DNorm"
    )
    options = {"residue_symbols": _SYMBOLS[alphabet]}
    if method == "gsc":
        helper = gsc_raw_weights(list(sequences), **options)
    else:
        helper = blosum_raw_weights(list(sequences), identity_cutoff=cutoff, **options)
    normalized, normalization = _normalize_easel_weights(helper["raw_weights"])
    _write_json(directory / "python_result.json", {
        "helper": helper, "shared_normalized_weights": normalized,
        "shared_normalization": normalization,
    })
    _exact_doubles(helper["raw_weights"], native["raw_weights_hex"], field="raw_weights")
    _exact_doubles(normalized, native["normalized_weights_hex"], field="normalized_weights")
    _exact_doubles([normalization["sum"]], [native["normalization_sum_hex"]], field="native_Kahan_sum")
    assert normalization["method"] == "easel_kahan_divide_then_scale"
    assert normalization["sequence_count"] == len(sequences)
    assert normalization["zero_sum"] is (float.fromhex(native["normalization_sum_hex"]) == 0.0)
    if case_id.startswith("minimum_residue_count"):
        assert native["pairs"] == [{
            "rows": [0, 1], "identity_hex": native["pairs"][0]["identity_hex"],
            "identical_residues": 1, "denominator": 2,
        }]
        _exact_doubles([0.5], [native["pairs"][0]["identity_hex"]], field="native_pair_identity")
    return directory, helper, native


# Constructed inputs, not fabricated native answers. C supplies every expected
# tree, cluster, raw vector, normalized vector and sample row at execution time.
_GSC_CASES = [
    ("singleton", "dna", ("A",)),
    ("singleton_without_residues", "dna", ("-~*",)),
    ("identical_residues", "dna", ("ACGN",) * 4),
    ("identical_all_gap", "dna", ("---",) * 4),
    ("no_residues", "dna", ("--", "~*", "**")),
    ("exact_upgma_ties", "dna", ("A", "C", "G", "T")),
    ("ties_reordered", "dna", ("T", "G", "A", "C")),
    ("zero_subtree_allocation", "dna", ("A", "A", "A", "C")),
    ("clade_weighted_distances", "dna", ("AAAA", "AAAA", "AAAC", "CCCC")),
    ("minimum_residue_count", "dna", ("A-CG", "AT--")),
    ("contained_fragment", "dna", ("AC--", "ACGT")),
    ("mixed_lengths", "dna", ("ACGTN-*~", "A-GTN-C~", "--GTNR*~", "CCCCN-*~")),
    ("degenerate_exact_codes", "dna", ("N-*~", "N-**", "A-~*")),
    ("rna_residues", "rna", ("AU--N", "AUGCN", "AU--R")),
    ("amino_degeneracies", "amino", ("ABJ-OUX*~", "ABZ-OUX~~", "A--DQLX*~")),
]


@pytest.mark.parametrize("case_id,alphabet,sequences", _GSC_CASES, ids=[case[0] for case in _GSC_CASES])
def test_gsc_raw_normalized_weights_and_exact_native_tree(native_oracles, case_id, alphabet, sequences):
    directory, helper, native = _native_weight_case(native_oracles, "gsc", case_id, alphabet, sequences)
    assert native["clusters"] is None and native["clusters_basis"] is None
    tree = helper["tree"]
    assert tree["children"] == native["tree"]["children"]
    assert tree["clade_sizes"] == native["tree"]["clade_sizes"]
    assert len(tree["branches"]) == len(native["tree"]["branches_hex"])
    for index, (branches, tokens) in enumerate(zip(tree["branches"], native["tree"]["branches_hex"])):
        _exact_doubles(branches, tokens, field=f"tree_branch_{index}")
    assert native["tree_basis"] == (
        "singleton_early_return_no_native_tree" if len(sequences) == 1 else "independent_esl_tree_UPGMA"
    )
    _write_json(directory / "comparison.json", {"status": "passed", "comparison": "exact_double_and_topology"})


_BLOSUM_CASES = [
    ("singleton", "dna", ("A",), 0.62),
    ("singleton_without_residues", "dna", ("-~*",), 1.0),
    ("identical_residues", "dna", ("N",) * 4, 1.0),
    ("identical_all_gap", "dna", ("---",) * 4, 1.0),
    ("no_residues_cutoff_one", "dna", ("--", "~*", "**"), 1.0),
    ("no_residues_cutoff_zero", "dna", ("--", "~*", "**"), 0.0),
    ("minimum_residue_count_equality", "dna", ("A-CG", "AT--"), 0.5),
    ("minimum_residue_count_above", "dna", ("A-CG", "AT--"), math.nextafter(0.5, 1.0)),
    ("contained_fragment", "dna", ("AC--", "ACGT"), 1.0),
    ("transitive_links", "dna", ("AAAA", "AACC", "CCCC", "GGGG"), 0.5),
    ("reverse_stack_cluster_ids", "dna", ("A", "C", "G", "A", "T"), 1.0),
    ("reordered_rows", "dna", ("T", "A", "G", "C", "A"), 1.0),
    ("degenerate_exact_codes", "dna", ("N-*~", "N-**", "A-~*"), 1.0),
    ("cutoff_zero", "dna", ("A", "C", "-"), 0.0),
    ("rna_residues", "rna", ("AU--N", "AUGCN", "AU--R"), 0.62),
    ("amino_degeneracies", "amino", ("ABJ-OUX*~", "ABZ-OUX~~", "A--DQLX*~"), 0.62),
]


@pytest.mark.parametrize("case_id,alphabet,sequences,cutoff", _BLOSUM_CASES, ids=[case[0] for case in _BLOSUM_CASES])
def test_blosum_raw_normalized_weights_and_native_cluster_order(
    native_oracles, case_id, alphabet, sequences, cutoff,
):
    directory, helper, native = _native_weight_case(
        native_oracles, "blosum", case_id, alphabet, sequences, cutoff,
    )
    assert native["tree"] is None and native["tree_basis"] is None
    assert helper["clusters"]["assignment"] == native["clusters"]["assignment"]
    assert helper["clusters"]["sizes"] == native["clusters"]["sizes"]
    _exact_doubles([helper["clusters"]["identity_cutoff"]],
                   [native["clusters"]["identity_cutoff_hex"]], field="identity_cutoff")
    assert native["clusters_basis"] == "independent_esl_msacluster_SingleLinkage"
    _write_json(directory / "comparison.json", {"status": "passed", "comparison": "exact_double_and_cluster_order"})


_NORMALIZATION_CASES = [
    ("singleton", [1.0]),
    ("zero_sum_49", [0.0] * 49),
    ("kahan_small_after_large", [1.0] + [2.0 ** -54] * 63),
    ("kahan_small_before_large", [2.0 ** -54] * 63 + [1.0]),
    ("large_integer_and_units", [2.0 ** 53, 1.0, 1.0, 1.0, 1.0]),
    ("unequal_positive", [0.1, 0.2, 0.3, 1e-17]),
]


@pytest.mark.parametrize("case_id,raw", _NORMALIZATION_CASES, ids=[case[0] for case in _NORMALIZATION_CASES])
def test_shared_kahan_divide_then_scale_against_native_vectorops(native_oracles, case_id, raw):
    directory = native_oracles.case(f"normalize_{case_id}", inputs={"basis": "constructed_raw_vector", "raw": raw})
    native = native_oracles.call(native_oracles.weights, ["normalize", *(value.hex() for value in raw)], directory)
    normalized, normalization = _normalize_easel_weights(raw)
    _write_json(directory / "python_result.json", {"weights": normalized, "normalization": normalization})
    assert native["kind"] == "diagnostic_easel_vector_normalization"
    assert native["easel_version"] == "0.49" and native["sequence_count"] == len(raw)
    _exact_doubles(raw, native["raw_weights_hex"], field="retained_normalization_operand")
    _exact_doubles(normalized, native["normalized_weights_hex"], field="normalized_weights")
    _exact_doubles([normalization["sum"]], [native["normalization_sum_hex"]], field="native_Kahan_sum")
    assert normalization["zero_sum"] is (float.fromhex(native["normalization_sum_hex"]) == 0.0)
    _write_json(directory / "comparison.json", {"status": "passed", "comparison": "exact_native_vectorops"})


# Every case has m>=1, m<=N<=INT64_MAX, 13*m<=INT64_MAX and a positive
# uint64 seed. Native seed=0, m=0 and signed-overflow setups are never executed.
_SAMPLE_CASES = [
    ("pb_scale_initial_A", 50001, 10000, 42),
    ("strict_D_switch_boundary", 130000, 10000, 42),
    ("pb_scale_D_then_A", 130001, 10000, 42),
    ("positive_seed_low_A", 50001, 10000, 1),
    ("positive_seed_high_A", 50001, 10000, (1 << 64) - 1),
    ("positive_seed_low_D", 130001, 10000, 1),
    ("positive_seed_high_D", 130001, 10000, (1 << 64) - 1),
    ("nondefault_seed_API", 130001, 10000, 43),
    ("singleton_population", 1, 1, 42),
    ("one_sample_seed_low", 17, 1, 1),
    ("one_sample_seed_high", 17, 1, (1 << 64) - 1),
    ("one_sample_double_integer_boundary", (1 << 53) + 1, 1, 42),
    ("one_sample_int64_boundary", (1 << 63) - 1, 1, 42),
    ("full_sample", 17, 17, 42),
    ("full_sample_refill_seed_high", 313, 313, (1 << 64) - 1),
    ("small_method_A", 10, 3, 42),
    ("small_method_D", 100, 3, 42),
]


@pytest.mark.parametrize("case_id,population_size,sample_size,seed", _SAMPLE_CASES, ids=[case[0] for case in _SAMPLE_CASES])
def test_sampler_exact_native_deal_indices(native_oracles, case_id, population_size, sample_size, seed):
    directory = native_oracles.case(f"sample_{case_id}", inputs={
        "basis": "explicit_positive_seed_sampler_API_not_CLI_seed",
        "population_size": population_size, "sample_size": sample_size, "seed": seed,
    })
    native = native_oracles.call(native_oracles.sampler,
                                ["deal", population_size, sample_size, seed], directory)
    actual = sampling.sample_easel_pb_rows(population_size, sample_size=sample_size, seed=seed)
    _write_json(directory / "python_result.json", {"rows": actual})
    assert native["kind"] == "diagnostic_easel_rand64_Deal"
    assert (native["population_size"], native["sample_size"], native["seed"]) == (
        population_size, sample_size, seed,
    )
    assert actual == native["rows"]
    assert len(actual) == sample_size
    assert 0 <= actual[0] <= actual[-1] < population_size
    assert all(left < right for left, right in zip(actual, actual[1:]))
    _write_json(directory / "comparison.json", {"status": "passed", "comparison": "every_native_row_ordinal"})


@pytest.mark.parametrize("seed", [1, 42, (1 << 64) - 1], ids=["minimum_positive", "effective_PB_42", "uint64_max"])
def test_sampler_native_mt_words_across_two_state_refills(native_oracles, seed):
    directory = native_oracles.case(f"stream_{seed}", inputs={"seed": seed, "word_count": 625})
    native = native_oracles.call(native_oracles.sampler, ["stream", seed, 625], directory)
    rng = sampling._EaselMT19937_64(seed)
    actual = [rng.uint64() for _ in range(625)]
    _write_json(directory / "python_result.json", {"words": actual})
    assert native["kind"] == "diagnostic_easel_rand64" and native["seed"] == seed
    assert actual == native["words"]
    _write_json(directory / "comparison.json", {"status": "passed", "comparison": "every_native_uint64_word"})
