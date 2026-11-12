"""Durable shared USD accounting. Unknown usage keeps its reservation allocated."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path


class BudgetExceeded(RuntimeError):
    pass


def amount(value) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("USD amounts must be finite and nonnegative")
    return result


class BudgetLedger:
    def __init__(self, path: Path, *, ceiling="5", opening="1.27642592"):
        self.path = path
        self.ceiling, self.opening = amount(ceiling), amount(opening)
        if self.opening > self.ceiling:
            raise BudgetExceeded("Opening consumption exceeds the ceiling")
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._locked() as data:
            if not data:
                if path.exists():
                    raise ValueError("Existing empty/corrupt ledger cannot be reset")
                data.update(
                    schema=1,
                    ceiling_usd=str(self.ceiling),
                    opening_usd=str(self.opening),
                    reservations={},
                )
            if (
                amount(data["ceiling_usd"]) != self.ceiling
                or amount(data["opening_usd"]) != self.opening
            ):
                raise ValueError("Existing ledger configuration cannot be silently reset")

    @contextmanager
    def _locked(self):
        with self.path.with_suffix(self.path.suffix + ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = json.loads(self.path.read_text()) if self.path.exists() else {}
            try:
                yield data
                descriptor, filename = tempfile.mkstemp(dir=self.path.parent, prefix=".budget-")
                try:
                    with os.fdopen(descriptor, "w") as stream:
                        json.dump(data, stream, indent=2)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(filename, self.path)
                    directory = os.open(self.path.parent, os.O_RDONLY)
                    try:
                        os.fsync(directory)
                    finally:
                        os.close(directory)
                finally:
                    if os.path.exists(filename):
                        os.unlink(filename)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    @staticmethod
    def _used(data) -> Decimal:
        return amount(data["opening_usd"]) + sum(
            (
                amount(r["actual_usd"])
                if r["status"] == "reconciled"
                else amount(r["reserved_usd"])
                for r in data["reservations"].values()
            ),
            Decimal(0),
        )

    def snapshot(self) -> dict:
        with self._locked() as data:
            return {
                **data,
                "committed_usd": str(self._used(data)),
                "available_usd": str(self.ceiling - self._used(data)),
            }

    def reserve(self, key: str, upper_bound, *, description="") -> None:
        reservation = amount(upper_bound)
        if reservation <= 0:
            raise ValueError("A positive reservation is required")
        with self._locked() as data:
            if data.get("overrun"):
                raise BudgetExceeded("An accounting overrun requires investigation")
            if key in data["reservations"]:
                raise ValueError("Reservation already exists; inspect/reconcile it before resuming")
            if self._used(data) + reservation > self.ceiling:
                raise BudgetExceeded("Insufficient shared budget; no request may start")
            data["reservations"][key] = {
                "reserved_usd": str(reservation),
                "actual_usd": None,
                "status": "pending",
                "description": description,
            }

    def reconcile(self, key: str, actual=None) -> None:
        overrun = False
        with self._locked() as data:
            reservation = data["reservations"][key]
            if reservation["status"] == "reconciled":
                raise ValueError("Already reconciled")
            if actual is None:
                reservation["status"] = "unknown"
            else:
                charge = amount(actual)
                reservation.update(actual_usd=str(charge), status="reconciled")
                overrun = (
                    charge > amount(reservation["reserved_usd"]) or self._used(data) > self.ceiling
                )
                if overrun:
                    data["overrun"] = True
        if overrun:
            raise BudgetExceeded("Usage exceeded reservation: recorded, further calls blocked")
