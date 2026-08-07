import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """Generate a UUIDv7 (RFC 9562): time-ordered, sortable primary keys.

    Sorting inserts by primary key keeps btree indexes append-mostly instead
    of fragmenting on random UUIDv4 inserts.
    """
    unix_ms = int(time.time() * 1000)
    time_bytes = unix_ms.to_bytes(6, byteorder="big")
    rand_bytes = os.urandom(10)

    buf = bytearray(time_bytes + rand_bytes)
    buf[6] = (buf[6] & 0x0F) | 0x70  # version 7
    buf[8] = (buf[8] & 0x3F) | 0x80  # variant RFC 9562

    return uuid.UUID(bytes=bytes(buf))
