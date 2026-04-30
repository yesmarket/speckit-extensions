---
name: plan-from-swagger
description: Use when the user wants to create an implementation plan from a SwaggerHub OpenAPI spec — e.g. "plan from swagger <url>", "/speckit-extensions:plan-from-swagger <url>". Fetches the OpenAPI spec via the fetch-swagger MCP server and pipes it into /speckit.plan to produce an implementation plan.
user-invocable: true
argument-hint: <swaggerhub-url> [additional-input]
---

# plan-from-swagger

Fetch an OpenAPI spec from SwaggerHub and use its content as context for `/speckit.plan`.

## Arguments

`$ARGUMENTS` contains: `<swaggerhub-url> [additional-input]`

- `swaggerhub-url` (required): URL to a SwaggerHub API spec, e.g. `https://api.swaggerhub.com/apis/MyOrg/MyAPI/1.0.0`
- `additional-input` (optional): Extra context or instructions to pass alongside the spec

## Steps

### 1. Parse Arguments

Extract the SwaggerHub URL (first whitespace-delimited token from `$ARGUMENTS`) and any additional input (everything after it).

### 2. Resolve the API Key

The SwaggerHub API requires an `Authorization` header containing the API key.

1. Check whether `SWAGGERHUB_API_KEY` is available in the environment (it is injected into the fetch-swagger MCP server process via the plugin's MCP config).
2. If it is **not** available, use MCP elicitation to request it from the user before proceeding. Store the value in session memory so it is not requested again during this session.
3. Use the resolved key as the value for the `Authorization` header on every SwaggerHub request in this session.

### 3. Fetch the OpenAPI Spec

Using the fetch-swagger MCP server, make a GET request to the SwaggerHub URL with the following header:

```
Authorization: <SWAGGERHUB_API_KEY>
```

Request the response in JSON format (append `?format=json` to the URL if a format parameter is not already present). If the server returns a resolve/dereference option (e.g. `?resolve=true`), prefer using it to receive a fully-resolved spec without `$ref` pointers.

### 4. Compose Context

Format the retrieved spec into a context block:

```
SwaggerHub API Spec: <url>

OpenAPI Spec:
<full spec content as returned>
```

Append any additional input from `$ARGUMENTS` after the above block.

### 5. Invoke /speckit.plan

Pass the composed context block as the feature description to `/speckit.plan`.
