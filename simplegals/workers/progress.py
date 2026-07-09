from __future__ import annotations

import multiprocessing
import queue as _queue
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ProgressState:
    thumb_total: int = 0
    thumb_done: int = 0
    thumb_failed: int = 0
    output_total: int = 0
    output_done: int = 0
    output_failed: int = 0
    current_file: str = ""
    zip_total: int = 0
    zip_done: int = 0


def post_status(
    queue: multiprocessing.Queue,
    type_: str,
    file: str,
    status: str,
) -> None:
    queue.put({
        "type": type_,
        "file": file,
        "status": status,
        "ts": datetime.now(timezone.utc).isoformat(),
    })


def drain_queue(
    queue: multiprocessing.Queue,
    state: ProgressState,
    timeout: float = 0.1,
) -> ProgressState:
    # Use a blocking get with timeout; get_nowait() misses items still in the
    # feeder thread's buffer when the caller itself is the queue writer.
    while True:
        try:
            msg = queue.get(block=True, timeout=timeout)
        except _queue.Empty:
            break
        state.current_file = msg.get("file", "")
        if msg["type"] == "thumb":
            if msg["status"] == "done":
                state.thumb_done += 1
            else:
                state.thumb_failed += 1
        elif msg["type"] == "output":
            if msg["status"] == "done":
                state.output_done += 1
            else:
                state.output_failed += 1
    return state


def format_cli_progress(state: ProgressState) -> str:
    def bar(done: int, failed: int, total: int, label: str) -> str:
        filled = done + failed
        pct = filled / total if total else 0
        width = 20
        n_fill = round(pct * width)
        b = "█" * n_fill + "░" * (width - n_fill)
        return f"{label} [{b}] {done}/{total}" + (f" ({failed} err)" if failed else "")

    lines = [
        bar(state.thumb_done, state.thumb_failed, state.thumb_total, "Previews"),
        bar(state.output_done, state.output_failed, state.output_total, "Output "),
    ]
    if state.zip_total:
        lines.append(bar(state.zip_done, 0, state.zip_total, "Zip    "))
    return "\n".join(lines)
