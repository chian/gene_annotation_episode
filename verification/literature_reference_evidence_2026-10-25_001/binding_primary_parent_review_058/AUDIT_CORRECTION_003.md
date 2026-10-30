Root's first independent saved-only audit incorrectly queried the ordinary
runtime_record_receipts table in the separately direct-populated C4 fixture.
That fixture has its actual original admission/form, not an ordinary selected
loop receipt table. The failed script is preserved. The correction uses that
fixture's original source/admitted references and leaves the ordinary selected
case's real receipt query intact. No source/native/runtime state was changed.
The repaired verifier also closes its metadata-only read connection explicitly
before the separate first-projection read-only reconstruction connection.

The second audit then reached C4 replay but incorrectly attempted to construct
ReceiverBindingV1 without its required real Store/Journal connection. That
failed script is preserved separately. The corrected audit uses the actual
read-only metadata connection and its real Journal, satisfying the unchanged
receiver constructor, then reconstruct replaces both with the fresh read-only
projection/replay connection. No guard was bypassed or production file edited.
