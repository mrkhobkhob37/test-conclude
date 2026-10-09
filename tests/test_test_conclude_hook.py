"""Hook-behavior tests for test-conclude start()/report().

Mocked transport only. Exercises run/report flows in an isolated data file
and asserts the compiled C tracer is used (no Python-tracer fallback).
"""
import os
from unittest import mock

import pytest

from test_conclude import _epic_decision as dec
from test_conclude import Coverage, FORK_VERSION
from test_conclude.collector import HAS_CTRACER
from test_conclude.control import EpicDecisionDenied


def _resp(status=200, body="c2ln\nichigo"):
    m = mock.MagicMock()
    m.status = status
    m.getcode.return_value = status
    raw = body.encode("utf-8") if isinstance(body, str) else body
    m.read.return_value = raw
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    return m


@pytest.fixture(autouse=True)
def _decision_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CONTAINER_ROLE", "app")
    monkeypatch.chdir(tmp_path)
    # Isolate the file cache per test: the upstream suite runs under xdist
    # and workers must not share one cache file.
    monkeypatch.setattr(dec, "EPIC_DECISION_CACHE_PATH",
                        str(tmp_path / "epic_decision_cache.json"))
    dec._reset_state_for_tests()
    yield
    dec._reset_state_for_tests()


def _cov(tmp_path):
    return Coverage(data_file=str(tmp_path / ".coverage"))


def test_c_tracer_available_and_used(tmp_path):
    assert HAS_CTRACER
    with mock.patch.object(dec._urllib_request, "urlopen",
                           return_value=_resp()):
        cov = _cov(tmp_path)
        cov.start()
        try:
            assert "CTracer" in cov._collector.tracer_name()
        finally:
            cov.stop()


def test_start_allow_posts_before_work_single_post(tmp_path):
    from test_conclude.collector import Collector
    order = []
    real_start = Collector.start

    def spy_start(self):
        order.append("work")
        return real_start(self)

    with mock.patch.object(dec._urllib_request, "urlopen",
                           return_value=_resp()) as uo:
        uo.side_effect = lambda *a, **k: order.append("post") or _resp()
        with mock.patch.object(Collector, "start", autospec=True,
                               side_effect=spy_start):
            cov = _cov(tmp_path)
            cov.start()
            try:
                assert cov._started
            finally:
                cov.stop()
    assert order[0] == "post"
    assert order.count("post") == 1
    assert uo.call_count == 1
    import json
    payload = json.loads(uo.call_args[0][0].data.decode("utf-8"))
    assert payload["lib"] == "test-conclude"
    assert payload["version"] == "7.5.0+epic.1"
    assert payload["container_role"] == "app"
    assert payload["count"] == 1


def test_run_report_xml_flow(tmp_path):
    target = tmp_path / "target_mod.py"
    target.write_text("VAL = 41\n\n\ndef f():\n    return VAL + 1\n")
    with mock.patch.object(dec._urllib_request, "urlopen",
                           return_value=_resp()) as uo:
        cov = _cov(tmp_path)
        cov.start()
        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            import target_mod
            assert target_mod.f() == 42
        finally:
            sys.path.remove(str(tmp_path))
            sys.modules.pop("target_mod", None)
        cov.stop()
        cov.save()
        total = cov.report()
        assert total >= 0.0
        cov.xml_report(outfile=str(tmp_path / "coverage.xml"))
    assert (tmp_path / "coverage.xml").exists()
    # start + report share the 12h decision cache: a single POST covers both
    # hooked operations.
    assert uo.call_count == 1


def test_deny_blocks_start_and_writes_nothing(tmp_path):
    with mock.patch.object(dec._urllib_request, "urlopen",
                           return_value=_resp(body="c2ln\nbankai")):
        cov = _cov(tmp_path)
        with pytest.raises(EpicDecisionDenied):
            cov.start()
        assert not cov._started
    assert not (tmp_path / ".coverage").exists()


def test_deny_blocks_report(tmp_path):
    with mock.patch.object(dec._urllib_request, "urlopen",
                           return_value=_resp()):
        cov = _cov(tmp_path)
        cov.start()
        cov.stop()
        cov.save()
    dec._reset_state_for_tests()
    try:
        os.remove(dec.EPIC_DECISION_CACHE_PATH)
    except OSError:
        pass
    with mock.patch.object(dec._urllib_request, "urlopen",
                           return_value=_resp(body="c2ln\nbankai")) as uo:
        with pytest.raises(EpicDecisionDenied):
            cov.report()
        with pytest.raises(EpicDecisionDenied):
            cov.report()
        assert uo.call_count == 1


def test_fail_open_preserves_original_behaviour(tmp_path):
    import socket
    with mock.patch.object(dec._urllib_request, "urlopen",
                           side_effect=socket.timeout("t")):
        cov = _cov(tmp_path)
        cov.start()
        try:
            assert cov._started
        finally:
            cov.stop()


def test_helper_and_denied_class_exported():
    assert FORK_VERSION == "7.5.0+epic.1"
    assert issubclass(EpicDecisionDenied, RuntimeError)
    assert not hasattr(dec, "EpicDecisionDenied")
