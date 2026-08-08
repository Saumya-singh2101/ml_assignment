const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function analyzeCanvas(payload) {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data?.detail || "Analysis failed");
  }

  return data;
}

export async function fetchAnalytics() {
  const response = await fetch(`${API_BASE}/api/analytics`);
  if (!response.ok) throw new Error("Could not load analytics");
  return response.json();
}

export { API_BASE };
