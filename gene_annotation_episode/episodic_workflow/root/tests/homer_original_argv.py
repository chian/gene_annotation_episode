"""Authenticated original pure requested-command function and literal identities."""
WORKER_MODULE = "gene_annotation_episode.native_homer_worker"
PLAN_FILENAME = "homer-plan.json"

def homer_adapter_argv(plan):
    return [plan["software"]["python"]["path"], "-B", "-S", "-m", WORKER_MODULE,
        "--native-plan", PLAN_FILENAME, "--selected-payload-sha256", plan["selected_payload_sha256"]]

