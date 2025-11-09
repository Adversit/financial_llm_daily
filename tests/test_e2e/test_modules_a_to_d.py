import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.tasks import orchestrator


class FakeQuery:
    def __init__(self, records):
        self._records = records

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._records


class FakeSession:
    def __init__(self, records):
        self._records = records
        self.closed = False

    def query(self, _model):
        return FakeQuery(self._records)

    def close(self):
        self.closed = True


class DummyTask:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def si(self, *args, **kwargs):
        call = {"task": self.name, "args": args, "kwargs": kwargs}
        self.calls.append(call)
        return call


class DummySendTask(DummyTask):
    def __init__(self, name, recipients):
        super().__init__(name)
        self.recipients = recipients

    def si(self, *args, **kwargs):
        call = super().si(*args, **kwargs)
        call["recipients"] = list(self.recipients)
        return call


class FakeGroup:
    def __init__(self, tasks):
        self.tasks = tasks


class FakeChain:
    def __init__(self, steps):
        self.steps = steps
        self.applied = False

    def apply_async(self):
        self.applied = True
        return SimpleNamespace(id="workflow-test")


@pytest.mark.parametrize("report_date", ["2024-01-15"])
def test_daily_report_workflow_ends_to_mail(report_date):
    data_path = Path(__file__).resolve().parent.parent / "data" / "e2e_sources_and_recipients.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))

    recipients = payload["recipients"]
    sources = [
        SimpleNamespace(
            id=index,
            name=entry["name"],
            type=entry["type"],
            url=entry["url"],
            enabled=True,
        )
        for index, entry in enumerate(payload["sources"], start=1)
    ]

    fake_session = FakeSession(sources)

    def fake_get_db():
        yield fake_session

    dummy_rss_task = DummyTask("crawl_rss")
    dummy_static_task = DummyTask("crawl_static")
    dummy_extract_task = DummyTask("run_extraction_batch")
    dummy_build_task = DummyTask("build_report")
    dummy_send_task = DummySendTask("send_report", recipients)

    groups = []
    chains = []

    def fake_group(*tasks):
        grp = FakeGroup(tasks)
        groups.append(grp)
        return grp

    def fake_chain(*steps):
        chain = FakeChain(steps)
        chains.append(chain)
        return chain

    fake_crawl_module = types.SimpleNamespace(
        crawl_rss_task=dummy_rss_task,
        crawl_static_task=dummy_static_task,
    )

    with patch.dict(sys.modules, {"src.tasks.crawl_tasks": fake_crawl_module}):
        with patch("src.tasks.orchestrator.get_db", new=fake_get_db), \
                patch("src.tasks.orchestrator.group", new=fake_group), \
                patch("src.tasks.orchestrator.chain", new=fake_chain), \
                patch("src.tasks.extract_tasks.run_extraction_batch", new=dummy_extract_task), \
                patch("src.tasks.report_tasks.build_report_task", new=dummy_build_task), \
                patch("src.tasks.mail_tasks.send_report_task", new=dummy_send_task):
            result = orchestrator._run_daily_report_core_logic(report_date)

    assert result["status"] == "success"
    assert result["report_date"] == report_date
    assert result["sources_count"] == len(sources)
    assert result["tasks_count"] == len(sources)
    assert result["workflow_id"] == "workflow-test"
    assert fake_session.closed is True

    rss_count = sum(1 for source in sources if source.type == "rss")
    static_count = len(sources) - rss_count

    assert len(dummy_rss_task.calls) == rss_count
    assert all(call["args"][0] > 0 for call in dummy_rss_task.calls)
    assert len(dummy_static_task.calls) == static_count
    assert chains and chains[0].applied is True
    assert groups and len(groups[0].tasks) == len(sources)

    if static_count:
        assert all(call["args"][0] > 0 for call in dummy_static_task.calls)

    assert len(chains[0].steps) == 4
    extract_step = chains[0].steps[1]
    build_step = chains[0].steps[2]
    send_step = chains[0].steps[3]

    assert extract_step["task"] == "run_extraction_batch"
    assert extract_step["args"] == (report_date,)
    assert build_step["task"] == "build_report"
    assert build_step["args"] == (report_date,)
    assert send_step["task"] == "send_report"
    assert send_step["args"] == (report_date,)
    assert send_step["recipients"] == recipients
