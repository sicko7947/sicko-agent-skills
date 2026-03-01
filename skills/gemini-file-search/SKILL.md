---
name: gemini-file-search
description: Use when building, debugging, or querying Google Gemini File Search API — managed RAG with FileSearchStores, document upload, metadata filtering, chunking config, or grounding citations. Triggers on Gemini file search, FileSearchStore, managed RAG, AIP-160 filters, grounding metadata.
---

# Gemini File Search API

Fully managed RAG system built into the Gemini API. Handles storage, chunking, embedding, indexing, and retrieval — replaces DIY RAG stacks.

**Gemini Developer API only.** Not on Vertex AI.

## Quick Reference

| Item | Value |
|------|-------|
| SDK | `@google/genai` (JS) / `google-genai` (Python) |
| Models | gemini-2.5-pro, 2.5-flash, 2.5-flash-lite, 3-flash-preview, 3.1-pro-preview |
| Max file size | 100 MB |
| Stores per project | 10 |
| Metadata pairs/doc | 20 |
| Indexing cost | $0.15/1M tokens (free tier: free) |
| Storage cost | Free (but 3x raw size overhead) |
| Filter syntax | AIP-160 (`genre = "fiction" AND year > 2020`) |
| Chunking | `whiteSpaceConfig`: 100-600 tokens, configurable overlap |

## 3-Step Pattern

1. **Create store** — `ai.fileSearchStores.create({ config: { displayName } })`
2. **Upload docs** — Use Files API import (NOT direct upload — see critical bug below)
3. **Query** — Pass `fileSearch` tool in `generateContent` config

## Critical Bugs (March 2026)

- **Direct upload 503** — `uploadToFileSearchStore` fails for files >10KB. **Always use Files API import instead.**
- **Interactions API filters broken** — `metadataFilter` silently ignored. Use `generateContent` API.
- **ThinkingConfig + Structured Output + File Search** — nil response on Gemini 3. Use gemini-2.5-flash without thinkingConfig.
- **Office files MIME errors** — .doc/.xls/.xlsx fail on direct upload. Use Files API import.

## Cannot Combine With

- Google Search grounding (same request)
- URL Context (same request)
- Live API (not supported)

## Common Mistakes

1. Using `uploadToFileSearchStore` instead of Files API import (hits 503 bug)
2. Forgetting to poll operation until `done === true` before querying
3. Trying to update documents in-place (must delete + re-upload)
4. Using metadata filters in Interactions API (broken, use generateContent)
5. Assuming storage = raw file size (it's ~3x due to embeddings)

## Full API Reference

See `api-reference.md` in this directory for complete SDK signatures, all REST endpoints, code examples, chunking config, metadata filtering syntax, grounding/citation format, pagination patterns, and detailed bug workarounds.
