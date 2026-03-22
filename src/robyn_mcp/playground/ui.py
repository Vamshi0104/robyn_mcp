from __future__ import annotations


def build_playground_html(mcp_path: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>robyn-mcp Playground</title>
  <style>
    :root {{
      --bg: #0b1020;
      --bg-elev: rgba(255, 255, 255, 0.06);
      --bg-elev-2: rgba(255, 255, 255, 0.08);
      --panel: rgba(15, 23, 42, 0.72);
      --panel-border: rgba(255, 255, 255, 0.12);
      --text: #e5e7eb;
      --muted: #94a3b8;
      --primary: #7c3aed;
      --primary-2: #06b6d4;
      --success: #22c55e;
      --danger: #ef4444;
      --warning: #f59e0b;
      --shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
      --radius: 20px;
      --radius-sm: 14px;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    * {{
      box-sizing: border-box;
    }}

    html, body {{
      margin: 0;
      min-height: 100%;
      background:
        radial-gradient(circle at top left, rgba(124, 58, 237, 0.24), transparent 32%),
        radial-gradient(circle at top right, rgba(6, 182, 212, 0.18), transparent 28%),
        linear-gradient(180deg, #0b1020 0%, #0f172a 100%);
      color: var(--text);
      font-family: var(--sans);
    }}

    body {{
      padding: 32px 20px 48px;
    }}

    .container {{
      max-width: 1320px;
      margin: 0 auto;
    }}

    .hero {{
      position: relative;
      overflow: hidden;
      background: linear-gradient(135deg, rgba(124, 58, 237, 0.18), rgba(6, 182, 212, 0.12));
      border: 1px solid var(--panel-border);
      border-radius: 28px;
      padding: 32px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
      margin-bottom: 24px;
    }}

    .hero::before {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(circle at 15% 20%, rgba(255, 255, 255, 0.14), transparent 20%),
        radial-gradient(circle at 85% 15%, rgba(255, 255, 255, 0.08), transparent 18%);
      pointer-events: none;
    }}

    .hero-top {{
      position: relative;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 18px;
      flex-wrap: wrap;
    }}

    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: #c4b5fd;
      background: rgba(124, 58, 237, 0.14);
      border: 1px solid rgba(196, 181, 253, 0.18);
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    h1 {{
      margin: 14px 0 8px;
      font-size: clamp(32px, 5vw, 52px);
      line-height: 1.02;
      letter-spacing: -0.03em;
    }}

    .subtitle {{
      margin: 0;
      max-width: 860px;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.65;
    }}

    .endpoint-chip {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      margin-top: 18px;
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(15, 23, 42, 0.5);
      border: 1px solid var(--panel-border);
      color: var(--text);
      font-size: 14px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
    }}

    .endpoint-chip code {{
      font-family: var(--mono);
      color: #bfdbfe;
      font-size: 13px;
      word-break: break-all;
    }}

    .status-stack {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-width: 230px;
    }}

    .status-card {{
      background: rgba(15, 23, 42, 0.58);
      border: 1px solid var(--panel-border);
      border-radius: 18px;
      padding: 14px 16px;
      min-height: 76px;
    }}

    .status-label {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 8px;
      font-weight: 700;
    }}

    .status-value {{
      font-size: 15px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 10px;
      word-break: break-word;
    }}

    .dot {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      display: inline-block;
      background: var(--warning);
      box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.14);
      flex-shrink: 0;
    }}

    .dot.connected {{
      background: var(--success);
      box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.14);
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 20px;
    }}

    .card {{
      grid-column: span 6;
      position: relative;
      overflow: hidden;
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: var(--radius);
      padding: 22px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(16px);
    }}

    .card.full {{
      grid-column: span 12;
    }}

    .card.narrow {{
      grid-column: span 4;
    }}

    .card.wide {{
      grid-column: span 8;
    }}

    .card::after {{
      content: "";
      position: absolute;
      inset: 0;
      border-radius: inherit;
      pointer-events: none;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
    }}

    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }}

    .card-title {{
      margin: 0;
      font-size: 18px;
      font-weight: 800;
      letter-spacing: -0.02em;
    }}

    .card-subtitle {{
      margin: 6px 0 0;
      font-size: 13px;
      color: var(--muted);
      line-height: 1.5;
    }}

    .toolbar {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}

    button {{
      appearance: none;
      border: 0;
      border-radius: 14px;
      padding: 11px 16px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      color: white;
      background: linear-gradient(135deg, var(--primary), var(--primary-2));
      box-shadow: 0 8px 28px rgba(124, 58, 237, 0.28);
      transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
    }}

    button:hover {{
      transform: translateY(-1px);
      box-shadow: 0 12px 30px rgba(124, 58, 237, 0.34);
    }}

    button:active {{
      transform: translateY(0);
    }}

    button.secondary {{
      background: rgba(255,255,255,0.08);
      color: var(--text);
      box-shadow: none;
      border: 1px solid var(--panel-border);
    }}

    button.secondary:hover {{
      background: rgba(255,255,255,0.12);
    }}

    label {{
      display: block;
      margin: 14px 0 8px;
      font-size: 13px;
      font-weight: 700;
      color: #dbeafe;
    }}

    input, textarea, select {{
      width: 100%;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(2, 6, 23, 0.55);
      color: var(--text);
      border-radius: 14px;
      padding: 12px 14px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
    }}

    input:focus, textarea:focus, select:focus {{
      border-color: rgba(96, 165, 250, 0.7);
      box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.14);
      background: rgba(2, 6, 23, 0.72);
    }}

    textarea {{
      min-height: 180px;
      resize: vertical;
      font-family: var(--mono);
      line-height: 1.55;
    }}

    .json-actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 12px;
    }}

    pre {{
      margin: 0;
      min-height: 240px;
      background: rgba(2, 6, 23, 0.72);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 16px;
      padding: 16px;
      overflow: auto;
      font-size: 13px;
      line-height: 1.6;
      color: #dbeafe;
      font-family: var(--mono);
      white-space: pre-wrap;
      word-break: break-word;
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}

    .stat {{
      padding: 14px;
      border-radius: 16px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.08);
    }}

    .stat-label {{
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
      font-weight: 700;
    }}

    .stat-value {{
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.03em;
    }}

    .footer {{
      margin-top: 22px;
      text-align: center;
      color: var(--muted);
      font-size: 13px;
    }}

    .hint {{
      font-size: 12px;
      color: var(--muted);
      margin-top: 8px;
      line-height: 1.5;
    }}

    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 12px;
      font-weight: 700;
      background: rgba(255,255,255,0.07);
      border: 1px solid rgba(255,255,255,0.08);
      color: var(--muted);
    }}

    @media (max-width: 1100px) {{
      .card,
      .card.narrow,
      .card.wide {{
        grid-column: span 12;
      }}
    }}

    @media (max-width: 720px) {{
      body {{
        padding: 20px 14px 36px;
      }}

      .hero {{
        padding: 22px;
      }}

      .stats {{
        grid-template-columns: 1fr;
      }}

      h1 {{
        font-size: 34px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <section class="hero">
      <div class="hero-top">
        <div>
          <div class="eyebrow">⚡ MCP Playground</div>
          <h1>robyn-mcp Playground</h1>
          <p class="subtitle">
            Explore your MCP server with a clean modern interface. Inspect metadata, list tools,
            execute calls, browse resources, resolve prompts, and review trace activity — all from one place.
          </p>
          <div class="endpoint-chip">
            <span>Endpoint</span>
            <code>{mcp_path}</code>
          </div>
        </div>

        <div class="status-stack">
          <div class="status-card">
            <div class="status-label">Session</div>
            <div class="status-value">
              <span id="sessionDot" class="dot"></span>
              <span id="sessionStatus">Not initialized</span>
            </div>
          </div>
          <div class="status-card">
            <div class="status-label">Last action</div>
            <div class="status-value" id="lastAction">Ready</div>
          </div>
        </div>
      </div>
    </section>

    <div class="grid">
      <section class="card wide">
        <div class="card-header">
          <div>
            <h2 class="card-title">Server Metadata</h2>
            <p class="card-subtitle">Load compatibility info, capabilities, metrics, and traces from the MCP endpoint.</p>
          </div>
          <div class="toolbar">
            <button onclick="loadMetadata()">Load metadata</button>
          </div>
        </div>

        <div class="stats">
          <div class="stat">
            <div class="stat-label">Tools</div>
            <div class="stat-value" id="statTools">—</div>
          </div>
          <div class="stat">
            <div class="stat-label">Resources</div>
            <div class="stat-value" id="statResources">—</div>
          </div>
          <div class="stat">
            <div class="stat-label">Prompts</div>
            <div class="stat-value" id="statPrompts">—</div>
          </div>
        </div>

        <pre id="metadata">Click "Load metadata" to inspect the MCP server.</pre>
      </section>

      <section class="card narrow">
        <div class="card-header">
          <div>
            <h2 class="card-title">Quick Actions</h2>
            <p class="card-subtitle">Bootstrap your session and inspect the main MCP surfaces.</p>
          </div>
        </div>
        <div class="toolbar">
          <button onclick="initialize()">Initialize</button>
          <button class="secondary" onclick="listTools()">Tools</button>
          <button class="secondary" onclick="listResources()">Resources</button>
          <button class="secondary" onclick="listPrompts()">Prompts</button>
        </div>
        <p class="hint">
          The session ID is created automatically when needed and reused for subsequent MCP calls.
        </p>
      </section>

      <section class="card full">
        <div class="card-header">
          <div>
            <h2 class="card-title">Available Tools</h2>
            <p class="card-subtitle">Discover generated and explicit tools exposed by your Robyn MCP server.</p>
          </div>
          <div class="toolbar">
            <button onclick="listTools()">List tools</button>
          </div>
        </div>
        <pre id="tools">No tool data loaded yet.</pre>
      </section>

      <section class="card full">
        <div class="card-header">
          <div>
            <h2 class="card-title">Call Tool</h2>
            <p class="card-subtitle">Run a tool using MCP JSON-RPC and inspect the full response payload.</p>
          </div>
        </div>

        <label for="toolName">Tool name</label>
        <input id="toolName" placeholder="health" />

        <label for="toolArgs">Arguments (JSON)</label>
        <textarea id="toolArgs" rows="10">{{}}</textarea>

        <div class="json-actions">
          <button onclick="callTool()">Call tool</button>
          <button class="secondary" onclick="formatJson('toolArgs')">Format JSON</button>
          <button class="secondary" onclick="resetToolArgs()">Reset</button>
        </div>

        <p class="hint">
          Example for autogenerated action tools:
          <span class="pill">{{ "product_id": "p1", "qty": 2 }}</span>
        </p>

        <pre id="toolResult">Tool response will appear here.</pre>
      </section>

      <section class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">Resources</h2>
            <p class="card-subtitle">List available MCP resources.</p>
          </div>
          <div class="toolbar">
            <button onclick="listResources()">List resources</button>
          </div>
        </div>
        <pre id="resources">No resource data loaded yet.</pre>
      </section>

      <section class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">Prompts</h2>
            <p class="card-subtitle">List available MCP prompts.</p>
          </div>
          <div class="toolbar">
            <button onclick="listPrompts()">List prompts</button>
          </div>
        </div>
        <pre id="prompts">No prompt data loaded yet.</pre>
      </section>

      <section class="card full">
        <div class="card-header">
          <div>
            <h2 class="card-title">Metrics & Recent Traces</h2>
            <p class="card-subtitle">Review tool metrics and recent trace activity captured by the server.</p>
          </div>
          <div class="toolbar">
            <button onclick="loadMetadata()">Refresh traces</button>
          </div>
        </div>
        <pre id="traces">Trace and metrics data will appear here after loading metadata.</pre>
      </section>
    </div>

    <div class="footer">
      Built for a smoother local MCP development experience.
    </div>
  </div>

<script>
let sessionId = null;
let reqId = 1;

function setLastAction(text) {{
  document.getElementById("lastAction").textContent = text;
}}

function setSessionState(connected) {{
  const dot = document.getElementById("sessionDot");
  const text = document.getElementById("sessionStatus");
  if (connected && sessionId) {{
    dot.classList.add("connected");
    text.textContent = sessionId;
  }} else {{
    dot.classList.remove("connected");
    text.textContent = "Not initialized";
  }}
}}

function pretty(value) {{
  try {{
    return JSON.stringify(value, null, 2);
  }} catch (_) {{
    return String(value);
  }}
}}

function formatJson(id) {{
  const el = document.getElementById(id);
  try {{
    el.value = JSON.stringify(JSON.parse(el.value || "{{}}"), null, 2);
  }} catch (e) {{
    alert("Invalid JSON");
  }}
}}

function resetToolArgs() {{
  document.getElementById("toolArgs").value = "{{}}";
}}

async function initialize() {{
  setLastAction("Initializing session...");
  const res = await fetch("{mcp_path}", {{
    method: "POST",
    headers: {{
      "content-type": "application/json",
      "accept": "application/json"
    }},
    body: JSON.stringify({{
      jsonrpc: "2.0",
      id: reqId++,
      method: "initialize",
      params: {{}}
    }})
  }});
  sessionId = res.headers.get("mcp-session-id");
  setSessionState(Boolean(sessionId));
  setLastAction("Session initialized");
  return await res.json();
}}

async function post(method, params) {{
  if (!sessionId) {{
    await initialize();
  }}
  setLastAction(`Calling ${{method}}...`);
  const res = await fetch("{mcp_path}", {{
    method: "POST",
    headers: {{
      "content-type": "application/json",
      "accept": "application/json",
      "mcp-session-id": sessionId
    }},
    body: JSON.stringify({{
      jsonrpc: "2.0",
      id: reqId++,
      method,
      params
    }})
  }});
  setLastAction(`Completed ${{method}}`);
  return await res.json();
}}

async function loadMetadata() {{
  setLastAction("Loading metadata...");
  const res = await fetch("{mcp_path}");
  const data = await res.json();
  document.getElementById("metadata").textContent = pretty(data);

  const tools = data.toolMetrics?.tools || {{}};
  document.getElementById("traces").textContent = pretty({{
    toolMetrics: data.toolMetrics || {{}},
    recentToolEvents: data.recentToolEvents || []
  }});

  document.getElementById("statTools").textContent =
    typeof data.compatibility?.toolCount === "number"
      ? data.compatibility.toolCount
      : Object.keys(tools).length || "—";

  document.getElementById("statResources").textContent =
    data.compatibility?.resourceCount ?? "—";

  document.getElementById("statPrompts").textContent =
    data.compatibility?.promptCount ?? "—";

  setLastAction("Metadata loaded");
}}

async function listTools() {{
  const data = await post("tools/list", {{}});
  document.getElementById("tools").textContent = pretty(data);
}}

async function callTool() {{
  const name = document.getElementById("toolName").value.trim();
  if (!name) {{
    alert("Enter a tool name");
    return;
  }}

  let args = {{}};
  try {{
    args = JSON.parse(document.getElementById("toolArgs").value || "{{}}");
  }} catch (e) {{
    document.getElementById("toolResult").textContent = "Invalid JSON arguments";
    setLastAction("Tool call failed: invalid JSON");
    return;
  }}

  const data = await post("tools/call", {{ name, arguments: args }});
  document.getElementById("toolResult").textContent = pretty(data);
}}

async function listResources() {{
  const data = await post("resources/list", {{}});
  document.getElementById("resources").textContent = pretty(data);
}}

async function listPrompts() {{
  const data = await post("prompts/list", {{}});
  document.getElementById("prompts").textContent = pretty(data);
}}

setSessionState(false);
</script>
</body>
</html>
"""