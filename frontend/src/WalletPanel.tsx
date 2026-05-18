import { useCallback, useEffect, useState } from "react";
import {
  api,
  type CashDeposit,
  type DividendForecastResponse,
  type DividendReceipt,
  type WalletSummary,
} from "./api";

export default function WalletPanel({ onChanged }: { onChanged: () => Promise<void> }) {
  const [sum, setSum] = useState<WalletSummary | null>(null);
  const [deposits, setDeposits] = useState<CashDeposit[]>([]);
  const [divs, setDivs] = useState<DividendReceipt[]>([]);
  const [depAmt, setDepAmt] = useState("");
  const [depNote, setDepNote] = useState("");
  const [divTicker, setDivTicker] = useState("");
  const [divAmt, setDivAmt] = useState("");
  const [divNote, setDivNote] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [forecast, setForecast] = useState<DividendForecastResponse | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const [s, d, v] = await Promise.all([api.walletSummary(), api.deposits(), api.dividends()]);
      setSum(s);
      setDeposits(d);
      setDivs(v);
    } catch (e) {
      setErr(String(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const loadForecastCached = useCallback(async () => {
    setErr(null);
    try {
      const f = await api.dividendForecast(365);
      if (f.from_cache || f.holdings.length > 0) {
        setForecast(f);
      }
    } catch (e) {
      setErr(String(e));
    }
  }, []);

  useEffect(() => {
    void loadForecastCached();
  }, [loadForecastCached]);

  async function addDep(e: React.FormEvent) {
    e.preventDefault();
    const a = parseFloat(depAmt.replace(",", "."));
    if (!(a > 0)) return;
    await api.addDeposit({ amount_pln: a, note: depNote || null });
    setDepAmt("");
    setDepNote("");
    await load();
    await onChanged();
  }

  async function loadForecast(refresh = true) {
    setErr(null);
    setForecastLoading(true);
    try {
      const f = await api.dividendForecast(365, { refresh });
      setForecast(f);
    } catch (e) {
      setErr(String(e));
    } finally {
      setForecastLoading(false);
    }
  }

  async function addDiv(e: React.FormEvent) {
    e.preventDefault();
    const a = parseFloat(divAmt.replace(",", "."));
    if (!divTicker.trim() || !(a > 0)) return;
    await api.addDividend({ ticker: divTicker.trim(), amount_pln: a, note: divNote || null });
    setDivTicker("");
    setDivAmt("");
    setDivNote("");
    await load();
    await onChanged();
  }

  return (
    <>
      {err ? <div className="card alert-card">{err}</div> : null}

      {sum && (
        <div className="card">
          <h2>Podsumowanie (PLN)</h2>
          <div className="stat-grid">
            <div className="stat-item">
              <div className="stat-item__label">Wpłaty na konto</div>
              <div className="stat-item__value">{sum.deposits_total_pln.toFixed(2)}</div>
            </div>
            <div className="stat-item">
              <div className="stat-item__label">Dywidendy (wpływy)</div>
              <div className="stat-item__value">{sum.dividends_total_pln.toFixed(2)}</div>
            </div>
            <div className="stat-item">
              <div className="stat-item__label">Zainwestowane (koszt)</div>
              <div className="stat-item__value">{sum.invested_pln.toFixed(2)}</div>
            </div>
            <div className="stat-item">
              <div className="stat-item__label">Gotówka dostępna</div>
              <div className="stat-item__value">{sum.cash_available_pln.toFixed(2)}</div>
            </div>
            <div className="stat-item">
              <div className="stat-item__label">Wartość rynkowa</div>
              <div className="stat-item__value">{sum.holdings_market_pln.toFixed(2)}</div>
            </div>
            <div className="stat-item stat-item--highlight">
              <div className="stat-item__label">Łącznie (rynek + gotówka)</div>
              <div className="stat-item__value">{sum.total_equity_pln.toFixed(2)}</div>
            </div>
          </div>
          <p className="muted" style={{ marginTop: "0.75rem" }}>
            Gotówka = wpłaty + dywidendy − suma kosztów zakupów (z lotów). Kursy USD/EUR → PLN ustaw w Ustawieniach.
          </p>
        </div>
      )}

      <div className="card">
        <h2>Prognoza dywidend (z Yahoo)</h2>
        <p className="muted">
          Ostatnia prognoza jest zapisywana na serwerze (bez ponownego odpytywania Yahoo przy każdym wejściu). Kwoty
          są dopasowywane do bieżących lotów; pełne odświeżenie z Yahoo — przyciskiem lub automatycznie raz na dobę.
        </p>
        {forecast?.generated_at_utc ? (
          <p className="muted" style={{ marginTop: 0, fontSize: "0.85rem" }}>
            Wygenerowano:{" "}
            {new Date(forecast.generated_at_utc).toLocaleString("pl-PL")}
            {forecast.from_cache ? " (z cache)" : ""}
            {forecast.shares_resynced ? " · ilości zsynchronizowane z portfelem" : ""}
            {forecast.refresh_recommended ? " · zalecane pełne odświeżenie" : ""}
          </p>
        ) : null}
        <button
          type="button"
          className="btn btn-primary"
          style={{ marginBottom: "1rem" }}
          disabled={forecastLoading}
          onClick={() => void loadForecast(true)}
        >
          {forecastLoading ? "Liczenie…" : forecast ? "Odśwież z Yahoo" : "Oblicz prognozę"}
        </button>
        {forecast && (
          <>
            <div className="row" style={{ gap: "1.25rem", marginBottom: "1rem", flexWrap: "wrap" }}>
              <div>
                <div className="muted">Szac. dywidendy (12 m, suma pozycji)</div>
                <strong>{forecast.total_trailing_12m_pln_estimate.toFixed(2)} PLN</strong>
              </div>
              <div>
                <div className="muted">Szac. w oknie {forecast.horizon_days} dni (suma zaplanowanych wpłat)</div>
                <strong>{forecast.total_upcoming_horizon_pln_estimate.toFixed(2)} PLN</strong>
              </div>
            </div>
            {forecast.holdings.length === 0 ? (
              <p className="muted">Brak lotów w portfelu.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead>
                    <tr>
                      <th>Ticker</th>
                      <th>Ilość</th>
                      <th>12 m (PLN)</th>
                      <th>Następne (szac.)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecast.holdings.map((h) => (
                      <tr key={h.ticker}>
                        <td>
                          <strong>{h.ticker}</strong>
                          {h.note ? (
                            <div className="muted" style={{ fontSize: "0.8rem", marginTop: "0.2rem" }}>
                              {h.note}
                            </div>
                          ) : null}
                        </td>
                        <td>{h.shares}</td>
                        <td>{h.trailing_12m_pln_estimate.toFixed(2)}</td>
                        <td>
                          {h.upcoming.length === 0 ? (
                            <span className="muted">—</span>
                          ) : (
                            <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
                              {h.upcoming.map((u) => (
                                <li key={u.estimated_date}>
                                  {new Date(u.estimated_date + "T12:00:00").toLocaleDateString("pl-PL")}:{" "}
                                  <strong>{u.amount_pln_estimate.toFixed(2)}</strong> PLN
                                </li>
                              ))}
                            </ul>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>
              {forecast.disclaimer}
            </p>
          </>
        )}
      </div>

      <div className="card">
        <h2>Wpłata na portfel</h2>
        <form onSubmit={(e) => void addDep(e)} className="row">
          <div className="field" style={{ flex: "0 1 140px", marginBottom: 0 }}>
            <label>Kwota PLN</label>
            <input value={depAmt} onChange={(e) => setDepAmt(e.target.value)} inputMode="decimal" />
          </div>
          <div className="field" style={{ flex: "1 1 200px", marginBottom: 0 }}>
            <label>Notatka</label>
            <input value={depNote} onChange={(e) => setDepNote(e.target.value)} placeholder="np. przelew 500" />
          </div>
          <button type="submit" className="btn btn-primary">
            Zapisz wpłatę
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Dywidenda (wpływ PLN)</h2>
        <form onSubmit={(e) => void addDiv(e)} className="row">
          <div className="field" style={{ flex: "0 1 120px", marginBottom: 0 }}>
            <label>Ticker</label>
            <input value={divTicker} onChange={(e) => setDivTicker(e.target.value)} placeholder="PZU.WA" />
          </div>
          <div className="field" style={{ flex: "0 1 120px", marginBottom: 0 }}>
            <label>Kwota PLN</label>
            <input value={divAmt} onChange={(e) => setDivAmt(e.target.value)} inputMode="decimal" />
          </div>
          <div className="field" style={{ flex: "1 1 180px", marginBottom: 0 }}>
            <label>Notatka</label>
            <input value={divNote} onChange={(e) => setDivNote(e.target.value)} />
          </div>
          <button type="submit" className="btn btn-primary">
            Zapisz dywidendę
          </button>
        </form>
      </div>

      <div className="card">
        <h2>Historia wpłat</h2>
        {deposits.length === 0 ? (
          <p className="muted">Brak.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Kwota</th>
                <th>Data</th>
                <th>Notatka</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {deposits.map((d) => (
                <tr key={d.id}>
                  <td>{d.amount_pln.toFixed(2)}</td>
                  <td className="muted">{new Date(d.received_at).toLocaleString("pl-PL")}</td>
                  <td className="muted">{d.note ?? "—"}</td>
                  <td>
                    <button
                      type="button"
                      className="btn-danger"
                      onClick={() => void api.deleteDeposit(d.id).then(() => load()).then(() => onChanged())}
                    >
                      Usuń
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h2>Historia dywidend</h2>
        {divs.length === 0 ? (
          <p className="muted">Brak.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Kwota</th>
                <th>Data</th>
                <th>Notatka</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {divs.map((d) => (
                <tr key={d.id}>
                  <td>{d.ticker}</td>
                  <td>{d.amount_pln.toFixed(2)}</td>
                  <td className="muted">{new Date(d.received_at).toLocaleString("pl-PL")}</td>
                  <td className="muted">{d.note ?? "—"}</td>
                  <td>
                    <button
                      type="button"
                      className="btn-danger"
                      onClick={() => void api.deleteDividend(d.id).then(() => load()).then(() => onChanged())}
                    >
                      Usuń
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
