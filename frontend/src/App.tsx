import Canvas from "./components/Canvas";
import Toolbar from "./components/Toolbar";
import CanvasControls from "./components/CanvasControls";
import { useCanvas } from "./hooks/useCanvas";

function App() {
  const {
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
    clearSelection,
    deleteSelected,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
    handleWheel,
  } = useCanvas();

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-neutral-950 text-white">
      <Toolbar
        tool={tool}
        setTool={setTool}
        color={color}
        setColor={setColor}
        strokeWidth={strokeWidth}
        setStrokeWidth={setStrokeWidth}
        undo={undo}
        redo={redo}
        canUndo={canUndo}
        canRedo={canRedo}
        deleteSelected={deleteSelected}
        hasSelection={selectedIds.length > 0}
      />

      <Canvas
        strokes={strokes}
        selectedIds={selectedIds}
        tool={tool}
        color={color}
        strokeWidth={strokeWidth}
        zoom={zoom}
        pan={pan}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onWheel={handleWheel}
        onClearSelection={clearSelection}
      />

      <CanvasControls
        zoom={zoom}
        setZoom={setZoom}
        pan={pan}
        setPan={setPan}
      />
    </div>
  );
}

export default App;