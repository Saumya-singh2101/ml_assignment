import {
  Pen,
  Eraser,
  MousePointer2,
  Hand,
  Undo2,
  Redo2,
  Trash2,
} from "lucide-react";

import type { Tool } from "../models/stroke";

interface ToolbarProps {
  tool: Tool;
  setTool: (tool: Tool) => void;

  color: string;
  setColor: (color: string) => void;

  strokeWidth: number;
  setStrokeWidth: (width: number) => void;

  undo: () => void;
  redo: () => void;

  canUndo: boolean;
  canRedo: boolean;

  deleteSelected: () => void;
  hasSelection: boolean;
}

function Toolbar({
  tool,
  setTool,
  color,
  setColor,
  strokeWidth,
  setStrokeWidth,
  undo,
  redo,
  canUndo,
  canRedo,
  deleteSelected,
  hasSelection,
}: ToolbarProps) {
  return (
    <div className="pointer-events-auto fixed left-1/2 top-4 z-[100] flex -translate-x-1/2 items-center gap-2 rounded-2xl border border-white/10 bg-neutral-900/95 p-2 shadow-2xl backdrop-blur">
      <ToolButton
        active={tool === "pen"}
        onClick={() => setTool("pen")}
        title="Pen (P)"
      >
        <Pen size={18} />
      </ToolButton>

      <ToolButton
        active={tool === "eraser"}
        onClick={() => setTool("eraser")}
        title="Eraser (E)"
      >
        <Eraser size={18} />
      </ToolButton>

      <ToolButton
        active={tool === "select"}
        onClick={() => setTool("select")}
        title="Select (V)"
      >
        <MousePointer2 size={18} />
      </ToolButton>

      <ToolButton
        active={tool === "pan"}
        onClick={() => setTool("pan")}
        title="Pan (H)"
      >
        <Hand size={18} />
      </ToolButton>

      <div className="mx-1 h-6 w-px bg-white/10" />

      <input
        type="color"
        value={color}
        onChange={(e) =>
          setColor(e.target.value)
        }
        className="h-8 w-8 cursor-pointer rounded border-0 bg-transparent"
        title="Pen color"
      />

      <input
        type="range"
        min="1"
        max="20"
        value={strokeWidth}
        onChange={(e) =>
          setStrokeWidth(
            Number(e.target.value)
          )
        }
        className="w-20"
        title="Stroke width"
      />

      <div className="mx-1 h-6 w-px bg-white/10" />

      <ToolButton
        onClick={undo}
        disabled={!canUndo}
        title="Undo (Ctrl+Z)"
      >
        <Undo2 size={18} />
      </ToolButton>

      <ToolButton
        onClick={redo}
        disabled={!canRedo}
        title="Redo (Ctrl+Shift+Z)"
      >
        <Redo2 size={18} />
      </ToolButton>

      <ToolButton
        onClick={deleteSelected}
        disabled={!hasSelection}
        title="Delete selected (Delete)"
      >
        <Trash2 size={18} />
      </ToolButton>
    </div>
  );
}

interface ToolButtonProps {
  children: React.ReactNode;
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  title?: string;
}

function ToolButton({
  children,
  active = false,
  disabled = false,
  onClick,
  title,
}: ToolButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`flex h-9 w-9 items-center justify-center rounded-lg transition ${
        active
          ? "bg-white text-black"
          : "text-white/70 hover:bg-white/10 hover:text-white"
      } ${
        disabled
          ? "cursor-not-allowed opacity-30"
          : ""
      }`}
    >
      {children}
    </button>
  );
}

export default Toolbar;