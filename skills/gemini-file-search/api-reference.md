# Gemini File Search API — Complete Reference

**Status: Public Preview (March 2026). Schemas and features may change.**

Gemini Developer API only. Not available on Vertex AI.

---

## Architecture

3-step managed RAG:
1. **Create FileSearchStore** — empty container for documents
2. **Upload/import documents** — files are chunked, embedded (gemini-embedding-001), and indexed
3. **Query** — pass `fileSearch` tool in generateContent; model retrieves relevant chunks automatically

Documents are **immutable** after indexing. To update: delete + re-upload.

---

## REST API Endpoints

Base URL: `https://generativelanguage.googleapis.com`

### Store Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1beta/fileSearchStores` | Create store |
| GET | `/v1beta/fileSearchStores` | List stores (paginated) |
| GET | `/v1beta/fileSearchStores/{name}` | Get store |
| DELETE | `/v1beta/fileSearchStores/{name}` | Delete store |

### File Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload/v1beta/{store}:uploadToFileSearchStore` | Direct upload (BUGGY — use importFile) |
| POST | `/v1beta/{store}:importFile` | Import from Files API (RECOMMENDED) |

### Document Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1beta/{parent=fileSearchStores/*}/documents` | List documents |
| GET | `/v1beta/{name=fileSearchStores/*/documents/*}` | Get document |
| DELETE | `/v1beta/{name=fileSearchStores/*/documents/*}` | Delete document |

### Operation Polling
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1beta/fileSearchStores/*/operations/{op}` | Poll store operation |
| GET | `/v1beta/fileSearchStores/*/upload/operations/{op}` | Poll upload operation |

---

## Resource Schemas

### FileSearchStore
```json
{
  "name": "fileSearchStores/{id}",
  "displayName": "string (max 512 chars)",
  "createTime": "RFC 3339",
  "updateTime": "RFC 3339",
  "activeDocumentsCount": 0,
  "pendingDocumentsCount": 0,
  "failedDocumentsCount": 0,
  "sizeBytes": "string"
}
```

### Document
```json
{
  "name": "fileSearchStores/{id}/documents/{id}",
  "displayName": "string (max 512 chars)",
  "state": "STATE_PENDING | STATE_ACTIVE | STATE_FAILED",
  "mimeType": "string",
  "sizeBytes": "string",
  "createTime": "RFC 3339",
  "updateTime": "RFC 3339",
  "customMetadata": [{ "key": "string", "stringValue|numericValue|stringListValue": "..." }]
}
```

### CustomMetadata (max 20 per document)
```json
{ "key": "genre",  "stringValue": "fiction" }
{ "key": "year",   "numericValue": 2024 }
{ "key": "tags",   "stringListValue": { "values": ["sci-fi", "classic"] } }
```

---

## JavaScript/TypeScript SDK (`@google/genai`)

### Store CRUD

```typescript
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

// Create
const store = await ai.fileSearchStores.create({
  config: { displayName: 'my-store' },
});

// List (paginated)
const pager = await ai.fileSearchStores.list({ config: { pageSize: 10 } });
let page = pager.page;
while (true) {
  for (const s of page) console.log(s.name, s.displayName);
  if (!pager.hasNextPage()) break;
  page = await pager.nextPage();
}

// Get
const fetched = await ai.fileSearchStores.get({ name: store.name });

// Delete (force=true deletes all contained documents)
await ai.fileSearchStores.delete({
  name: store.name,
  config: { force: true },
});
```

### Upload Documents (RECOMMENDED: Files API Import)

Direct upload (`uploadToFileSearchStore`) has a critical bug causing 503 errors for files >10KB. **Always use the two-step Files API import pattern:**

```typescript
// Step 1: Upload to Files API
const fileRef = await ai.files.upload({
  file: '/path/to/document.pdf',
  config: { displayName: 'My Document' },
});

// Step 2: Import into store
let op = await ai.fileSearchStores.importFile({
  fileSearchStoreName: store.name,
  fileName: fileRef.name,
});

