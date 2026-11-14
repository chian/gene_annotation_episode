"""Visible allocated-byte accounting without launch or workflow policy."""
from __future__ import annotations
import os
from pathlib import Path


def allocated_bytes(directory):
    """Visible allocated blocks, without following links; not a hard quota."""
    total, stack = 0, [Path(directory)]
    while stack:
        try:
            with os.scandir(stack.pop()) as entries:
                for entry in entries:
                    try:
                        total += entry.stat(follow_symlinks=False).st_blocks * 512
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                    except FileNotFoundError:
                        pass
        except FileNotFoundError:
            pass
    return total

