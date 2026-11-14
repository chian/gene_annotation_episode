"""Cancellation-safe file locking for explicitly selected native operations."""
import asyncio
from contextlib import asynccontextmanager
import fcntl
import os


@asynccontextmanager
async def _action_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(root / ".action.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    task = asyncio.create_task(asyncio.to_thread(fcntl.flock, descriptor, fcntl.LOCK_EX))
    acquired = False
    try:
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    pass
            task.result()
            acquired = True
            raise
        acquired = True
        yield
    finally:
        if acquired:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