// Step 3: Poll until done (REQUIRED before querying)
while (!op.done) {
  await new Promise((r) => setTimeout(r, 2000));
  op = await ai.operations.get({ operation: op });
}
```

### Upload with Metadata and Chunking Config

```typescript
// Direct upload (use only if files are tiny <10KB, otherwise use import)
let op = await ai.fileSearchStores.uploadToFileSearchStore({
  file: filePath,
  fileSearchStoreName: store.name,
  config: {
    displayName: 'doc.pdf',
    customMetadata: [
      { key: 'doc_type', stringValue: 'manual' },
      { key: 'version', numericValue: 2 },
      { key: 'tags', stringListValue: { values: ['setup', 'install'] } },
    ],
    chunkingConfig: {
      whiteSpaceConfig: {
        maxTokensPerChunk: 400, // default ~400
        maxOverlapTokens: 40, // default ~40
      },
    },
  },
});
```

**Note:** Metadata and chunking config are NOT available via `importFile()` — only via `uploadToFileSearchStore()`. This is a design tension with Bug #1. For files >10KB that need metadata, you must either: (a) accept no custom metadata, or (b) try direct upload and fall back to import on failure.

### Concurrent Uploads

```typescript
const uploadAll = files.map(async (filePath) => {
  const fileRef = await ai.files.upload({ file: filePath });
  let op = await ai.fileSearchStores.importFile({
    fileSearchStoreName: store.name,
    fileName: fileRef.name,
  });
  while (!op.done) {
    await new Promise((r) => setTimeout(r, 2000));
    op = await ai.operations.get({ operation: op });
  }
  return op;
});
await Promise.all(uploadAll);
```

### Query with File Search

```typescript
const response = await ai.models.generateContent({
  model: 'gemini-2.5-flash',
  contents: 'What does the document say about installation?',
  config: {
    tools: [
      {
        fileSearch: {
          fileSearchStoreNames: [store.name],
          top_k: 5, // chunks retrieved (higher = more context, more cost)
          metadataFilter: 'doc_type = "manual" AND version >= 2',
        },
      },
    ],
  },
});

console.log(response.text);
```

### Inspect Grounding/Citations

```typescript
const grounding = response.candidates?.[0]?.groundingMetadata;

// Retrieved chunks (source snippets)
grounding?.groundingChunks?.forEach((chunk) => {
  console.log(chunk.retrievedContext.title); // document displayName
  console.log(chunk.retrievedContext.text); // retrieved text snippet
});

// Citation mapping (response text -> source chunks)
grounding?.groundingSupports?.forEach((support) => {
  console.log(support.segment.text); // model's response text segment
  console.log(support.segment.startIndex); // char offset start
  console.log(support.segment.endIndex); // char offset end
  console.log(support.groundingChunkIndices); // which chunks cited
  console.log(support.confidenceScores); // confidence per citation
});
```

### Document Management

```typescript
// List documents in store
const docPager = await ai.fileSearchStores.documents.list({
  parent: store.name,
});

// Get specific document
const doc = await ai.fileSearchStores.documents.get({
  name: 'fileSearchStores/abc/documents/xyz',
});

// Delete document
await ai.fileSearchStores.documents.delete({
  name: doc.name,
  config: { force: true },
});
```

### Update Document Pattern (delete + re-upload)

Documents are immutable. To update content:

```typescript
// 1. Delete old document
await ai.fileSearchStores.documents.delete({
  name: oldDoc.name,
  config: { force: true },
});

// 2. Upload new version
const fileRef = await ai.files.upload({ file: updatedFilePath });
let op = await ai.fileSearchStores.importFile({
  fileSearchStoreName: store.name,
  fileName: fileRef.name,
});
while (!op.done) {
  await new Promise((r) => setTimeout(r, 2000));
  op = await ai.operations.get({ operation: op });
}
```

---

## Python SDK (`google-genai >= 1.49.0`)

### Store CRUD

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

# Create
store = client.file_search_stores.create(
    config=types.CreateFileSearchStoreConfig(display_name='My Store')
)

# List
for s in client.file_search_stores.list():
    print(s.name, s.display_name)

# Get
store = client.file_search_stores.get(name='fileSearchStores/abc123')

# Delete
client.file_search_stores.delete(
    name=store.name,
    config=types.DeleteFileSearchStoreConfig(force=True)
)
```

