# Native HIC fixture provenance and commands

This packet implements prerequisite workload P for the fixed B-L124 format
boundary. It changes no production/parser/prompt file, shared environment,
scientific mode, accounting row or tally. The original supplied goal attachment
is authoritative; this is an implementation record, not a substitute goal.
Its path and SHA256 are retained in each selected request and FIXTURES.json.
GOAL.md was not read.

## Selected upstream software

The selected official hictk release is **2.2.0**, source commit
`473017312558cd805f470722c2c91a03b91df807`. Primary sources examined:

- [Official release](https://github.com/paulsengroup/hictk/releases/tag/v2.2.0).
  The retained release API response has no binary assets.
- [Official installation instructions](https://hictk.readthedocs.io/en/v2.2.0/installation.html)
  explicitly publish `ghcr.io/paulsengroup/hictk:2.2.0`.
- [Pinned upstream Dockerfile](https://github.com/paulsengroup/hictk/blob/473017312558cd805f470722c2c91a03b91df807/Dockerfile).
  Its final image copies the native binary to `/usr/local/bin/hictk`.
- [Official source-build instructions](https://hictk.readthedocs.io/en/v2.2.0/installation_src.html).
- [Official HIC v9 format](https://github.com/aidenlab/hic-format/blob/master/HiCFormatV9.md).
  The inspected retained snapshot is in packet452/sources/hic-format-v9.md;
  this is a retained source snapshot, not a claim that an unpinned web page can
  never change.
- [Pinned native writer](https://github.com/paulsengroup/hictk/blob/473017312558cd805f470722c2c91a03b91df807/src/libhictk/hic/include/hictk/hic/impl/file_writer_data_structures_impl.hpp),
  [writer API](https://github.com/paulsengroup/hictk/blob/473017312558cd805f470722c2c91a03b91df807/src/libhictk/hic/include/hictk/hic/file_writer.hpp),
  [independent native reader](https://github.com/paulsengroup/hictk/blob/473017312558cd805f470722c2c91a03b91df807/src/libhictk/hic/include/hictk/hic/impl/block_reader_impl.hpp).

`prerequisite002` retains the source archive, extracted pinned source, HTTP
request/response identities, official image index, manifest and configuration.
The selected linux/amd64 manifest is
`sha256:df5f95075d476cf453f63c12e72894d873d33f268ec0ba9159a1a49c71eb15c5`.
Its configuration names the exact source commit above. The selected binary layer
is `sha256:c7bf16a195dfd733b95757f7243c08b0f27830d5edb31cac9b54fc68bcc40821`
(8,195,493 compressed bytes); both digest and declared length were checked.
Only the native binary was extracted, without installing/running a container
engine or importing a container root filesystem.

`prerequisite003/hictk` is 19,885,568 bytes, SHA256
`aaae1ec459a63ff8be922b026c4799da4135bb81df78c756feae9dc7a8176afe`.
It actually reports `hictk-v2.2.0`. Its runtime linker/library bytes are pinned
in `prerequisite003/RUNTIME_DEPENDENCIES.json`. Its embedded build/dependency
report is `evidence011/official_build_metadata.stdout.txt`: Release build,
Clang 21.1.5, with the full actual embedded dependency-version map retained.
These are distinct from the local GCC build used for the harness.

## Resource and lifecycle commands

The copied `run_bounded.py` is packet-local launch/collection code using the
existing `LocalJobPolicy`, `start_job`, `status` and `wait_job`. The parent command
uses repository `.venv/bin/python`; the actual selected payload interpreter is
`reference/episode_tools/.venv/bin/python` (CPython 3.12.3). Native commands and
imports are inside those jobs. Every job has 20 GiB RAM, zero swap, 4 GiB scratch
and no wall allocation. Scratch is monitored with possible overshoot, not a hard
aggregate filesystem quota. Original handles were followed to authoritative
terminal/quiescent state; observation waits did not resubmit work.

From the repository root, the exact packet launch/collection form was:

```text
.venv/bin/python -B verification/tool_graders_chromatin_hic_native_2026-10-27_454/run_bounded.py launch ATTEMPT SCRIPT
.venv/bin/python -B verification/tool_graders_chromatin_hic_native_2026-10-27_454/run_bounded.py collect ATTEMPT
```

| Attempt | Selected script | Terminal result |
|---|---|---|
| prerequisite001 | probe_release.py | Exit1: an incorrectly named `installation_source.rst` returned HTTP404; environment/release facts retained. |
| prerequisite002 | acquire_official.py | Exit0: exact source archive and official image metadata acquired. |
| prerequisite003 | acquire_binary.py | Exit0: layer digest/length checked, binary extracted, actual CLI/version/dependencies inspected. |
| native004 | generate_four.py | Exit0: exact nine-row first fixture; native dump and independent byte audit agree. |
| native005 | generate_variants.py | Exit0: insulation, terminal bins, All index, multiblock and actual absent-matrix output. |
| prerequisite006 | prepare_writer_build.py | Exit1: PyPI has no CMake3.31.8 distribution. Failed request/snapshot retained. |
| prerequisite007 | prepare_writer_build.py | Exit0: explicitly corrected CMake3.31.10, Conan2.22.1, Ninja1.13.0; isolated pinned-source dependencies built. |
| native008 | build_and_run_writer.py | Exit1: harness compilation lacked the explicit official `file_writer.hpp` include. |
| native009 | build_and_run_writer.py | Exit0 after include repair: official API vectors generated; separate short/long requests correctly exited2. |
| native010 | generate_encoding_fixtures.py | Exit0:16 full native encoding cases independently decoded by official hictk. |
| evidence011 | finalize_evidence.py | Exit0: build/runtime pins, corrected native weights dumps, independent arithmetic and27-case manifest. |

Each attempt retains `selected_request.json`, immutable `selected_input.py`,
`handle.json`, native output/error files, `terminal_status.json`, `receipt.json`
and before/after source pins. All11 receipts are terminal/quiescent and their
source pins were unchanged during their original runs. Failed script snapshots
are preserved even where the reusable source script was corrected later.

Native subcommands are preserved as complete absolute argv arrays in each
`*.request.json`; stdout, stderr and exact return code remain alongside them.
For example, `native004/load.request.json` records the actual command after
`load --help` had been checked:

```text
hictk load --format coo --output-fmt hic --bin-size 10
  --chrom-sizes <native004>/four.chrom.sizes --assembly synthetic_four_bin
  --zero-based --validate-pixels --no-transpose-lower-triangular-pixels
  --skip-all-vs-all --threads 2 --chunk-size 32 --tmpdir <native004>/tmp
  <native004>/four.coo <native004>/four.hic
```

The original input is literal tab-delimited `chrA\t40\n` plus nine COO rows;
the actual retained inputs and their hashes are in `native004`. No guessed
layout was imposed on that writer. All hictk commands set
`HICTK_NO_TELEMETRY=1`; native temporary locations are explicit owned paths.

## Official writer harness and distinct fixture writer

`writer_harness.cpp` calls the unmodified official
`hictk::hic::internal::HiCFileWriter` and `add_norm_vector` with
`Weights::Type::DIVISIVE`. Each selected variant starts from a separate copy of
the retained native004 file. The harness writes the named vector and native
normalized-expected section through the official API. Expected-vector values
are not used as the scientific diagonal denominator.

`prerequisite007` contains the isolated build environment, exact original source,
Conan package graph and pip artifact reports. No shared environment was changed.
`native009` retains the CMake request, source snapshot, successful binary,
linker/runtime identities and all seven variant requests. `evidence011` adds
the actual Ninja compile/link commands and **571** hashed compile/tool/source
inputs, including the compiler and statically linked dependency archives.

The separately named `fixture_spec_writer.py` is an explicitly authored
**whole-file native-format fixture serializer**, not hictk, Juicer or H1 code.
It emits actual HIC\0/version9 headers, chromosome/zoom/master indexes,
zlib-compressed blocks, footer and optional vector bytes. It follows the official
byte specification and independently varied count/x/y flags. Each emitted file
was then read by the pinned official hictk binary; no in-memory decoded object
was substituted for a native file. `WIRE_LAYOUT.json` records its byte offsets
and `BYTE_AUDIT.json` records a separately authored diagnostic decoder's results.
The diagnostic decoder imports no production code. It is limited to this small
fixture audit and is not a proposed production reader.

The official reader is essential independent evidence for these custom-format
fixtures: its native raw dump matches all original nonfiller rows for every
case, including explicit zeros and row-list NaN/Inf/negative values. That proves
serialization/decoding agreement for those supplied bytes, not experimental
validity or production integration.
