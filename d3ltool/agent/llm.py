# -*- coding: utf-8 -*-
"""OpenAI-compatible chat client with SSE streaming and tool calls.

Works with any provider implementing POST {base_url}/chat/completions:
OpenAI, DeepSeek, Qwen/DashScope, Moonshot Kimi, Zhipu GLM, SiliconFlow,
OpenRouter, Ollama and similar. Pure Python (no Qt), so tests can fake the
transport at the HTTP level or higher.
"""

import json
import re
from urllib.parse import urlparse

import requests

PROVIDER_PRESETS = [
    ("OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"),
    ("DeepSeek", "https://api.deepseek.com/v1", "deepseek-chat"),
    ("Qwen / 通义千问", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
    ("Moonshot / Kimi", "https://api.moonshot.cn/v1", "moonshot-v1-8k"),
    ("智谱 / GLM", "https://open.bigmodel.cn/api/paas/v4", "glm-4-flash"),
    ("SiliconFlow", "https://api.siliconflow.cn/v1", "Qwen/Qwen2.5-72B-Instruct"),
    ("Ollama (local)", "http://127.0.0.1:11434/v1", ""),
    ("Custom / 自定义", "", ""),
]


class LLMError(RuntimeError):
    pass


class StopRequested(LLMError):
    """The user pressed stop; abort the stream quietly."""


def _endpoint(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise LLMError("API base URL is empty (set it in the AI Assistant panel)")
    if base.endswith("/chat/completions"):
        return base
    if re.search(r"/v\d+$", base):          # .../v1, .../v4 (Zhipu) etc.
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def _error_detail(resp) -> str:
    try:
        data = resp.json()
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
        if isinstance(err, str):
            return err
        return json.dumps(data, ensure_ascii=False)[:300]
    except Exception:
        return (resp.text or "")[:300]


def _check_status(resp, url):
    if resp.status_code == 200:
        return
    detail = _error_detail(resp)
    if resp.status_code in (401, 403):
        raise LLMError(f"API key rejected ({resp.status_code}) by {url}: {detail}")
    if resp.status_code == 404:
        raise LLMError(f"endpoint not found at {url} — check the base URL "
                       f"(404): {detail}")
    raise LLMError(f"provider returned HTTP {resp.status_code}: {detail}")


def _proxies(url=""):
    """Proxy from the app settings ("" = none), applied to LLM requests.

    Loopback targets (Ollama on 127.0.0.1, local test servers) never go
    through the proxy: routing them to a remote node yields empty 502s."""
    try:
        from .. import config

        if _is_loopback(url):
            return None
        proxy = (config.load_config() or {}).get("proxy_url") or ""
        if proxy:
            return {"http": proxy, "https": proxy}
    except Exception:
        pass
    return None


def _is_loopback(url: str) -> bool:
    try:
        host = (urlparse(url or "").hostname or "").lower()
    except ValueError:
        return False
    return (host in ("localhost", "::1")
            or host.startswith("127.")
            or host.endswith(".localhost"))


def stream_chat(base_url, api_key, model, messages, tools=None,
                timeout=(30, 600), should_stop=None):
    """POST /chat/completions with stream=True and yield structured events:

      {"type": "text", "text": str}         — a content delta as it arrives
      {"type": "tool_calls", "calls": [...] } — after the stream ends, each
          call = {"id", "name", "arguments": dict, "arguments_raw": str}
      {"type": "done", "finish_reason": str}

    Raises LLMError on network/HTTP problems; StopRequested when should_stop
    turns true between chunks.
    """
    url = _endpoint(base_url)
    body = {"model": model, "messages": messages, "stream": True}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    # explicit None: LLM requests follow only the app's own proxy setting
    # (deliberately not env/system proxies — keeps local test servers safe)
    try:
        resp = requests.post(url, json=body, headers=headers, stream=True,
                             timeout=timeout, proxies=_proxies(url))
    except requests.RequestException as exc:
        raise LLMError(f"network error reaching {url}: {exc}") from exc

    text_parts = []
    fragments = {}
    finish_reason = None
    try:
        if not resp.ok:
            _check_status(resp, url)
        # SSE is UTF-8 by spec, but requests defaults text/* responses to
        # ISO-8859-1 when the provider omits a charset (Ollama does) —
        # decode the byte lines explicitly instead.
        for raw in resp.iter_lines():
            if should_stop is not None and should_stop():
                raise StopRequested("stopped by user")
            line = raw.decode("utf-8", errors="replace") \
                if isinstance(raw, (bytes, bytearray)) else raw
            if not line or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                chunk = json.loads(payload)
            except ValueError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            choice = choices[0]
            delta = choice.get("delta") or {}
            finish_reason = choice.get("finish_reason") or finish_reason
            piece = delta.get("content")
            if piece:
                text_parts.append(piece)
                yield {"type": "text", "text": piece}
            for frag in delta.get("tool_calls") or []:
                idx = frag.get("index", 0)
                slot = fragments.setdefault(
                    idx, {"id": "", "name": "", "arguments": ""})
                if frag.get("id"):
                    slot["id"] = frag["id"]
                fn = frag.get("function") or {}
                if fn.get("name") and not slot["name"]:
                    slot["name"] = fn["name"]
                if fn.get("arguments"):
                    slot["arguments"] += fn["arguments"]
    finally:
        resp.close()

    calls = []
    for idx in sorted(fragments):
        slot = fragments[idx]
        try:
            arguments = json.loads(slot["arguments"] or "{}")
            if not isinstance(arguments, dict):
                arguments = {"_raw": slot["arguments"]}
        except ValueError:
            arguments = {"_raw": slot["arguments"]}
        calls.append({
            "id": slot["id"] or f"call_{idx}",
            "name": slot["name"],
            "arguments": arguments,
            "arguments_raw": slot["arguments"],
        })
    if calls:
        yield {"type": "tool_calls", "calls": calls}
    yield {"type": "done",
           "finish_reason": finish_reason or ("tool_calls" if calls else "stop")}


def test_connection(base_url, api_key, model):
    """Cheap one-shot request to validate base URL / key / model."""
    try:
        url = _endpoint(base_url)
    except LLMError as exc:
        return False, str(exc)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        resp = requests.post(
            url,
            json={"model": model, "messages": [{"role": "user", "content": "ping"}],
                  "max_tokens": 1, "stream": False},
            headers=headers, timeout=30, proxies=_proxies(url))
    except requests.RequestException as exc:
        return False, f"network error: {exc}"
    if resp.status_code == 200:
        return True, "ok"
    try:
        _check_status(resp, url)
    except LLMError as exc:
        return False, str(exc)
    return False, f"HTTP {resp.status_code}: {_error_detail(resp)}"


def endpoint_host(base_url: str) -> str:
    """Human-readable host of the effective endpoint, for the UI."""
    try:
        return urlparse(_endpoint(base_url)).netloc
    except LLMError:
        return ""
