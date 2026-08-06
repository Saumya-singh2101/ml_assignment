import type { Point } from "../models/stroke";

export function getPointerPoints(
  event: PointerEvent,
  transformPoint: (x: number, y: number) => Point
): Point[] {
  const events =
    typeof event.getCoalescedEvents === "function"
      ? event.getCoalescedEvents()
      : [event];

  return events.map((e) =>
    transformPoint(e.clientX, e.clientY)
  );
}