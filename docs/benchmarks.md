# Benchmarks

Use the scripts in `benchmarks/` to measure the current implementation before and after major changes.

## Current benchmark targets

- registry/discovery overhead
- tool-call dispatch overhead
- auth/policy hook overhead
- schema generation latency for larger handlers

Benchmarks in this repository are intentionally local and reproducible; they are meant for regression tracking, not public bragging numbers.
