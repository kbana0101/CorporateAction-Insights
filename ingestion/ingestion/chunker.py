"""Structure-aware chunking over a DoclingDocument.

The chunker walks Docling's document tree in reading order and emits chunks
whose boundaries follow document structure (section headers, tables, lists)
rather than arbitrary character counts.

Design goals
------------
* A chunk never crosses a section header boundary.
* A table is always a single atomic chunk (never split by row).
* Paragraph accumulation targets a soft token budget; if the budget is
  exceeded mid-paragraph the chunk is emitted and the next chunk carries a
  small tail overlap from the previous one for retrieval continuity.
* Every chunk gets the section-header breadcrumb prepended so the embedding
  model has enough context to disambiguate similar snippets across sections.

Extensive DEBUG logging is emitted for every boundary decision, budget
check, and emit — trace the log to see exactly where chunks were cut and
why. Enable with ``python main.py --verbose`` or ``LOG_LEVEL=DEBUG``.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# --- Tunables -----------------------------------------------------------------

TOKEN_BUDGET_SOFT = 600      # target chunk size
TOKEN_BUDGET_HARD = 1200     # forced flush above this
TOKEN_MIN_CHUNK = 40         # merge-forward threshold for tiny chunks
TOKEN_OVERLAP = 60           # tail overlap on paragraph-overflow splits only
ENCODING_NAME = "cl100k_base"  # matches text-embedding-3-small


# --- Token counting -----------------------------------------------------------

_encoder = None


def _encoder_instance():
    global _encoder
    if _encoder is None:
        import tiktoken
        _encoder = tiktoken.get_encoding(ENCODING_NAME)
    return _encoder


def count_tokens(text):
    # type: (str) -> int
    if not text:
        return 0
    return len(_encoder_instance().encode(text))


def _tail_overlap(text, budget):
    # type: (str, int) -> str
    """Return the trailing ``budget`` tokens of ``text`` as a string.

    Used to produce a small overlap when a paragraph run overflows and we
    need to start a new chunk that keeps the prior context.
    """
    if not text:
        return ""
    enc = _encoder_instance()
    tokens = enc.encode(text)
    if len(tokens) <= budget:
        return text
    return enc.decode(tokens[-budget:])


# --- Docling item introspection ----------------------------------------------

def _item_kind(item):
    # type: (Any) -> str
    """Map a Docling item to one of: heading / paragraph / list / table /
    picture / other. Uses attribute duck-typing to stay resilient across
    Docling minor versions."""
    cls_name = type(item).__name__
    if "SectionHeader" in cls_name or "Heading" in cls_name:
        return "heading"
    if "Table" in cls_name:
        return "table"
    if "List" in cls_name:
        return "list"
    if "Picture" in cls_name or "Figure" in cls_name:
        return "picture"
    if "Text" in cls_name:
        return "paragraph"
    return "other"


def _item_text(item):
    # type: (Any) -> str
    text = getattr(item, "text", None)
    if text:
        return str(text).strip()
    return ""


def _item_pages(item):
    # type: (Any) -> Tuple[Optional[int], Optional[int]]
    """Extract (page_start, page_end) from a Docling item's provenance."""
    prov = getattr(item, "prov", None)
    if not prov:
        return (None, None)
    pages = []
    for p in prov:
        page_no = getattr(p, "page_no", None)
        if page_no is not None:
            pages.append(int(page_no))
    if not pages:
        return (None, None)
    return (min(pages), max(pages))


def _item_heading_level(item):
    # type: (Any) -> int
    level = getattr(item, "level", None)
    if isinstance(level, int) and level > 0:
        return level
    # Fallback for TextItem with label containing 'section_header'
    label = getattr(item, "label", None)
    if label and "heading" in str(label).lower():
        return 2
    return 1


def _table_to_markdown(item):
    # type: (Any) -> str
    """Render a TableItem as Markdown. Falls back to text() if pandas fails."""
    try:
        df = item.export_to_dataframe()
        return df.to_markdown(index=False)
    except Exception as exc:
        logger.debug("Table export_to_dataframe failed (%s); falling back to text", exc)
        text = _item_text(item)
        if text:
            return text
        return "(table content unavailable)"


def _list_item_prefix(item):
    # type: (Any) -> str
    """Prefix a list entry with a bullet or number if we can figure one out."""
    marker = getattr(item, "marker", None)
    if marker:
        return "{0} ".format(marker)
    return "- "


# --- Chunk container ---------------------------------------------------------

