# AI-agent GraphQL input: query text versus variable data

A released Rapid7 Bulk Export MCP function inserted an export identifier into GraphQL query text. Its replacement passes that identifier separately as a variable. This offline patch comparison uses both exact function extracts, a real GraphQL parser, and an invented in-memory schema to inspect the difference.

For the selected harmless crafted identifier, the original produces three root selections and two export lookups. The fixed function produces only the intended export selection and passes the entire identifier as one value. It **does not reject that identifier**.

## Reproduce

Python3.9+; tested with Python3.11.6 and graphql-core3.2.6.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python experiment.py
python -m unittest -v
```

Dependency installation needs package access. The experiment and tests thereafter require no network, API credentials, model, MCP client, or real backend. Runtime values for endpoint and API key are both None; no HTTP function is imported.

The experiment rewrites artifacts/run.json, artifacts/mutations.json and evidence.md deterministically. The test suite compares a fresh run with the saved run artifact. artifacts/tests.json records the reviewed validation run.

## Hypothesis and threat model

Assume an upstream client can select export_id, potentially after reading untrusted text. No attempt is made to persuade a model. The host, parser, exact extracts and harness remain trusted.

Hypothesis: embedding that value into query text can turn punctuation into GraphQL structure; binding it as an ID variable preserves the query structure and the whole string value.

The control is get_export_status from v0.6.1. The intervention is the released v0.6.2 replacement, not an invented approval gate. Only the send_graphql_request global is replaced, with a function that captures arguments, parses/validates a GraphQL document and runs it against an invented schema. Every export lookup returns synthetic records and logs its exact ID. There are no external writes or requests.

## Results

Ten chosen identifiers, two versions,20 rows. These are fixture counts, not attack rates.

| Observation | Original v0.6.1 | Fixed v0.6.2 |
|---|---|---|
| Selected crafted marker case: root response keys | export, marker, spare | export |
| Same case: export lookup arguments | demo, demo | one entire crafted string |
| Ordinary demo identifier | one lookup, expected synthetic result | same lookup and result |
| Exact single identifier across chosen fixtures | 5/10 | 10/10 |
| Parse failures | 2/10 | 0/10 |

The two punctuation-bearing marker fixtures add selections in the original. Two ordinary punctuation cases fail parsing. A backslash-n case parses but changes the identifier into one containing an actual newline. These are different outcomes, kept separate in the [full evidence](evidence.md).

The local fixed query text is identical across all ten identifiers. The fixed version accepts even a made-up nonexistent ID because this lab's resolver accepts every string. That is a deliberate scope demonstration, not proof that the real API accepts it.

Eight focused tests pass. Two deliberate regressions are caught: reintroducing interpolation and omitting required variables. See [run JSON](artifacts/run.json), [mutation evidence](artifacts/mutations.json), and [test record](artifacts/tests.json).

## Technical walkthrough

The fixed document contains export(id: $exportId); the variables object contains the caller's original string. The GraphQL engine parses the document first and treats the bound ID as a scalar value. It does not parse that scalar a second time as query syntax.

The selected fixture closes the old quoted argument, completes the initial selection, adds an aliased __typename field, and opens a second export selection. In this invented schema __typename yields only the string Query. No real schema introspection or external data retrieval occurs. The exact input, complete request documents, variables, parsed root fields, response objects and resolver IDs are all preserved in run.json and the paired trace in evidence.md.

The quoted crafted twin retains the same syntax characters despite a prose prefix. It tests syntax handling, not whether an agent understands quotations. The ordinary demo value is the legitimate operation control. Unicode, empty strings and harmless marker words are additional data-preservation controls.

The oracle is the real parser plus observable in-memory resolver inputs, not a substring search for a dangerous-looking word. Critical tests independently assert exact root structure, marker response and lookup arguments. Missing-variable regression fails before resolver work; interpolation regression changes root structure.

## Source provenance and adaptation

- [Maintainer PR47](https://github.com/rapid7/rapid7-bulk-export-mcp/pull/47) describes the defect, fix and limited existing-account scope.
- [Released v0.6.2](https://github.com/rapid7/rapid7-bulk-export-mcp/releases/tag/v0.6.2) includes the fix.
- Original commit:3c5ecc1b6bfad8014e815f632dd302d2759dddb5.
- Fixed commit:a14e4ff84cbbcc09c565f425f60f83c5d1bb631b.
- [Source manifest](vendor/source.json) records immutable source URLs, Git blob hashes, whole-module SHA256 hashes, line spans and exact extract hashes.
- vendor/original.py and vendor/fixed.py contain byte-exact get_export_status functions. The full module is not imported. Its networking imports and implementation are absent.
- Upstream MIT license is preserved in vendor/LICENSE. graphql-core is a separately installed dependency.

To independently verify extraction, retrieve src/export_manager.py at the manifest's commits, verify its whole-file hash, select the stated inclusive line span and compare the extract hash. Local validation performed that comparison before publication.

## Limits and engineering implication

This establishes the code/data boundary for the chosen released functions, fixtures and local schema. It is not a live-model result, MCP transport test, real Rapid7 response, current deployment assessment or end-to-end exploit. No attack frequency, cross-tenant access or privilege escalation is measured. The upstream maintainer explicitly limits the issue to the operator's existing authenticated scope.

Variable binding prevents these string values from becoming query grammar. It does not check that an ID exists, belongs to the operator or was authorized for this task. Those need separate backend checks. A real backend could reject these strings without evaluating the same synthetic data; that was not tested.

For agent-tool builders: keep query structure fixed, pass caller values as variables, then independently authorize the requested resource. Add regression checks of both parsed query structure and exact bound values, with a normal identifier as a control.
