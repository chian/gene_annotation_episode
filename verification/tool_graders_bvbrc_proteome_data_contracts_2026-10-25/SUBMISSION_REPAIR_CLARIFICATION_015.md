# Exact retained submission and task correlation

Additive to handoff014. Worker175 traced the real parameter pointer to
/prepared/native_operands/call/rpc_request/params/1. The selected RPC is
AppService.start_app2 with operands [native application ID, parameters, start
parameters]. It is not an arbitrary equal-valued /parameters field.

The retained request wrapper precedes the returned task ID. Its pure decoder
can check original operation key, resource, app, selected request/RPC, parameters
and start parameters. It cannot claim to establish the native returned task ID
from bytes that do not contain it. The actual host TaskHandoff/submission-receipt
path proves that relationship using its separately retained native response.
Tests must distinguish these responsibilities and include wrong-task rejection
through that host path. Do not impose a new response-byte dependency on pure
parameter decoding solely to duplicate the host proof; response echoes never
substitute for original parameter evidence.

Root also authorizes worker175 to update its candidate-only
bvbrc_proteome_directional_schemas.json. The delivered directional contracts
compare the embedded NativeSource definitions with the existing native schema
at import. That dependency copy must match the prospective request_ref addition.
No directional parser change is needed. Production original sources remain
unchanged while161 is active.
