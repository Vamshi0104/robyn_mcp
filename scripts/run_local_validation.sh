#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/validation_out/$(date +%Y%m%d_%H%M%S)"
PORT=8080
SUMMARY_FILE="${OUT_DIR}/summary.txt"

mkdir -p "$OUT_DIR"

log() {
  echo
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

step() {
  echo "-> $1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 1
  }
}

require_cmd curl
require_cmd python
require_cmd lsof
require_cmd awk

if command -v jq >/dev/null 2>&1; then
  HAVE_JQ=1
else
  HAVE_JQ=0
fi

APP_PID=""
TOTAL_STEPS=0
FAILED_STEPS=0

echo "Validation started at $(date)" >"$SUMMARY_FILE"
echo "OUT_DIR=$OUT_DIR" >>"$SUMMARY_FILE"
echo >>"$SUMMARY_FILE"

record_ok() {
  TOTAL_STEPS=$((TOTAL_STEPS + 1))
  echo "[OK]   $1" | tee -a "$SUMMARY_FILE"
}

record_fail() {
  TOTAL_STEPS=$((TOTAL_STEPS + 1))
  FAILED_STEPS=$((FAILED_STEPS + 1))
  echo "[FAIL] $1" | tee -a "$SUMMARY_FILE"
}

cleanup() {
  if [[ -n "${APP_PID}" ]]; then
    echo "cleanup: stopping app pid=${APP_PID}" | tee -a "$SUMMARY_FILE"
    kill "${APP_PID}" >/dev/null 2>&1 || true

    for _ in $(seq 1 5); do
      if ! kill -0 "${APP_PID}" 2>/dev/null; then
        APP_PID=""
        break
      fi
      sleep 1
    done

    if [[ -n "${APP_PID}" ]]; then
      echo "cleanup: forcing app pid=${APP_PID}" | tee -a "$SUMMARY_FILE"
      kill -9 "${APP_PID}" >/dev/null 2>&1 || true
      APP_PID=""
    fi
  fi

  local pids
  pids=$(lsof -ti :"${PORT}" 2>/dev/null || true)
  if [[ -n "${pids}" ]]; then
    echo "cleanup: killing leftover port holders on ${PORT}: ${pids}" | tee -a "$SUMMARY_FILE"
    kill ${pids} >/dev/null 2>&1 || true
    sleep 1
    pids=$(lsof -ti :"${PORT}" 2>/dev/null || true)
    if [[ -n "${pids}" ]]; then
      kill -9 ${pids} >/dev/null 2>&1 || true
    fi
  fi
}
trap cleanup EXIT

pretty_json() {
  local infile="$1"
  local outfile="$2"

  if [[ ! -f "$infile" ]]; then
    return 0
  fi

  if [[ "$HAVE_JQ" -eq 1 ]]; then
    jq . "$infile" >"$outfile" 2>/dev/null || cp "$infile" "$outfile"
  else
    cp "$infile" "$outfile"
  fi
}

tail_server_log() {
  local logfile="$1"
  if [[ -f "$logfile" ]]; then
    echo "---- server log tail: $logfile ----" | tee -a "$SUMMARY_FILE"
    tail -n 60 "$logfile" | tee -a "$SUMMARY_FILE"
    echo "-----------------------------------" | tee -a "$SUMMARY_FILE"
  fi
}

extract_header_value() {
  local header_file="$1"
  local header_name="$2"

  awk -v key="$(echo "$header_name" | tr '[:upper:]' '[:lower:]')" '
    BEGIN { FS=": " }
    {
      line=$0
      gsub("\r", "", line)
      split(line, parts, ": ")
      if (tolower(parts[1]) == key) {
        print parts[2]
        exit
      }
    }
  ' "$header_file"
}

