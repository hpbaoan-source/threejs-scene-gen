"""MiniMax Anthropic-compatible API client.

The API key is read from ~/.nanobot/config.json at runtime and is never placed
in argv, environment dumps, or logs.

Verified MiniMax-M3.1-Flash quirks (see skills/minimax-api-quirks):
  * `thinking.budget_tokens` is SILENTLY IGNORED on this endpoint.
    Use `output_config: {"effort": ...}` to control reasoning depth.
  * `max_tokens` counts thinking tokens too.
  * `thinking.type="disabled"` returns HTTP 400 on M3.1-Flash.
  * temperature / top_p / top_k / stop_sequences are ignored.
"""
import base64
import json
import os
import urllib.error
import urllib.request

CONFIG_PATH = os.path.expanduser("~/.nanobot/config.json")
PROVIDER = "minimaxAnthropic"

# USD per 1M tokens, as published 2026-11-02.
PRICE = {"input": 0.15, "output": 0.60, "cache_read": 0.015}


class MiniMaxError(RuntimeError):
    pass


def _credentials():
    if not os.path.exists(CONFIG_PATH):
        raise MiniMaxError(f"khong tim thay {CONFIG_PATH}")
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        cfg = json.load(fh)
    prov = cfg.get("providers", {}).get(PROVIDER)
    if not prov:
        raise MiniMaxError(f"config khong co providers.{PROVIDER}")
    return prov["apiBase"].rstrip("/"), prov["apiKey"]


def estimate_cost(usage):
    usage = usage or {}
    total = (
        (usage.get("input_tokens") or 0) * PRICE["input"]
        + (usage.get("output_tokens") or 0) * PRICE["output"]
        + (usage.get("cache_read_input_tokens") or 0) * PRICE["cache_read"]
    )
    return total / 1e6


class Client:
    """Thin wrapper over the Anthropic-compatible MiniMax endpoint."""

    def __init__(self, model="MiniMax-M3.1-Flash", effort="medium", max_tokens=32768):
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.base, self.key = _credentials()
        self.cost = 0.0
        self.calls = 0

    # -- transport ---------------------------------------------------------

    def _post(self, body):
        req = urllib.request.Request(
            self.base + "/v1/messages",
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.key,
                "anthropic-version": "2023-06-01",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=1800) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode()[:400]
            raise MiniMaxError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise MiniMaxError(f"network error: {exc.reason}") from exc

        usage = data.get("usage") or {}
        self.cost += estimate_cost(usage)
        self.calls += 1
        return data

    def _body(self, messages, system=None, max_tokens=None, effort=None):
        body = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": messages,
        }
        if system:
            body["system"] = system
        eff = effort if effort is not None else self.effort
        if eff:
            body["output_config"] = {"effort": eff}
        return body

    # -- public API --------------------------------------------------------

    def complete(self, prompt, system=None, max_tokens=None, effort=None):
        """One text-in / text-out call."""
        data = self._post(
            self._body([{"role": "user", "content": prompt}], system, max_tokens, effort)
        )
        return Response(data)

    def complete_with_image(self, image_bytes, prompt, system=None, max_tokens=None, effort=None):
        """One image-in / text-out call. Image must be PNG or JPEG bytes."""
        media_type = "image/jpeg" if image_bytes[:2] == b"\xff\xd8" else "image/png"
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(image_bytes).decode(),
                },
            },
            {"type": "text", "text": prompt},
        ]
        data = self._post(
            self._body([{"role": "user", "content": content}], system, max_tokens, effort)
        )
        return Response(data)


class Response:
    """Normalised view of one API response."""

    def __init__(self, raw):
        self.raw = raw
        self.text = "\n".join(
            block.get("text", "")
            for block in raw.get("content", [])
            if block.get("type") == "text"
        )
        usage = raw.get("usage") or {}
        self.usage = usage
        self.output_tokens = usage.get("output_tokens") or 0
        self.input_tokens = usage.get("input_tokens") or 0
        self.cache_read_tokens = usage.get("cache_read_input_tokens") or 0
        self.thinking_tokens = (
            (usage.get("output_tokens_details") or {}).get("thinking_tokens") or 0
        )
        self.stop_reason = raw.get("stop_reason")
        self.model = raw.get("model")

    def json(self):
        """Parse the response text as JSON, tolerating markdown fences."""
        from .extract import parse_json_block

        return parse_json_block(self.text)
