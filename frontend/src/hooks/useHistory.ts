import { useCallback, useRef, useState } from "react";

export function useHistory<T>(initialState: T) {
  const [state, setState] = useState<T>(initialState);

  const past = useRef<T[]>([]);
  const future = useRef<T[]>([]);

  const update = useCallback((newState: T) => {
    past.current.push(state);
    future.current = [];
    setState(newState);
  }, [state]);

  const undo = useCallback(() => {
    if (past.current.length === 0) return;

    const previous = past.current[past.current.length - 1];

    past.current = past.current.slice(0, -1);
    future.current.push(state);

    setState(previous);
  }, [state]);

  const redo = useCallback(() => {
    if (future.current.length === 0) return;

    const next = future.current[future.current.length - 1];

    future.current = future.current.slice(0, -1);
    past.current.push(state);

    setState(next);
  }, [state]);

  return {
    state,
    setState,
    update,
    undo,
    redo,
    canUndo: past.current.length > 0,
    canRedo: future.current.length > 0,
  };
}