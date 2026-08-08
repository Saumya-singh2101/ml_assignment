import { useEffect, useRef, useState } from "react";
import {
  Sparkles, Wand2, Eraser, Undo2, Redo2, Trash2, Send,
  Check, X, BarChart3, Zap, Coins, Gauge, MousePointer2,
  CircleHelp, Settings2, Brain, ChevronDown
} from "lucide-react";
import { analyzeCanvas, fetchAnalytics } from "./api";
import katex from "katex";
import "katex/dist/katex.min.css";

const COLORS = ["#1c1b21", "#2f4bd6", "#c23f3f", "#1f8f63", "#c1791f", "#7c3aed"];
const PAPER = "#fbf9f2";
const GRID_STEP = 28;
const GRID_LINE = "rgba(28, 27, 33, 0.07)";

function paintCanvasBackground(ctx, width, height) {
  ctx.fillStyle = PAPER;
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = GRID_LINE;
  ctx.lineWidth = 1;
  for (let x = GRID_STEP; x < width; x += GRID_STEP) {
    ctx.beginPath();
    ctx.moveTo(x + 0.5, 0);
    ctx.lineTo(x + 0.5, height);
    ctx.stroke();
  }
  for (let y = GRID_STEP; y < height; y += GRID_STEP) {
    ctx.beginPath();
    ctx.moveTo(0, y + 0.5);
    ctx.lineTo(width, y + 0.5);
    ctx.stroke();
  }
}

function renderMathContent(text) {
  if (!text) return null;
  // Split on block math ($$...$$) first, then inline math ($...$), keeping the rest as plain text.
  const blockParts = String(text).split(/(\$\$[^$]+\$\$)/g);

  return blockParts.map((block, bi) => {
    if (block.startsWith("$$") && block.endsWith("$$") && block.length > 4) {
      const expr = block.slice(2, -2);
      try {
        const html = katex.renderToString(expr, { throwOnError: false, displayMode: true });
        return <div key={bi} dangerouslySetInnerHTML={{ __html: html }} />;
      } catch {
        return <div key={bi}>{block}</div>;
      }
    }

    const inlineParts = block.split(/(\$[^$]+\$)/g);
    return (
      <span key={bi}>
        {inlineParts.map((part, i) => {
          if (part.startsWith("$") && part.endsWith("$") && part.length > 2) {
            const expr = part.slice(1, -1);
            try {
              const html = katex.renderToString(expr, { throwOnError: false, displayMode: false });
              return <span key={i} dangerouslySetInnerHTML={{ __html: html }} />;
            } catch {
              return <span key={i}>{part}</span>;
            }
          }
          return <span key={i}>{part}</span>;
        })}
      </span>
    );
  });
}