### Upload (Files API Import — recommended)

```python
# Step 1: Upload to Files API
file_ref = client.files.upload(
    file='path/to/file.pdf',
    config=types.UploadFileConfig(display_name='My Document')
)

# Step 2: Import into store
import_op = client.file_search_stores.import_file(
    file_search_store_name=store.name,
    file_name=file_ref.name,
)

# Step 3: Poll
import time
while not (import_op := client.operations.get(import_op)).done:
    time.sleep(2)
```

### Upload with Metadata and Chunking

```python
upload_op = client.file_search_stores.upload_to_file_search_store(
    file_search_store_name=store.name,
    file='path/to/file.pdf',
    config=types.UploadToFileSearchStoreConfig(
        display_name='My Document',
        custom_metadata=[
            types.CustomMetadata(key='genre', string_value='fiction'),
            types.CustomMetadata(key='year', numeric_value=2024),
            types.CustomMetadata(key='tags',
                string_list_value=types.StringList(values=['sci-fi', 'classic'])),
        ],
        chunking_config=types.ChunkingConfig(
            white_space_config=types.WhiteSpaceChunkingConfig(
                max_tokens_per_chunk=400,
                max_overlap_tokens=40
            )
        )
    )
)
```

### Query with File Search

```python
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='What does the text say about installation?',
    config=types.GenerateContentConfig(
        tools=[types.Tool(
            file_search=types.FileSearch(
                file_search_store_names=[store.name],
                top_k=5,
                metadata_filter='genre = "fiction" AND year > 2020'
            )
        )]
    )
)
print(response.text)
```

### Inspect Grounding/Citations (Python)

```python
grounding = response.candidates[0].grounding_metadata

for chunk in grounding.grounding_chunks:
    print(chunk.retrieved_context.title)
    print(chunk.retrieved_context.text)

for support in grounding.grounding_supports:
    print(support.segment.text)
    print(support.segment.start_index, support.segment.end_index)
    print(support.grounding_chunk_indices)
    print(support.confidence_scores)
```

---

## AIP-160 Metadata Filter Syntax

Filters are strings passed via `metadataFilter` (JS) / `metadata_filter` (Python).

### Operators
| Operator | Example | Notes |
|----------|---------|-------|
| `=` | `genre = "fiction"` | String equality |
| `!=` | `genre != "poetry"` | Not equal |
| `<` `>` `<=` `>=` | `year > 2020` | Numeric comparison |
| `:` | `tags : "sci-fi"` | Has operator — list membership |
| `*` | `title = "Report*"` | Wildcard match |
| `AND` | `genre = "fiction" AND year > 2020` | Logical AND |
| `OR` | `genre = "fiction" OR genre = "history"` | Logical OR |
| `NOT` / `-` | `NOT genre = "poetry"` | Negation |

### Rules
- Field names on LEFT side of comparison
- String values in **double quotes**
- Numeric values unquoted
- `:` (has) operator checks list membership for `stringListValue` fields
- Wildcards (`*`) for prefix/suffix matching on strings
- Full spec: https://google.aip.dev/160

### Examples
```
genre = "fiction"
author = "Lewis Carroll" AND year > 2000
genre = "fiction" OR genre = "non-fiction"
NOT genre = "poetry"
doc_type = "manual" AND version >= 2
tags : "sci-fi"
title = "Report*"
```

---

## Chunking Configuration

Only `whiteSpaceConfig` type is currently documented.

| Parameter | Default | Range | Notes |
|-----------|---------|-------|-------|
| `maxTokensPerChunk` | ~400 | No hard documented limits | API treats as hints |
| `maxOverlapTokens` | ~40 | No hard documented limits | Overlap between adjacent chunks |

**Recommendations by use case:**
- FAQ/concise content: 200 tokens, 20 overlap
- Technical manuals: 400 tokens, 40 overlap (default)
- Research papers: 600 tokens, 60 overlap

Chunking is set at **indexing time** and cannot be changed after upload. To re-chunk: delete document, re-upload with new config.

---

