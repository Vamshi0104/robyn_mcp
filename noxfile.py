from __future__ import annotations

import nox


PYTHONS = ["3.10", "3.11", "3.12"]
ROBYN_VERSIONS = ["0.79.0", "0.81.0"]


@nox.session(python=PYTHONS)
def tests(session: nox.Session) -> None:
    session.install("-e", ".[dev]")
    session.run("pytest")


@nox.session(python=PYTHONS)
def lint(session: nox.Session) -> None:
    session.install("-e", ".[dev]")
    session.run("ruff", "check", ".")


@nox.session(python=PYTHONS)
@nox.parametrize("robyn_version", ROBYN_VERSIONS)
def compat(session: nox.Session, robyn_version: str) -> None:
    session.install("-e", ".[dev]", f"robyn=={robyn_version}")
    session.run("python", "-m", "robyn_mcp.cli", "runtime", "--json")
    session.run("pytest", "tests/test_phase10_cli.py", "tests/test_http_dispatch.py")


@nox.session(python="3.11")
def docs(session: nox.Session) -> None:
    session.install("-e", ".[docs]")
    session.run("mkdocs", "build", "--strict")
