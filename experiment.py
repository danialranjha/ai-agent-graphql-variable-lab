"""Offline released-function comparison. No HTTP implementation is imported."""
import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Dict
from graphql import build_schema, graphql_sync, parse, validate, __version__ as graphql_version

ROOT = Path(__file__).resolve().parent
SCHEMA_TEXT = """
type Part { prefix: String!, urls: [String!]! }
type Export { id: ID!, status: String!, dataset: String!, timestamp: String!, result: [Part!]! }
type Query { export(id: ID!): Export! }
"""
CRAFTED = 'demo") { id status result { prefix urls } } marker: __typename spare: export(id: "demo'
FIXTURES = [
    ("ordinary", "demo"),
    ("unicode", "café-東京"),
    ("empty", ""),
    ("plain_marker_words", "marker __typename"),
    ("quote", 'demo"note'),
    ("backslash_n", r"demo\nnext"),
    ("literal_newline", "demo\nnext"),
    ("closing_brace", "demo}note"),
    ("marker_selection", CRAFTED),
    ("quoted_crafted_twin", "This is a quoted test: " + CRAFTED),
]

def load_function(mode, sender):
    path = ROOT / "vendor" / (mode + ".py")
    code = path.read_text()
    tree = ast.parse(code)
    assert len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef)
    assert tree.body[0].name == "get_export_status"
    env = {"Dict": Dict, "Any": Any, "send_graphql_request": sender}
    exec(compile(tree, str(path), "exec"), env)
    return env["get_export_status"]

def run_case(mode, fixture, identifier, mutation=None):
    row = {"mode": mode, "fixture": fixture, "identifier": identifier}
    schema = build_schema(SCHEMA_TEXT)
    calls = []
    def export_resolver(obj, info, id):
        calls.append(id)
        return {"id": id, "status": "COMPLETE", "dataset": "synthetic",
                "timestamp": "fixed", "result": [{"prefix": "fixture", "urls": []}]}
    schema.get_type("Query").fields["export"].resolve = export_resolver

    def sender(*, endpoint, api_key, query, variables=None):
        assert endpoint is None and api_key is None
        if mutation == "omit_variables":
            variables = None
        row["request"] = {"query": query, "variables": variables}
        try:
            document = parse(query)
        except Exception as error:
            row.update(parse_ok=False, root_fields=[], validation_errors=[],
                       errors=[str(error)], data=None)
            raise ValueError("local GraphQL parse failed") from error
        fields = document.definitions[0].selection_set.selections
        row["root_fields"] = [{"field": f.name.value,
            "response_key": f.alias.value if f.alias else f.name.value} for f in fields]
        row["parse_ok"] = True
        row["validation_errors"] = [str(e) for e in validate(schema, document)]
        result = graphql_sync(schema, query, variable_values=variables)
        row["data"] = result.data
        row["errors"] = [str(e) for e in result.errors or []]
        if result.errors:
            raise ValueError("local GraphQL validation/execution failed")
        return {"data": result.data}
    actual_mode = "original" if mutation == "interpolate_again" else mode
    fn = load_function(actual_mode, sender)
    try:
        row["function_result"] = fn({"endpoint": None, "api_key": None}, identifier)
        row["function_error"] = None
    except Exception as error:
        row["function_result"] = None
        row["function_error"] = type(error).__name__ + ": " + str(error)
    row["resolver_ids"] = calls
    row["exact_single_identifier"] = calls == [identifier]
    return row

def fixed_contract(row, identifier):
    return (row["parse_ok"] and not row["errors"]
            and row["root_fields"] == [{"field": "export", "response_key": "export"}]
            and row["resolver_ids"] == [identifier]
            and row["request"]["variables"] == {"exportId": identifier}
            and row["function_error"] is None)

def run():
    rows = [run_case(mode, label, value) for label, value in FIXTURES
            for mode in ("original", "fixed")]
    assert all(fixed_contract(r, r["identifier"]) for r in rows if r["mode"] == "fixed")
    out = {"scope": "released function extracts; real local GraphQL parser; synthetic schema",
           "graphql_core": graphql_version, "fixture_count": len(FIXTURES),
           "row_count": len(rows), "schema": SCHEMA_TEXT, "rows": rows}
    return out

def mutations():
    checks = []
    for mutation in ("interpolate_again", "omit_variables"):
        row = run_case("fixed", "marker_selection", CRAFTED, mutation)
        detected = not fixed_contract(row, CRAFTED)
        assert detected, mutation
        checks.append({"mutation": mutation, "detected": detected,
                       "root_fields": row["root_fields"],
                       "resolver_ids": row["resolver_ids"], "errors": row["errors"]})
    return {"checks": checks, "all_detected": all(x["detected"] for x in checks)}

def write_artifacts():
    out = run()
    target = ROOT / "artifacts"
    target.mkdir(exist_ok=True)
    (target / "run.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    (target / "mutations.json").write_text(json.dumps(mutations(), indent=2) + "\n")
    lines = ["# Exact local evidence", "",
             "Ten chosen identifiers, two released-function versions, 20 rows. No sampled attack rates.",
             "A real GraphQL parser and invented in-memory schema are used. No model or real API.", "",
             "| Fixture | Original parse | Original root response keys | Original exact ID | Fixed exact ID |",
             "|---|---|---|---|---|"]
    for i in range(0, len(out["rows"]), 2):
        old, new = out["rows"][i:i+2]
        keys = ", ".join(f["response_key"] for f in old["root_fields"]) or "(parse failed)"
        lines.append(f"| {old['fixture']} | {old['parse_ok']} | {keys} | {old['exact_single_identifier']} | {new['exact_single_identifier']} |")
    lines += ["", "## Paired marker trace",
              "The exact same string is sent to each version. Original has three root selections; fixed has one.",
              "The extra marker asks only for the invented Query type name. No real schema information is queried.",
              "Original executes two export lookups for demo. Fixed executes one lookup for the entire crafted string.",
              "Fixed does not reject this ID. Variable binding keeps it data; identifier authorization is a separate problem.", ""]
    for r in out["rows"]:
        if r["fixture"] == "marker_selection":
            lines += ["### " + r["mode"], "Request:", "```json",
                      json.dumps(r["request"], indent=2, ensure_ascii=False), "```",
                      "Observed local result:", "```json",
                      json.dumps({k:r[k] for k in ("root_fields","resolver_ids","data")}, indent=2),
                      "```", ""]
    lines += ["## Limits", "The local export resolver deliberately accepts every string. No real ID existence, access policy, tenant boundary, network, authentication or MCP/model behavior is measured. Ordinary punctuation becoming a parse error is not successful additional-field injection. Escaped characters may also change a parsed identifier without adding a field. The quoted crafted twin contains the same punctuation and is not a semantic intent detector test."]
    (ROOT / "evidence.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"fixtures": len(FIXTURES), "rows": len(out["rows"]),
                      "fixed_contract_passes": 10, "mutations_detected": 2}))

if __name__ == "__main__":
    write_artifacts()
