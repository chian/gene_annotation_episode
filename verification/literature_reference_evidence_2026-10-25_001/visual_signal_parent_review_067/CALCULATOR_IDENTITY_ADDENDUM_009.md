# Bind the complete pure numerical implementation in071

The existing calculation_artifact.calculator_implementation_sha256 field binds
the pure numerical implementation used to produce that saved sheet.070's
calculations module delegates exact numerical/domain primitives to validation
and obtains its contract definitions from inputs. Hashing only the49-line
wrapper does not bind those actual semantics. Earlier071004/005 exploratory
receipts describe their module-only identity and remain historical; they are
not accepted as a full implementation identity.

For final071 generation006, the field is SHA256 of canonical UTF8 JSON of this
closed descriptor, using the application's existing canonical serialization:

    {
      version: relative_signal_calculator_implementation_v1,
      modules: {
        literature_ratio_source_inputs.py: <SHA256 of actual file bytes>,
        literature_ratio_source_calculations.py: <SHA256 of actual file bytes>,
        literature_ratio_source_validation.py: <SHA256 of actual file bytes>
      }
    }

All keys/values are JSON strings; hashes are lowercase64-character hex.071
computes this only for NEW population from the actual selected frozen code.
Record the exact descriptor and hashes in the engineering receipt/pin proof.
The complete runtime pin and external dependency/environment binding remain
separate and are not replaced by this three-module identity.

Saved reads validate original immutable artifact/source/request/outcome and
sheet associations; they do not rehash future current modules to reinterpret
old observations. Original pins retain their original implementations. This
clarification changes no numerical input, sheet/return schema, public API,
source meaning, observation, controller or final annotation-credit policy.
Preserve all earlier actual tests/failures and rerun the affected final joined
storage/projection proof on the one coherent generation before sealing.