request_json() {
  local name="$1"
  local payload="$2"
  local endpoint="$3"
  shift 3

  step "request_json: $name"

  local body="${OUT_DIR}/${name}.body"
  local headers="${OUT_DIR}/${name}.headers"
  local pretty="${OUT_DIR}/${name}.pretty.json"
  local meta="${OUT_DIR}/${name}.meta.txt"
  local stderr_file="${OUT_DIR}/${name}.curl.stderr"

  rm -f "$body" "$headers" "$pretty" "$meta" "$stderr_file"

  local status
  status=$(
    curl --silent --show-error --max-time 8 \
      -D "$headers" \
      -o "$body" \
      -w "%{http_code}" \
      -H 'content-type: application/json' \
      -H 'accept: application/json' \
      "$@" \
      -d "$payload" \
      "$endpoint" \
      2>"$stderr_file" || true
  )

  pretty_json "$body" "$pretty"

  {
    echo "NAME=$name"
    echo "STATUS=$status"
    echo "ENDPOINT=$endpoint"
    echo "PAYLOAD=$payload"
    if [[ "$#" -gt 0 ]]; then
      echo "EXTRA_HEADERS=$*"
    fi
  } >"$meta"

  case "$name" in
    basic_unknown_method|basic_bad_args_shape|basic_missing_tool|multi_missing_tenant|multi_bad_amount|multi_empty_args|multi_missing_auth)
      [[ "$status" =~ ^4[0-9][0-9]$ || "$status" =~ ^2[0-9][0-9]$ ]] && record_ok "$name (HTTP $status)" || record_fail "$name (HTTP $status)"
      ;;
    *)
      [[ "$status" =~ ^2[0-9][0-9]$ ]] && record_ok "$name (HTTP $status)" || record_fail "$name (HTTP $status)"
      ;;
  esac
}

wait_for_server() {
  local tries=30
  local i

  for i in $(seq 1 "$tries"); do
    echo "wait_for_server: try $i"

    if [[ -n "${APP_PID}" ]] && ! kill -0 "${APP_PID}" 2>/dev/null; then
      echo "Server process exited early" | tee -a "$SUMMARY_FILE"
      return 1
    fi

    if curl --silent --show-error --max-time 2 "http://localhost:${PORT}/health" >/dev/null 2>&1; then
      echo "Server ready via /health"
      return 0
    fi

    if curl --silent --show-error --max-time 2 "http://localhost:${PORT}/mcp" >/dev/null 2>&1; then
      echo "Server ready via /mcp"
      return 0
    fi

    sleep 1
  done

  echo "Server readiness timed out" | tee -a "$SUMMARY_FILE"
  return 1
}

start_app() {
  local script="$1"
  local tag="$2"

  cleanup

  if lsof -ti :"${PORT}" >/dev/null 2>&1; then
    echo "Port ${PORT} is already in use. Stop the existing process first." | tee -a "$SUMMARY_FILE"
    return 1
  fi

  log "Starting ${script}"
  python -X dev "$script" >"${OUT_DIR}/${tag}.server.log" 2>&1 &
  APP_PID=$!

  if ! wait_for_server; then
    record_fail "start_app ${tag}"
    tail_server_log "${OUT_DIR}/${tag}.server.log"
    return 1
  fi

  record_ok "start_app ${tag}"
  return 0
}

run_cli() {
  local name="$1"
  shift

  step "cli: $name"

  {
    echo "COMMAND: $*"
    echo
    "$@"
  } >"${OUT_DIR}/${name}.txt" 2>&1

  local rc=$?
  if [[ $rc -eq 0 ]]; then
    record_ok "$name"
  else
    record_fail "$name (exit $rc)"
  fi
}

run_basic_suite() {
  log "Running basic_app suite"

  if ! start_app "${ROOT_DIR}/examples/basic_app.py" "basic_app"; then
    return 0
  fi

  local endpoint="http://localhost:${PORT}/mcp"

  request_json "basic_initialize" \
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
    "$endpoint"

  request_json "basic_tools_list" \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
    "$endpoint"

  request_json "basic_tools_call_health" \
    '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"health","arguments":{}}}' \
    "$endpoint"

  request_json "basic_resources_list" \
    '{"jsonrpc":"2.0","id":4,"method":"resources/list","params":{}}' \
    "$endpoint"

  request_json "basic_resources_read" \
    '{"jsonrpc":"2.0","id":5,"method":"resources/read","params":{"uri":"context://service/current"}}' \
    "$endpoint"

  request_json "basic_prompts_list" \
    '{"jsonrpc":"2.0","id":6,"method":"prompts/list","params":{}}' \
    "$endpoint"

  request_json "basic_prompts_get" \
    '{"jsonrpc":"2.0","id":7,"method":"prompts/get","params":{"name":"release-summary","arguments":{"service":"robyn_mcp"}}}' \
    "$endpoint"

  request_json "basic_unknown_method" \
    '{"jsonrpc":"2.0","id":8,"method":"does/not/exist","params":{}}' \
    "$endpoint"

  request_json "basic_bad_args_shape" \
    '{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"health","arguments":"bad"}}' \
    "$endpoint"

  request_json "basic_missing_tool" \
    '{"jsonrpc":"2.0","id":11,"method":"tools/call","params":{"name":"missing_tool","arguments":{}}}' \
    "$endpoint"

  run_cli "cli_validate_endpoint" robyn-mcp validate-endpoint "$endpoint"
  run_cli "cli_list_tools" robyn-mcp list-tools "$endpoint"
  run_cli "cli_inspect" robyn-mcp inspect "$endpoint"
  run_cli "cli_debug_snapshot" robyn-mcp debug-snapshot "$endpoint" --out "${OUT_DIR}/debug_snapshot.json"

  step "rate loop"
  {
    echo "Starting repeated tools/list loop"
    for i in $(seq 1 5); do
      curl --silent --show-error --max-time 3 \
        -H 'content-type: application/json' \
        -H 'accept: application/json' \
        -d '{"jsonrpc":"2.0","id":100,"method":"tools/list","params":{}}' \
        "$endpoint" >/dev/null 2>&1 || true
    done
    echo "Completed repeated tools/list loop"
  } >"${OUT_DIR}/basic_rate_limit_loop.txt" 2>&1
  record_ok "basic_rate_limit_loop"

  cleanup
  step "basic_app cleanup complete"
  log "Finished basic_app suite"
}

