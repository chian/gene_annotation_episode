# Stage 2 blockers: lib2 (literature/storage/experimental_activity_evidence)

1. `ScopedStore.list(kind, scope=None)` (and every inventory built on `__held_rows`, `episode_runtime/store_scope.py`
   line 468) raises `ContractError('unknown_reference')` once the Episode holds the problem record made by
   `store.create_problem(...)`: `refs()` contains `problem_...` and `_held_records()` passes it to `Store.get`, which
   does not know it. Needed: `_held_records()` leaves out (or `get` answers for) the held `problem_...` reference.
   File: `literature/storage/experimental_activity_evidence/tests/*` call `store.list('reference')` after
   `create_problem`; the tests use `held(store, kind)` from `tests/unit_world.py` until this is fixed.
