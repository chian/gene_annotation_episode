# Candidate application instructions

This delivery has **not** been applied to the original checkout. All eight
implementation/schema edits and all five test edits exist only in `candidate/`.
`DELTA_MANIFEST_001.json` lists the exact thirteen paths and before/after hashes.
`DELTA_001.patch` is the complete reviewable delta, SHA256
`4449fb7c681fdf51dfb500d2ce9ea8e2f76003dd2688a9ce54d2a20f6ade8b56`.

Root owns application. Preserve the original GenomeAlignment verification161
closure until that run's natural terminal status and its final source guards,
as required by handoff014. Do not edit a source while a verification process is
using its original closure. The steps below describe the later concrete apply;
they do not report that it occurred.

1. From `/home/chia/repos/gene_annotation_episode`, verify the target files still
   match the manifest. Any mismatch needs an additive conflict review, not a
   forced patch or replacement of historical source receipts:

   ```python
   from pathlib import Path
   import hashlib, json
   root = Path.cwd()
   area = root / 'verification/tool_graders_bvbrc_proteome_submission_binding_2026-10-25_175'
   manifest = json.loads((area / 'DELTA_MANIFEST_001.json').read_text())
   assert hashlib.sha256((area / 'DELTA_001.patch').read_bytes()).hexdigest() == manifest['patch_sha256']
   for row in manifest['files']:
       target = root / row['path']
       if row['kind'] == 'new':
           assert not target.exists(), row['path']
       else:
           assert hashlib.sha256(target.read_bytes()).hexdigest() == row['before_sha256'], row['path']
   ```

2. Dry-run and apply the complete patch from that same working directory:

   ```sh
   patch --dry-run --forward -p1 < verification/tool_graders_bvbrc_proteome_submission_binding_2026-10-25_175/DELTA_001.patch
   patch --forward -p1 < verification/tool_graders_bvbrc_proteome_submission_binding_2026-10-25_175/DELTA_001.patch
   ```

   Do not apply only the host enum. The native/data/sheet/bundle/directional
   dependency copies must change together. The two decoder/validator edits
   establish the real retained-wrapper path. The three prospective assertion
   amendments preserve exact historical checks after removing only the new
   final enum member from detached schema copies; frozen JSON assets stay
   unchanged.

3. Verify every resulting file's SHA256 equals `candidate_sha256` in the
   manifest. `PATCH_APPLICATION_RECEIPT_001.json` records a successful dry-run
   and application to the separate `patch_apply_check_001/` copy, where all
   thirteen results already matched these candidate hashes.

4. Run the submitted-source and affected consumers from the applied checkout
   using its `.venv/bin/python`, recording new logs/XML under a new receipt
   name. The complete candidate command is in `TEST_COMMAND_009.json`; it covers
   the two new tests and AppService, native/data/sheet/provider/projection and
   directional consumers. Verify imports resolve to the intended applied
   checkout. Preserve every numbered receipt in this delivery.

5. Connect any selected provider dispatch, publication or episode-return work
   through the separately owned integration changes. This patch does not add
   those bindings. Do not describe a pure provider result or the controlled
   transport test as a live GenomeComparison scientific run.

The request source remains the exact `OriginalTask.submission_source_ref`.
It is read through `ContentBinding.artifact_field='request_ref'`; the parameter
pointer is `/prepared/native_operands/call/rpc_request/params/1`. No historical
TaskHandoff, source record, request, observation or numerical result is rewritten
by applying these source changes.