class _ChunkBuilder(object):
    """Accumulates text + metadata for the chunk currently being assembled.

    A single builder is a chunk-in-progress; emit_chunk drains it and returns
    a plain dict ready for JSON serialisation.
    """

    def __init__(self, section_path, doc_metadata, first_chunk_index):
        # type: (List[str], Dict[str, Any], int) -> None
        self.section_path = list(section_path)
        self.doc_metadata = doc_metadata
        self.first_chunk_index = first_chunk_index

        self._parts = []  # type: List[str]
        self._element_kinds = set()  # type: set
        self._page_start = None  # type: Optional[int]
        self._page_end = None  # type: Optional[int]
        self._token_count = 0

    def is_empty(self):
        # type: () -> bool
        return not self._parts

    def token_count(self):
        # type: () -> int
        return self._token_count

    def raw_text(self):
        # type: () -> str
        return "\n\n".join(self._parts).strip()

    def add(self, text, element_kind, page_start, page_end):
        # type: (str, str, Optional[int], Optional[int]) -> None
        if not text:
            return
        self._parts.append(text)
        self._element_kinds.add(element_kind)
        self._token_count += count_tokens(text)
        if page_start is not None:
            self._page_start = page_start if self._page_start is None else min(self._page_start, page_start)
        if page_end is not None:
            self._page_end = page_end if self._page_end is None else max(self._page_end, page_end)

    def prime_with_overlap(self, overlap_text, overlap_tokens):
        # type: (str, int) -> None
        """Seed a fresh builder with a tail-overlap from the previous chunk."""
        if not overlap_text:
            return
        self._parts.append(overlap_text)
        self._element_kinds.add("overlap")
        self._token_count += overlap_tokens

    def element_type(self):
        # type: () -> str
        kinds = self._element_kinds - {"overlap"}
        if len(kinds) == 1:
            (only,) = kinds
            return only
        if not kinds:
            return "paragraph"
        return "mixed"

    def to_chunk_dict(self, chunk_index, oversize_table=False):
        # type: (int, bool) -> Dict[str, Any]
        breadcrumb = ""
        if self.section_path:
            breadcrumb = "## " + " > ".join(self.section_path) + "\n\n"
        body = self.raw_text()
        text = breadcrumb + body

        metadata = {
            "chunk_index": chunk_index,
            "element_type": self.element_type(),
            "page_start": self._page_start,
            "page_end": self._page_end,
            "section_path": list(self.section_path),
            "token_count": count_tokens(text),
        }
        if oversize_table:
            metadata["oversize_table"] = True

        # Denormalise corp-action fields onto every chunk so retrieval
        # results are self-sufficient (no join back to corporate_actions).
        for key in ("doc_id", "company", "scrip_code", "subject",
                    "announcement_date", "source"):
            if key in self.doc_metadata and self.doc_metadata[key] is not None:
                metadata[key] = self.doc_metadata[key]

        return {"text": text, "metadata": metadata}


# --- Section-path tracking ---------------------------------------------------

def _update_section_path(section_path, heading_text, level):
    # type: (List[str], str, int) -> List[str]
    """Push/pop the heading stack so section_path reflects the current context."""
    level = max(1, level)
    new_path = section_path[: level - 1]
    new_path.append(heading_text)
    return new_path


# --- Main entry point --------------------------------------------------------

