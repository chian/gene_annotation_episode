"""Preserve bytes actually emitted by the native gzip decoder before failure.

The returned prefix is not a claim that the wrapper checksum, trailer or
unread suffix was valid. Decoding and biological interpretation are separate.
"""
from __future__ import annotations

import gzip
import platform
import zlib


MODE = "native_gzip_read1_prefix_v1"


def decode_prefix(original, destination):
    """Write native decoder output, retaining a prefix if a later read fails.

    read1 returns available decoded bytes without asking a buffered read to
    fill a large requested size and thereby lose that output on a later trailer
    error. Only decoder-read exceptions are represented as incomplete decoding;
    failures opening or writing custody files remain operational exceptions.
    """
    size, failure = 0, None
    with gzip.open(original, "rb") as reader, destination.open("wb") as output:
        while True:
            try:
                chunk = reader.read1(1024 * 1024)
            except (EOFError, OSError, zlib.error) as error:
                failure = error
                break
            if not chunk:
                break
            output.write(chunk)
            size += len(chunk)
    return {"decoder": "python.gzip", "decoder_mode": MODE,
            "python_version": platform.python_version(),
            "decoded_bytes": size, "complete": failure is None,
            "exception_type": type(failure).__name__ if failure else None}, failure
