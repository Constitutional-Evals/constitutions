"""Validated, cached OpenRouter chat and embedding requests."""

import json
import os
import random
import re
import threading
import time
from copy import deepcopy
from getpass import getpass
from pathlib import Path

import numpy as np
import requests

from . import config as cfg
from .core import atomic_json, canonical, digest, read_json

def extract_json(text):
    """Decode an LLM JSON reply, tolerating a surrounding Markdown fence."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Empty model reply")
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < start:
            raise
        return json.loads(text[start:end + 1])


def obtain_openrouter_key():
    key = os.environ.get("OPENROUTER_API_KEY") or getpass("OpenRouter API key: ").strip()
    if not key:
        raise ValueError("OpenRouter API key required")
    return key


class OpenRouterClient:
    """Cached OpenRouter calls with retry, an API budget, and durable usage logs."""

    def __init__(self, root, api_key):
        self.root, self.api_key = Path(root), api_key
        self.lock = threading.Lock()
        self.usage_dir = self.root / "audit/api_usage_chunks"
        self.usage_dir.mkdir(parents=True, exist_ok=True)
        chunks = sorted(self.usage_dir.glob("usage_*.json"))
        self.event_count = sum(len(read_json(p, [])) for p in chunks)
        self.request_count = sum(
            event.get("event") == "request_attempt"
            for path in chunks for event in read_json(path, [])
        )

    def _record(self, event):
        # Small atomic JSON chunks survive disconnects.
        with self.lock:
            path = self.usage_dir / f"usage_{self.event_count // 100:06d}.json"
            events = read_json(path, [])
            events.append(event)
            atomic_json(path, events)
            self.event_count += 1

    def _post(self, endpoint, body):
        with self.lock:
            if self.request_count >= cfg.MAX_API_REQUESTS:
                raise RuntimeError("API budget exhausted: increase MAX_API_REQUESTS deliberately")
            self.request_count += 1
        self._record({"event": "request_attempt", "endpoint": endpoint,
                      "model": body.get("model")})
        response = requests.post(
            "https://openrouter.ai/api/v1/" + endpoint,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            json=body, timeout=cfg.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def chat(self, model, task, payload, validate, reasoning=None):
        effort = cfg.REASONING_EFFORT if reasoning is None else reasoning
        messages = [
            {"role": "system", "content": cfg.SYSTEM_MESSAGE},
            {"role": "user", "content": canonical({"task": task, "input": payload})},
        ]
        identity = {"model": model, "messages": messages,
                    "reasoning": effort, "max_output": cfg.MAX_OUTPUT_TOKENS}
        cache = self.root / "cache/chat" / (digest(identity) + ".json")
        saved = read_json(cache)
        if saved is not None:
            validate(saved["parsed"])
            return deepcopy(saved["parsed"])

        last_error, blanks = None, 0
        for attempt in range(cfg.HTTP_RETRIES):
            budget = max(12000, cfg.MAX_OUTPUT_TOKENS) if blanks else cfg.MAX_OUTPUT_TOKENS
            reasoning_effort = "low" if blanks >= 2 else effort
            body = {"model": model, "messages": messages, "max_tokens": budget}
            if reasoning_effort:
                body["reasoning"] = {"effort": reasoning_effort}
            try:
                data = self._post("chat/completions", body)
                choice = (data.get("choices") or [None])[0]
                if not choice:
                    raise ValueError("OpenRouter returned no choices")
                content = (choice.get("message") or {}).get("content", "")
                if isinstance(content, list):
                    content = "\n".join(
                        part if isinstance(part, str) else part.get("text", "")
                        for part in content
                    )
                if not content or not content.strip():
                    blanks += 1
                    usage = data.get("usage") or {}
                    reason_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
                    raise ValueError(
                        f"Empty response; finish={choice.get('finish_reason')}, "
                        f"completion={usage.get('completion_tokens')}, reasoning={reason_tokens}"
                    )
                parsed = extract_json(content)
                validate(parsed)
                atomic_json(cache, {"parsed": parsed, "model": model,
                                    "usage": data.get("usage", {}), "request": identity,
                                    "finish_reason": choice.get("finish_reason")})
                self._record({"type": "chat", "model": model, "task": task[:100],
                              "usage": data.get("usage", {}), "cache_key": cache.stem})
                return deepcopy(parsed)
            except Exception as exc:
                last_error = exc
                if attempt + 1 < cfg.HTTP_RETRIES:
                    time.sleep(min(25, 2 ** attempt + random.random()))
        raise RuntimeError(f"{model}: failed {task[:60]!r} after {cfg.HTTP_RETRIES} tries: {last_error}")

    def embeddings(self, texts):
        if not texts:
            return np.empty((0, 0))
        paths = [self.root / "cache/embeddings" /
                 (digest({"model": cfg.EMBEDDING_MODEL, "text": text}) + ".json")
                 for text in texts]
        missing = [i for i, path in enumerate(paths) if not path.exists()]

        for start in range(0, len(missing), cfg.EMBEDDING_BATCH_SIZE):
            indices = missing[start:start + cfg.EMBEDDING_BATCH_SIZE]
            body = {"model": cfg.EMBEDDING_MODEL, "input": [texts[i] for i in indices]}
            for attempt in range(cfg.HTTP_RETRIES):
                try:
                    data = self._post("embeddings", body)
                    vectors = {int(item["index"]): item["embedding"]
                               for item in data["data"]}
                    if set(vectors) != set(range(len(indices))):
                        raise ValueError("Incomplete embedding response")
                    for position, index in enumerate(indices):
                        atomic_json(paths[index], {"vector": vectors[position],
                                                   "model": cfg.EMBEDDING_MODEL})
                    self._record({"type": "embeddings", "model": cfg.EMBEDDING_MODEL,
                                  "count": len(indices), "usage": data.get("usage", {})})
                    break
                except Exception:
                    if attempt + 1 == cfg.HTTP_RETRIES:
                        raise
                    time.sleep(min(25, 2 ** attempt + random.random()))

        vectors = np.asarray([read_json(path)["vector"] for path in paths], dtype=float)
        if vectors.ndim != 2 or not np.isfinite(vectors).all():
            raise ValueError("Invalid embeddings")
        norms = np.linalg.norm(vectors, axis=1)
        if np.any(norms == 0):
            raise ValueError("Zero embedding")
        return vectors / norms[:, None]
