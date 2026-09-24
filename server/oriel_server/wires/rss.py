"""Parse a public RSS or Atom document into headline entries."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

FEED_ENTRY_LIMIT = 40
_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class FeedEntry:
    id: str
    title: str
    link: str
    observed_at: datetime


def parse_feed(payload: bytes, *, fallback: datetime) -> list[FeedEntry]:
    if payload.startswith(b"\xef\xbb\xbf"):
        payload = payload[3:]
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise ValueError("unreadable feed") from exc

    entries: list[FeedEntry] = []
    for node in _entries(root):
        title = _text(node, "title")
        if not title:
            continue
        link = _link(node)
        identity = _text(node, "guid") or _text(node, "id") or link or title
        entries.append(
            FeedEntry(
                id=identity,
                title=title,
                link=link,
                observed_at=_observed(node, fallback),
            )
        )
        if len(entries) >= FEED_ENTRY_LIMIT:
            break
    return entries


def _entries(root: ElementTree.Element) -> list[ElementTree.Element]:
    items = [node for node in root.iter() if _local(node.tag) == "item"]
    if items:
        return items
    return [node for node in root.iter() if _local(node.tag) == "entry"]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(node: ElementTree.Element, name: str) -> str:
    for child in list(node):
        if _local(child.tag) == name:
            return _clean("".join(child.itertext()))
    return ""


def _link(node: ElementTree.Element) -> str:
    alternate = ""
    href = ""
    plain = ""
    for child in list(node):
        if _local(child.tag) != "link":
            continue
        candidate = (child.get("href") or "").strip()
        rel = (child.get("rel") or "alternate").strip()
        text = _clean("".join(child.itertext()))
        if candidate and rel == "alternate" and not alternate:
            alternate = candidate
        elif candidate and not href:
            href = candidate
        if text.startswith(("http://", "https://")) and not plain:
            plain = text
    return alternate or plain or href


def _observed(node: ElementTree.Element, fallback: datetime) -> datetime:
    for name in ("pubDate", "published", "updated", "date"):
        parsed = _parse_time(_text(node, name))
        if parsed is not None:
            return parsed
    if fallback.tzinfo is None:
        return fallback.replace(tzinfo=timezone.utc)
    return fallback.astimezone(timezone.utc)


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clean(value: str) -> str:
    value = _TAG.sub("", value)
    value = html.unescape(value)
    return " ".join(value.split())
