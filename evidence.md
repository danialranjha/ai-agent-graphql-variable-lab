# Exact local evidence

Ten chosen identifiers, two released-function versions, 20 rows. No sampled attack rates.
A real GraphQL parser and invented in-memory schema are used. No model or real API.

| Fixture | Original parse | Original root response keys | Original exact ID | Fixed exact ID |
|---|---|---|---|---|
| ordinary | True | export | True | True |
| unicode | True | export | True | True |
| empty | True | export | True | True |
| plain_marker_words | True | export | True | True |
| quote | False | (parse failed) | False | True |
| backslash_n | True | export | False | True |
| literal_newline | False | (parse failed) | False | True |
| closing_brace | True | export | True | True |
| marker_selection | True | export, marker, spare | False | True |
| quoted_crafted_twin | True | export, marker, spare | False | True |

## Paired marker trace
The exact same string is sent to each version. Original has three root selections; fixed has one.
The extra marker asks only for the invented Query type name. No real schema information is queried.
Original executes two export lookups for demo. Fixed executes one lookup for the entire crafted string.
Fixed does not reject this ID. Variable binding keeps it data; identifier authorization is a separate problem.

### original
Request:
```json
{
  "query": "\n    {\n      export(id: \"demo\") { id status result { prefix urls } } marker: __typename spare: export(id: \"demo\") {\n        id\n        status\n        dataset\n        timestamp\n        result {\n          prefix\n          urls\n        }\n      }\n    }\n    ",
  "variables": null
}
```
Observed local result:
```json
{
  "root_fields": [
    {
      "field": "export",
      "response_key": "export"
    },
    {
      "field": "__typename",
      "response_key": "marker"
    },
    {
      "field": "export",
      "response_key": "spare"
    }
  ],
  "resolver_ids": [
    "demo",
    "demo"
  ],
  "data": {
    "export": {
      "id": "demo",
      "status": "COMPLETE",
      "result": [
        {
          "prefix": "fixture",
          "urls": []
        }
      ]
    },
    "marker": "Query",
    "spare": {
      "id": "demo",
      "status": "COMPLETE",
      "dataset": "synthetic",
      "timestamp": "fixed",
      "result": [
        {
          "prefix": "fixture",
          "urls": []
        }
      ]
    }
  }
}
```

### fixed
Request:
```json
{
  "query": "\n    query GetExportStatus($exportId: ID!) {\n      export(id: $exportId) {\n        id\n        status\n        dataset\n        timestamp\n        result {\n          prefix\n          urls\n        }\n      }\n    }\n    ",
  "variables": {
    "exportId": "demo\") { id status result { prefix urls } } marker: __typename spare: export(id: \"demo"
  }
}
```
Observed local result:
```json
{
  "root_fields": [
    {
      "field": "export",
      "response_key": "export"
    }
  ],
  "resolver_ids": [
    "demo\") { id status result { prefix urls } } marker: __typename spare: export(id: \"demo"
  ],
  "data": {
    "export": {
      "id": "demo\") { id status result { prefix urls } } marker: __typename spare: export(id: \"demo",
      "status": "COMPLETE",
      "dataset": "synthetic",
      "timestamp": "fixed",
      "result": [
        {
          "prefix": "fixture",
          "urls": []
        }
      ]
    }
  }
}
```

## Limits
The local export resolver deliberately accepts every string. No real ID existence, access policy, tenant boundary, network, authentication or MCP/model behavior is measured. Ordinary punctuation becoming a parse error is not successful additional-field injection. Escaped characters may also change a parsed identifier without adding a field. The quoted crafted twin contains the same punctuation and is not a semantic intent detector test.
