"""Tiny subprocess fixture for a native panic with a still-open RPC transport.

This creates no threads and makes no network or model request. The diagnostic
matches the failure captured in the A106 evaluation; stdin keeps the process
alive until the owning connection closes it.
"""
import json
import sys


PANIC = (b"thread '<unnamed>' (373427) panicked at std/src/thread/scoped.rs:206:46:\n"
    b'failed to spawn thread: Os { code: 11, kind: WouldBlock, message: "Resource temporarily unavailable" }\n')
mode = sys.argv[1]
failed = False
for line in sys.stdin:
    request = json.loads(line)
    if "id" not in request or failed:
        continue
    if ((mode == "initialize" and request["method"] == "initialize")
            or (mode == "thread" and request["method"] == "thread/start")):
        sys.stderr.buffer.write(PANIC)
        sys.stderr.buffer.flush()
        failed = True
        continue
    if mode == "ordinary":
        sys.stderr.write("worker warning: failed to spawn thread: retry scheduled\n")
        sys.stderr.write('worker note: prior "panicked at ... failed to spawn thread:" report was handled\n')
        sys.stderr.flush()
    print(json.dumps({"id": request["id"], "result": {"ok": True}}), flush=True)
