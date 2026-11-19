"""Test-only episode: executes the plan its commissioner's message carries, so each system behaviour can be
exercised by the real runner (services, the scoped store and its transactions, work tables, side effects and
abandoned attempts, several child slots, a slot that commissions its own kind, the decision context, a model
call inside a tool, the three yield controllers, credit that reads records)."""
