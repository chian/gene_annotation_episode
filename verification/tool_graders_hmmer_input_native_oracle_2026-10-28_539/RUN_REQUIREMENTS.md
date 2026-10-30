# Root-owned bounded execution handoff

Use the existing packet529 `run_checks.py`/`bounded_entry.py` lifecycle, selected
by root. Do not run compiler, application imports, pytest collection or tests on
the host. Limits are 20 GiB RAM, 4 GiB scratch, zero swap, and no wall-time cap.
This packet creates no scheduler, runtime, service, job or production dependency.

Select `tests/test_hmmer_alignment_input_native_oracle.py` with the coherent root
snapshot containing the new alphabet, FASTA and shared primitive modules plus
existing hmmalign_inputs and its existing package dependencies. Stage this entire
539 packet, the complete retained Easel tree, and these two original emission
folders, preserving repository-relative paths:

- verification/tool_graders_infernal_preparation_emission_2026-10-26_250/native/aligned_a2m
- verification/tool_graders_infernal_preparation_emission_2026-10-26_250/native/a2m_insertions

The finite exact build/input dependencies are SOURCE_PINS.json: 43 Easel files
(12 original C translation units, 30 headers, original libeasel.a), the observer,
case metadata and every used fixture. Staging a complete source tree preserves
upstream source identity without selecting additional execution. The native
compile/link flags, include paths and all file hashes are fixed there. The
archive SHA256 is 94db21cb1a09e54abf99682d2120571915cdf70bfeef8b7515969691248dd48d.

Set explicitly inside the selected job:

```
HMMER_NATIVE_ORACLE_EASEL_DIR=<snapshot>/resources/software/infernal-1.1.5/easel
HMMER_NATIVE_ORACLE_CC=<absolute root-selected pinned C99 compiler>
```

The first name deliberately reuses the exact 528/529 spelling, including DIR.
No alimask executable is required or invoked. Root owns pinning compiler/internal
compiler/linker programs, system C headers, runtime startup objects, libc, libm,
pthread and their dependencies through packet 529's existing compiler audit. No implicit
installed-program lookup, make/configure run, source rewrite or native producer
invocation is present. C locale and temporary directories are explicit in each
recorded compile/link/native subprocess. No process timeout is supplied.

Each source is compiled separately with the inherited packet 528 C99/O2/fno-fast-math/
ffp-contract=off flags and an MMD dependency file. Only original esl_alphabet.c
gets `-Desl_abc_GuessAlphabet=oracle_original_GuessAlphabet`. All twelve compiled
objects and observer object precede original libeasel.a at link time, followed
by -lm -lpthread. This binds original input/scanner/checksum implementation to
the diagnostic and leaves support objects in the pinned original archive.

Exact test selectors:

```
tests/test_hmmer_alignment_input_native_oracle.py
tests/test_hmmer_alignment_input_native_oracle.py::test_classifier_exact_native_status_and_precedence
tests/test_hmmer_alignment_input_native_oracle.py::test_per_format_guess_histograms_and_checkpoints
tests/test_hmmer_alignment_input_native_oracle.py::test_afa_a2m_native_digital_rows_rf_width_and_failures
```

Retain the entire job receipt and pytest basetemp. The module fixture writes its
verified pins, explicit selected paths/compiler digest/version, all compile/link
argv/stdout/stderr/returncodes, object dependency files and binary digest. Each
case retains its metadata, exact native input bytes and identity, command, actual
native stdout/stderr/returncode, Python result, and comparison.json only after
all assertions pass. The source reset record verifies original source/fixture
bytes remain identical; no reset is needed because originals are never edited.
Missing pins/build inputs are failures, never skipped conformance. A build failure
or inaccessible instrumentation must be reported as such; no fabricated histogram
or downgraded claim may stand in for a missing checkpoint oracle.

No build, pytest collection, native comparison, scientific execution, episode
return or resource verification has been run by the author. Root's first bounded
run remains necessary. Diagnostic compilation identifies this retained Easel 0.49
profile; it does not recover the historical HMMER executable compilation history.