## Supported Models

| Model | Status |
|-------|--------|
| `gemini-2.5-pro` | Stable |
| `gemini-2.5-flash` | Stable (recommended for most use cases) |
| `gemini-2.5-flash-lite` | Stable |
| `gemini-3-flash-preview` | Preview |
| `gemini-3.1-pro-preview` | Preview |

`gemini-3-pro-preview` was deprecated March 9, 2026 — use `gemini-3.1-pro-preview`.

---

## Pricing

| Component | Free Tier | Paid Tier |
|-----------|-----------|-----------|
| Indexing (embedding) | Free | $0.15 / 1M tokens |
| Storage | Free | Free |
| Query-time embeddings | Free | Free |
| Retrieved tokens | Billed as model input tokens | Billed as model input tokens |

**Storage overhead:** ~3x raw file size (raw data + embeddings). A 300 MB corpus uses ~900 MB of quota.

---

## Rate Limits and Quotas

| Limit | Value |
|-------|-------|
| Stores per project | 10 |
| Max file size | 100 MB |
| Max metadata pairs per doc | 20 |
| displayName max length | 512 chars |
| Store name max length | 40 chars (server-assigned) |
| Free tier storage | 1 GB |
| Tier 1 storage | 10 GB |
| Tier 2 storage | 100 GB |
| Tier 3 storage | 1 TB |
| Recommended max per store | 20 GB (for optimal search) |

---

## Supported File Types

**IMPORTANT: File Search only supports TEXT-BASED files. Do NOT confuse with the general Gemini Files API which supports images/audio/video.**

**Documents:** PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, RTF
**Data:** JSON, XML, YAML, SQL, CSV, TSV
**Text:** TXT, Markdown, HTML, CSS
**Code:** Python, JavaScript, TypeScript, Java, Go, Rust, Kotlin, Swift, C, C++, PHP, Shell, Dart, LaTeX, and many more

**NOT supported (will fail):** Images (PNG, JPEG, GIF, WebP), audio (MP3, WAV), video (MP4, MOV). These work with the general Gemini Files API but NOT with File Search stores.

**MIME type note:** Office files (.doc, .xls, .xlsx) may fail on direct upload with MIME type errors. Use Files API import as workaround.

---

## Known Bugs (Active — March 2026)

### 1. `uploadToFileSearchStore` 503 for files >10KB
**Error:** HTTP 503 — `"Failed to count tokens"`
**Scope:** All file types, JS SDK confirmed, Python likely affected
**Status:** Reported Nov 2025, unresolved Feb 2026
**Workaround:** Always use Files API two-step import pattern
**Ref:** https://discuss.ai.google.dev/t/123818

### 2. `metadataFilter` broken in Interactions API
**Error:** No error — filtering silently has no effect
**Scope:** Interactions API only; `generateContent` works correctly
**Status:** Reported Feb 28 2026, unresolved
**Workaround:** Use `generateContent` instead of Interactions API
**Ref:** https://discuss.ai.google.dev/t/127506

### 3. File Search + Structured Output + ThinkingConfig = nil response (Gemini 3)
**Error:** `candidates[0].content.parts[0].text` returns nil; `groundingMetadata.groundingChunks` absent; `toolUsePromptTokenCount` spikes to 190K-234K tokens
**Scope:** Gemini 3 models with `thinkingLevel: "low"` or `"high"`; `"medium"` partially works but with ~28K tokens overhead
**Status:** Reported Feb 27 2026, unresolved
**Workaround:** Use `gemini-2.5-flash` without `thinkingConfig`; specify JSON format via system instructions and parse text response
**Ref:** https://discuss.ai.google.dev/t/127444

### 4. Office file MIME type errors on direct upload
**Error:** `"When provided, MIME type must be in a valid type/subtype format"` or `"Unknown mime type"`
**Scope:** .doc, .xls, .xlsx via `uploadToFileSearchStore`
**Workaround:** Upload via Files API then `importFile()`
**Ref:** https://discuss.ai.google.dev/t/110281

### 5. Storage quota — real limit ~1GB vs documented 10GB (Tier 1)
**Error:** Uploads silently fail / stuck in pre-condition state after ~1GB
**Ref:** https://discuss.ai.google.dev/t/126331

