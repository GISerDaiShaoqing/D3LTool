# -*- coding: utf-8 -*-
"""Minimal agent loop: model <-> tool registry, provider-agnostic.

Pure Python (no Qt). The GUI drives it from a worker thread and renders the
on_event dicts; MCP-style clients could reuse it the same way.
"""

import json

from . import llm

CONFIRM_TOOLS = {"start_download"}     # these need explicit user consent
TOOL_RESULT_LIMIT = 6000               # chars fed back to the model per result


def default_transport(base_url, api_key, model, should_stop=None):
    """transport(messages, tool_specs) -> iterable of stream events."""
    def _transport(messages, tool_specs):
        return llm.stream_chat(
            base_url=base_url, api_key=api_key, model=model,
            messages=messages, tools=tool_specs or None,
            should_stop=should_stop)
    return _transport


def _emit(on_event, event):
    if on_event is not None:
        try:
            on_event(event)
        except Exception:
            pass


def run_agent_loop(messages, transport, registry, on_event=None,
                   confirm_cb=None, max_rounds=8):
    """Advance the conversation by up to `max_rounds` model turns, executing
    any requested tools from `registry` in between.

    messages: the full history INCLUDING the latest user message; extended
              in place (assistant/tool messages are appended).
    confirm_cb(tool_name, arguments) -> bool is consulted for CONFIRM_TOOLS
              before a download is queued (None = allow).

    Emits events to on_event: text / assistant_text / tool_start /
    tool_result / error / done. Returns the (mutated) messages list.
    """
    tool_specs = None
    if registry is not None and getattr(registry, "openai_tool_specs", None):
        tool_specs = registry.openai_tool_specs()

    empties = 0
    for _round in range(max_rounds):
        text_parts = []
        calls = []
        try:
            for event in transport(messages, tool_specs):
                if event["type"] == "text":
                    text_parts.append(event["text"])
                    _emit(on_event, {"type": "text", "text": event["text"]})
                elif event["type"] == "tool_calls":
                    calls = event["calls"]
                elif event["type"] == "done":
                    pass
        except llm.StopRequested:
            _emit(on_event, {"type": "done", "note": "stopped by user"})
            return messages
        except llm.LLMError as exc:
            _emit(on_event, {"type": "error", "message": str(exc)})
            return messages

        text = "".join(text_parts)
        if not calls:
            if text:
                messages.append({"role": "assistant", "content": text})
                _emit(on_event, {"type": "done"})
                return messages
            # Dead-air round: some providers hiccup or free models return an
            # empty reply. Retry instead of ending the turn in silence —
            # nothing was consumed, so re-posting the same messages is safe.
            if empties < 2 and _round < max_rounds - 1:
                empties += 1
                continue
            _emit(on_event, {"type": "error",
                             "message": f"the model returned an empty reply "
                                        f"({empties} retries) — resend the "
                                        "message, or try another model or "
                                        "provider"})
            return messages

        messages.append({
            "role": "assistant",
            "content": text,
            "tool_calls": [
                {
                    "id": c["id"],
                    "type": "function",
                    "function": {
                        "name": c["name"],
                        "arguments": json.dumps(c["arguments"],
                                                ensure_ascii=False),
                    },
                }
                for c in calls
            ],
        })
        if text:
            _emit(on_event, {"type": "assistant_text", "text": text})

        for call in calls:
            result = _run_tool(call, registry, confirm_cb, on_event)
            payload = json.dumps(result, ensure_ascii=False, default=str)
            if len(payload) > TOOL_RESULT_LIMIT:
                payload = payload[:TOOL_RESULT_LIMIT] + " ...(truncated)"
            _emit(on_event, {"type": "tool_result", "name": call["name"],
                             "result": payload})
            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": payload,
            })

    _emit(on_event, {"type": "error",
                     "message": f"reached the {max_rounds}-round tool limit "
                                "before the model produced a final answer"})
    return messages


def _run_tool(call, registry, confirm_cb, on_event):
    name = call["name"]
    arguments = call["arguments"] if isinstance(call["arguments"], dict) else {}
    arguments.pop("_raw", None)

    spec = registry.get_spec(name)
    if spec is None:
        return {"error": f"unknown tool: {name}"}

    if name in CONFIRM_TOOLS and confirm_cb is not None:
        try:
            allowed = bool(confirm_cb(name, arguments))
        except Exception:
            allowed = False
        if not allowed:
            return {"error": "user declined this download"}

    _emit(on_event, {"type": "tool_start", "name": name, "arguments": arguments})
    try:
        return spec.fn(**arguments)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