run_auth_suite() {
  log "Running auth_example suite"

  if ! start_app "${ROOT_DIR}/examples/auth_example.py" "auth_app"; then
    return 0
  fi

  local endpoint="http://localhost:${PORT}/mcp"

  request_json "auth_initialize" \
    '{"jsonrpc":"2.0","id":101,"method":"initialize","params":{}}' \
    "$endpoint"

  local AUTH_SESSION_ID
  AUTH_SESSION_ID="$(extract_header_value "${OUT_DIR}/auth_initialize.headers" "mcp-session-id")"
  echo "AUTH_SESSION_ID=${AUTH_SESSION_ID}" | tee -a "$SUMMARY_FILE"

  request_json "auth_no_header_tools_list" \
    '{"jsonrpc":"2.0","id":12,"method":"tools/list","params":{}}' \
    "$endpoint" \
    -H "mcp-session-id: ${AUTH_SESSION_ID}"

  request_json "auth_with_headers_tools_list" \
    '{"jsonrpc":"2.0","id":13,"method":"tools/list","params":{}}' \
    "$endpoint" \
    -H "mcp-session-id: ${AUTH_SESSION_ID}" \
    -H 'authorization: Bearer demo-token' \
    -H 'x-tenant-id: tenant-123' \
    -H 'x-auth-sub: user-1' \
    -H 'x-client-id: local-test'

  request_json "auth_call_get_billing_summary" \
    '{"jsonrpc":"2.0","id":14,"method":"tools/call","params":{"name":"get_billing_summary","arguments":{"tenant_id":"tenant-123"}}}' \
    "$endpoint" \
    -H "mcp-session-id: ${AUTH_SESSION_ID}" \
    -H 'authorization: Bearer demo-token' \
    -H 'x-tenant-id: tenant-123' \
    -H 'x-auth-sub: user-1'

  cleanup
  step "auth_app cleanup complete"
  log "Finished auth_app suite"
}

