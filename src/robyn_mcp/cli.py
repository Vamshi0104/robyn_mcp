from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from robyn_mcp.core.compat import build_compatibility_report
from robyn_mcp.core.config import RobynMCPConfig
from robyn_mcp.core.models import RequestContext
from robyn_mcp.core.openapi_gateway import (
    OpenAPIGatewayConfig,
    OpenAPIGatewayInvoker,
    find_operation,
)
from robyn_mcp.core.openapi_source import OpenAPIOperationSource, inspect_openapi_source
from robyn_mcp.install_notice import build_install_banner
from robyn_mcp.testing.announcement import build_announcement_bundle
from robyn_mcp.testing.benchmark_compare import compare_benchmarks
from robyn_mcp.testing.benchmark_publish import write_benchmark_markdown
from robyn_mcp.testing.doctor import run_doctor
from robyn_mcp.testing.endpoint_validator import EndpointValidator
from robyn_mcp.testing.launch_bundle import build_launch_bundle
from robyn_mcp.testing.marketplace_audit import audit_marketplace_assets
from robyn_mcp.testing.openapi_benchmark import benchmark_openapi_inspection
from robyn_mcp.testing.release_audit import audit_release_bundle
from robyn_mcp.testing.site_export import export_static_site


def _emit(payload: dict[str, Any], *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
            else:
                print(f"{key}: {value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="robyn-mcp", description="robyn_mcp CLI utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    runtime = sub.add_parser("runtime", help="Print runtime and compatibility information")
    runtime.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    validate = sub.add_parser("validate-endpoint", help="Validate a live MCP endpoint")
    validate.add_argument("endpoint", help="MCP endpoint URL, e.g. http://localhost:8080/mcp")
    validate.add_argument("--timeout", type=float, default=5.0, help="Request timeout in seconds")
    validate.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    tools = sub.add_parser("list-tools", help="List tools from a live MCP endpoint")
    tools.add_argument("endpoint", help="MCP endpoint URL")
    tools.add_argument("--timeout", type=float, default=5.0)
    tools.add_argument("--json", action="store_true")

    inspect = sub.add_parser("inspect", help="Inspect a live MCP endpoint with richer tool detail")
    inspect.add_argument("endpoint", help="MCP endpoint URL")
    inspect.add_argument("--timeout", type=float, default=5.0)
    inspect.add_argument("--json", action="store_true")

    openapi = sub.add_parser(
        "inspect-openapi", help="Inspect an OpenAPI JSON/YAML document as future MCP operations"
    )
    openapi.add_argument("source", help="OpenAPI file path or URL")
    openapi.add_argument("--json", action="store_true")

    invoke_openapi = sub.add_parser(
        "invoke-openapi", help="Invoke one OpenAPI operation against an upstream base URL"
    )
    invoke_openapi.add_argument("source", help="OpenAPI file path or URL")
    invoke_openapi.add_argument(
        "--upstream", required=True, help="Upstream base URL, e.g. http://localhost:8000"
    )
    invoke_openapi.add_argument("--operation", required=True, help="Operation name or operationId")
    invoke_openapi.add_argument("--args", default="{}", help="JSON object of operation arguments")
    invoke_openapi.add_argument(
        "--header", action="append", default=[], help="Static upstream header as Name: value"
    )
    invoke_openapi.add_argument("--json", action="store_true")

    bench_openapi = sub.add_parser(
        "benchmark-openapi", help="Benchmark OpenAPI inspection and contract scoring"
    )
    bench_openapi.add_argument("source", help="OpenAPI file path or URL")
    bench_openapi.add_argument("--iterations", type=int, default=25)
    bench_openapi.add_argument("--json", action="store_true")

    doctor = sub.add_parser(
        "doctor", help="Run MCP conformance-oriented checks against a live endpoint"
    )
    doctor.add_argument("endpoint", help="MCP endpoint URL")
    doctor.add_argument("--timeout", type=float, default=5.0)
    doctor.add_argument("--json", action="store_true")

    snapshot = sub.add_parser(
        "debug-snapshot", help="Create a local debugger snapshot for docs or bug reports"
    )
    snapshot.add_argument("endpoint", help="MCP endpoint URL")
    snapshot.add_argument("--timeout", type=float, default=5.0)
    snapshot.add_argument("--out", default="robyn_mcp_debug_snapshot.json", help="Output JSON path")

    scaffold = sub.add_parser("launch-checklist", help="Print the launch checklist doc path")
    scaffold.add_argument("--json", action="store_true")

    compare = sub.add_parser(
        "compare-benchmarks", help="Compare robyn_mcp and fastapi_mcp benchmark result JSON files"
    )
    compare.add_argument("robyn", help="Path to robyn_mcp benchmark JSON")
    compare.add_argument("fastapi", help="Path to fastapi_mcp benchmark JSON")
    compare.add_argument("--json", action="store_true")

    publish = sub.add_parser(
        "publish-benchmarks", help="Render benchmark comparison markdown from two JSON result files"
    )
    publish.add_argument("robyn", help="Path to robyn_mcp benchmark JSON")
    publish.add_argument("fastapi", help="Path to fastapi_mcp benchmark JSON")
    publish.add_argument("--out", default="benchmark_report.md", help="Output markdown path")

    release = sub.add_parser(
        "release-bundle", help="Print release asset locations for the final launch work"
    )
    release.add_argument("--json", action="store_true")

    audit = sub.add_parser("release-audit", help="Validate version consistency and release assets")
    audit.add_argument(
        "--project-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Project root to audit",
    )
    audit.add_argument("--json", action="store_true")

    bundle = sub.add_parser(
        "build-launch-bundle", help="Copy launch-ready assets plus checksums into one folder"
    )
    bundle.add_argument("--project-root", default=str(Path(__file__).resolve().parents[2]))
    bundle.add_argument("--out", default="dist/launch_bundle")
    bundle.add_argument("--json", action="store_true")

    site = sub.add_parser(
        "export-site", help="Export the static launch site assets into a standalone folder"
    )
    site.add_argument("--project-root", default=str(Path(__file__).resolve().parents[2]))
    site.add_argument("--out", default="dist/site_export")
    site.add_argument("--json", action="store_true")

    announce = sub.add_parser(
        "build-announcement", help="Generate launch announcement assets and summary files"
    )
    announce.add_argument("--project-root", default=str(Path(__file__).resolve().parents[2]))
    announce.add_argument("--out", default="dist/announcement")
    announce.add_argument("--json", action="store_true")

    market = sub.add_parser(
        "marketplace-audit", help="Validate marketplace submission assets for editor extensions"
    )
    market.add_argument("--project-root", default=str(Path(__file__).resolve().parents[2]))
    market.add_argument("--json", action="store_true")

    sub.add_parser("install-note", help="Print install banner and package metadata")

    # NEW: trace / playground helpers
    trace = sub.add_parser(
        "trace-endpoint",
        help="Fetch tool metrics and recent tool trace events from a live MCP endpoint",
    )
    trace.add_argument("endpoint", help="MCP endpoint URL")
    trace.add_argument("--timeout", type=float, default=5.0)
    trace.add_argument("--json", action="store_true")

    playground = sub.add_parser(
        "playground-url", help="Print likely playground URL for an MCP endpoint"
    )
    playground.add_argument("endpoint", help="MCP endpoint URL")
    playground.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "runtime":
        payload = build_compatibility_report(RobynMCPConfig())
        return _emit(payload, as_json=args.json)

    if args.command == "validate-endpoint":
        report = EndpointValidator(args.endpoint, timeout=args.timeout).validate()
        payload = report.as_dict()
        return _emit(payload, as_json=args.json)

    if args.command == "list-tools":
        report = EndpointValidator(args.endpoint, timeout=args.timeout).validate()
        payload = report.as_dict()
        payload["tools"] = report.fetch_tools() if report.ok else []
        return _emit(payload, as_json=args.json)

    if args.command == "inspect":
        report = EndpointValidator(args.endpoint, timeout=args.timeout).validate()
        payload = report.as_dict()
        payload["tools"] = report.fetch_tools() if report.ok else []
        payload["summary"] = {
            "toolNames": [tool.get("name") for tool in payload["tools"]],
            "readOnlyTools": [
                tool.get("name")
                for tool in payload["tools"]
                if (tool.get("annotations") or {}).get("readOnlyHint")
            ],
        }
        return _emit(payload, as_json=args.json)

    if args.command == "inspect-openapi":
        payload = inspect_openapi_source(args.source)
        return _emit(payload, as_json=args.json)

    if args.command == "invoke-openapi":
        raw_args = json.loads(args.args)
        if not isinstance(raw_args, dict):
            raise SystemExit("--args must be a JSON object")
        static_headers: dict[str, str] = {}
        for header in args.header:
            if ":" not in header:
                raise SystemExit("--header values must be formatted as 'Name: value'")
            key, value = header.split(":", 1)
            static_headers[key.strip()] = value.strip()
        operations = OpenAPIOperationSource.from_source(args.source).discover()
        operation = find_operation(operations, args.operation)
        invoker = OpenAPIGatewayInvoker(
            OpenAPIGatewayConfig(
                upstream_base_url=args.upstream,
                static_headers=static_headers,
            )
        )
        result = asyncio.run(invoker.invoke(operation, raw_args, RequestContext()))
        payload = {
            "operation": operation.name,
            "statusCode": result.status_code,
            "headers": result.headers,
            "value": result.value,
            "metadata": result.metadata,
        }
        return _emit(payload, as_json=args.json)

    if args.command == "benchmark-openapi":
        payload = benchmark_openapi_inspection(args.source, iterations=args.iterations)
        return _emit(payload, as_json=args.json)

    if args.command == "doctor":
        payload = run_doctor(args.endpoint, timeout=args.timeout).as_dict()
        return _emit(payload, as_json=args.json)

    if args.command == "debug-snapshot":
        report = EndpointValidator(args.endpoint, timeout=args.timeout).validate()
        payload = report.as_dict()
        payload["tools"] = report.fetch_tools() if report.ok else []
        out_path = Path(args.out)
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(str(out_path))
        return 0

    if args.command == "launch-checklist":
        root = Path(__file__).resolve().parents[2]
        payload = {"launchChecklist": str(root / "docs" / "launch.md")}
        return _emit(payload, as_json=args.json)

    if args.command == "compare-benchmarks":
        payload = compare_benchmarks(args.robyn, args.fastapi)
        return _emit(payload, as_json=args.json)

    if args.command == "publish-benchmarks":
        out = write_benchmark_markdown(args.robyn, args.fastapi, args.out)
        print(out)
        return 0

    if args.command == "release-bundle":
        root = Path(__file__).resolve().parents[2]
        payload = {
            "docs": str(root / "docs"),
            "releaseGuide": str(root / "docs" / "release.md"),
            "quickstart": str(root / "docs" / "quickstart.md"),
            "examples": str(root / "docs" / "examples.md"),
            "openapi": str(root / "docs" / "openapi_gateway.md"),
            "compatibility": str(root / "docs" / "compatibility.md"),
            "assets": str(root / "docs" / "assets"),
            "website": str(root / "index.html"),
            "releaseScript": str(root / "scripts" / "release_final.sh"),
        }
        return _emit(payload, as_json=args.json)

    if args.command == "release-audit":
        payload = audit_release_bundle(args.project_root)
        return _emit(payload, as_json=args.json)

    if args.command == "build-launch-bundle":
        payload = build_launch_bundle(args.project_root, args.out).as_dict()
        return _emit(payload, as_json=args.json)

    if args.command == "export-site":
        payload = export_static_site(args.project_root, args.out)
        return _emit(payload, as_json=args.json)

    if args.command == "build-announcement":
        payload = build_announcement_bundle(args.project_root, args.out).as_dict()
        return _emit(payload, as_json=args.json)

    if args.command == "marketplace-audit":
        payload = audit_marketplace_assets(args.project_root)
        return _emit(payload, as_json=args.json)

    if args.command == "install-note":
        print(build_install_banner())
        return 0

    if args.command == "trace-endpoint":
        report = EndpointValidator(args.endpoint, timeout=args.timeout).validate()
        payload = report.as_dict()
        metadata = {}
        if report.steps and isinstance(report.steps[0].payload, dict):
            metadata = report.steps[0].payload
        payload["toolMetrics"] = metadata.get("toolMetrics", {})
        payload["recentToolEvents"] = metadata.get("recentToolEvents", [])
        return _emit(payload, as_json=args.json)

    if args.command == "playground-url":
        endpoint = str(args.endpoint).rstrip("/")
        if endpoint.endswith("/mcp"):
            url = endpoint + "/playground"
        else:
            url = endpoint + "/mcp/playground"
        payload = {"playgroundUrl": url}
        return _emit(payload, as_json=args.json)

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
