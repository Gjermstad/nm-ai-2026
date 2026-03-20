# Tripletex API

- Version: `2.74.00`
- Format: `OAS3`
- Spec path: `/v2/openapi.json`
- Base URL: `https://kkpqfuj-amager.tripletex.dev/v2`

## Usage

Download the spec `openapi.json` file. It is an `OpenAPI Specification`.

Generating a client can easily be done using tools like `openapi-generator` or `swagger-codegen`, or others that accept `OpenAPI Specification` specs.

For `swagger-codegen` it is recommended to use the flag `--removeOperationIdPrefix`. Unique operation IDs are about to be introduced to the spec, and this ensures forward compatibility — and results in less verbose generated code.

Please note that `Tripletex` offers several packages. Some endpoints are only supported in certain packages. You can see the `Tripletex` packages here.

## Overview

- Partial resource updating is done using the `PUT` method with optional fields instead of the `PATCH` method.
- Actions or commands are represented in the RESTful path with a prefixed `:`. Example: `/hours/123/:approve`.
- Summaries or aggregated results are represented in the RESTful path with a prefixed `>`. Example: `/hours/>thisWeeksBillables`.
- Request ID is a key found in all responses in the header with the name `x-tlx-request-id`. For validation and error responses it is also in the response body. If additional log information is absolutely necessary, support can locate the key value.
- `version` is a revision number found on all persisted resources. If included, it will prevent your `PUT`/`POST` from overriding any updates to the resource since your `GET`.
- `Date` follows the `ISO 8601` standard, meaning the format `YYYY-MM-DD`.
- `DateTime` follows the `ISO 8601` standard, meaning the format `YYYY-MM-DDThh:mm:ss`.
- Searching is done by entering values in the optional fields for each API call. The values fall into the following categories: `range`, `in`, `exact`, and `like`.
- Missing fields or even no response data can occur because result objects and fields are filtered on authorization.
- See `GitHub` for more documentation, code examples, changelog, and more.
- See `Tripletex for developers` for more practical information, support, updates, and access form.

## Authentication

Read more here.

### Tokens

The `Tripletex API` uses `3` different tokens:

- `consumerToken` is a token provided to the consumer by `Tripletex` after the `API 2.0` registration is completed.
- `employeeToken` is a token created by an administrator in your `Tripletex` account via the user settings and the tab `"API access"`. Each employee token must be given a set of entitlements.
- `sessionToken` is the token from `/token/session/:create`, which requires a `consumerToken` and an `employeeToken` created with the same consumer token, but not an authentication header.

Authentication is done via `Basic` access authentication.

- `username` is used to specify what company to access.
- `0` or blank means the company of the employee.
- Any other value means accountant clients. Use `/company/>withLoginAccess` to get a list of those.
- `password` is the `sessionToken`.

If you need to create the header yourself, use:

```http
Authorization: Basic <encoded token>
```

Where `encoded token` is the string `<target company id or 0>:<your session token>` Base64 encoded.

## Tags

- `[BETA]` means the endpoint is a beta endpoint and can be subject to change.
- `[DEPRECATED]` means that `Tripletex` intends to remove or change this feature or capability in a future major API release. Use of this feature is discouraged.

## Fields

Use the `fields` parameter to specify which fields should be returned. This also supports fields from sub-elements, done via `<field>(<subResourceFields>)`. `*` means all fields for that resource.

Example values:

- `project,activity,hours` returns `{project:..., activity:...., hours:...}`.
- `project` returns `"project": { "id": 12345, "url": "tripletex.no/v2/projects/12345" }`.
- `project(*)` returns `"project": { "id": 12345, "name":"ProjectName", "number":..., "startDate": "2013-01-07" }`.
- `project(name)` returns `"project": { "name":"ProjectName" }`.
- All resources and some sub-resources: `*,activity(name),employee(*)`.

## Sorting

Use the `sorting` parameter to specify sorting. It takes a comma-separated list, where a `-` prefix denotes descending. You can sort by sub-object with the following format: `<field>.<subObjectField>`.

Example values:

- `date`
- `project.name`
- `project.name,-date`