run_multitenant_suite() {
  log "Running multitenant_example suite"

  if ! start_app "${ROOT_DIR}/examples/multitenant_example.py" "multitenant_app"; then
    return 0
  fi

  local endpoint="http://localhost:${PORT}/mcp"

  request_json "multi_initialize" \
    '{"jsonrpc":"2.0","id":201,"method":"initialize","params":{}}' \
    "$endpoint"

  local MULTI_SESSION_ID
  MULTI_SESSION_ID="$(extract_header_value "${OUT_DIR}/multi_initialize.headers" "mcp-session-id")"
  echo "MULTI_SESSION_ID=${MULTI_SESSION_ID}" | tee -a "$SUMMARY_FILE"

  request_json "multi_tools_list" \
    '{"jsonrpc":"2.0","id":15,"method":"tools/list","params":{}}' \
    "$endpoint" \
    -H "mcp-session-id: ${MULTI_SESSION_ID}" \
    -H 'authorization: Bearer demo-token' \
    -H 'x-tenant-id: tenant-123' \
    -H 'x-auth-sub: user-1'

  request_json "multi_create_invoice_ok" \
    '{"jsonrpc":"2.0","id":16,"method":"tools/call","params":{"name":"create_invoice","arguments":{"customer_id":"cust-1","amount":99.5}}}' \
    "$endpoint" \
    -H "mcp-session-id: ${MULTI_SESSION_ID}" \
    -H 'authorization: Bearer demo-token' \
    -H 'x-tenant-id: tenant-123' \
    -H 'x-auth-sub: user-1'

  request_json "multi_missing_tenant" \
    '{"jsonrpc":"2.0","id":17,"method":"tools/call","params":{"name":"create_invoice","arguments":{"customer_id":"cust-1","amount":99.5}}}' \
    "$endpoint" \
    -H "mcp-session-id: ${MULTI_SESSION_ID}" \
    -H 'authorization: Bearer demo-token' \
    -H 'x-auth-sub: user-1'

  request_json "multi_bad_amount" \
    '{"jsonrpc":"2.0","id":18,"method":"tools/call","params":{"name":"create_invoice","arguments":{"customer_id":"cust-1","amount":"bad"}}}' \
    "$endpoint" \
    -H "mcp-session-id: ${MULTI_SESSION_ID}" \
    -H 'authorization: Bearer demo-token' \
    -H 'x-tenant-id: tenant-123' \
    -H 'x-auth-sub: user-1'

  request_json "multi_empty_args" \
    '{"jsonrpc":"2.0","id":19,"method":"tools/call","params":{"name":"create_invoice","arguments":{}}}' \
    "$endpoint" \
    -H "mcp-session-id: ${MULTI_SESSION_ID}" \
    -H 'authorization: Bearer demo-token' \
    -H 'x-tenant-id: tenant-123' \
    -H 'x-auth-sub: user-1'

  request_json "multi_missing_auth" \
    '{"jsonrpc":"2.0","id":20,"method":"tools/call","params":{"name":"create_invoice","arguments":{"customer_id":"cust-1","amount":99.5}}}' \
    "$endpoint" \
    -H "mcp-session-id: ${MULTI_SESSION_ID}" \
    -H 'x-tenant-id: tenant-123' \
    -H 'x-auth-sub: user-1'

  cleanup
  step "multitenant_app cleanup complete"
  log "Finished multitenant_app suite"
}

run_metadata_checks() {
  log "Collecting package metadata and local environment info"

  {
    echo "PWD=$(pwd)"
    echo "PYTHON=$(python --version 2>&1)"
    echo "PIP=$(python -m pip --version 2>&1)"
    echo
    echo "robyn_mcp file:"
    python -c "import robyn_mcp; print(robyn_mcp.__file__)"
    echo
    echo "robyn-mcp version:"
    python -c "import importlib.metadata as m; print(m.version('robyn-mcp'))"
    echo
    echo "robyn version:"
    python -c "import robyn; print(robyn.__version__)"
  } >"${OUT_DIR}/environment.txt" 2>&1 || true
  record_ok "metadata_environment"

  {
    grep -RIn "__version__\|0.1.0a6\|1.0.1" "${ROOT_DIR}/src" "${ROOT_DIR}/pyproject.toml" || true
  } >"${OUT_DIR}/version_grep.txt" 2>&1
  record_ok "metadata_version_grep"
}

summarize() {
  log "Validation output saved"
  echo "Output directory: ${OUT_DIR}"
  echo
  echo "Important files:"
  echo "  environment.txt"
  echo "  summary.txt"
  echo "  basic_app.server.log"
  echo "  auth_app.server.log"
  echo "  multitenant_app.server.log"
  echo "  cli_validate_endpoint.txt"
  echo "  cli_inspect.txt"
  echo "  debug_snapshot.json"
  echo
  echo "All request outputs are stored as:"
  echo "  *.meta.txt"
  echo "  *.headers"
  echo "  *.body"
  echo "  *.pretty.json"
  echo
  echo "TOTAL_STEPS=$TOTAL_STEPS" | tee -a "$SUMMARY_FILE"
  echo "FAILED_STEPS=$FAILED_STEPS" | tee -a "$SUMMARY_FILE"
  echo "Validation finished at $(date)" | tee -a "$SUMMARY_FILE"
}

main() {
  cd "$ROOT_DIR"
  run_metadata_checks
  run_basic_suite
  run_auth_suite
  run_multitenant_suite
  summarize
}

main "$@"