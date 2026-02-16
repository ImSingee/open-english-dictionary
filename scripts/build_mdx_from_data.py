#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


DEFAULT_TITLE = "Open English Dictionary"
DEFAULT_DESCRIPTION = "一个开源的 AI 词典"

PHONETIC_LABEL_ZH = {
    "uk": "英式",
    "us": "美式",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an MDX dictionary file from data/*.ndjson."
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing NDJSON shard files (default: data)",
    )
    parser.add_argument(
        "--out-mdx",
        default="open-english-dictionary.mdx",
        help="Output MDX file path (default: open-english-dictionary.mdx)",
    )
    parser.add_argument(
        "--title",
        default=DEFAULT_TITLE,
        help=f"Dictionary title stored in MDX metadata (default: {DEFAULT_TITLE!r})",
    )
    parser.add_argument(
        "--description",
        default=DEFAULT_DESCRIPTION,
        help="Dictionary description stored in MDX metadata",
    )
    return parser.parse_args()


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def iter_ndjson_files(data_dir: Path) -> list[Path]:
    return sorted(path for path in data_dir.glob("*.ndjson") if path.is_file())


def text_from_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def compact_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [compact_text(item) for item in value]
        parts = [part for part in parts if part]
        return "; ".join(parts)
    if isinstance(value, dict):
        en = compact_text(value.get("en"))
        zh = compact_text(value.get("zh"))
        if en or zh:
            return " ".join(part for part in [en, zh] if part)
        parts: list[str] = []
        for key, child in value.items():
            child_text = compact_text(child)
            if child_text:
                parts.append(f"{key}: {child_text}")
        return "; ".join(parts)
    return str(value).strip()


def render_string_list_section(title_zh: str, value: Any) -> str:
    if isinstance(value, str):
        items = [value.strip()] if value.strip() else []
    elif isinstance(value, list):
        items = [compact_text(item) for item in value]
        items = [item for item in items if item]
    else:
        text = compact_text(value)
        items = [text] if text else []

    if not items:
        return ""
    return (
        '<section class="section">'
        f'<h2 class="title">{html.escape(title_zh)}</h2>'
        "<ul>"
        + "".join(f"<li>{html.escape(item)}</li>" for item in items)
        + "</ul>"
        "</section>"
    )


def render_phonetic(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
        return text
    if isinstance(value, list):
        parts = [compact_text(item) for item in value]
        parts = [part for part in parts if part]
        return " / ".join(parts)
    if isinstance(value, dict):
        parts: list[str] = []
        for key, child in value.items():
            text = compact_text(child)
            if text:
                key_text = PHONETIC_LABEL_ZH.get(str(key).lower(), str(key))
                parts.append(f"{key_text}: {text}")
        return " | ".join(parts)

    return compact_text(value)


def render_entry(word: str, payload: dict[str, Any]) -> str:
    blocks: list[str] = []
    blocks.append('<div class="entry">')
    blocks.append(f'<h1 class="word">{html.escape(word)}</h1>')

    phonetic_text = render_phonetic(payload.get("phonetic"))

    summary = payload.get("summary")
    summary_zh = ""
    if isinstance(summary, dict):
        summary_zh = text_from_value(summary.get("zh")).strip()
    elif isinstance(summary, str):
        summary_zh = summary.strip()
    line_parts = [part for part in [phonetic_text, summary_zh] if part]
    if line_parts:
        blocks.append(f'<div class="phonetic-summary">{html.escape(" ".join(line_parts))}</div>')

    definitions = payload.get("definitions")
    if isinstance(definitions, list) and definitions:
        blocks.append('<section class="section">')
        blocks.append("<ol>")
        for item in definitions:
            if isinstance(item, dict):
                blocks.append("<li>")
                pos = compact_text(item.get("partOfSpeech"))
                definition_text = compact_text(item.get("definition"))
                line_parts = [part for part in [pos, definition_text] if part]
                if line_parts:
                    blocks.append(
                        f'<div class="def-line">{html.escape(" ".join(line_parts))}</div>'
                    )

                examples = item.get("examples")
                if isinstance(examples, list) and examples:
                    blocks.append('<ul class="examples">')
                    for ex in examples:
                        ex_text = compact_text(ex)
                        if ex_text:
                            blocks.append(f"<li>{html.escape(ex_text)}</li>")
                    blocks.append("</ul>")
                blocks.append("</li>")
                continue

            line_text = compact_text(item)
            if not line_text:
                continue
            blocks.append(f"<li>{html.escape(line_text)}</li>")
        blocks.append("</ol>")
        blocks.append("</section>")

    synonyms_html = render_string_list_section("相关词", payload.get("synonyms"))
    if synonyms_html:
        blocks.append(synonyms_html)

    extra_explanation_html = render_string_list_section(
        "额外说明", payload.get("extra_explanation")
    )
    if extra_explanation_html:
        blocks.append(extra_explanation_html)

    blocks.append("</div>")
    return "".join(blocks)


def load_entries(data_dir: Path) -> tuple[dict[str, str], int]:
    entries: dict[str, str] = {}
    overwritten = 0

    for file_path in iter_ndjson_files(data_dir):
        with file_path.open("r", encoding="utf-8") as handle:
            for line_no, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SystemExit(
                        f"ERROR: invalid JSON at {file_path}:{line_no}: {exc.msg}"
                    ) from exc

                if not isinstance(payload, dict):
                    raise SystemExit(
                        f"ERROR: expected JSON object at {file_path}:{line_no}"
                    )

                word = payload.get("word")
                if not isinstance(word, str) or not word:
                    raise SystemExit(
                        f"ERROR: missing/invalid 'word' at {file_path}:{line_no}"
                    )

                if word in entries:
                    overwritten += 1
                entries[word] = render_entry(word, payload)

    return entries, overwritten


def main() -> int:
    args = parse_args()

    try:
        from mdict_utils.base.writemdict import MDictWriter
    except ImportError as exc:
        raise SystemExit(
            "ERROR: missing dependency 'mdict-utils'. "
            "Run with: uv run --with mdict-utils python scripts/build_mdx_from_data.py"
        ) from exc

    repo_root = Path(__file__).resolve().parents[1]
    data_dir = resolve_path(repo_root, args.data_dir)
    out_mdx = resolve_path(repo_root, args.out_mdx)

    if not data_dir.exists() or not data_dir.is_dir():
        raise SystemExit(f"ERROR: data directory not found: {data_dir}")

    ndjson_files = iter_ndjson_files(data_dir)
    if not ndjson_files:
        raise SystemExit(f"ERROR: no .ndjson files found in: {data_dir}")

    entries, overwritten = load_entries(data_dir)
    if not entries:
        raise SystemExit("ERROR: no dictionary entries loaded")

    sorted_items = sorted(entries.items(), key=lambda kv: (kv[0].lower(), kv[0]))
    mdx_items = {word: html_text for word, html_text in sorted_items}

    writer = MDictWriter(
        mdx_items,
        title=args.title,
        description=args.description,
        encrypt_index=False,
    )

    out_mdx.parent.mkdir(parents=True, exist_ok=True)
    with out_mdx.open("wb") as handle:
        writer.write(handle)

    print(f"data_dir={data_dir}")
    print(f"out_mdx={out_mdx}")
    print(f"ndjson_files={len(ndjson_files)}")
    print(f"entries={len(entries)}")
    print(f"overwritten_duplicates={overwritten}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