def chunk_document(docling_doc, doc_metadata):
    # type: (Any, Dict[str, Any]) -> List[Dict[str, Any]]
    """Walk a DoclingDocument and emit structure-aware chunks.

    ``doc_metadata`` should contain doc_id and the denormalised corp-action
    fields (company, scrip_code, subject, announcement_date, source).
    """
    doc_id = doc_metadata.get("doc_id", "<unknown>")
    logger.info(
        "chunker: begin doc_id=%s budget_soft=%d budget_hard=%d overlap=%d",
        doc_id, TOKEN_BUDGET_SOFT, TOKEN_BUDGET_HARD, TOKEN_OVERLAP,
    )

    chunks = []  # type: List[Dict[str, Any]]
    section_path = []  # type: List[str]

    def _new_builder():
        return _ChunkBuilder(section_path, doc_metadata, len(chunks))

    builder = _new_builder()

    items_iter = _iter_document_items(docling_doc)

    item_index = -1
    for item in items_iter:
        item_index += 1
        kind = _item_kind(item)
        text = _item_text(item)
        page_start, page_end = _item_pages(item)

        if kind == "heading":
            level = _item_heading_level(item)
            logger.debug(
                "chunker: item#%d HEADING level=%d text=%r page=%s",
                item_index, level, _preview(text), page_start,
            )
            # Emit the in-progress chunk before switching sections.
            if not builder.is_empty():
                chunk = _finalise_and_emit(builder, chunks, reason="section-boundary")
                _ = chunk  # only used for logging below via chunks[-1]
            section_path = _update_section_path(section_path, text, level)
            logger.debug(
                "chunker: section_path now = %s",
                " > ".join(section_path) if section_path else "(root)",
            )
            builder = _new_builder()
            # The heading itself is NOT added as body text — it's captured in
            # the breadcrumb of every subsequent chunk under this section.
            continue

        if kind == "table":
            logger.debug(
                "chunker: item#%d TABLE page=%s-%s",
                item_index, page_start, page_end,
            )
            # Any in-progress paragraph flushes before we emit the table.
            if not builder.is_empty():
                _finalise_and_emit(builder, chunks, reason="pre-table")
                builder = _new_builder()
            table_md = _table_to_markdown(item)
            table_tokens = count_tokens(table_md)
            oversize = table_tokens > TOKEN_BUDGET_HARD
            table_builder = _new_builder()
            table_builder.add(table_md, "table", page_start, page_end)
            logger.debug(
                "chunker: emit TABLE tokens=%d oversize=%s",
                table_tokens, oversize,
            )
            _finalise_and_emit(
                table_builder, chunks,
                reason="table-atomic",
                oversize_table=oversize,
            )
            builder = _new_builder()
            continue

        if kind == "picture":
            caption_attr = getattr(item, "caption_text", None)
            caption = None
            if callable(caption_attr):
                # Newer Docling requires the DoclingDocument; older versions
                # took no args. Try the new shape first and fall back.
                try:
                    caption = caption_attr(docling_doc)
                except TypeError:
                    caption = caption_attr()
            else:
                caption = caption_attr
            if caption:
                logger.debug(
                    "chunker: item#%d PICTURE with caption=%r — folding into current chunk",
                    item_index, _preview(str(caption)),
                )
                builder.add(str(caption).strip(), "paragraph", page_start, page_end)
            else:
                logger.debug("chunker: item#%d PICTURE (no caption) — skipping", item_index)
            continue

        if kind in ("paragraph", "list", "other"):
            if not text:
                logger.debug(
                    "chunker: item#%d %s empty text — skipping", item_index, kind.upper(),
                )
                continue
            body = text
            if kind == "list":
                body = _list_item_prefix(item) + body
            token_delta = count_tokens(body)
            logger.debug(
                "chunker: item#%d %s tokens=%d page=%s builder=%d/%d",
                item_index, kind.upper(), token_delta, page_start,
                builder.token_count(), TOKEN_BUDGET_SOFT,
            )
            # Overflow decision.
            projected = builder.token_count() + token_delta
            if not builder.is_empty() and projected > TOKEN_BUDGET_SOFT:
                logger.debug(
                    "chunker: OVERFLOW projected=%d > soft=%d — emitting with overlap",
                    projected, TOKEN_BUDGET_SOFT,
                )
                prev_tail = _tail_overlap(builder.raw_text(), TOKEN_OVERLAP)
                overlap_tokens = count_tokens(prev_tail)
                _finalise_and_emit(builder, chunks, reason="soft-budget-overflow")
                builder = _new_builder()
                builder.prime_with_overlap(prev_tail, overlap_tokens)
                logger.debug(
                    "chunker: new builder primed with overlap tokens=%d preview=%r",
                    overlap_tokens, _preview(prev_tail),
                )
            builder.add(body, "paragraph" if kind != "list" else "list", page_start, page_end)
            # Hard cap: if we blew way past the soft budget in a single item,
            # cut immediately so a huge paragraph doesn't produce a giant chunk.
            if builder.token_count() > TOKEN_BUDGET_HARD:
                logger.debug(
                    "chunker: HARD CAP builder=%d > hard=%d — force flush",
                    builder.token_count(), TOKEN_BUDGET_HARD,
                )
                _finalise_and_emit(builder, chunks, reason="hard-cap")
                builder = _new_builder()

    # Drain any residual chunk.
    if not builder.is_empty():
        logger.debug("chunker: final flush builder=%d tokens", builder.token_count())
        _finalise_and_emit(builder, chunks, reason="end-of-document")

    # Post-pass: merge sub-min chunks forward (unless they're tables).
    merged = _merge_tiny_chunks(chunks)

    logger.info(
        "chunker: done doc_id=%s emitted=%d final=%d",
        doc_id, len(chunks), len(merged),
    )
    for c in merged:
        m = c["metadata"]
        logger.debug(
            "chunker: chunk#%d type=%s pages=%s-%s tokens=%d section=%s preview=%r",
            m["chunk_index"], m["element_type"],
            m.get("page_start"), m.get("page_end"),
            m["token_count"],
            " > ".join(m["section_path"]) if m["section_path"] else "(root)",
            _preview(c["text"]),
        )
    return merged


# --- Internals ---------------------------------------------------------------

