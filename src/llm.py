"""Thin wrapper around the Claude API: one model and effort per role, taken from config.yaml.

In dry-run mode no request is sent; each call returns the canned answer its step provides.
"""

import base64
import json
import logging
from collections import Counter
from pathlib import Path

log = logging.getLogger(__name__)

# Server-side fallback: if a safety classifier declines a request,
# the API re-runs it on a recommended fallback model instead of returning a refusal.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}


class Refusal(RuntimeError):
    pass


class Claude:
    def __init__(self, cfg: dict, dry_run: bool = False):
        self.roles = cfg["models"]
        self.max_tokens = cfg["limits"]["max_tokens"]
        self.max_continuations = cfg["limits"]["max_continuations"]
        self.system = (
            "You are one step of an automated research loop.\n"
            f"Research question: {cfg['question'].strip()}\n"
            "Be concrete, state your confidence, and say so plainly when the evidence does not support a claim."
        )
        self.dry_run = dry_run
        self.usage: list[dict] = []
        self.client = None
        if not dry_run:
            import anthropic

            self.client = anthropic.Anthropic()  # ANTHROPIC_API_KEY or an `ant auth login` profile

    def ask_json(self, role: str, prompt: str, schema: dict, *, images=(), dry_run_response: dict) -> dict:
        """Ask for an answer that matches a JSON schema (structured output)."""
        if self.dry_run:
            return dry_run_response
        content = self._call(role, _user_content(prompt, images), output_format={"type": "json_schema", "schema": schema})
        return json.loads(next(b.text for b in content if b.type == "text"))

    def ask_text(self, role: str, prompt: str, *, tools=(), dry_run_response: tuple) -> tuple[str, list[str], list[str]]:
        """Ask for free text, optionally with server tools such as web search.

        Returns the text, the URLs cited in it, and the other URLs the web search returned.
        """
        if self.dry_run:
            return dry_run_response
        content = self._call(role, _user_content(prompt, ()), tools=list(tools))
        log.info("%s: content blocks %s", role, dict(Counter(block.type for block in content)))
        texts, cited, searched = [], [], []
        for block in content:
            if block.type == "text":
                texts.append(block.text)
                for citation in getattr(block, "citations", None) or []:
                    url = getattr(citation, "url", None)
                    if url and url not in cited:
                        cited.append(url)
            elif block.type == "web_search_tool_result" and isinstance(block.content, list):
                # a list of web_search_result items; on failure the content is a single error object instead
                for result in block.content:
                    url = getattr(result, "url", None)
                    if url and url not in searched:
                        searched.append(url)
        return "".join(texts), cited, [url for url in searched if url not in cited]

    def _call(self, role: str, user_content: list, *, output_format=None, tools=None) -> list:
        spec = self.roles[role]
        output_config = {"effort": spec["effort"]}
        if output_format:
            output_config["format"] = output_format
        request = dict(
            model=spec["model"],
            max_tokens=self.max_tokens,
            system=self.system,
            thinking={"type": "adaptive"},
            output_config=output_config,
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if tools:
            request["tools"] = tools

        assistant: list = []
        for _ in range(self.max_continuations + 1):
            messages = [{"role": "user", "content": user_content}]
            if assistant:  # resume a paused server-tool turn: resend it, the server continues it
                messages.append({"role": "assistant", "content": assistant})
            message = self.client.beta.messages.create(messages=messages, **request)
            server_tools = getattr(message.usage, "server_tool_use", None)
            self.usage.append(
                {
                    "role": role,
                    "model": message.model,
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                    "web_search_requests": getattr(server_tools, "web_search_requests", 0) or 0,
                }
            )
            assistant = assistant + list(message.content)
            if message.stop_reason != "pause_turn":
                break

        if message.stop_reason == "refusal":
            raise Refusal(f"{role}: request declined ({message.stop_details})")
        if message.stop_reason == "max_tokens":
            log.warning("%s: answer cut at max_tokens=%d", role, self.max_tokens)
        return assistant


def _user_content(prompt: str, images) -> list:
    content = []
    for path in map(Path, images):
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": MEDIA_TYPES[path.suffix.lower()],
                    "data": base64.standard_b64encode(path.read_bytes()).decode(),
                },
            }
        )
    content.append({"type": "text", "text": prompt})
    return content
