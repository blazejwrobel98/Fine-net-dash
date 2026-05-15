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
import { type ChartColorScheme, chartPalette } from "./chartTheme";

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

const chartFont = { family: "'Plus Jakarta Sans', system-ui, sans-serif" };

export default function ChartsPanel({ colorScheme = "dark" }: { colorScheme?: ChartColorScheme }) {
  const pal = chartPalette(colorScheme);
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
              borderColor: pal.accent,
              backgroundColor: pal.accentFill,
              fill: true,
              tension: 0.25,
            },
            {
              label: "Papiery (PLN)",
              data: tl.equity_series.map((x) => x.holdings_pln),
              borderColor: pal.green,
              backgroundColor: "transparent",
              tension: 0.2,
            },
            {
              label: "Gotówka (PLN)",
              data: tl.equity_series.map((x) => x.cash_pln),
              borderColor: pal.mutedLine,
              backgroundColor: "transparent",
              tension: 0.2,
            },
          ],
        }
      : null;

  const depositsVsEquityData =
    tl && tl.equity_series.length > 0
      ? {
          labels: tl.equity_series.map((x) =>
            new Date(x.date).toLocaleDateString("pl-PL", { day: "2-digit", month: "short" })
          ),
          datasets: [
            {
              label: "Suma wpłat (PLN)",
              data: tl.equity_series.map((x) => x.deposits_cumulative_pln),
              borderColor: pal.mutedLine,
              backgroundColor: "transparent",
              tension: 0.2,
            },
            {
              label: "Wartość portfela (PLN)",
              data: tl.equity_series.map((x) => x.total_equity_pln),
              borderColor: pal.accent,
              backgroundColor: pal.accentFill,
              fill: true,
              tension: 0.25,
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
              backgroundColor: pal.bar,
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
              backgroundColor: pal.pie,
            },
          ],
        }
      : null;

  return (
    <>
      {err ? <div className="card alert-card">{err}</div> : null}
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
          <div className="chart-box">
            <Line
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { labels: { color: pal.legend, ...chartFont } },
                },
                scales: {
                  x: { ticks: { color: pal.tick, ...chartFont }, grid: { color: pal.grid } },
                  y: { ticks: { color: pal.tick, ...chartFont }, grid: { color: pal.grid } },
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
        <h3>Wpłaty vs wartość portfela</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          „Suma wpłat” to skumulowane wpłaty na konto (zakładka Portfel) — bez dywidend. „Wartość portfela” to
          papiery + gotówka (jak na wykresie powyżej). Ostatni punkt jest zawsze aktualny.
        </p>
        {depositsVsEquityData ? (
          <div className="chart-box">
            <Line
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { labels: { color: pal.legend, ...chartFont } },
                },
                scales: {
                  x: { ticks: { color: pal.tick, ...chartFont }, grid: { color: pal.grid } },
                  y: { ticks: { color: pal.tick, ...chartFont }, grid: { color: pal.grid } },
                },
              }}
              data={depositsVsEquityData}
            />
          </div>
        ) : (
          <p className="muted">Brak danych — dodaj wpłaty lub odśwież ceny, żeby powstały snapshoty.</p>
        )}
      </div>

      <div className="card">
        <h3>Wypłaty dywidend (kwoty)</h3>
        {divBar ? (
          <div className="chart-box">
            <Bar
              options={{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: "y" as const,
                plugins: {
                  legend: { display: false },
                },
                scales: {
                  x: { ticks: { color: pal.tick, ...chartFont }, grid: { color: pal.grid } },
                  y: { ticks: { color: pal.tick, ...chartFont, maxRotation: 0 }, grid: { color: pal.grid } },
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
          <div className="chart-box chart-box--pie">
            <Pie
              options={{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                  legend: {
                    position: "bottom",
                    labels: { color: pal.legend, ...chartFont },
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
