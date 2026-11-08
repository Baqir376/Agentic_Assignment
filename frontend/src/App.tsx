import { useEffect, useRef, useState } from "react";
import type { AuditRun, AuditStats, PipelineResponse } from "./types";
import { PRESET_DOCUMENTS } from "./data/presets";
import evidence from "./data/evaluation.json";
import {
  MAX_DOCUMENT_LENGTH,
  MAX_TASK_LENGTH,
  readResponse,
  parseResult,
  parseRuns,
} from "./api";

type View = "workspace" | "pipeline" | "evaluation" | "audit" | "help";
const pages: { id: View; label: string; icon: string }[] = [
  { id: "workspace", label: "Document workspace", icon: "document" },
  { id: "pipeline", label: "Pipeline", icon: "flow" },
  { id: "evaluation", label: "Evaluation", icon: "chart" },
  { id: "audit", label: "Audit log", icon: "list" },
];
const stages = [
  [
    "Detect identifiers",
    "Symbolic rules",
    "Recognizes structured identifiers using the symbolic rule engine.",
  ],
  [
    "Redact entities",
    "Neural redactor",
    "Replaces detected entities with tokens and maintains the reverse mapping.",
  ],
  [
    "Validate redaction",
    "Quality gate",
    "Checks the sanitized document. Failed checks retry redaction; if retries are exhausted, processing stops before routing and the failed run is logged.",
  ],
  [
    "Choose a route",
    "Hybrid router",
    "Selects local peer review or cloud processing. Cloud routing can send sanitized content to an external provider.",
  ],
  [
    "Process the task",
    "Local / cloud",
    "Runs the local peer-review swarm or the cloud processor selected by the router.",
  ],
  [
    "Inspect the answer",
    "Hallucination detector",
    "Checks the generated answer and can retry processing on its selected route.",
  ],
  [
    "Restore & record",
    "Reinsertion / audit",
    "Reinserts original values and records execution metadata in the audit log.",
  ],
];
function Icon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    document: "M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6 M9 16h6",
    flow: "M4 4h6v5H4z M14 15h6v5h-6z M7 9v8h7 M14 4h6v5h-6z",
    chart: "M4 20V4 M4 20h17 M8 16v-5 M13 16V7 M18 16V3",
    list: "M8 6h12 M8 12h12 M8 18h12 M3 6h1 M3 12h1 M3 18h1",
    arrow: "M4 12h16 M14 6l6 6-6 6",
    search: "M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14 M15 15l6 6",
    help: "M9 8a3 3 0 1 1 5 2c-2 1-2 2-2 4 M12 18h.01 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
    download: "M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5",
    refresh: "M20 7v5h-5 M20 12a8 8 0 1 0-2 6",
    check: "M5 12l4 4L19 6",
  };
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] || paths.document} />
    </svg>
  );
}
function download(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function Empty({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-symbol">
        <Icon name="document" />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function readView(): View {
  const hash = location.hash.slice(1);
  return [...pages.map((p) => p.id), "help"].includes(hash)
    ? (hash as View)
    : "workspace";
}
const API = import.meta.env.VITE_API_BASE_URL || "";
export default function App() {
  const [view, setView] = useState<View>(readView);
  const [health, setHealth] = useState<{
    ollama_online: boolean;
    groq_configured: boolean;
    local_model: string;
  } | null>(null);
  const [connection, setConnection] = useState("Checking connection");
  const [text, setText] = useState("");
  const [task, setTask] = useState(
    "Summarize this document and preserve its key facts.",
  );
  const [preset, setPreset] = useState("");
  const [result, setResult] = useState<PipelineResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [output, setOutput] = useState("Redacted");
  const [notice, setNotice] = useState("");
  const [runs, setRuns] = useState<AuditRun[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [auditError, setAuditError] = useState("");
  const [auditBusy, setAuditBusy] = useState(false);
  const [updated, setUpdated] = useState("");
  const [query, setQuery] = useState("");
  const [route, setRoute] = useState("all");
  const [ascending, setAscending] = useState(false);
  const [selected, setSelected] = useState<AuditRun | null>(null);
  const [stage, setStage] = useState(0);
  const [command, setCommand] = useState("");
  const [undoDraft, setUndoDraft] = useState<{
    text: string;
    task: string;
    preset: string;
    result: PipelineResponse | null;
  } | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [checking, setChecking] = useState(false);
  const resultPanel = useRef<HTMLElement>(null);
  const request = useRef<AbortController | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const commandInput = useRef<HTMLInputElement>(null);
  function openCommands() {
    setCommand("");
    dialog.current?.showModal();
    commandInput.current?.focus();
  }
  function navigate(next: View) {
    location.hash = next;
    setView(next);
    dialog.current?.close();
  }
  async function check() {
    setChecking(true);
    try {
      const r = await fetch(`${API}/api/health`, {
        signal: AbortSignal.timeout(4000),
      });
      const data = await readResponse(r);
      if (typeof data.ollama_online !== "boolean")
        throw Error("Invalid health response");
      setHealth({
        ollama_online: data.ollama_online,
        groq_configured: data.groq_configured === true,
        local_model:
          typeof data.local_model === "string" ? data.local_model : "Unknown",
      });
      setConnection("API connected");
    } catch {
      setHealth(null);
      setConnection("API unavailable");
    } finally {
      setChecking(false);
    }
  }
  async function refresh() {
    setAuditBusy(true);
    setAuditError("");
    try {
      const r = await fetch(`${API}/api/audit?limit=100`, {
        signal: AbortSignal.timeout(10000),
      });
      const data = await readResponse(r);
      setRuns(parseRuns(data.runs));
      setStats(
        data.stats &&
          typeof data.stats === "object" &&
          "total_runs" in data.stats &&
          typeof data.stats.total_runs === "number"
          ? (data.stats as AuditStats)
          : null,
      );
      setUpdated(new Date().toLocaleTimeString());
    } catch {
      setAuditError(
        "Audit records could not be loaded. Check the connection and retry.",
      );
    } finally {
      setAuditBusy(false);
    }
  }
  // Health requests synchronize with an external service.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- Synchronize health from the API.
    void check();
    const timer = setInterval(check, 15000);
    const hash = () => {
      if (location.hash !== "#main") setView(readView());
    };
    const key = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        openCommands();
      }
    };
    window.addEventListener("hashchange", hash);
    window.addEventListener("keydown", key);
    return () => {
      clearInterval(timer);
      window.removeEventListener("hashchange", hash);
      window.removeEventListener("keydown", key);
    };
  }, []);
  // Audit requests synchronize with the selected external resource.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- Load the selected external resource.
    if (view === "audit") void refresh();
  }, [view]);
  useEffect(() => {
    if (!busy) return;
    const start = Date.now();
    const timer = setInterval(
      () => setElapsed(Math.floor((Date.now() - start) / 1000)),
      1000,
    );
    return () => clearInterval(timer);
  }, [busy]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 6000);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    if (!text.trim() && !busy) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [text, busy]);
  function replaceDraft(value: string, nextTask = task, nextPreset = "") {
    setUndoDraft(text ? { text, task, preset, result } : null);
    changeText(value);
    setTask(nextTask);
    setPreset(nextPreset);
  }
  function undoReplace() {
    if (!undoDraft) return;
    setText(undoDraft.text);
    setTask(undoDraft.task);
    setPreset(undoDraft.preset);
    setResult(undoDraft.result);
    setUndoDraft(null);
    setError("");
    setNotice("Previous document restored.");
  }
  function stopWaiting() {
    request.current?.abort();
    request.current = null;
    setBusy(false);
    setNotice('');
    setError(
      "Stopped waiting. The server may still finish this run. Check the audit log before submitting again.",
    );
  }
  function changeText(value: string) {
    setText(value);
    setResult(null);
    setError("");
    setNotice("");
    setOutput("Redacted");
  }
  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim() || !task.trim() || busy) return;
    if (text.length > MAX_DOCUMENT_LENGTH || task.length > MAX_TASK_LENGTH) {
      setError(
        `Use a document of at most ${MAX_DOCUMENT_LENGTH.toLocaleString()} characters and an instruction of at most ${MAX_TASK_LENGTH.toLocaleString()} characters.`,
      );
      return;
    }
    setBusy(true);
    setElapsed(0);
    setNotice(
      "Processing started. Keep this page open while the service works.",
    );
    setError("");
    setResult(null);
    const controller = new AbortController();
    request.current = controller;
    const timeout = setTimeout(() => controller.abort("timeout"), 180000);
    try {
      const r = await fetch(`${API}/api/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, task }),
        signal: controller.signal,
      });
      const data = parseResult(await readResponse(r));
      if (request.current !== controller) return;
      setResult(data);
      setOutput("Redacted");
      setNotice("Processing finished. Your result is ready to review.");
      if (view === "workspace") resultPanel.current?.focus();
    } catch (e) {
      if (request.current !== controller) return;
      setNotice('');
      setError(
        controller.signal.aborted
          ? "This request took too long. The server may still be processing it. Check the audit log before trying again."
          : e instanceof TypeError
            ? "Could not reach the service. Your document is still here. Check the connection and try again."
            : e instanceof Error
              ? e.message
              : "Processing failed. Please retry.",
      );
    } finally {
      clearTimeout(timeout);
      if (request.current === controller) {
        request.current = null;
        setBusy(false);
      }
    }
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(
        output === "Restored answer"
          ? result?.final_answer || ""
          : output === "Entity map"
            ? JSON.stringify(result?.pii_token_map, null, 2)
            : output === "Compare"
              ? `Original\n${result?.raw_text || ""}\n\nRedacted\n${result?.sanitized_text || ""}`
              : result?.sanitized_text || "",
      );
      setNotice("Copied to clipboard.");
    } catch {
      setNotice("Copy unavailable. Select the text or download the result.");
    }
  }
  const filtered = runs
    .filter(
      (r) =>
        (route === "all" || r.routing_decision === route) &&
        `${r.run_id} ${r.category}`.toLowerCase().includes(query.toLowerCase()),
    )
    .sort((a, b) => (ascending ? a.id - b.id : b.id - a.id));
  const titles: Record<View, [string, string]> = {
    workspace: [
      "Review before you reveal.",
      "Inspect sensitive text, follow its route, and review the result.",
    ],
    pipeline: [
      "Inside the pipeline.",
      "Follow the decisions between a source document and its restored answer.",
    ],
    evaluation: [
      "Evidence, with context.",
      "Recorded evaluation results. A measured sample, not a privacy guarantee.",
    ],
    audit: [
      "Every run has a record.",
      "Inspect execution metadata from your connected local service.",
    ],
    help: [
      "A clearer path through.",
      "How to use this research workbench and interpret its results.",
    ],
  };
  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <a className="brand" href="#workspace">
          <span className="brand-mark">
            p<span>·</span>
          </span>
          <span>
            PrivacySwarm<small>RESEARCH WORKBENCH</small>
          </span>
        </a>
        <div className="workspace-label">
          <span className="workspace-avatar">PS</span>
          <span>
            Local workspace<small>Research environment</small>
          </span>
        </div>
        <p className="nav-label">WORKSPACE</p>
        <nav aria-label="Main navigation">
          {pages.map((p) => (
            <a
              key={p.id}
              href={`#${p.id}`}
              aria-current={view === p.id ? "page" : undefined}
            >
              <Icon name={p.icon} />
              {p.label}
              {view === p.id && <span className="nav-dot" />}
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-note">
            <span className="eyebrow">Designed for inspection</span>
            <p>
              Know what changes.
              <br />
              See where it goes.
            </p>
            <span className="line-art" aria-hidden="true">
              ○──□──○
            </span>
          </div>
          <a href="#help" className="help-link">
            <Icon name="help" />
            Guide & limitations
          </a>
          <small>PrivacySwarm / Research prototype</small>
        </div>
      </aside>
      <div className="body">
        <header className="topbar">
          <span>
            Workspace <span className="slash">/</span>{" "}
            <strong>
              {pages.find((p) => p.id === view)?.label || "Guide"}
            </strong>
          </span>
          <button
            className="command"
            aria-label="Find a screen (Ctrl or Command K)"
            onClick={openCommands}
          >
            <Icon name="search" />
            <span>Go to…</span>
            <kbd>Ctrl K</kbd>
          </button>
          <span className={`status ${health ? "connected" : ""}`}>
            <i />
            {connection}
          </span>
        </header>
        <main id="main" tabIndex={-1}>
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                {view === "workspace"
                  ? "DOCUMENT INTELLIGENCE"
                  : view === "evaluation"
                    ? "RESEARCH / RECORDED RESULTS"
                    : "PRIVACYSWARM / " + view.toUpperCase()}
              </span>
              <h1>{titles[view][0]}</h1>
              <p>{titles[view][1]}</p>
            </div>
            <span className="edition">
              LOCAL WORKSPACE
              <br />
              <strong>01 / Research</strong>
            </span>
          </div>
          {!health && (
            <div className="connection-banner" role="status">
              <span>
                <strong>
                  {checking ? "Checking connection" : connection}.
                </strong>{" "}
                Your document stays here. Start the local service to process it,
                or load a sample to explore the editor.
              </span>
              <button disabled={checking} onClick={check}>
                {checking ? "Checking…" : "Retry connection"}{" "}
                <Icon name="refresh" />
              </button>
              <a href="#help">Connection help</a>
            </div>
          )}
          {health && !health.ollama_online && (
            <div className="connection-banner" role="status">
              <span>
                <strong>Local model unavailable.</strong> The service is
                connected, but local AI steps cannot run normally. Start Ollama
                and check that the configured model is installed.
              </span>
              <a href="#help">Setup instructions</a>
            </div>
          )}
          {busy && view !== "workspace" && (
            <div className="connection-banner" role="status">
              <span>Your document is processing ({elapsed}s).</span>
              <button onClick={() => navigate("workspace")}>
                Return to document
              </button>
            </div>
          )}
          {view === "workspace" && (
            <>
              <div className="steps">
                <span
                  className={!busy && !result ? "current" : ""}
                  aria-current={!busy && !result ? "step" : undefined}
                >
                  <b>01</b> Prepare document
                </span>
                <span
                  className={busy ? "current" : ""}
                  aria-current={busy ? "step" : undefined}
                >
                  <b>02</b> Process & inspect
                </span>
                <span
                  className={result ? "current" : ""}
                  aria-current={result ? "step" : undefined}
                >
                  <b>03</b> Review result
                </span>
              </div>
              <div className="desk">
                <section className="document-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">SOURCE</span>
                      <h2>Your document</h2>
                    </div>
                    <span className="tag">
                      {preset
                        ? text ===
                          PRESET_DOCUMENTS.find((p) => p.id === preset)?.text
                          ? "Sample data"
                          : "Edited sample"
                        : "Unsaved draft"}
                    </span>
                  </div>
                  <form onSubmit={run}>
                    <div className="sample-row">
                      <label htmlFor="sample">Start with a sample</label>
                      <select
                        id="sample"
                        value={preset}
                        disabled={busy}
                        onChange={(e) => {
                          const p = PRESET_DOCUMENTS.find(
                            (p) => p.id === e.target.value,
                          );
                          if (p) replaceDraft(p.text, p.task, p.id);
                        }}
                      >
                        <option value="" disabled>
                          Choose a document
                        </option>
                        {PRESET_DOCUMENTS.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.category} · {p.title}
                          </option>
                        ))}
                      </select>
                    </div>
                    {!text && (
                      <div className="quick-start">
                        <p>
                          New here? Start with a sample, then select{" "}
                          <strong>Process document</strong>.
                        </p>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() =>
                            replaceDraft(
                              PRESET_DOCUMENTS[0].text,
                              PRESET_DOCUMENTS[0].task,
                              PRESET_DOCUMENTS[0].id,
                            )
                          }
                        >
                          Try a sample document <Icon name="arrow" />
                        </button>
                      </div>
                    )}
                    {undoDraft && (
                      <div className="undo-row" role="status">
                        <span>Previous document kept for undo.</span>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={undoReplace}
                        >
                          Undo replacement
                        </button>
                      </div>
                    )}
                    <div className="editor-label">
                      <label htmlFor="document">Document text</label>
                      <span>{text.length.toLocaleString()} characters</span>
                    </div>
                    <textarea
                      id="document"
                      dir="auto"
                      disabled={busy}
                      aria-describedby="document-hint"
                      aria-invalid={text.length > MAX_DOCUMENT_LENGTH}
                      value={text}
                      onChange={(e) => changeText(e.target.value)}
                      placeholder={
                        "Paste a document here.\n\nNames, contact details and other identifiers will be inspected by the pipeline.\n\nTry a sample to explore the workflow."
                      }
                    />
                    <p
                      id="document-hint"
                      className={
                        text.length > MAX_DOCUMENT_LENGTH
                          ? "error"
                          : "field-note"
                      }
                    >
                      Paste plain text, up to{" "}
                      {MAX_DOCUMENT_LENGTH.toLocaleString()} characters. Drafts
                      are not saved after you close this page.
                    </p>
                    <div className="task-field">
                      <label htmlFor="task">What should the pipeline do?</label>
                      <input
                        id="task"
                        required
                        maxLength={MAX_TASK_LENGTH}
                        disabled={busy}
                        value={task}
                        onChange={(e) => {
                          setTask(e.target.value);
                          setResult(null);
                          setError("");
                        }}
                      />
                      <div
                        className="task-options"
                        aria-label="Suggested tasks"
                      >
                        {[
                          "Summarize",
                          "List key facts",
                          "Extract next steps",
                        ].map((label) => (
                          <button
                            key={label}
                            type="button"
                            disabled={busy}
                            onClick={() => {
                              setTask(
                                label +
                                  " from this document. Preserve its key facts.",
                              );
                              setResult(null);
                              setError("");
                            }}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="submit-row">
                      <button
                        className="primary"
                        disabled={
                          busy ||
                          !health ||
                          !text.trim() ||
                          !task.trim() ||
                          text.length > MAX_DOCUMENT_LENGTH
                        }
                      >
                        {busy ? "Processing document…" : "Process document"}
                        <Icon name="arrow" />
                      </button>
                      <button
                        type="button"
                        disabled={busy || !text}
                        onClick={() => {
                          replaceDraft("");
                        }}
                      >
                        Clear
                      </button>
                    </div>
                    <p
                      className="field-note"
                      role="status"
                      aria-live={busy ? "off" : "polite"}
                    >
                      {busy
                        ? `Processing for ${elapsed}s. You can explore other screens while waiting.`
                        : !health
                          ? "Processing is disabled until the service connects."
                          : !text.trim()
                            ? "Add text or choose a sample to enable processing."
                            : !task.trim()
                              ? "Add an instruction to enable processing."
                              : "Ready to process. Review the result before using it."}
                    </p>
                    {busy && (
                      <button type="button" onClick={stopWaiting}>
                        Stop waiting
                      </button>
                    )}
                    <p className="field-note">
                      Routing may use a cloud provider. Review the pipeline
                      before submitting sensitive information.
                    </p>
                    {error && (
                      <div className="error" role="alert">
                        {error}
                      </div>
                    )}
                  </form>
                </section>
                <section
                  className="result-panel"
                  aria-busy={busy}
                  ref={resultPanel}
                  tabIndex={-1}
                  aria-label="Document result"
                >
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">RESULT</span>
                      <h2>Your result</h2>
                    </div>
                    <span className="tag">
                      {busy
                        ? "Processing"
                        : result
                          ? "Response received"
                          : "Awaiting input"}
                    </span>
                  </div>
                  <div className="segments" aria-label="Result views">
                    {[
                      "Redacted",
                      "Compare",
                      "Restored answer",
                      "Entity map",
                    ].map((t) => (
                      <button
                        key={t}
                        aria-pressed={output === t}
                        onClick={() => setOutput(t)}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                  {busy ? (
                    <Empty title="Processing your document">
                      Waiting for the service. Stage-level progress is not
                      available. Keep this page open; you can stop waiting using
                      the button beside your document.
                    </Empty>
                  ) : !result ? (
                    <Empty title="Your result belongs here">
                      Process a document to inspect redacted text, compare
                      changes, and review restored details.
                    </Empty>
                  ) : (
                    <div className="result-content">
                      {output === "Entity map" ? (
                        <>
                          <p className="field-note">
                            Contains original sensitive values.
                          </p>
                          {Object.keys(result.pii_token_map).length === 0 && (
                            <p>
                              No entities were detected. This does not prove the
                              document contains no sensitive information.
                            </p>
                          )}
                          {Object.entries(result.pii_token_map).map(
                            ([original, token]) => (
                              <div className="token-row" key={original}>
                                <span>{original}</span>
                                <code>{token}</code>
                              </div>
                            ),
                          )}
                        </>
                      ) : output === "Compare" ? (
                        <div className="compare">
                          <div>
                            <h3>Original</h3>
                            <pre>{result.raw_text}</pre>
                          </div>
                          <div>
                            <h3>Redacted</h3>
                            <TokenText text={result.sanitized_text} />
                          </div>
                        </div>
                      ) : output === "Restored answer" ? (
                        <pre>
                          {result.final_answer ||
                            "No answer was returned. Review the processing warnings and retry."}
                        </pre>
                      ) : (
                        <TokenText text={result.sanitized_text} />
                      )}
                    </div>
                  )}
                  {result && (
                    <>
                      <dl className="result-stats">
                        <div>
                          <dt>Entities detected</dt>
                          <dd>{Object.keys(result.pii_token_map).length}</dd>
                        </div>
                        <div>
                          <dt>Route</dt>
                          <dd>{result.routing_decision}</dd>
                        </div>
                        <div>
                          <dt>Elapsed</dt>
                          <dd>{result.latency_seconds}s</dd>
                        </div>
                        <div>
                          <dt>Validation</dt>
                          <dd>
                            {result.validation_passed
                              ? "Passed"
                              : "Needs review"}
                          </dd>
                        </div>
                      </dl>
                      <p className="field-note">
                        {result.routing_reason}{" "}
                        {result.hallucination_detected
                          ? "Hallucination flagged: review the response."
                          : ""}
                      </p>
                      {result.errors?.length > 0 && (
                        <p className="error" role="alert">
                          {result.errors.join(" · ")}
                        </p>
                      )}
                      <div className="result-actions">
                        <button onClick={copy}>Copy current view</button>
                        <button
                          onClick={() => {
                            const blob = new Blob([result.sanitized_text], {
                              type: "text/plain;charset=utf-8",
                            });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement("a");
                            a.href = url;
                            a.download = "redacted-document.txt";
                            a.click();
                            setTimeout(() => URL.revokeObjectURL(url), 1000);
                          }}
                        >
                          Save redacted text
                        </button>
                        <button
                          onClick={() =>
                            download(
                              result,
                              "privacyswarm-sensitive-result.json",
                            )
                          }
                        >
                          <Icon name="download" />
                          Export full result
                        </button>
                      </div>
                      <p className="field-note">
                        Full exports include original sensitive text and entity
                        mappings.
                      </p>
                    </>
                  )}
                  <div className="result-foot">
                    <Icon name="flow" />
                    <span>Detection / redaction / routing / review</span>
                  </div>
                </section>
              </div>
              <section className="below-desk">
                <div>
                  <span className="eyebrow">A TRACEABLE WORKFLOW</span>
                  <h2>
                    Privacy is a process. <br />
                    Inspect each step.
                  </h2>
                </div>
                <p>
                  Redaction is only part of the story. Explore how the pipeline
                  validates tokens, chooses a processing route, and restores the
                  answer.
                </p>
                <button onClick={() => navigate("pipeline")}>
                  Explore the pipeline <Icon name="arrow" />
                </button>
              </section>
            </>
          )}
          {view === "pipeline" && (
            <div className="pipeline-layout">
              <section className="flow-panel">
                <div className="panel-heading">
                  <h2>Document lifecycle</h2>
                  <span className="tag">Architecture · not a live trace</span>
                </div>
                <ol className="flow">
                  {stages.map((s, i) => (
                    <li key={s[0]}>
                      <button
                        aria-pressed={stage === i}
                        onClick={() => setStage(i)}
                      >
                        <span className="stage-number">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span>
                          <strong>{s[0]}</strong>
                          <small>{s[1]}</small>
                        </span>
                        <Icon name="arrow" />
                      </button>
                      {i === 2 && (
                        <span className="branch-note">
                          If validation fails - retry redaction
                        </span>
                      )}
                      {i === 3 && (
                        <span className="branch-note">
                          Local peer review or cloud processing
                        </span>
                      )}
                      {i === 5 && (
                        <span className="branch-note">
                          If flagged - retry processing
                        </span>
                      )}
                    </li>
                  ))}
                </ol>
              </section>
              <aside className="inspector">
                <span className="eyebrow">
                  STAGE {String(stage + 1).padStart(2, "0")} / INSPECTOR
                </span>
                <h2>{stages[stage][0]}</h2>
                <span className="tag">{stages[stage][1]}</span>
                <p>{stages[stage][2]}</p>
                <hr />
                <h3>Connection details</h3>
                <dl className="key-values">
                  <dt>API</dt>
                  <dd>{health ? "Connected" : "Unavailable"}</dd>
                  <dt>Local inference</dt>
                  <dd>
                    {health
                      ? health.ollama_online
                        ? "Online"
                        : "Unavailable"
                      : "Unknown"}
                  </dd>
                  <dt>Cloud configured</dt>
                  <dd>
                    {health
                      ? health.groq_configured
                        ? "Yes"
                        : "No"
                      : "Unknown"}
                  </dd>
                  <dt>Local model</dt>
                  <dd>{health?.local_model || "Unknown"}</dd>
                </dl>
                <div className="notice">
                  A successful validation is a pipeline check, not a guarantee
                  that all sensitive information was detected.
                </div>
              </aside>
            </div>
          )}
          {view === "evaluation" && (
            <>
              <div className="evidence-banner">
                <div>
                  <span className="eyebrow">RECORDED EXPERIMENT</span>
                  <h2>{evidence.n_docs} documents. One bounded result.</h2>
                  <p>
                    Repository snapshot · November 5, 2026 · {evidence.mode}
                  </p>
                </div>
                <button
                  onClick={() => download(evidence, "evaluation-20261105.json")}
                >
                  <Icon name="download" />
                  Download evidence
                </button>
              </div>
              <div className="metrics">
                <div>
                  <span>Detection recall</span>
                  <strong>{evidence.avg_pii_detection_recall}%</strong>
                  <small>Reported by the evaluator</small>
                </div>
                <div>
                  <span>Factual retention</span>
                  <strong>{evidence.avg_factual_retention}%</strong>
                  <small>Review answer quality carefully</small>
                </div>
                <div>
                  <span>Average latency</span>
                  <strong>
                    {evidence.avg_latency_seconds}
                    <em>s</em>
                  </strong>
                  <small>Recorded execution duration</small>
                </div>
              </div>
              <section className="table-panel">
                <div className="panel-heading">
                  <div>
                    <span className="eyebrow">DOCUMENT-LEVEL EVIDENCE</span>
                    <h2>Look beyond the aggregate</h2>
                  </div>
                  <span className="tag">Static snapshot</span>
                </div>
                <div
                  className="table-scroll"
                  tabIndex={0}
                  aria-label="Evaluation results"
                >
                  <table>
                    <caption>Recorded evaluation per document</caption>
                    <thead>
                      <tr>
                        <th>Document</th>
                        <th>Domain</th>
                        <th>PII count</th>
                        <th>Recall</th>
                        <th>Factual retention</th>
                        <th>Latency</th>
                        <th>Route</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evidence.per_doc_results.map((d) => (
                        <tr key={d.id}>
                          <th scope="row">
                            <code>{d.id}</code>
                          </th>
                          <td>{d.category}</td>
                          <td>{d.pii_count}</td>
                          <td>{d.pii_recall}%</td>
                          <td>
                            <span className="bar-cell">
                              <meter
                                min="0"
                                max="100"
                                value={d.factual_retention}
                                aria-label={`${d.id} factual retention`}
                              />
                              {d.factual_retention}%
                            </span>
                          </td>
                          <td>{d.latency_s}s</td>
                          <td>{d.routing}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <div className="method-note">
                <h3>Read this result within its limits</h3>
                <p>
                  The snapshot reports {evidence.avg_pii_leakage_rate}% leakage
                  on these {evidence.n_docs} documents. It does not establish
                  zero leakage on unseen documents. These results were loaded
                  from <code>results_20261105_215814.json</code>; this interface
                  does not rerun the evaluation.
                </p>
              </div>
            </>
          )}
          {view === "audit" && (
            <>
              <div className="audit-summary">
                <div>
                  <span className="eyebrow">RECORDED RUNS</span>
                  <strong>{stats?.total_runs ?? "—"}</strong>
                </div>
                <p>
                  {updated
                    ? `Last fetched at ${updated} · showing up to 100 recent records`
                    : "Refresh to retrieve execution records."}
                  <br />
                  Metadata only. Document contents are not displayed in this
                  table.
                </p>
                <button disabled={auditBusy} onClick={refresh}>
                  <Icon name="refresh" />
                  {auditBusy ? "Loading…" : "Refresh records"}
                </button>
              </div>
              {auditError && (
                <p role="alert" className="error">
                  {auditError}{" "}
                  {runs.length > 0 ? "Previous records remain visible." : ""}
                </p>
              )}
              <section className="table-panel">
                <div className="table-toolbar">
                  <label className="search-field">
                    <Icon name="search" />
                    <input
                      aria-label="Search audit records"
                      placeholder="Search run ID or category…"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </label>
                  <select
                    aria-label="Filter by route"
                    value={route}
                    onChange={(e) => setRoute(e.target.value)}
                  >
                    <option value="all">All routes</option>
                    <option value="local">Local</option>
                    <option value="cloud">Cloud</option>
                  </select>
                  <button
                    disabled={!filtered.length}
                    onClick={() => download(filtered, "audit-records.json")}
                  >
                    <Icon name="download" />
                    Export filtered
                  </button>
                </div>
                {filtered.length ? (
                  <div
                    className="table-scroll"
                    tabIndex={0}
                    aria-label="Audit records"
                  >
                    <table>
                      <caption>Recent execution records</caption>
                      <thead>
                        <tr>
                          <th
                            aria-sort={ascending ? "ascending" : "descending"}
                          >
                            <button onClick={() => setAscending(!ascending)}>
                              Run {ascending ? "Oldest first" : "Newest first"}
                            </button>
                          </th>
                          <th>Timestamp (server)</th>
                          <th>Category</th>
                          <th>Entities</th>
                          <th>Route</th>
                          <th>Latency</th>
                          <th>Outcome</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.map((r) => (
                          <tr key={r.id}>
                            <th scope="row">
                              <button
                                className="text-button"
                                onClick={() => setSelected(r)}
                              >
                                {r.run_id.slice(0, 8)}
                              </button>
                            </th>
                            <td>{r.timestamp}</td>
                            <td>{r.category || "Unspecified"}</td>
                            <td>{r.pii_found_total}</td>
                            <td>{r.routing_decision}</td>
                            <td>{r.latency_seconds}s</td>
                            <td>
                              <span className="tag">
                                {r.success ? "Completed" : "Failed"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    title={
                      auditBusy
                        ? "Loading records…"
                        : query || route !== "all"
                          ? "No matching records"
                          : "No records to display"
                    }
                  >
                    {auditError
                      ? "Reconnect to the API and refresh."
                      : "Run a document or adjust your filters to see its execution record."}
                  </Empty>
                )}
              </section>
              {selected && (
                <section className="run-detail">
                  <div className="panel-heading">
                    <h2>Run details</h2>
                    <button onClick={() => setSelected(null)}>
                      Close details
                    </button>
                  </div>
                  <dl className="key-values">
                    <dt>Run ID</dt>
                    <dd>{selected.run_id}</dd>
                    <dt>Category</dt>
                    <dd>{selected.category || "Unspecified"}</dd>
                    <dt>Outcome</dt>
                    <dd>{selected.success ? "Completed" : "Failed"}</dd>
                    <dt>Processing route</dt>
                    <dd>{selected.routing_decision}</dd>
                    <dt>Entities detected</dt>
                    <dd>{selected.pii_found_total}</dd>
                    <dt>Duration</dt>
                    <dd>{selected.latency_seconds}s</dd>
                  </dl>
                  <details>
                    <summary>View technical record</summary>
                    <pre>{JSON.stringify(selected, null, 2)}</pre>
                  </details>
                </section>
              )}
            </>
          )}
          {view === "help" && (
            <div className="help-content">
              <section>
                <h2>Connect the local service</h2>
                <p>
                  Open a terminal in the <code>privacyswarm</code> folder. With
                  the project's Python environment active, run{" "}
                  <code>python server.py</code>. For local AI processing, start
                  Ollama and install the model configured by your project (the
                  default is <code>llama3.2:1b</code>). Return to the workspace
                  and choose <strong>Retry connection</strong>.
                </p>
                <p>
                  If Python reports a missing package, install the project's{" "}
                  <code>requirements.txt</code> in that environment. The API and
                  the local model have separate connection states; a connected
                  API alone does not mean the model is ready.
                </p>
                <h2>From source to answer</h2>
                <ol>
                  <li>Paste a document or load a clearly marked sample.</li>
                  <li>
                    Describe the task, then process the document with the
                    connected service.
                  </li>
                  <li>
                    Inspect redacted text, compare it with the original, and
                    review the restored answer.
                  </li>
                  <li>
                    Review the route and validation result. Export only when you
                    intend to save sensitive content.
                  </li>
                </ol>
                <h2>Data handling</h2>
                <p>
                  Drafts and results are held in this page's memory. Reloading
                  clears them. Processing sends the document to the configured
                  API. Its router can use an external cloud provider for
                  sanitized content. Audit metadata is stored by the backend.
                  This prototype has no account, role management, or deletion
                  API.
                </p>
                <h2>Keyboard & accessibility</h2>
                <p>
                  Use Tab to move between controls, Enter or Space to activate
                  buttons, and Ctrl/Cmd + K to open navigation. Escape closes
                  the navigation dialog. All pipeline steps have buttons; no
                  drag or hover is required.
                </p>
                <h2>Research limitations</h2>
                <p>
                  Review outputs before reuse. Detection can miss identifiers
                  and generated answers can lose facts. Recorded evaluation is
                  evidence for its specific sample only. Audit timestamps ending
                  in Z are UTC; older records without an offset are displayed as
                  recorded.
                </p>
              </section>
              <aside className="inspector">
                <span className="eyebrow">GET STARTED</span>
                <h2>Try a sample first.</h2>
                <p>
                  Sample documents are fictional test content. They are not
                  authentic medical, financial, employment or legal records.
                </p>
                <button onClick={() => navigate("workspace")}>
                  Open workspace <Icon name="arrow" />
                </button>
              </aside>
            </div>
          )}
          <p className="sr-only" role="status">
            {notice}
          </p>
          {notice && (
            <button className="toast" onClick={() => setNotice("")}>
              {notice} ×
            </button>
          )}
          <footer>
            <span>
              PrivacySwarm <span className="slash">/</span> Research workbench
            </span>
            <a href="#help">
              Guide & limitations <Icon name="arrow" />
            </a>
          </footer>
        </main>
      </div>
      <dialog
        ref={dialog}
        className="command-dialog"
        aria-labelledby="command-title"
      >
        <div className="panel-heading">
          <h2 id="command-title">Go to a screen</h2>
          <button onClick={() => dialog.current?.close()}>Close</button>
        </div>
        <input
          ref={commandInput}
          aria-label="Find a screen"
          placeholder="Search screens…"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
        />
        <nav>
          {![...pages, { label: "Guide & limitations" }].some((p) =>
            p.label.toLowerCase().includes(command.toLowerCase()),
          ) && (
            <p className="field-note">
              No matching screens. Try “document”, “audit”, or “help”.
            </p>
          )}
          {[
            ...pages,
            { id: "help" as View, label: "Guide & limitations", icon: "help" },
          ]
            .filter((p) =>
              p.label.toLowerCase().includes(command.toLowerCase()),
            )
            .map((p) => (
              <button key={p.id} onClick={() => navigate(p.id)}>
                <Icon name={p.icon} />
                {p.label}
                <Icon name="arrow" />
              </button>
            ))}
        </nav>
      </dialog>
    </div>
  );
}
function TokenText({ text }: { text: string }) {
  return (
    <pre>
      {text
        .split(/(\[[A-Z_]+_\d+\])/g)
        .map((part, i) =>
          /^\[[A-Z_]+_\d+\]$/.test(part) ? <mark key={i}>{part}</mark> : part,
        )}
    </pre>
  );
}
