/** Kolory wykresów dopasowane do motywu UI (Chart.js nie czyta CSS variables wprost). */

export type ChartColorScheme = "dark" | "light";

export function chartPalette(scheme: ChartColorScheme) {
  if (scheme === "light") {
    return {
      tick: "#64748b",
      grid: "#e2e8f0",
      legend: "#0f172a",
      accent: "#ca8a04",
      accentFill: "rgba(202, 138, 4, 0.15)",
      green: "#059669",
      mutedLine: "#94a3b8",
      bar: "rgba(202, 138, 4, 0.72)",
      pie: [
        "#ca8a04",
        "#059669",
        "#2563eb",
        "#dc2626",
        "#7c3aed",
        "#db2777",
        "#64748b",
        "#0891b2",
        "#ea580c",
        "#16a34a",
      ],
    };
  }
  return {
    tick: "#94a3b8",
    grid: "#334155",
    legend: "#f1f5f9",
    accent: "#fbbf24",
    accentFill: "rgba(251, 191, 36, 0.14)",
    green: "#34d399",
    mutedLine: "#64748b",
    bar: "rgba(251, 191, 36, 0.62)",
    pie: [
      "#fbbf24",
      "#34d399",
      "#60a5fa",
      "#f87171",
      "#a78bfa",
      "#f472b6",
      "#94a3b8",
      "#22d3ee",
      "#fb923c",
      "#4ade80",
    ],
  };
}
