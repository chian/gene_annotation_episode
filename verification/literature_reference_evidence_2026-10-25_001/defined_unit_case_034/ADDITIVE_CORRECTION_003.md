# Additive correction 003: retained censored selector

The parent identified a preservation defect: verify_original_source.py saved CENSORED_SELECTION_002.json before replacing the test rate-number selector. That file retains the corrected crotonyl-CoA-omission label and intended change but still selects the Hyd 0.1 operand. It does not reproduce the reported censored result. The historical script, selector, reports and manifests remain unchanged.

CENSORED_SELECTION_003.json changes only arms.test.rate.number, binding the already reviewed omission row and its actual <0.01 source text. The new mechanical verification reloads that saved file before invoking unchanged pin030. It reproduces test_rate value=null, threshold=0.01, bound=lt and unavailable_reason=censored_measurement; rate_difference, retained_fraction and fractional_decrease remain unavailable. The source reference rate is7. No new scientific interpretation, model, workflow, observation, production edit, live-state mutation or historical rewrite occurred.

CENSORED_VERIFICATION_003.json contains the exact saved selection hash, extraction and calculated sheet. CENSORED_HASH_RECEIPT_003.json records original source/pin/import hashes and verifies every pre-existing case034 file is byte-identical. The old FILE_MANIFEST.json is preserved, not refreshed.
