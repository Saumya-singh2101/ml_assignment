import {
  Minus,
  Plus,
  Maximize,
} from "lucide-react";

interface Props {
  zoom: number;

  setZoom: React.Dispatch<
    React.SetStateAction<number>
  >;

  pan: {
    x: number;
    y: number;
  };

  setPan: React.Dispatch<
    React.SetStateAction<{
      x: number;
      y: number;
    }>
  >;
}

function CanvasControls({
  zoom,
  setZoom,
  setPan,
}: Props) {
  const zoomIn = () => {
    setZoom((prev) =>
      Math.min(4, prev * 1.2)
    );
  };

  const zoomOut = () => {
    setZoom((prev) =>
      Math.max(0.25, prev / 1.2)
    );
  };

  const reset = () => {
    setZoom(1);
    setPan({
      x: 0,
      y: 0,
    });
  };

  return (
    <div className="fixed bottom-5 right-5 z-50 flex items-center gap-1 rounded-xl border border-white/10 bg-neutral-900/95 p-1 shadow-xl">
      <button
        onClick={zoomOut}
        className="rounded-lg p-2 text-white/70 hover:bg-white/10 hover:text-white"
        title="Zoom out"
      >
        <Minus size={17} />
      </button>

      <span className="min-w-14 text-center text-sm text-white/70">
        {Math.round(zoom * 100)}%
      </span>

      <button
        onClick={zoomIn}
        className="rounded-lg p-2 text-white/70 hover:bg-white/10 hover:text-white"
        title="Zoom in"
      >
        <Plus size={17} />
      </button>

      <button
        onClick={reset}
        className="ml-1 rounded-lg p-2 text-white/70 hover:bg-white/10 hover:text-white"
        title="Reset view"
      >
        <Maximize size={17} />
      </button>
    </div>
  );
}

export default CanvasControls;