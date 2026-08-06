export interface Point {
  x: number;
  y: number;
  pressure: number;
  timestamp: number;
}

export interface Stroke {
  id: string;
  points: Point[];
  color: string;
  width: number;
  createdAt: number;
}

export interface Viewport {
  x: number;
  y: number;
  zoom: number;
}

export type Tool =
  | "pen"
  | "eraser"
  | "select"
  | "pan";