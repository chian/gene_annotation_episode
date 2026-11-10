# Explicit model OAuth account selection

An investigation can pin its model workers to a particular ChatGPT OAuth
account through its model configuration:

```toml
[models.connection.authentication]
mode = "chatgpt_oauth"
account_sha256 = "<SHA-256 of the selected ChatGPT account ID>"
workspace_label = "<human-readable workspace label>"
```

The account must be selected from the intended authenticated client. A cached
OAuth login alone does not establish that it is the intended workspace. The
label is descriptive; the account fingerprint is the identity check.

For a configured policy, each new worker selects the direct OpenAI provider
and removes API-key, project and endpoint-routing environment overrides from
its own environment. After initialization, before any thread or inference
request, it reads the actual server's effective route and authenticated account.
API-key login, a different OAuth account, a custom gateway or an authentication
header override fails verification. The saved `authentication.json` retains
the mode, provider, account fingerprint and reported workspace/plan metadata.
Bearer and refresh tokens are not written to the report or model context.

The existing Codex credential cache is reused without changing its login or
global configuration. A failed check tears down the owned worker and enters
the existing model-source failure path. It does not retry against another
account, change scientific credit or alter the continuation controller.
Historical configurations without a policy retain their original behavior.

Official references: [authentication](https://learn.chatgpt.com/docs/auth) and
[app-server authentication](https://learn.chatgpt.com/docs/app-server).

On 2026-11-09 UTC, the user stopped this window's investigations and requested
the OAuth login used by this Codex window instead of AmSC. A read-only query of
this window's daemon identified `(Leu) Lifesciences Alpha`; its account matched
the current local OAuth cache. The A107/A110 prepared configurations are pinned
to that account. Historical model-call intervals identify execution times but
did not record the account used, so they cannot establish billing attribution.
The central evidence-axis ledger records validation and execution status.
