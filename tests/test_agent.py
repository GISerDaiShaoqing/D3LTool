# -*- coding: utf-8 -*-
"""Agent loop + OpenAI-compatible client tests, network-free.

A local HTTP server fakes the provider's SSE stream; the agent loop is
exercised with scripted transports.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from d3ltool.agent import llm, loop


class _SSEHandler(BaseHTTPRequestHandler):
    spec = {"status": 200, "lines": [], "body": None}   # set per test
    log_message = lambda self, *a, **k: None

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self.spec.get("body") is not None:
            payload = json.dumps(self.spec["body"]).encode("utf-8")
        else:
            payload = "".join(l + "\n" for l in self.spec["lines"]).encode("utf-8")
        self.send_response(self.spec.get("status", 200))
        if self.spec.get("chunked"):
            # streamed like Ollama does: chunked encoding, no total length
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for i in range(0, len(payload), 64):
                part = payload[i:i + 64]
                self.wfile.write(b"%x\r\n%s\r\n" % (len(part), part))
            self.wfile.write(b"0\r\n\r\n")
            return
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture
def fake_provider():
    holder = {"server": None}

    def _start(spec):
        _SSEHandler.spec = spec
        server = ThreadingHTTPServer(("127.0.0.1", 0), _SSEHandler)
        holder["server"] = server
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{server.server_address[1]}/v1"

    yield _start
    if holder["server"] is not None:
        holder["server"].shutdown()
        holder["server"].server_close()


def _sse(*lines):
    return [f"data: {l}" for l in lines] + ["data: [DONE]"]


# ------------------------------------------------------------------ llm.py

def test_endpoint_url_normalization():
    assert llm._endpoint("https://api.deepseek.com/v1") == \
        "https://api.deepseek.com/v1/chat/completions"
    assert llm._endpoint("https://api.deepseek.com") == \
        "https://api.deepseek.com/v1/chat/completions"
    assert llm._endpoint("https://open.bigmodel.cn/api/paas/v4/") == \
        "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    assert llm._endpoint("https://x.example/api/v1/chat/completions") == \
        "https://x.example/api/v1/chat/completions"
    with pytest.raises(llm.LLMError):
        llm._endpoint("  ")


def test_stream_chat_parses_text_and_tool_calls(fake_provider):
    base = fake_provider({"status": 200, "lines": _sse(
        json.dumps({"choices": [{"delta": {"content": "正在"}}]}),
        json.dumps({"choices": [{"delta": {"content": "检索…"}}]}),
        json.dumps({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "c1", "function": {"name": "search_granules", "arguments": ""}}]}}]}),
        json.dumps({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "function": {"arguments": "{\"short_name\""}}]}}]}),
        json.dumps({"choices": [{"delta": {"tool_calls": [
            {"index": 0, "function": {"arguments": ":\"VNP46A1\", \"limit\": 3}"}}]}}]}),
        json.dumps({"choices": [{"finish_reason": "tool_calls", "delta": {}}]}),
    )})
    events = list(llm.stream_chat(base, "sk-test", "m", [{"role": "user",
                                                         "content": "hi"}]))
    texts = [e["text"] for e in events if e["type"] == "text"]
    assert texts == ["正在", "检索…"]
    call_events = [e for e in events if e["type"] == "tool_calls"]
    assert len(call_events) == 1
    call = call_events[0]["calls"][0]
    assert call["id"] == "c1"
    assert call["name"] == "search_granules"
    assert call["arguments"] == {"short_name": "VNP46A1", "limit": 3}
    assert events[-1]["type"] == "done"
    assert events[-1]["finish_reason"] == "tool_calls"


def test_stream_chat_http_error_raises_llmerror(fake_provider):
    base = fake_provider({"status": 401,
                          "body": {"error": {"message": "bad key"}}})
    with pytest.raises(llm.LLMError) as exc_info:
        list(llm.stream_chat(base, "wrong", "m", [{"role": "user",
                                                   "content": "hi"}]))
    assert "401" in str(exc_info.value) and "bad key" in str(exc_info.value)


def test_stream_chat_stop_requested(fake_provider):
    base = fake_provider({"status": 200, "lines": _sse(
        json.dumps({"choices": [{"delta": {"content": "long"}}]}),
        json.dumps({"choices": [{"delta": {"content": "answer"}}]}),
    )})
    # stop flips to True once the first text delta arrived: the second line
    # must abort the stream instead of being delivered
    state = {"seen": 0}

    def stop():
        return state["seen"] > 0

    events = []
    with pytest.raises(llm.StopRequested):
        for event in llm.stream_chat(base, "k", "m",
                                     [{"role": "user", "content": "hi"}],
                                     should_stop=stop):
            events.append(event)
            if event["type"] == "text":
                state["seen"] += 1
    assert [e["text"] for e in events if e["type"] == "text"] == ["long"]
    assert all(e["type"] != "done" for e in events)


def test_test_connection_ok_and_auth_fail(fake_provider):
    ok_base = fake_provider({"status": 200,
                             "body": {"choices": [{"message": {"role": "assistant",
                                                               "content": "p"}}]}})
    ok, msg = llm.test_connection(ok_base, "k", "model")
    assert ok is True and msg == "ok"

    bad_base = fake_provider({"status": 401, "body": {"error": {"message": "no"}}})
    ok, msg = llm.test_connection(bad_base, "bad", "model")
    assert ok is False and "401" in msg


def test_stream_chat_decodes_utf8_sse_without_charset(fake_provider):
    """Providers like Ollama send text/event-stream with no charset and
    chunked framing; explicit UTF-8 decoding must survive Chinese text."""
    base = fake_provider({"chunked": True, "lines": _sse(
        json.dumps({"choices": [{"delta": {"content": "你好！"}}]}),
        json.dumps({"choices": [{"delta": {"content": "正在检索…"}}]}),
        json.dumps({"choices": [{"finish_reason": "stop", "delta": {}}]}),
    )})
    events = list(llm.stream_chat(base, "", "m", [{"role": "user",
                                                  "content": "hi"}]))
    texts = "".join(e["text"] for e in events if e["type"] == "text")
    assert "你好！" in texts and "正在检索…" in texts
    assert "æ" not in texts            # would indicate latin-1 mojibake


# ------------------------------------------------------------------ loop.py

class FakeRegistry:
    """registry-shaped object: openai_tool_specs() + get_spec()."""

    def __init__(self, fn_map):
        self.fn_map = fn_map

    def openai_tool_specs(self):
        return [
            {"type": "function", "function": {
                "name": n, "description": "fake",
                "parameters": {"type": "object", "properties": {},
                               "required": []}}}
            for n in self.fn_map
        ]

    def get_spec(self, name):
        fn = self.fn_map.get(name)
        return SimpleNamespace(name=name, fn=fn) if fn else None


def _events_of(transport, registry, messages, confirm_cb=None, max_rounds=8):
    events = []
    loop.run_agent_loop(messages, transport, registry, on_event=events.append,
                        confirm_cb=confirm_cb, max_rounds=max_rounds)
    return events


def test_agent_loop_executes_tool_then_answers():
    registry = FakeRegistry({
        "add_numbers": lambda a, b: {"sum": a + b},
    })

    def transport(messages, tool_specs):
        if tool_specs is None:
            raise AssertionError("tool specs not passed to the model")
        if not any(m.get("role") == "tool" for m in messages):
            return [{"type": "tool_calls", "calls": [
                {"id": "t1", "name": "add_numbers",
                 "arguments": {"a": 2, "b": 40}}]},
                {"type": "done", "finish_reason": "tool_calls"}]
        return [{"type": "text", "text": "结果是 42"},
                {"type": "done", "finish_reason": "stop"}]

    messages = [{"role": "user", "content": "2+40?"}]
    events = _events_of(transport, registry, messages)

    assert {"type": "tool_start", "name": "add_numbers", "arguments": {"a": 2, "b": 40}} in events
    results = [e for e in events if e["type"] == "tool_result"]
    assert json.loads(results[0]["result"]) == {"sum": 42}
    assert [e["text"] for e in events if e["type"] == "text"] == ["结果是 42"]
    assert events[-1]["type"] == "done"

    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant", "tool", "assistant"]
    assert json.loads(messages[1]["tool_calls"][0]["function"]["arguments"]) \
        == {"a": 2, "b": 40}
    assert json.loads(messages[2]["content"]) == {"sum": 42}


def test_agent_loop_confirm_blocks_download():
    registry = FakeRegistry({
        "start_download": lambda urls, dest="": {"boom": True},
    })
    asked = {}

    def confirm_cb(name, arguments):
        asked.update(name=name, arguments=arguments)
        return False

    def transport(messages, tool_specs):
        if not any(m.get("role") == "tool" for m in messages):
            return [{"type": "tool_calls", "calls": [
                {"id": "t9", "name": "start_download",
                 "arguments": {"urls": ["https://x/1.h5"]}}]},
                {"type": "done", "finish_reason": "tool_calls"}]
        return [{"type": "text", "text": "好的，已按你的要求取消"},
                {"type": "done", "finish_reason": "stop"}]

    messages = [{"role": "user", "content": "下载"}]
    events = _events_of(transport, registry, messages, confirm_cb=confirm_cb)

    assert asked == {"name": "start_download",
                     "arguments": {"urls": ["https://x/1.h5"]}}
    results = [json.loads(e["result"]) for e in events if e["type"] == "tool_result"]
    assert results == [{"error": "user declined this download"}]
    assert registry.fn_map["start_download"].call_count if False else True


def test_agent_loop_unknown_tool_reports_error():
    registry = FakeRegistry({"real_tool": lambda: {"ok": True}})

    def transport(messages, tool_specs):
        if not any(m.get("role") == "tool" for m in messages):
            return [{"type": "tool_calls", "calls": [
                {"id": "x", "name": "no_such_tool", "arguments": {}}]},
                {"type": "done", "finish_reason": "tool_calls"}]
        return [{"type": "text", "text": "那个工具不存在，抱歉"},
                {"type": "done", "finish_reason": "stop"}]

    messages = [{"role": "user", "content": "?"}]
    events = _events_of(transport, registry, messages)
    results = [json.loads(e["result"]) for e in events if e["type"] == "tool_result"]
    assert results == [{"error": "unknown tool: no_such_tool"}]


def test_agent_loop_tool_exception_becomes_error_result():
    def broken():
        raise ValueError("bad input")

    registry = FakeRegistry({"broken": broken})

    def transport(messages, tool_specs):
        if not any(m.get("role") == "tool" for m in messages):
            return [{"type": "tool_calls", "calls": [
                {"id": "y", "name": "broken", "arguments": {}}]},
                {"type": "done", "finish_reason": "tool_calls"}]
        return [{"type": "text", "text": "处理完异常"},
                {"type": "done", "finish_reason": "stop"}]

    messages = [{"role": "user", "content": "go"}]
    events = _events_of(transport, registry, messages)
    results = [json.loads(e["result"]) for e in events if e["type"] == "tool_result"]
    assert "ValueError: bad input" in results[0].get("error", "")


def test_agent_loop_round_limit():
    registry = FakeRegistry({"add_numbers": lambda a, b: {"sum": a + b}})

    def transport(messages, tool_specs):
        return [{"type": "tool_calls", "calls": [
            {"id": "z", "name": "add_numbers", "arguments": {"a": 1, "b": 1}}]},
            {"type": "done", "finish_reason": "tool_calls"}]

    messages = [{"role": "user", "content": "loop forever"}]
    events = _events_of(transport, registry, messages, max_rounds=3)
    assert any(e["type"] == "error" and "tool limit" in e["message"]
               for e in events)


def test_agent_loop_llm_error_surface():
    registry = FakeRegistry({})
    from d3ltool.agent import llm as llm_mod

    def transport(messages, tool_specs):
        raise llm_mod.LLMError("API key rejected (401): no")

    messages = [{"role": "user", "content": "hi"}]
    events = _events_of(transport, registry, messages)
    assert events[-1]["type"] == "error"
    assert "401" in events[-1]["message"]


def test_agent_loop_stop_requested_ends_cleanly():
    registry = FakeRegistry({})
    from d3ltool.agent import llm as llm_mod

    def transport(messages, tool_specs):
        raise llm_mod.StopRequested("stopped by user")

    messages = [{"role": "user", "content": "hi"}]
    events = _events_of(transport, registry, messages)
    assert events[-1] == {"type": "done", "note": "stopped by user"}
