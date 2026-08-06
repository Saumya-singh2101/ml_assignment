
import { useEffect, useRef } from "react";

import type { Stroke, Tool } from "../models/stroke";

interface CanvasProps {
  strokes: Stroke[];
  selectedIds: string[];
  tool: Tool;
  color: string;
  strokeWidth: number;
  zoom: number;
  pan: {
    x: number;
    y: number;
  };

  onPointerDown: (
    event: React.PointerEvent<HTMLCanvasElement>
  ) => void;

  onPointerMove: (
    event: React.PointerEvent<HTMLCanvasElement>
  ) => void;

  onPointerUp: (
    event: React.PointerEvent<HTMLCanvasElement>
  ) => void;

  onWheel: (
    event: React.WheelEvent<HTMLCanvasElement>
  ) => void;

  onClearSelection: () => void;
}

function Canvas({
  strokes,
  selectedIds,
  tool,
  zoom,
  pan,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onWheel,
  onClearSelection,
}: CanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;

    if (!canvas) return;

    const context = canvas.getContext("2d");

    if (!context) return;

    const dpr = window.devicePixelRatio || 1;

    const width = window.innerWidth;
    const height = window.innerHeight;

    canvas.width = width * dpr;
    canvas.height = height * dpr;

    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    context.setTransform(dpr, 0, 0, dpr, 0, 0);

    context.clearRect(0, 0, width, height);

    // Background
    context.fillStyle = "#0a0a0a";
    context.fillRect(0, 0, width, height);

    // Canvas world transform
    context.save();

    context.translate(pan.x, pan.y);
    context.scale(zoom, zoom);

    // Draw grid
    drawGrid(context, width, height, zoom, pan);

    // Draw strokes
    for (const stroke of strokes) {
      if (stroke.points.length < 1) {
        continue;
      }

      const selected = selectedIds.includes(stroke.id);

      drawStroke(context, stroke, selected);
    }

    context.restore();
  }, [strokes, selectedIds, zoom, pan]);

  return (
    <canvas
      ref={canvasRef}
      className={`fixed inset-0 z-0 touch-none ${
        tool === "pen"
          ? "cursor-crosshair"
          : tool === "eraser"
          ? "cursor-cell"
          : tool === "pan"
          ? "cursor-grab"
          : "cursor-default"
      }`}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onWheel={onWheel}
      onContextMenu={(e) => e.preventDefault()}
      onDoubleClick={onClearSelection}
    />
  );
}

function drawStroke(
  context: CanvasRenderingContext2D,
  stroke: Stroke,
  selected: boolean
) {
  const points = stroke.points;

  if (points.length === 1) {
    const p = points[0];

    context.beginPath();

    context.arc(
      p.x,
      p.y,
      stroke.width / 2,
      0,
      Math.PI * 2
    );

    context.fillStyle = stroke.color;
    context.fill();

    return;
  }

  context.beginPath();

  context.moveTo(points[0].x, points[0].y);

  for (let i = 1; i < points.length; i++) {
    const p = points[i];

    context.lineTo(p.x, p.y);
  }

  context.lineCap = "round";
  context.lineJoin = "round";

  context.strokeStyle = selected
    ? "#60a5fa"
    : stroke.color;

  context.lineWidth = selected
    ? stroke.width + 3
    : stroke.width;

  context.globalAlpha = selected ? 0.85 : 1;

  context.stroke();

  context.globalAlpha = 1;
}

function drawGrid(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  zoom: number,
  pan: { x: number; y: number }
) {
  const gridSize = 50;

  const startX =
    Math.floor(-pan.x / zoom / gridSize) * gridSize -
    gridSize;

  const startY =
    Math.floor(-pan.y / zoom / gridSize) * gridSize -
    gridSize;

  const endX =
    startX +
    width / zoom +
    gridSize * 2;

  const endY =
    startY +
    height / zoom +
    gridSize * 2;

  context.strokeStyle =
    "rgba(255,255,255,0.04)";

  context.lineWidth = 1 / zoom;

  context.beginPath();

  for (let x = startX; x <= endX; x += gridSize) {
    context.moveTo(x, startY);
    context.lineTo(x, endY);
  }

  for (let y = startY; y <= endY; y += gridSize) {
    context.moveTo(startX, y);
    context.lineTo(endX, y);
  }

  context.stroke();
}

export default Canvas;

