---
name: plan-from-lucid
description: Use when the user wants to create an implementation plan from a Lucidchart diagram — e.g. "plan from lucid <url>", "/speckit-extensions:plan-from-lucid <url>". Fetches the diagram via the Lucidchart MCP server and pipes it into /speckit.plan to produce an implementation plan.
user-invocable: true
argument-hint: <lucid-url> [additional-input]
---

# plan-from-lucid

Fetch a Lucidchart diagram and use its content as context for `/speckit.plan`.

## Arguments

`$ARGUMENTS` contains: `<lucid-url> [additional-input]`

- `lucid-url` (required): URL to a Lucidchart document page, e.g. `https://lucid.app/lucidchart/9c028565-3df6-4c34-9db4-449bb5c7c20d/edit?page=4WDSdv3BMKuG`
- `additional-input` (optional): Extra context or instructions to include alongside the diagram

## Steps

### 1. Parse Arguments

Extract the Lucid URL (first whitespace-delimited token from `$ARGUMENTS`) and any additional input (everything after it).

### 2. Parse the Lucid URL

From the URL, extract:

- **documentId**: the GUID path segment between `/lucidchart/` and `/edit`, e.g. `9c028565-3df6-4c34-9db4-449bb5c7c20d`
- **pageId**: the value of the `page` query parameter, e.g. `4WDSdv3BMKuG`

If `pageId` is absent from the URL, omit it when calling the fetch tool (the server will default to the first page).

### 3. Fetch the Diagram

Using the Lucidchart MCP server, call its document fetch tool with `documentId` and `pageId`. Request the content in the most structured format available — prefer SVG or XML over raster images, as structured vector formats are more accurately interpreted by the AI. If the server returns a PNG image, use it as-is for visual analysis.

### 4. Compose Context

Format the retrieved diagram content into a context block:

```
Lucidchart Document: <documentId>
Page: <pageId>

Diagram:
<diagram content — SVG, XML, or image as returned by the MCP server>
```

Append any additional input from `$ARGUMENTS` after the above block.

### 5. Invoke /speckit.plan

Pass the composed context block as the feature description to `/speckit.plan`.
