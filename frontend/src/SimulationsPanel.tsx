import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";
import {
  api,
  type ForwardSimulation,
  type LookbackSimulation,
  type SimulationSavedSummary,
} from "./api";
import { type ChartColorScheme, chartPalette } from "./chartTheme";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const chartFont = { family: "'Plus Jakarta Sans', system-ui, sans-serif" };

export default function SimulationsPanel({ colorScheme = "dark" }: { colorScheme?: ChartColorScheme }) {
  const pal = chartPalette(colorScheme);
  const [yearsBack, setYearsBack] = useState(1);
  const [yearsFwd, setYearsFwd] = useState(10);
  const [returnPct, setReturnPct] = useState(7);
  const [divPct, setDivPct] = useState(3);
  const [monthlyDep, setMonthlyDep] = useState(0);
  const [lookback, setLookback] = useState<LookbackSimulation | null>(null);
  const [forward, setForward] = useState<ForwardSimulation | null>(null);
  const [saved, setSaved] = useState<SimulationSavedSummary[]>([]);
  const [loadingLb, setLoadingLb] = useState(false);
  const [loadingFwd, setLoadingFwd] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const refreshSavedList = useCallback(async () => {
    try {
      const r = await api.simulationsSavedList();
      setSaved(r.items);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    void refreshSavedList();
  }, [refreshSavedList]);

  const loadSaved = useCallback(
    async (item: SimulationSavedSummary) => {
      setErr(null);
      if (item.kind === "forward") {
        setLoadingFwd(true);
        try {
          const f = await api.simulationForward(
            {
              yearsForward: yearsFwd,
              annualReturnPct: returnPct,
              dividendYieldPct: divPct,
              monthlyDepositPln: monthlyDep,
            },
            { savedId: item.id }
          );
          setForward(f);
          setYearsFwd(f.years_forward);
          setReturnPct(f.annual_return_pct);
          setDivPct(f.dividend_yield_pct);
          setMonthlyDep(f.monthly_deposit_pln);
        } catch (e) {
          setErr(String(e));
        } finally {
          setLoadingFwd(false);
        }
      } else {
        setLoadingLb(true);
        try {
          const lb = await api.simulationLookback(yearsBack, { savedId: item.id });
          setLookback(lb);
          setYearsBack(lb.years_back);
        } catch (e) {
          setErr(String(e));
        } finally {
          setLoadingLb(false);
        }
      }
    },
    [yearsBack, yearsFwd, returnPct, divPct, monthlyDep]
  );

  useEffect(() => {
    const latestLb = saved.find((s) => s.kind === "lookback");
    const latestFwd = saved.find((s) => s.kind === "forward");
    if (latestLb && !lookback) void loadSaved(latestLb);
    if (latestFwd && !forward) void loadSaved(latestFwd);
  }, [saved, lookback, forward, loadSaved]);

  const loadLookback = useCallback(async () => {
    setLoadingLb(true);
    setErr(null);
    try {
      const lb = await api.simulationLookback(yearsBack, { save: true });
      setLookback(lb);
      await refreshSavedList();
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoadingLb(false);
    }
  }, [yearsBack, refreshSavedList]);

  const loadForward = useCallback(async () => {
    setLoadingFwd(true);
    setErr(null);
    try {
      const f = await api.simulationForward(
        {
          yearsForward: yearsFwd,
          annualReturnPct: returnPct,
          dividendYieldPct: divPct,
          monthlyDepositPln: monthlyDep,
        },
        { save: true }
      );
      setForward(f);
      await refreshSavedList();
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoadingFwd(false);
    }
  }, [yearsFwd, returnPct, divPct, monthlyDep, refreshSavedList]);

  async function deleteSaved(id: string) {
    if (!window.confirm("Usunąć zapisaną symulację?")) return;
    setErr(null);
    try {
      await api.simulationDeleteSaved(id);
      if (lookback?.saved_id === id) setLookback(null);
      if (forward?.saved_id === id) setForward(null);
      await refreshSavedList();
    } catch (e) {
      setErr(String(e));
    }
  }

  const lookbackChart = useMemo(() => {
    if (!lookback?.series.length) return null;
    const labels = lookback.series.map((x) =>
      new Date(x.date).toLocaleDateString("pl-PL", { month: "short", year: "2-digit" })
    );
    return {
      labels,
      datasets: [
        {
          label: "Wartość pozycji (gdyby trzymał od startu okna)",
          data: lookback.series.map((x) => x.holdings_value_pln ?? 0),
          borderColor: pal.accent,
          backgroundColor: pal.accentFill,
          fill: true,
          tension: 0.2,
        },
        {
          label: `Koszt zakupu przy cenach z ${lookback.start_date ?? "startu"}`,
          data: labels.map(() => lookback.virtual_cost_pln),
          borderColor: pal.mutedLine,
          borderDash: [6, 4],
          pointRadius: 0,
          tension: 0,
        },
      ],
    };
  }, [lookback, pal]);

  const forwardChart = useMemo(() => {
    if (!forward?.series.length) return null;
    return {
      labels: forward.series.map((x) =>
        new Date(x.date).toLocaleDateString("pl-PL", { month: "short", year: "2-digit" })
      ),
      datasets: [
        {
          label: "Prognoza wartości portfela (PLN)",
          data: forward.series.map((x) => x.total_equity_pln ?? 0),
          borderColor: pal.green,
          backgroundColor: "transparent",
          tension: 0.2,
        },
      ],
    };
  }, [forward, pal]);

  const chartOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: pal.legend, ...chartFont } } },
    scales: {
      x: { ticks: { color: pal.tick, ...chartFont }, grid: { color: pal.grid } },
      y: { ticks: { color: pal.tick, ...chartFont }, grid: { color: pal.grid } },
    },
  };

  return (
    <>
      {err ? <div className="card alert-card">{err}</div> : null}

      <div className="card">
        <h2>Symulacje</h2>
        <p className="muted">
          Każde obliczenie jest zapisywane na serwerze — możesz wrócić do wcześniejszych wyników bez ponownego
          odpytywania Yahoo (lookback) lub przeliczania projekcji.
        </p>
      </div>

      <div className="card">
        <h3>Zapisane symulacje</h3>
        {saved.length === 0 ? (
          <p className="muted">Brak zapisów — oblicz lookback lub projekcję poniżej.</p>
        ) : (
          <ul className="sim-saved-list" style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {saved.map((item) => (
              <li
                key={item.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.5rem 0",
                  borderBottom: "1px solid var(--border-subtle, rgba(255,255,255,0.08))",
                }}
              >
                <button
                  type="button"
                  className="btn btn-ghost"
                  style={{ flex: 1, textAlign: "left", justifyContent: "flex-start" }}
                  onClick={() => void loadSaved(item)}
                >
                  <span className="badge" style={{ marginRight: "0.5rem" }}>
                    {item.kind === "forward" ? "projekcja" : "lookback"}
                  </span>
                  {item.label}
                  <span className="muted" style={{ marginLeft: "0.5rem", fontSize: "0.8rem" }}>
                    {new Date(item.created_at_utc).toLocaleString("pl-PL")}
                  </span>
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-danger"
                  title="Usuń"
                  onClick={() => void deleteSaved(item.id)}
                >
                  Usuń
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h3>Gdybyś kupił to samo wcześniej</h3>
        <div className="row" style={{ alignItems: "flex-end", flexWrap: "wrap", gap: "1rem", marginBottom: "1rem" }}>
          <div className="field" style={{ marginBottom: 0, flex: "0 1 160px" }}>
            <label>Lata wstecz</label>
            <select value={yearsBack} onChange={(e) => setYearsBack(Number(e.target.value))}>
              <option value={1}>1 rok</option>
              <option value={2}>2 lata</option>
              <option value={3}>3 lata</option>
              <option value={5}>5 lat</option>
            </select>
          </div>
          <button type="button" className="btn btn-primary" disabled={loadingLb} onClick={() => void loadLookback()}>
            {loadingLb ? "Pobieranie historii…" : "Oblicz i zapisz lookback"}
          </button>
        </div>
        {lookback?.created_at_utc ? (
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            {lookback.from_cache ? "Z cache" : "Świeże"} · {new Date(lookback.created_at_utc).toLocaleString("pl-PL")}
            {lookback.shares_resynced ? " · ilości dopasowane do portfela" : ""}
          </p>
        ) : null}
        {lookback?.note ? <p className="muted">{lookback.note}</p> : null}
        {lookback && lookback.series.length > 0 ? (
          <>
            <div className="row" style={{ gap: "1.25rem", flexWrap: "wrap", marginBottom: "1rem" }}>
              <div>
                <div className="muted">Koszt przy cenach z początku okna</div>
                <strong>{lookback.virtual_cost_pln.toFixed(2)} PLN</strong>
              </div>
              <div>
                <div className="muted">Wartość dziś (portfel)</div>
                <strong>{lookback.current_value_pln.toFixed(2)} PLN</strong>
              </div>
              <div>
                <div className="muted">Rzeczywisty koszt zakupów (loty)</div>
                <strong>{lookback.actual_invested_pln.toFixed(2)} PLN</strong>
              </div>
            </div>
            <div className="chart-box">
              <Line options={chartOpts} data={lookbackChart!} />
            </div>
          </>
        ) : lookback && !loadingLb ? (
          <p className="muted">Brak serii — sprawdź pozycje lub historię cen.</p>
        ) : !lookback ? (
          <p className="muted">Wybierz okres i kliknij „Oblicz i zapisz” (Yahoo, może potrwać).</p>
        ) : null}
        {lookback ? (
          <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>
            {lookback.disclaimer}
          </p>
        ) : null}
      </div>

      <div className="card">
        <h3>Projekcja na przyszłość</h3>
        <div className="row" style={{ alignItems: "flex-end", flexWrap: "wrap", gap: "1rem", marginBottom: "1rem" }}>
          <div className="field" style={{ marginBottom: 0, flex: "0 1 120px" }}>
            <label>Lata</label>
            <select value={yearsFwd} onChange={(e) => setYearsFwd(Number(e.target.value))}>
              {[5, 10, 15, 20, 30].map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ marginBottom: 0, flex: "0 1 120px" }}>
            <label>Zwrot / rok (%)</label>
            <input type="number" step={0.5} value={returnPct} onChange={(e) => setReturnPct(Number(e.target.value))} />
          </div>
          <div className="field" style={{ marginBottom: 0, flex: "0 1 120px" }}>
            <label>Dyw. / rok (%)</label>
            <input type="number" step={0.5} value={divPct} onChange={(e) => setDivPct(Number(e.target.value))} />
          </div>
          <div className="field" style={{ marginBottom: 0, flex: "0 1 140px" }}>
            <label>Wpłata / mies. (PLN)</label>
            <input type="number" step={100} min={0} value={monthlyDep} onChange={(e) => setMonthlyDep(Number(e.target.value))} />
          </div>
          <button type="button" className="btn btn-primary" disabled={loadingFwd} onClick={() => void loadForward()}>
            {loadingFwd ? "Liczenie…" : "Przelicz i zapisz"}
          </button>
        </div>
        {forward?.created_at_utc ? (
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            {forward.from_cache ? "Z cache" : "Świeże"} · {new Date(forward.created_at_utc).toLocaleString("pl-PL")}
          </p>
        ) : null}
        {forward && forward.series.length > 0 ? (
          <>
            <div className="row" style={{ gap: "1.25rem", flexWrap: "wrap", marginBottom: "1rem" }}>
              <div>
                <div className="muted">Dziś</div>
                <strong>{forward.start_equity_pln.toFixed(2)} PLN</strong>
              </div>
              <div>
                <div className="muted">Za {forward.years_forward} lat (model)</div>
                <strong>{forward.end_equity_pln.toFixed(2)} PLN</strong>
              </div>
            </div>
            <div className="chart-box">
              <Line options={chartOpts} data={forwardChart!} />
            </div>
            <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>
              Założenia: zwrot {forward.annual_return_pct}%/rok, dywidenda {forward.dividend_yield_pct}%/rok (reinwest.),
              wpłata {forward.monthly_deposit_pln} PLN/mies. — {forward.disclaimer}
            </p>
          </>
        ) : null}
      </div>
    </>
  );
}
