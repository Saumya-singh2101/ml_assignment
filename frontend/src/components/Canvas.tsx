import React, { useEffect, useRef, useState } from "react";
import { useCanvas } from "../hooks/useCanvas";

type Draft = {
  title: string;
  content: string;
  latex?: string | null;
  format: string;
  confidence: number;
  x: number;
  y: number;
  width: number;
  height: number;
  status: "draft" | "accepted" | "discarded";
};

const API_URL = "http://127.0.0.1:8000/api/analyze";

export default function Canvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const {
    tool,
    setTool,
    color,
    setColor,
    strokeWidth,
    setStrokeWidth,
    zoom,
    pan,
    strokes,
    selectedIds,
    undo,
    redo,
    canUndo,
    canRedo,
    deleteSelected,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
    handleWheel,
  } = useCanvas();

  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(false);

  /*
   * ============================
   * RENDER CANVAS
   * ============================
   */

  useEffect(() => {
    const canvas = canvasRef.current;

    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.clearRect(
      0,
      0,
      rect.width,
      rect.height
    );

    // White background
    ctx.fillStyle = "#ffffff";

    ctx.fillRect(
      0,
      0,
      rect.width,
      rect.height
    );

    /*
     * Pan + Zoom
     */

    ctx.save();

    ctx.translate(
      pan.x,
      pan.y
    );

    ctx.scale(
      zoom,
      zoom
    );

    /*
     * Draw strokes
     */

    for (const stroke of strokes) {
      if (
        !stroke.points ||
        stroke.points.length === 0
      ) {
        continue;
      }

      ctx.beginPath();

      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      ctx.strokeStyle =
        stroke.color;

      /*
       * Pressure
       */

      const firstPoint =
        stroke.points[0];

      const pressure =
        firstPoint.pressure || 0.5;

      ctx.lineWidth =
        stroke.width *
        (0.65 + pressure * 0.7);

      /*
       * Start
       */

      ctx.moveTo(
        stroke.points[0].x,
        stroke.points[0].y
      );

      /*
       * Smooth stroke
       */

      if (
        stroke.points.length === 1
      ) {
        ctx.lineTo(
          stroke.points[0].x + 0.01,
          stroke.points[0].y + 0.01
        );
      } else {
        for (
          let i = 1;
          i < stroke.points.length - 1;
          i++
        ) {
          const current =
            stroke.points[i];

          const next =
            stroke.points[i + 1];

          const midX =
            (current.x + next.x) / 2;

          const midY =
            (current.y + next.y) / 2;

          ctx.quadraticCurveTo(
            current.x,
            current.y,
            midX,
            midY
          );
        }

        const last =
          stroke.points[
            stroke.points.length - 1
          ];

        ctx.lineTo(
          last.x,
          last.y
        );
      }

      ctx.stroke();

      /*
       * Selection box
       */

      if (
        selectedIds.includes(
          stroke.id
        )
      ) {
        ctx.save();

        ctx.strokeStyle =
          "#2563eb";

        ctx.lineWidth =
          1 / zoom;

        ctx.setLineDash([
          6 / zoom,
          4 / zoom,
        ]);

        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;

        for (
          const point of stroke.points
        ) {
          minX = Math.min(
            minX,
            point.x
          );

          minY = Math.min(
            minY,
            point.y
          );

          maxX = Math.max(
            maxX,
            point.x
          );

          maxY = Math.max(
            maxY,
            point.y
          );
        }

        const padding = 8;

        ctx.strokeRect(
          minX - padding,
          minY - padding,
          maxX -
            minX +
            padding * 2,
          maxY -
            minY +
            padding * 2
        );

        ctx.restore();
      }
    }

    ctx.restore();
  }, [
    strokes,
    selectedIds,
    zoom,
    pan,
  ]);

  /*
   * ============================
   * CANVAS → BASE64
   * ============================
   */

  const canvasToBase64 = () => {
    const canvas =
      canvasRef.current;

    if (!canvas) {
      return "";
    }

    return canvas
      .toDataURL("image/png")
      .split(",")[1];
  };

  /*
   * ============================
   * CLEAN AI RESPONSE
   * ============================
   *
   * Some reasoning models return:
   *
   * <think>
   * internal reasoning...
   * </think>
   *
   * We don't want that shown to the user.
   */

  const cleanAIContent = (
    content: string
  ) => {
    if (!content) {
      return "";
    }

    let cleaned = content;

    // Remove <think>...</think>
    cleaned = cleaned.replace(
      /<think>[\s\S]*?<\/think>/gi,
      ""
    );

    // Remove any remaining think tags
    cleaned = cleaned.replace(
      /<\/?think>/gi,
      ""
    );

    // Remove excessive blank lines
    cleaned = cleaned.replace(
      /\n{3,}/g,
      "\n\n"
    );

    return cleaned.trim();
  };

  /*
   * ============================
   * AI ANALYSIS
   * ============================
   */

  const analyzeCanvas =
    async () => {
      if (
        strokes.length === 0
      ) {
        alert(
          "Draw something first."
        );

        return;
      }

      setLoading(true);

      try {
        const imageBase64 =
          canvasToBase64();

        const response =
          await fetch(
            API_URL,
            {
              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body: JSON.stringify({
                image_base64:
                  imageBase64,

                context: {
                  zoom,

                  pan_x:
                    pan.x,

                  pan_y:
                    pan.y,

                  stroke_count:
                    strokes.length,

                  region_x: 0,

                  region_y: 0,

                  region_width:
                    canvasRef.current
                      ?.width ??
                    1000,

                  region_height:
                    canvasRef.current
                      ?.height ??
                    700,

                  prompt:
                    "Analyze this handwritten canvas. Identify the equation or mathematical content. Ignore uncertainty unless necessary. Give only the final useful answer and concise step-by-step solution. Do not include internal reasoning or <think> tags.",
                },

                trigger:
                  "explicit",
              }),
            }
          );

        if (
          !response.ok
        ) {
          throw new Error(
            `Request failed: ${response.status}`
          );
        }

        const data =
          await response.json();

        console.log(
          "AI RESPONSE:",
          data
        );

        /*
         * Clean content
         */

        const cleanedContent =
          cleanAIContent(
            data.draft?.content || ""
          );

        const cleanedLatex =
          cleanAIContent(
            data.draft?.latex || ""
          );

        /*
         * Put result on canvas
         */

        setDraft({
          title:
            data.draft?.title ||
            "AI Analysis",

          content:
            cleanedContent ||
            "No useful result returned.",

          latex:
            cleanedLatex ||
            null,

          format:
            data.draft?.format ||
            "markdown",

          confidence:
            data.draft?.confidence ??
            0,

          /*
           * Always put result
           * somewhere visible.
           */

          x: 520,

          y: 100,

          width:
            data.draft?.width ??
            400,

          height:
            data.draft?.height ??
            250,

          status:
            "draft",
        });
      } catch (error) {
        console.error(
          "AI ERROR:",
          error
        );

        alert(
          "AI analysis failed. Check that the backend is running and your API key is valid."
        );
      } finally {
        setLoading(false);
      }
    };

  /*
   * ============================
   * ACCEPT
   * ============================
   */

  const acceptDraft =
    () => {
      if (!draft) return;

      setDraft({
        ...draft,

        status:
          "accepted",
      });
    };

  /*
   * ============================
   * DISCARD
   * ============================
   */

  const discardDraft =
    () => {
      setDraft(null);
    };

  /*
   * ============================
   * UI
   * ============================
   */

  return (
    <div
      style={{
        position:
          "relative",

        width:
          "100%",

        height:
          "100%",

        overflow:
          "hidden",

        background:
          "#ffffff",
      }}
    >

      {/* =========================
          TOOLBAR
          ========================= */}

      <div
        style={{
          position:
            "absolute",

          top: 15,

          left: 15,

          zIndex: 50,

          display:
            "flex",

          alignItems:
            "center",

          gap: 8,

          padding: 8,

          background:
            "#ffffff",

          border:
            "1px solid #ddd",

          borderRadius:
            10,

          boxShadow:
            "0 4px 15px rgba(0,0,0,0.1)",
        }}
      >

        {/* PEN */}

        <button
          onClick={() =>
            setTool("pen")
          }
          style={{
            padding:
              "7px 10px",

            background:
              tool === "pen"
                ? "#111"
                : "#eee",

            color:
              tool === "pen"
                ? "#fff"
                : "#111",

            border:
              "none",

            borderRadius:
              6,

            cursor:
              "pointer",
          }}
        >
          ✏ Pen
        </button>

        {/* ERASER */}

        <button
          onClick={() =>
            setTool(
              "eraser"
            )
          }
          style={{
            padding:
              "7px 10px",

            background:
              tool ===
              "eraser"
                ? "#111"
                : "#eee",

            color:
              tool ===
              "eraser"
                ? "#fff"
                : "#111",

            border:
              "none",

            borderRadius:
              6,

            cursor:
              "pointer",
          }}
        >
          Eraser
        </button>

        {/* SELECT */}

        <button
          onClick={() =>
            setTool(
              "select"
            )
          }
          style={{
            padding:
              "7px 10px",

            background:
              tool ===
              "select"
                ? "#111"
                : "#eee",

            color:
              tool ===
              "select"
                ? "#fff"
                : "#111",

            border:
              "none",

            borderRadius:
              6,

            cursor:
              "pointer",
          }}
        >
          Select
        </button>

        {/* PAN */}

        <button
          onClick={() =>
            setTool("pan")
          }
          style={{
            padding:
              "7px 10px",

            background:
              tool === "pan"
                ? "#111"
                : "#eee",

            color:
              tool === "pan"
                ? "#fff"
                : "#111",

            border:
              "none",

            borderRadius:
              6,

            cursor:
              "pointer",
          }}
        >
          ✋ Pan
        </button>

        {/* COLOR */}

        <input
          type="color"
          value={color}
          onChange={(e) =>
            setColor(
              e.target.value
            )
          }
          title="Pen colour"
        />

        {/* STROKE WIDTH */}

        <input
          type="range"
          min="1"
          max="12"
          value={
            strokeWidth
          }
          onChange={(e) =>
            setStrokeWidth(
              Number(
                e.target.value
              )
            )
          }
          title="Pen size"
        />

        {/* UNDO */}

        <button
          onClick={undo}
          disabled={
            !canUndo
          }
          style={{
            cursor:
              canUndo
                ? "pointer"
                : "default",
          }}
        >
          ↶
        </button>

        {/* REDO */}

        <button
          onClick={redo}
          disabled={
            !canRedo
          }
          style={{
            cursor:
              canRedo
                ? "pointer"
                : "default",
          }}
        >
          ↷
        </button>

        {/* DELETE */}

        <button
          onClick={
            deleteSelected
          }
          disabled={
            selectedIds.length ===
            0
          }
          style={{
            cursor:
              selectedIds.length >
              0
                ? "pointer"
                : "default",
          }}
        >
          Delete
        </button>

        {/* ANALYZE */}

        <button
          onClick={
            analyzeCanvas
          }
          disabled={
            loading
          }
          style={{
            padding:
              "8px 14px",

            border:
              "none",

            borderRadius:
              7,

            background:
              "#111",

            color:
              "#fff",

            cursor:
              loading
                ? "wait"
                : "pointer",
          }}
        >
          {loading
            ? "Analyzing..."
            : "✨ Analyze"}
        </button>
      </div>

      {/* =========================
          CANVAS
          ========================= */}

      <canvas
        ref={canvasRef}

        style={{
          display:
            "block",

          width:
            "100%",

          height:
            "100%",

          background:
            "#fff",

          touchAction:
            "none",

          cursor:
            tool === "pan"
              ? "grab"
              : tool ===
                "eraser"
              ? "crosshair"
              : "crosshair",
        }}

        onPointerDown={
          handlePointerDown
        }

        onPointerMove={
          handlePointerMove
        }

        onPointerUp={
          handlePointerUp
        }

        onPointerCancel={
          handlePointerUp
        }

        onWheel={
          handleWheel
        }
      />

      {/* =========================
          AI DRAFT
          ========================= */}

      {draft && (
        <div
          style={{
            position:
              "fixed",

            left:
              draft.x,

            top:
              draft.y,

            width:
              draft.width,

            minHeight:
              draft.height,

            padding:
              18,

            background:
              draft.status ===
              "accepted"
                ? "#f0fff4"
                : "#fffdf0",

            border:
              draft.status ===
              "accepted"
                ? "2px solid #22c55e"
                : "2px dashed #eab308",

            borderRadius:
              12,

            boxShadow:
              "0 8px 30px rgba(0,0,0,0.15)",

            zIndex:
              9999,

            overflow:
              "auto",

            fontFamily:
              "Arial, sans-serif",

            maxHeight:
              "70vh",
          }}
        >

          {/* HEADER */}

          <div
            style={{
              display:
                "flex",

              justifyContent:
                "space-between",

              alignItems:
                "center",

              marginBottom:
                12,
            }}
          >
            <strong
              style={{
                fontSize:
                  17,
              }}
            >
              {draft.title}
            </strong>

            <span
              style={{
                fontSize:
                  11,

                padding:
                  "4px 8px",

                borderRadius:
                  6,

                background:
                  draft.status ===
                  "accepted"
                    ? "#dcfce7"
                    : "#fef3c7",
              }}
            >
              {draft.status}
            </span>
          </div>

          {/* CONTENT */}

          <div
            style={{
              fontSize:
                15,

              lineHeight:
                1.6,

              whiteSpace:
                "pre-wrap",

              color:
                "#111827",
            }}
          >
            {draft.content}
          </div>

          {/* LATEX */}

          {draft.latex && (
            <div
              style={{
                marginTop:
                  14,

                padding:
                  10,

                background:
                  "#f5f5f5",

                borderRadius:
                  7,

                fontFamily:
                  "monospace",

                fontSize:
                  15,
              }}
            >
              {draft.latex}
            </div>
          )}

          {/* CONFIDENCE */}

          <div
            style={{
              marginTop:
                12,

              fontSize:
                11,

              color:
                "#666",
            }}
          >
            Confidence:{" "}
            {Math.round(
              draft.confidence *
                100
            )}
            %
          </div>

          {/* ACTIONS */}

          {draft.status ===
            "draft" && (
            <div
              style={{
                display:
                  "flex",

                gap: 8,

                marginTop:
                  14,
              }}
            >

              <button
                onClick={
                  acceptDraft
                }
                style={{
                  padding:
                    "8px 14px",

                  border:
                    "none",

                  borderRadius:
                    6,

                  background:
                    "#16a34a",

                  color:
                    "#fff",

                  cursor:
                    "pointer",
                }}
              >
                ✓ Accept
              </button>

              <button
                onClick={
                  discardDraft
                }
                style={{
                  padding:
                    "8px 14px",

                  border:
                    "none",

                  borderRadius:
                    6,

                  background:
                    "#dc2626",

                  color:
                    "#fff",

                  cursor:
                    "pointer",
                }}
              >
                ✕ Discard
              </button>

            </div>
          )}
        </div>
      )}
    </div>
  );
}