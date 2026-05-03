import { useCallback, useEffect, useState } from "react";
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import { Bar, Line, Pie } from "react-chartjs-2";
import { api, type AllocationPayload, type TimelinePayload } from "./api";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const chartFont = { family: "DM Sans, system-ui, sans-serif" };

export default function ChartsPanel() {
  const [tl, setTl] = useState<TimelinePayload | null>(null);
  const [alloc, setAlloc] = useState<AllocationPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const [a, b] = await Promise.all([api.chartTimeline(), api.chartAllocation()]);
      setTl(a);
      setAlloc(b);
    } catch (e) {
      setErr(String(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const equityData =
    tl && tl.equity_series.length > 0
      ? {
          labels: tl.equity_series.map((x) =>
            new Date(x.date).toLocaleDateString("pl-PL", { day: "2-digit", month: "short" })
          ),
          datasets: [
            {
              label: "Wartość całkowita (PLN)",
              data: tl.equity_series.map((x) => x.total_equity_pln),
              borderColor: "#c9a227",
              backgroundColor: "rgba(201, 162, 39, 0.15)",
              fill: true,
              tension: 0.25,
            },
            {
              label: "Papiery (PLN)",
              data: tl.equity_series.map((x) => x.holdings_pln),
              borderColor: "#5cb88a",
              backgroundColor: "transparent",
              tension: 0.2,
            },
            {
              label: "Gotówka (PLN)",
              data: tl.equity_series.map((x) => x.cash_pln),
              borderColor: "#8fa99a",
              backgroundColor: "transparent",
              tension: 0.2,
            },
          ],
        }
      : null;

  const divBar =
    tl && tl.dividends.length > 0
      ? {
          labels: tl.dividends.map((d) =>
            `${new Date(d.date).toLocaleDateString("pl-PL")} ${d.ticker}`
          ),
          datasets: [
            {
              label: "Dywidenda (PLN)",
              data: tl.dividends.map((d) => d.amount_pln),
              backgroundColor: "rgba(201, 162, 39, 0.65)",
            },
          ],
        }
      : null;

  const pieData =
    alloc && alloc.slices.length > 0
      ? {
          labels: alloc.slices.map((s) => (s.ticker === "CASH" ? "Gotówka" : s.label)),
          datasets: [
            {
              data: alloc.slices.map((s) => s.value_pln),
              backgroundColor: [
                "#c9a227",
                "#5cb88a",
                "#6b9bd1",
                "#e07a6e",
                "#a78bfa",
                "#f472b6",
                "#94a3b8",
                "#22d3ee",
                "#fb923c",
                "#4ade80",
              ],
            },
          ],
        }
      : null;

  return (
    <>
      {err && <div className="card error">{err}</div>}
      <div className="card">
        <h2>Wykresy</h2>
        <p className="muted">
          Historia to zapisane snapshoty (scheduler / odświeżanie cen / zmiany w portfelu). Ostatni punkt na wykresie
          pokazuje zawsze aktualne łącznie (jak w zakładce Portfel).
        </p>
        <button type="button" className="btn btn-ghost" style={{ marginBottom: "1rem" }} onClick={() => void load()}>
          Odśwież wykresy
        </button>
      </div>

      <div className="card">
        <h3>Wartość portfela w czasie</h3>
        {equityData ? (
          <div style={{ maxHeight: 320, position: "relative" }}>
            <Line
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { labels: { color: "#e8f0eb", ...chartFont } },
                },
                scales: {
                  x: { ticks: { color: "#8fa99a", ...chartFont }, grid: { color: "#2d3d35" } },
                  y: { ticks: { color: "#8fa99a", ...chartFont }, grid: { color: "#2d3d35" } },
                },
              }}
              data={equityData}
            />
          </div>
        ) : (
          <p className="muted">Brak zapisanych snapshotów — odśwież ceny na pozycjach (przycisk „Odśwież ceny”).</p>
        )}
      </div>

      <div className="card">
        <h3>Wypłaty dywidend (kwoty)</h3>
        {divBar ? (
          <div style={{ maxHeight: 320, position: "relative" }}>
            <Bar
              options={{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: "y" as const,
                plugins: {
                  legend: { display: false },
                },
                scales: {
                  x: { ticks: { color: "#8fa99a", ...chartFont }, grid: { color: "#2d3d35" } },
                  y: { ticks: { color: "#8fa99a", ...chartFont, maxRotation: 0 }, grid: { color: "#2d3d35" } },
                },
              }}
              data={divBar}
            />
          </div>
        ) : (
          <p className="muted">Brak zapisanych dywidend — dodaj w zakładce Portfel.</p>
        )}
      </div>

      <div className="card">
        <h3>Struktura (wartość rynkowa + gotówka)</h3>
        {pieData ? (
          <div style={{ maxHeight: 360, position: "relative", margin: "0 auto", maxWidth: 400 }}>
            <Pie
              options={{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                  legend: {
                    position: "bottom",
                    labels: { color: "#e8f0eb", ...chartFont },
                  },
                },
              }}
              data={pieData}
            />
          </div>
        ) : (
          <p className="muted">Brak pozycji z ceną lub brak danych do wykresu.</p>
        )}
      </div>
    </>
  );
}
