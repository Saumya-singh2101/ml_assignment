import {
  useCallback,
  useRef,
  useState,
} from "react";

import type {
  Point,
  Stroke,
  Tool,
} from "../models/stroke";

import { useHistory } from "./useHistory";
import { getPointerPoints } from "../utils/pointer";

export function useCanvas() {
  const [tool, setTool] = useState<Tool>("pen");

  const [color, setColor] = useState("#111111");

  const [strokeWidth, setStrokeWidth] =
    useState(3);

  const [zoom, setZoom] = useState(1);

  const [pan, setPan] = useState({
    x: 0,
    y: 0,
  });

  const [selectedIds, setSelectedIds] =
    useState<string[]>([]);

  const [isDrawing, setIsDrawing] =
    useState(false);

  const currentStroke =
    useRef<Stroke | null>(null);

  const lastPointer =
    useRef<{ x: number; y: number } | null>(null);

  const {
    state: strokes,
    update,
    undo,
    redo,
    canUndo,
    canRedo,
  } = useHistory<Stroke[]>([]);

  const screenToCanvas = useCallback(
    (clientX: number, clientY: number): Point => {
      return {
        x: (clientX - pan.x) / zoom,
        y: (clientY - pan.y) / zoom,
        pressure: 0.5,
        timestamp: performance.now(),
      };
    },
    [pan, zoom]
  );

  const createStroke = useCallback(
    (points: Point[]): Stroke => {
      return {
        id: crypto.randomUUID(),
        points,
        color,
        width: strokeWidth,
        createdAt: Date.now(),
      };
    },
    [color, strokeWidth]
  );

  const eraseAtPoint = useCallback(
    (point: Point) => {
      const threshold =
        Math.max(strokeWidth * 2, 15);

      const remaining = strokes.filter(
        (stroke) => {
          return !stroke.points.some(
            (p) =>
              Math.hypot(
                p.x - point.x,
                p.y - point.y
              ) < threshold
          );
        }
      );

      if (remaining.length !== strokes.length) {
        update(remaining);
      }
    },
    [strokes, strokeWidth, update]
  );

  const selectAtPoint = useCallback(
    (point: Point) => {
      for (let i = strokes.length - 1; i >= 0; i--) {
        const stroke = strokes[i];

        const hit = stroke.points.some(
          (p) =>
            Math.hypot(
              p.x - point.x,
              p.y - point.y
            ) < Math.max(stroke.width * 2, 12)
        );

        if (hit) {
          setSelectedIds([stroke.id]);
          return;
        }
      }

      setSelectedIds([]);
    },
    [strokes]
  );

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLCanvasElement>) => {
      event.currentTarget.setPointerCapture(
        event.pointerId
      );

      const point = screenToCanvas(
        event.clientX,
        event.clientY
      );

      point.pressure =
        event.pressure > 0
          ? event.pressure
          : 0.5;

      if (tool === "pen") {
        setIsDrawing(true);

        currentStroke.current =
          createStroke([point]);

        return;
      }

      if (tool === "eraser") {
        eraseAtPoint(point);
        return;
      }

      if (tool === "select") {
        selectAtPoint(point);
        lastPointer.current = {
          x: point.x,
          y: point.y,
        };
        return;
      }

      if (tool === "pan") {
        lastPointer.current = {
          x: event.clientX,
          y: event.clientY,
        };
      }
    },
    [
      tool,
      screenToCanvas,
      createStroke,
      eraseAtPoint,
      selectAtPoint,
    ]
  );

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLCanvasElement>) => {
      const points = getPointerPoints(
        event.nativeEvent,
        (x, y) => {
          const point = screenToCanvas(x, y);

          point.pressure =
            event.pressure > 0
              ? event.pressure
              : 0.5;

          return point;
        }
      );

      if (tool === "pen" && isDrawing) {
        if (!currentStroke.current) return;

        currentStroke.current.points.push(
          ...points
        );

        return;
      }

      if (tool === "eraser") {
        points.forEach(eraseAtPoint);
        return;
      }

      if (tool === "pan" && lastPointer.current) {
        const dx =
          event.clientX -
          lastPointer.current.x;

        const dy =
          event.clientY -
          lastPointer.current.y;

        setPan((prev) => ({
          x: prev.x + dx,
          y: prev.y + dy,
        }));

        lastPointer.current = {
          x: event.clientX,
          y: event.clientY,
        };
      }
    },
    [
      tool,
      isDrawing,
      screenToCanvas,
      eraseAtPoint,
    ]
  );

  const handlePointerUp = useCallback(
    (event: React.PointerEvent<HTMLCanvasElement>) => {
      event.currentTarget.releasePointerCapture(
        event.pointerId
      );

      if (
        tool === "pen" &&
        isDrawing &&
        currentStroke.current
      ) {
        update([
          ...strokes,
          currentStroke.current,
        ]);

        currentStroke.current = null;
        setIsDrawing(false);
      }

      if (tool === "select") {
        lastPointer.current = null;
      }

      if (tool === "pan") {
        lastPointer.current = null;
      }
    },
    [
      tool,
      isDrawing,
      strokes,
      update,
    ]
  );

  const handleWheel = useCallback(
    (event: React.WheelEvent<HTMLCanvasElement>) => {
      event.preventDefault();

      if (event.ctrlKey || event.metaKey) {
        const factor =
          event.deltaY > 0 ? 0.9 : 1.1;

        setZoom((prev) =>
          Math.min(
            4,
            Math.max(0.25, prev * factor)
          )
        );

        return;
      }

      setPan((prev) => ({
        x: prev.x - event.deltaX,
        y: prev.y - event.deltaY,
      }));
    },
    []
  );

  const deleteSelected = useCallback(() => {
    if (selectedIds.length === 0) return;

    const remaining = strokes.filter(
      (stroke) =>
        !selectedIds.includes(stroke.id)
    );

    update(remaining);
    setSelectedIds([]);
  }, [
    selectedIds,
    strokes,
    update,
  ]);

  const clearSelection = useCallback(() => {
    setSelectedIds([]);
  }, []);

  return {
    tool,
    setTool,

    color,
    setColor,

    strokeWidth,
    setStrokeWidth,

    zoom,
    setZoom,

    pan,
    setPan,

    strokes,
    selectedIds,

    undo,
    redo,

    canUndo,
    canRedo,

    deleteSelected,
    clearSelection,

    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
    handleWheel,
  };
}