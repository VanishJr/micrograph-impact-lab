"""Sources come from text citations and from web search result blocks (a fake response, no API call)."""

from pathlib import Path
from types import SimpleNamespace as NS

from src.config import load_config
from src.llm import Claude

ROOT = Path(__file__).resolve().parents[1]


def fake_message():
    return NS(
        model="claude-opus-5-5",
        stop_reason="end_turn",
        usage=NS(input_tokens=10, output_tokens=5, server_tool_use=NS(web_search_requests=2)),
        content=[
            NS(type="server_tool_use"),
            NS(type="web_search_tool_result", content=[NS(type="web_search_result", url="https://a"),
                                                       NS(type="web_search_result", url="https://b")]),
            NS(type="web_search_tool_result", content=NS(type="web_search_tool_result_error", error_code="max_uses_exceeded")),
            NS(type="text", text="Grain size matters ", citations=[NS(type="web_search_result_location", url="https://a")]),
            NS(type="text", text="a lot.", citations=None),
        ],
    )


def test_ask_text_collects_cited_and_searched_urls():
    claude = Claude(load_config(ROOT / "config.yaml"), dry_run=True)
    claude.dry_run = False
    claude.client = NS(beta=NS(messages=NS(create=lambda **request: fake_message())))

    text, cited, searched = claude.ask_text("librarian", "prompt", tools=[], dry_run_response=("", [], []))

    assert text == "Grain size matters a lot."
    assert cited == ["https://a"]
    assert searched == ["https://b"]
    assert claude.usage[0]["web_search_requests"] == 2
