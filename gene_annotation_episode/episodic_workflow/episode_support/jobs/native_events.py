"""The native event ledger as a declared service of the run (``ctx.services['native_events']``).

``NativeEventLedger`` (``native_event_ledger.py``) is the ledger of detached local jobs: registered job targets,
each target's one publication and an event cursor, in its own SQLite file. It is outside the Store and outside
custody, and a detached job writes its publication into that file from its own process, after the Episode that
launched it has returned (``detached_job.py``). No episode opens the ledger: the run's caller names its directory in
the service's factory, and an episode reaches it only as this service.

- **The ledger's own interface** (``register_native_target``, ``native_target``, ``validate_event_targets``,
  ``wait_events``) is offered unchanged, so the library's ``waiting.selected_wait(events, condition)`` takes this
  service as its ``events``.
- **A decision reads** ``targets(handles)`` through the service's read handle: the descriptors of the registered
  targets among the handles it names.
- **Custody is built in** for what a wait learns. ``await wait(ctx, condition)`` waits as ``selected_wait`` does
  and then brings the receipt of every event it woke on into custody: the publication's original receipt bytes are
  written as an artifact and a row of the declared work table ``NATIVE_EVENT_RECEIPTS`` names it, both through
  ``ctx.store`` in one transaction. The unit therefore holds the receipt as produced, and returns it in a
  ``record_refs`` field. A unit that runs again waits again from the same cursor, wakes on the same durable event
  and writes the same row.
"""
from __future__ import annotations

from episode_runtime import TableDeclaration

from .native_event_ledger import NativeEventLedger, native_target_descriptor
from .waiting import selected_wait

NATIVE_EVENT_RECEIPTS = TableDeclaration(
    name='native_event_receipts', columns=('handle', 'record_ref', 'cursor', 'publication', 'receipt_ref'),
    key=('handle', 'record_ref'), record_refs=('receipt_ref',))


class NativeEvents:
    """The native event ledger in ``root_directory``, for the episodes that declare ``native_events``."""

    def __init__(self, root_directory):
        self._ledger = NativeEventLedger(root_directory)

    @property
    def root_directory(self):
        return str(self._ledger.root_directory)

    # -- the ledger's interface ------------------------------------------------------------------------------
    def register_native_target(self, registration):
        return self._ledger.register_native_target(registration)

    def native_target(self, handle):
        return self._ledger.native_target(handle)

    def validate_event_targets(self, condition):
        return self._ledger.validate_event_targets(condition)

    async def wait_events(self, condition):
        return await self._ledger.wait_events(condition)

    # -- what a decision may read ----------------------------------------------------------------------------
    def targets(self, handles):
        """The descriptor of each registered target among ``handles``, in their order; a handle the ledger does
        not know raises ``KeyError``."""
        return [native_target_descriptor(self._ledger.native_target(handle)) for handle in handles]

    # -- a wait whose receipts come into custody ---------------------------------------------------------------
    def receipt(self, ctx, handle, record_ref):
        """Bring the published receipt ``record_ref`` of the target into custody; the row that names it."""
        published = self._ledger.native_publication(handle, record_ref)
        with ctx.store.transaction():
            receipt_ref = ctx.store.artifact(bytes(published['receipt_bytes']), 'application/json')
            return ctx.store.table(NATIVE_EVENT_RECEIPTS).put({
                'handle': handle, 'record_ref': record_ref, 'cursor': published['cursor'],
                'publication': published['publication'], 'receipt_ref': receipt_ref})

    async def wait(self, ctx, condition):
        """Wait for the selected events (``event_condition_v1``) or the reconsideration time. The outcome is
        ``selected_wait``'s, with the receipts of the events in custody: ``receipts`` lists ``{'handle',
        'record_ref', 'cursor', 'row_ref', 'receipt_ref'}`` and ``record_refs`` names the rows and artifacts."""
        outcome = await selected_wait(self, condition)
        if outcome['status'] != 'completed':
            return {**outcome, 'receipts': []}
        rows = [self.receipt(ctx, event['handle'], event['record_ref'])
                for event in outcome['result']['events'] if event['record_ref'] is not None]
        receipts = [{'handle': row['handle'], 'record_ref': row['record_ref'], 'cursor': row['cursor'],
                     'row_ref': row['id'], 'receipt_ref': row['receipt_ref']} for row in rows]
        refs = [ref for item in receipts for ref in (item['row_ref'], item['receipt_ref'])]
        return {**outcome, 'record_refs': refs, 'changed_record_refs': refs, 'receipts': receipts}


__all__ = ['NATIVE_EVENT_RECEIPTS', 'NativeEvents']