def _iter_document_items(docling_doc):
    # type: (Any) -> Iterable[Any]
    """Yield Docling items in reading order.

    Docling's public API for this has moved around a bit; we prefer the
    modern ``iterate_items`` and fall back to walking the item list.
    """
    if hasattr(docling_doc, "iterate_items"):
        for entry in docling_doc.iterate_items():
            # iterate_items yields (item, level) tuples in newer versions;
            # older yields items directly.
            if isinstance(entry, tuple):
                yield entry[0]
            else:
                yield entry
        return

    # Fallback: concatenate the well-known collections.
    for attr in ("texts", "tables", "pictures", "lists"):
        seq = getattr(docling_doc, attr, None) or []
        for item in seq:
            yield item


def _finalise_and_emit(builder, chunks, reason, oversize_table=False):
    # type: (_ChunkBuilder, List[Dict[str, Any]], str, bool) -> Optional[Dict[str, Any]]
    if builder.is_empty():
        return None
    chunk = builder.to_chunk_dict(len(chunks), oversize_table=oversize_table)
    logger.debug(
        "chunker: EMIT chunk#%d reason=%s type=%s tokens=%d pages=%s-%s",
        chunk["metadata"]["chunk_index"],
        reason,
        chunk["metadata"]["element_type"],
        chunk["metadata"]["token_count"],
        chunk["metadata"].get("page_start"),
        chunk["metadata"].get("page_end"),
    )
    chunks.append(chunk)
    return chunk


def _merge_tiny_chunks(chunks):
    # type: (List[Dict[str, Any]]) -> List[Dict[str, Any]]
    """Merge chunks under the minimum token threshold forward into the next
    chunk. Tables are never merged (they must stay atomic)."""
    if not chunks:
        return chunks

    merged = []  # type: List[Dict[str, Any]]
    pending = None  # type: Optional[Dict[str, Any]]

    for chunk in chunks:
        meta = chunk["metadata"]
        is_table = meta["element_type"] == "table"
        too_small = meta["token_count"] < TOKEN_MIN_CHUNK

        if pending is not None:
            # Absorb pending into current chunk if compatible.
            if not is_table:
                logger.debug(
                    "chunker: MERGE tiny chunk#%d (tokens=%d) forward into chunk#%d",
                    pending["metadata"]["chunk_index"],
                    pending["metadata"]["token_count"],
                    meta["chunk_index"],
                )
                chunk = _merge_two(pending, chunk)
                meta = chunk["metadata"]
                is_table = meta["element_type"] == "table"
                too_small = meta["token_count"] < TOKEN_MIN_CHUNK
            else:
                # Can't merge into a table — just emit the tiny chunk as-is.
                logger.debug(
                    "chunker: cannot merge tiny chunk#%d forward (next is table); keeping",
                    pending["metadata"]["chunk_index"],
                )
                merged.append(pending)
            pending = None

        if too_small and not is_table:
            pending = chunk
            continue

        merged.append(chunk)

    if pending is not None:
        # Last chunk was tiny — try merging back into the previous.
        if merged and merged[-1]["metadata"]["element_type"] != "table":
            logger.debug(
                "chunker: MERGE trailing tiny chunk#%d back into chunk#%d",
                pending["metadata"]["chunk_index"],
                merged[-1]["metadata"]["chunk_index"],
            )
            merged[-1] = _merge_two(merged[-1], pending)
        else:
            merged.append(pending)

    # Reindex chunk_index so consumers see a dense 0..N-1 sequence.
    for i, c in enumerate(merged):
        c["metadata"]["chunk_index"] = i
    return merged


def _merge_two(a, b):
    # type: (Dict[str, Any], Dict[str, Any]) -> Dict[str, Any]
    merged_text = a["text"].rstrip() + "\n\n" + b["text"].lstrip()
    ma, mb = a["metadata"], b["metadata"]
    page_start = _min_or_other(ma.get("page_start"), mb.get("page_start"))
    page_end = _max_or_other(ma.get("page_end"), mb.get("page_end"))
    # Prefer the earlier chunk's section_path (they're usually the same).
    section_path = ma.get("section_path") or mb.get("section_path") or []
    element_type = ma["element_type"] if ma["element_type"] == mb["element_type"] else "mixed"
    metadata = {
        **ma,
        "page_start": page_start,
        "page_end": page_end,
        "section_path": section_path,
        "element_type": element_type,
        "token_count": count_tokens(merged_text),
    }
    return {"text": merged_text, "metadata": metadata}


def _min_or_other(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


def _max_or_other(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


def _preview(text, limit=80):
    # type: (str, int) -> str
    if text is None:
        return ""
    flat = " ".join(text.split())
    return flat[:limit] + ("..." if len(flat) > limit else "")