## Changes

To get the changes for a resource, `changes` has to be explicitly specified as part of the `fields` parameter, for example `*,changes`.

There are currently two types of change available:

- `CREATE` for when the resource was created
- `UPDATE` for when the resource was updated

> Note: For objects created prior to October 24th 2018, the list may be incomplete, but will always contain the `CREATE` and the last change (if the object has been changed after creation).

## Rate limiting

Rate limiting is performed on the API calls for an employee for each API consumer. Status regarding the rate limit is returned as headers:

- `X-Rate-Limit-Limit` — The number of allowed requests in the current period
- `X-Rate-Limit-Remaining` — The number of remaining requests
- `X-Rate-Limit-Reset` — The number of seconds left in the current period

Once the rate limit is hit, all requests will return `HTTP 429` for the remainder of the current period.

## Response envelope

### Multiple values

```json
{
  "fullResultSize": 123,
  "from": 0,
  "count": 100,
  "versionDigest": "abc123",
  "values": [{}, {}, {}]
}
```

- `fullResultSize` — number `[DEPRECATED]`
- `from` — paging starting from
- `count` — paging count
- `versionDigest` — hash of full result, `null` if no result
- `values` — array of objects

### Single value

```json
{
  "value": {}
}
```

### WebHook envelope

```json
{
  "subscriptionId": 123,
  "event": "object.verb",
  "id": 456,
  "value": {}
}
```

- `subscriptionId` — subscription ID
- `event` — as listed from `/v2/event/`
- `id` — ID of object this event is for
- `value` — single object, `null` if `object.deleted`

### Error/warning envelope

```json
{
  "status": 422,
  "code": 15000,
  "message": "Validation failed",
  "link": "https://example.com/docs",
  "developerMessage": "Missing required field",
  "validationMessages": [
    {
      "field": "name",
      "message": "Name is required"
    }
  ],
  "requestId": "abc-123"
}
```

- `status` — `HTTP` status code
- `code` — internal status code of event
- `message` — basic feedback message in your language
- `link` — link to docs
- `developerMessage` — more technical message
- `validationMessages` — list of validation messages, can be `null`
- `requestId` — same as `x-tlx-request-id`

## Status codes / Error codes

| HTTP status | Meaning | Internal codes |
|---|---|---|
| `200 OK` | Success | — |
| `201 Created` | From `POST`s that create something new | — |
| `204 No Content` | When there is no answer, for example `/:anAction` or `DELETE` | — |
| `400 Bad Request` | Bad request | `4000`, `11000`, `12000`, `24000` |
| `401 Unauthorized` | Authentication is required and has failed or was not provided | `3000` |
| `403 Forbidden` | `AuthorisationManager` says no | `9000` |
| `404 Not Found` | Resource does not exist | `6000` |
| `409 Conflict` | Edit conflict or similar | `7000`, `8000`, `10000`, `14000` |
| `422 Bad Request` | Required fields missing or malformed payload | `15000`, `16000`, `17000`, `18000`, `21000`, `22000`, `23000` |
| `429 Too Many Requests` | Rate limit hit | — |
| `500 Internal Error` | Unexpected condition with no more specific message | `1000` |

### Internal code groups

- `4000` — Bad Request Exception
- `11000` — Illegal Filter Exception
- `12000` — Path Param Exception
- `24000` — Cryptography Exception
- `3000` — Authentication Exception
- `9000` — Security Exception
- `6000` — Not Found Exception
- `7000` — Object Exists Exception
- `8000` — Revision Exception
- `10000` — Locked Exception
- `14000` — Duplicate entry
- `15000` — Value Validation Exception
- `16000` — Mapping Exception
- `17000` — Sorting Exception
- `18000` — Validation Exception
- `21000` — Param Exception
- `22000` — Invalid JSON Exception
- `23000` — Result Set Too Large Exception
- `1000` — Exception

## Other

- [tripletex-api2 on GitHub](https://github.com/Tripletex/tripletex-api2)
- [Website: TripleTex for developers](https://developer.tripletex.no/docs/documentation/)
