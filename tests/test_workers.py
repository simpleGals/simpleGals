import multiprocessing
import shutil
import time
from pathlib import Path
import pytest
from simplegals.core.config import ProjectConfig
from simplegals.workers.progress import (
    ProgressState,
    drain_queue,
    format_cli_progress,
    post_status,
)
from simplegals.workers.pool import dispatch


def test_post_and_drain_status():
    q = multiprocessing.Queue()
    state = ProgressState(thumb_total=2, output_total=2)
    post_status(q, "thumb", "a.jpg", "done")
    post_status(q, "output", "b.jpg", "error")
    state = drain_queue(q, state)
    assert state.thumb_done == 1
    assert state.output_failed == 1


def test_format_cli_progress():
    state = ProgressState(thumb_total=4, thumb_done=2, output_total=4, output_done=3)
    output = format_cli_progress(state)
    assert "2/4" in output
    assert "3/4" in output


def test_format_cli_progress_zip_bar():
    from simplegals.workers.progress import ProgressState, format_cli_progress
    # No zip phase -> 2 lines, no Zip bar.
    s = ProgressState(thumb_total=2, thumb_done=2, output_total=2, output_done=2)
    assert format_cli_progress(s).count("\n") == 1  # 2 lines
    assert "Zip" not in format_cli_progress(s)
    # Zip phase active -> 3 lines including a Zip bar, real counts preserved.
    s.zip_total = 3
    s.zip_done = 1
    out = format_cli_progress(s)
    assert out.count("\n") == 2  # 3 lines
    assert "Zip" in out
    assert "2/2" in out  # Previews/Output real counts still shown, not 0/0


def test_dispatch_generates_thumbnails(tmp_project):
    meta_dir = tmp_project / ".meta"
    out_dir = tmp_project / "out"
    in_dir = tmp_project / "in"
    config = ProjectConfig(quality=85)
    q = multiprocessing.Queue()

    sources = list(in_dir.glob("*"))
    thumb_tasks = [(str(s), str(meta_dir), None) for s in sources]
    output_tasks = [(str(sources[0]), str(out_dir), {"quality": 85, "copyright": "", "template": None})]

    dispatch(thumb_tasks, output_tasks, q)

    from simplegals.workers.progress import ProgressState, drain_queue
    state = drain_queue(q, ProgressState(thumb_total=len(thumb_tasks), output_total=len(output_tasks)))
    assert state.thumb_done + state.thumb_failed == len(thumb_tasks)
