"""Slow inference remains bounded by configured model and API job deadlines."""
import time

import httpx
import pytest

from iam_sra.conversation_client import ConversationClient


def test_default_limits_are_unchanged(monkeypatch):
    monkeypatch.delenv('IAM_MODEL_TIMEOUT_SECONDS', raising=False)
    client = ConversationClient()
    client._start()
    assert client.request_timeout == 120
    assert client.stage_timeout == 180
    assert client.last_settings['stage_deadline_seconds'] == 180


def test_slow_gpu_setting_is_exported_and_external_deadline_still_wins(monkeypatch):
    monkeypatch.setenv('IAM_MODEL_TIMEOUT_SECONDS', '900')
    client = ConversationClient()
    deadline = time.monotonic() + 45
    client.external_deadline = deadline
    client._start()
    assert client._deadline == deadline
    assert client.request_timeout == 900
    assert client.last_settings['stage_deadline_seconds'] == 900
    assert client.last_settings['request_timeout_seconds'] == 900


@pytest.mark.parametrize('value', ['14', '1801', 'nan', 'unbounded', '0'])
def test_invalid_model_timeout_is_rejected(monkeypatch, value):
    monkeypatch.setenv('IAM_MODEL_TIMEOUT_SECONDS', value)
    with pytest.raises(ValueError):
        ConversationClient()


@pytest.mark.parametrize('remaining,expected', [(1000, 900), (30, 30)])
def test_http_timeout_uses_smaller_of_model_limit_and_job_deadline(monkeypatch, remaining, expected):
    monkeypatch.setenv('IAM_MODEL_TIMEOUT_SECONDS', '900')
    client = ConversationClient()
    client._start()
    monkeypatch.setattr('iam_sra.llm_client.time.monotonic', lambda: 100)
    client._deadline = 100 + remaining
    timeouts = []
    def endpoint(request):
        timeouts.append(request.extensions['timeout']['read'])
        return httpx.Response(200, json={'count': 10})
    with httpx.Client(transport=httpx.MockTransport(endpoint)) as transport:
        assert client._post_json(transport, '/tokenize', {}, 'chat_turn', 'tokenization') == {'count': 10}
    assert timeouts == [expected]
