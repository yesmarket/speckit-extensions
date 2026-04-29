---
name: plan-from-confluence
description: Use when the user wants to create an implementation plan from a Confluence page — e.g. "plan from confluence <url>", "/speckit-extensions:plan-from-confluence <url>". Fetches the page and all child pages via the Atlassian MCP server and feeds each page's content individually into /speckit.plan.
user-invocable: true
argument-hint: <confluence-url> [additional-input]
---

# plan-from-confluence

Fetch a Confluence page and its full child hierarchy, then feed each page into `/speckit.plan` one at a time.

## Arguments

`$ARGUMENTS` contains: `<confluence-url> [additional-input]`

- `confluence-url` (required): URL to a Confluence page, e.g. `https://mycompany.atlassian.net/wiki/spaces/PROJ/pages/123456789/Page+Title`
- `additional-input` (optional): Extra context or instructions to pass as a separate invocation of `/speckit.plan`

## Steps

### 1. Parse Arguments

Extract the Confluence URL (first whitespace-delimited token from `$ARGUMENTS`) and any additional input (everything after it).

### 2. Parse the Confluence URL

From the URL, extract:

- **spaceKey**: the path segment following `/spaces/`, e.g. `PROJ`
- **pageId**: the numeric path segment following `/pages/`, e.g. `123456789`

Example URL structure: `https://<domain>/wiki/spaces/<spaceKey>/pages/<pageId>/<optional-title>`

### 3. Fetch the Root Page

**IMPORTANT: Only perform read operations against Confluence. Never create, edit, or delete pages, comments, or any other Confluence resources.**

Using the Atlassian MCP server, fetch the root page content by `pageId`. Retrieve the full page body (storage or view format).

### 4. Collect All Pages in the Hierarchy

Recursively collect all descendant pages under the root page:

1. Fetch the direct children of the root page using its `pageId`.
2. For each child page, fetch its full content.
3. Repeat recursively for each child's children until no further descendants exist.

Collect all pages (root + all descendants) as an ordered list, traversed depth-first (parent before its children).

### 5. Feed Each Page into /speckit.plan

For each page in the collected list, compose a context block and invoke `/speckit.plan` with it — one invocation per page:

```
Confluence Page: <pageId>
Space: <spaceKey>
Title: <page title>
URL: <page URL or canonical link>

Content:
<full page body>
```

Invoke `/speckit.plan` once per page, passing its context block. Do not batch multiple pages into a single invocation — each page must be a separate call.

### 6. Pass Additional Input (if provided)

If `additional-input` was supplied in `$ARGUMENTS`, make one final invocation of `/speckit.plan` with that content as the context. This is a separate call from the per-page invocations above.