function App() {
  const canvasRef = useRef(null);
  const drawing = useRef(false);
  const last = useRef({ x: 0, y: 0 });
  const history = useRef([]);
  const redoStack = useRef([]);
  const [color, setColor] = useState(COLORS[0]);
  const [size, setSize] = useState(5);
  const [tool, setTool] = useState("pen");
  const [strokeCount, setStrokeCount] = useState(0);
  const [drafts, setDrafts] = useState([]);
  const [activeDraft, setActiveDraft] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("Draw something and let SLATE think with you.");
  const [metrics, setMetrics] = useState(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [zoom, setZoom] = useState(100);

  useEffect(() => {
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);
    return () => window.removeEventListener("resize", resizeCanvas);
  }, []);

  function resizeCanvas() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const old = canvas.toDataURL();
    canvas.width = Math.max(900, Math.floor(rect.width * devicePixelRatio));
    canvas.height = Math.max(600, Math.floor(rect.height * devicePixelRatio));
    const ctx = canvas.getContext("2d");
    ctx.scale(devicePixelRatio, devicePixelRatio);
    paintCanvasBackground(ctx, rect.width, rect.height);
    const img = new Image();
    img.onload = () => ctx.drawImage(img, 0, 0, rect.width, rect.height);
    if (old !== "data:,") img.src = old;
  }

  function snapshot() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    history.current.push(canvas.toDataURL());
    if (history.current.length > 25) history.current.shift();
    redoStack.current = [];
  }

  function restore(data) {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.onload = () => {
      const rect = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, rect.width, rect.height);
      paintCanvasBackground(ctx, rect.width, rect.height);
      ctx.drawImage(img, 0, 0, rect.width, rect.height);
    };
    img.src = data;
  }

  function pointerPos(e) {
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }

  function startDraw(e) {
    if (tool === "select") return;
    snapshot();
    drawing.current = true;
    last.current = pointerPos(e);
  }

  function draw(e) {
    if (!drawing.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const p = pointerPos(e);

    ctx.beginPath();
    ctx.moveTo(last.current.x, last.current.y);
    ctx.lineTo(p.x, p.y);
    ctx.lineWidth = tool === "eraser" ? size * 3 : size;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = tool === "eraser" ? PAPER : color;
    ctx.stroke();

    last.current = p;
  }

  function endDraw() {
    if (!drawing.current) return;
    drawing.current = false;
    setStrokeCount((n) => n + 1);
  }

  function undo() {
    if (!history.current.length) return;
    redoStack.current.push(canvasRef.current.toDataURL());
    restore(history.current.pop());
  }

  function redo() {
    if (!redoStack.current.length) return;
    history.current.push(canvasRef.current.toDataURL());
    restore(redoStack.current.pop());
  }

  function clearCanvas() {
    snapshot();
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    paintCanvasBackground(ctx, rect.width, rect.height);
    setStrokeCount(0);
    setDrafts([]);
    setActiveDraft(null);
  }

  async function runAnalysis() {
    if (!canvasRef.current) return;
    setLoading(true);
    setMessage("SLATE is reading your canvas...");
    try {
      const dataUrl = canvasRef.current.toDataURL("image/png");
      const base64 = dataUrl.split(",")[1];

      const response = await analyzeCanvas({
        image_base64: base64,
        context: {
          zoom: zoom / 100,
          pan_x: 0,
          pan_y: 0,
          stroke_count: strokeCount,
          region_x: 0,
          region_y: 0,
          region_width: canvasRef.current.clientWidth,
          region_height: canvasRef.current.clientHeight,
          prompt: prompt.trim() || "Analyze this canvas region and help the user.",
        },
        trigger: "explicit",
        session_id: `slate-${Date.now()}`,
        effort: "medium",
        config_id: "default",
      });

      setActiveDraft(response.draft);
      setDrafts((items) => [...items, response.draft]);
      setMetrics(response);
      setMessage("Draft ready. Accept it or keep sketching.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  function acceptDraft() {
    if (!activeDraft) return;
    setMessage("Nice. Draft accepted.");
    setActiveDraft(null);
  }

  function discardDraft() {
    setMessage("Draft discarded. Keep exploring.");
    setActiveDraft(null);
  }

  async function openAnalytics() {
    setShowAnalytics(true);
    try {
      const data = await fetchAnalytics();
      setMetrics(data);
    } catch {
      // Keep request-level metrics if the analytics route is unavailable.
    }
  }

  const latency = metrics?.latency?.average || {};
  const latencyStats = metrics?.latency?.statistics || {};
  const tokens = metrics?.tokens || {};
  const kpis = metrics?.kpis || {};
  const budget = metrics?.budget || {};

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><Sparkles size={19} /></div>
          <div>
            <div className="brand-name">SLATE</div>
            <div className="brand-sub">think freely, build visually</div>
          </div>
        </div>

        <div className="workspace-pill">
          <span className="status-dot" />
          Untitled canvas
          <ChevronDown size={14} />
        </div>

        <div className="top-actions">
          <button className="icon-btn" title="Help"><CircleHelp size={19} /></button>
          <button className="icon-btn" title="Settings"><Settings2 size={19} /></button>
          <button className="analytics-btn" onClick={openAnalytics}>
            <BarChart3 size={17} /> Analytics
          </button>
        </div>
      </header>

      <main className="workspace">
        <aside className="left-panel">
          <div className="tool-group">
            <Tool active={tool === "select"} onClick={() => setTool("select")} icon={<MousePointer2 />} label="Select" />
            <Tool active={tool === "pen"} onClick={() => setTool("pen")} icon={<Wand2 />} label="Pen" />
            <Tool active={tool === "eraser"} onClick={() => setTool("eraser")} icon={<Eraser />} label="Erase" />
          </div>

          <div className="divider" />

          <div className="tool-group">
            <Tool onClick={undo} icon={<Undo2 />} label="Undo" />
            <Tool onClick={redo} icon={<Redo2 />} label="Redo" />
            <Tool onClick={clearCanvas} icon={<Trash2 />} label="Clear" />
          </div>

          <div className="color-panel">
            <div className="mini-label">INK</div>
            <div className="colors">
              {COLORS.map((c) => (
                <button
                  key={c}
                  className={`color-dot ${color === c ? "selected" : ""}`}
                  style={{ background: c }}
                  onClick={() => { setColor(c); setTool("pen"); }}
                />
              ))}
            </div>
            <input
              className="size-slider"
              type="range"
              min="2"
              max="16"
              value={size}
              onChange={(e) => setSize(Number(e.target.value))}
            />
          </div>
        </aside>

        <section className="canvas-area">
          <div className="canvas-top">
            <div>
              <span className="canvas-title">Idea space</span>
              <span className="canvas-hint">{strokeCount} strokes</span>
            </div>
            <div className="zoom-control">
              <button onClick={() => setZoom(Math.max(50, zoom - 10))}>−</button>
              <span>{zoom}%</span>
              <button onClick={() => setZoom(Math.min(150, zoom + 10))}>+</button>
            </div>
          </div>

          <div className="canvas-wrap">
            <canvas
              ref={canvasRef}
              onPointerDown={startDraw}
              onPointerMove={draw}
              onPointerUp={endDraw}
              onPointerLeave={endDraw}
            />

            <div className="canvas-decoration deco-one" />
            <div className="canvas-decoration deco-two" />

            {activeDraft && (
              <div
                className="draft-card"
                style={{ left: `${Math.min(activeDraft.x || 530, 62)}%`, top: `${Math.min(activeDraft.y || 100, 62)}px` }}
              >
                <div className="draft-head">
                  <div className="ai-badge"><Sparkles size={14} /></div>
                  <div>
                    <div className="draft-label">SLATE DRAFT</div>
                    <strong>{activeDraft.title}</strong>
                  </div>
                  <span className="confidence">{Math.round((activeDraft.confidence || 0) * 100)}%</span>
                </div>
                <div className="draft-content">{renderMathContent(activeDraft.content)}</div>
                <div className="draft-actions">
                  <button className="accept-btn" onClick={acceptDraft}><Check size={15} /> Accept</button>
                  <button className="discard-btn" onClick={discardDraft}><X size={15} /> Discard</button>
                </div>
              </div>
            )}
          </div>

          <div className="command-bar">
            <div className="prompt-icon"><Brain size={18} /></div>
            <input
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runAnalysis()}
              placeholder="Ask SLATE to understand, solve, or explain your sketch..."
            />
            <button className="spark-btn" onClick={runAnalysis} disabled={loading}>
              {loading ? <span className="spinner" /> : <><Sparkles size={17} /> Think</>}
            </button>
          </div>

          <div className="canvas-status">
            <span>{message}</span>
            <span className="shortcut">Enter to run AI</span>
          </div>
        </section>

        <aside className="right-panel">
          <div className="panel-header">
            <div>
              <div className="panel-kicker">AI COPILOT</div>
              <h2>Your thinking buddy</h2>
            </div>
            <div className="live-badge"><span /> LIVE</div>
          </div>

          <div className="hero-card">
            <div className="hero-orb"><Sparkles size={28} /></div>
            <h3>Make the messy part easy.</h3>
            <p>Sketch an equation, diagram, idea, or question. SLATE turns your canvas into a useful draft.</p>
            <button onClick={runAnalysis} disabled={loading}>
              <Zap size={16} /> {loading ? "Thinking..." : "Analyze canvas"}
            </button>
          </div>

          {metrics && (
            <>
              <div className="metrics-grid">
                <Metric icon={<Gauge />} label="AI latency" value={`${Number(latency.ai_ms ?? 0).toFixed(0)} ms`} />
                <Metric icon={<Zap />} label="E2E latency" value={`${Number(latency.e2e_ms ?? 0).toFixed(0)} ms`} />
                <Metric icon={<Brain />} label="Tokens" value={tokens.total ?? "—"} />
                <Metric icon={<Coins />} label="Cost" value={`$${Number(metrics.cost_usd || 0).toFixed(5)}`} />
              </div>
              <div className="kpi-strip">
                <Kpi label="CPAD" value={`$${Number(kpis.CPAD ?? 0).toFixed(5)}`} />
                <Kpi label="DAR" value={`${Math.round(Number(kpis.DAR ?? 0) * 100)}%`} />
                <Kpi label="WTR" value={`${(Number(kpis.WTR ?? 0) * 100).toFixed(1)}%`} />
                <Kpi label="BC" value={`${Math.round(Number(kpis.BC ?? budget.budget_compliance ?? 0) * 100)}%`} />
              </div>
            </>
          )}

          <div className="mini-insight">
            <div className="insight-icon"><BarChart3 size={16} /></div>
            <div>
              <strong>Built for measurement</strong>
              <p>Latency, token usage, cost and confidence are captured for every analysis.</p>
            </div>
          </div>

          <div className="recent">
            <div className="section-title">RECENT DRAFTS</div>
            {drafts.length === 0 ? (
              <div className="empty-state">Your accepted and generated ideas will appear here.</div>
            ) : (
              drafts.slice(-4).reverse().map((draft, i) => (
                <button key={i} className="draft-row" onClick={() => setActiveDraft(draft)}>
                  <div className="row-icon"><Sparkles size={14} /></div>
                  <div><strong>{draft.title}</strong><span>{Math.round((draft.confidence || 0) * 100)}% confidence</span></div>
                </button>
              ))
            )}
          </div>
        </aside>
      </main>

      {showAnalytics && (
        <div className="modal-backdrop" onClick={() => setShowAnalytics(false)}>
          <div className="analytics-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div><div className="panel-kicker">OBSERVABILITY</div><h2>SLATE performance</h2></div>
              <button className="icon-btn" onClick={() => setShowAnalytics(false)}><X /></button>
            </div>
            <div className="big-stat-grid">
              <BigStat label="Requests" value={metrics?.total_requests ?? "—"} />
              <BigStat label="Success" value={metrics?.successful_requests ?? "—"} />
              <BigStat label="Confidence" value={metrics?.confidence != null ? `${Math.round(metrics.confidence * 100)}%` : "—"} />
              <BigStat label="Budget" value={budget.budget_compliance != null ? `${Math.round(Number(budget.budget_compliance) * 100)}%` : "—"} />
            </div>

            <div className="analytics-section-title">LATENCY DISTRIBUTION</div>
            <div className="latency-table">
              <div className="latency-table-head"><span>Segment</span><span>P50</span><span>P95</span><span>P99</span><span>Max</span><span>N</span></div>
              {Object.entries(latencyStats).map(([name, stat]) => (
                <div className="latency-table-row" key={name}>
                  <strong>{name.toUpperCase()}</strong>
                  <span>{Number(stat?.p50 ?? 0).toFixed(0)}</span>
                  <span>{Number(stat?.p95 ?? 0).toFixed(0)}</span>
                  <span>{Number(stat?.p99 ?? 0).toFixed(0)}</span>
                  <span>{Number(stat?.max ?? 0).toFixed(0)}</span>
                  <span>{stat?.n ?? 0}</span>
                </div>
              ))}
            </div>

            <div className="analytics-section-title">TOKEN & COST ACCOUNTING</div>
            <div className="analytics-list">
              <Row label="Input text" value={tokens.input_text ?? 0} />
              <Row label="Input image" value={tokens.input_image ?? 0} />
              <Row label="Output" value={tokens.output ?? 0} />
              <Row label="Reasoning" value={tokens.reasoning ?? 0} />
              <Row label="Cache read" value={tokens.cache_read ?? 0} />
              <Row label="Total tokens" value={tokens.total ?? 0} />
              <Row label="Total cost" value={`$${Number(metrics?.cost_usd ?? 0).toFixed(6)}`} />
            </div>

            <div className="analytics-section-title">ASSIGNMENT KPIs</div>
            <div className="kpi-modal-grid">
              <BigStat label="CPAD" value={`$${Number(kpis.CPAD ?? 0).toFixed(5)}`} />
              <BigStat label="DAR" value={`${(Number(kpis.DAR ?? 0) * 100).toFixed(1)}%`} />
              <BigStat label="WTR" value={`${(Number(kpis.WTR ?? 0) * 100).toFixed(1)}%`} />
              <BigStat label="BC" value={`${(Number(kpis.BC ?? 0) * 100).toFixed(1)}%`} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Tool({ icon, label, active, onClick }) {
  return <button className={`tool-btn ${active ? "active" : ""}`} onClick={onClick}>{icon}<span>{label}</span></button>;
}

function Metric({ icon, label, value }) {
  return <div className="metric-card"><div className="metric-icon">{icon}</div><span>{label}</span><strong>{value}</strong></div>;
}

function Kpi({ label, value }) {
  return <div className="kpi-chip"><span>{label}</span><strong>{value}</strong></div>;
}

function BigStat({ label, value }) {
  return <div className="big-stat"><span>{label}</span><strong>{value}</strong></div>;
}

function Row({ label, value }) {
  return <div className="analytics-row"><span>{label}</span><strong>{value}</strong></div>;
}

export default App;