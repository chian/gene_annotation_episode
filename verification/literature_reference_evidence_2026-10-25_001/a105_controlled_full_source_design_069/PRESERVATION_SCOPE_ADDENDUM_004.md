# Preservation scope004

The initial seal attempt stopped before creating a manifest because a broad
all-checked-checkout-files assertion was false. Current domain.py has SHA256
c76c6edd99ad9fdef94d7fba8416f0a2daf1643546948ffd697514f7f10a99a4,
while008 and063 pins retain
ccfacc70b7e7fc6c0c5a9eab4f410813ab5d155bfcc8e43a4ab40fba3170a775.
This agent did not modify domain.py or any production/test path. The cause or
author of that outside-owner checkout difference was not investigated here.
No unrelated repair or historical pin rewrite was attempted.

The corrected read-only audit records the mismatch instead of asserting global
checkout/pin equality. Every other current file checked against008/063 and every
checked068 entry matches its recorded identity, including the controlled source,
graph, owner calculator and arithmetic helper. READ_ONLY_PIN_CHECK_001.json gives
the exact per-file comparison. This is a preservation comparison, not execution
coverage or proof that all historical dependencies are the current checkout.

The source-only design, constructed arithmetic and reconstruction limits remain
unchanged. The first reconstruction path failure and this initial seal failure
are both preserved. The final manifest covers the coherent current design;
later corrections require a new additive generation.