### 6. File Search + Structured Output (was broken Dec 2025, resolved Jan 2026)
Working as of Jan 10 2026, but see Bug #3 for the ThinkingConfig variant that remains broken.
**Ref:** https://discuss.ai.google.dev/t/111665

---

## Limitations

1. **Not in Live API** — real-time streaming sessions don't support File Search
2. **Cannot combine with Google Search grounding** in same request
3. **Cannot combine with URL Context** in same request
4. **No in-place document update** — must delete + re-upload
5. **Documents immutable** after indexing (content, metadata, chunks)
6. **File API files expire after 48h** — but once imported into a FileSearchStore, data persists indefinitely
7. **No TTL setting** — embeddings persist until manual deletion or model deprecation
8. **No usage dashboard** in Google AI Studio for File Search stores
9. **No name-based document deletion filtering** — must list, find by name, then delete by resource ID
10. **MCP + Function Calls + Built-in tools** cannot be combined in a single Interactions API session (coming soon)

---

## Best Practices

1. **Always use Files API import** — avoids the 503 bug on direct upload
2. **Poll operations** — never query a store before upload operations complete (`done === true`)
3. **Clean up stores** — storage counts toward quota even though free; delete unused stores
4. **Use metadata strategically** — plan metadata schema upfront since documents can't be updated
5. **Size stores appropriately** — stay under 20GB per store for optimal search performance
6. **Handle concurrent uploads** — use `Promise.all()` / `asyncio.gather()` for batch imports
7. **Use gemini-2.5-flash** — most reliable model for File Search (avoids Gemini 3 ThinkingConfig bugs)
8. **Tune chunking per content type** — FAQ content benefits from smaller chunks; long-form from larger
9. **Always pass `force: true` on delete** — prevents errors from active document references
10. **Implement operation timeout** — uploads can hang; add a timeout (e.g., 5 min) to polling loops

---

## Complete Working Example: JavaScript

```typescript
import { GoogleGenAI } from '@google/genai';

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

// 1. Create or find store
async function getOrCreateStore(displayName: string) {
  const pager = await ai.fileSearchStores.list({ config: { pageSize: 10 } });
  let page = pager.page;
  while (true) {
    for (const store of page) {
      if (store.displayName === displayName) return store;
    }
    if (!pager.hasNextPage()) break;
    page = await pager.nextPage();
  }
  return await ai.fileSearchStores.create({ config: { displayName } });
}

// 2. Upload via Files API import (avoids 503 bug)
async function uploadDocument(storeName: string, filePath: string) {
  const fileRef = await ai.files.upload({ file: filePath });
  let op = await ai.fileSearchStores.importFile({
    fileSearchStoreName: storeName,
    fileName: fileRef.name!,
  });

  const timeout = Date.now() + 5 * 60 * 1000; // 5 min timeout
  while (!op.done) {
    if (Date.now() > timeout) throw new Error('Upload timed out');
    await new Promise((r) => setTimeout(r, 2000));
    op = await ai.operations.get({ operation: op });
  }
  return op;
}

// 3. Query with citations
async function query(
  storeName: string,
  question: string,
  metadataFilter?: string,
  topK = 5,
) {
  const response = await ai.models.generateContent({
    model: 'gemini-2.5-flash',
    contents: question,
    config: {
      tools: [
        {
          fileSearch: {
            fileSearchStoreNames: [storeName],
            top_k: topK,
            ...(metadataFilter && { metadataFilter }),
          },
        },
      ],
    },
  });

  const grounding = response.candidates?.[0]?.groundingMetadata;
  return {
    text: response.text,
    citations:
      grounding?.groundingChunks?.map((c) => ({
        title: c.retrievedContext?.title,
        text: c.retrievedContext?.text,
      })) ?? [],
  };
}

// Usage
const store = await getOrCreateStore('my-docs');
await uploadDocument(store.name!, '/path/to/manual.pdf');
const result = await query(store.name!, 'How do I install the software?');
console.log(result.text);
console.log('Sources:', result.citations);
```
