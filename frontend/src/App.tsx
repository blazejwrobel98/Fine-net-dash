import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Globe,
  LayoutDashboard,
  LineChart as LineChartIcon,
  Moon,
  PanelLeft,
  PanelLeftClose,
  Settings as SettingsIcon,
  Sun,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import {
  api,
  type AppSettings,
  type BackupFile,
  type BuildUpdate,
  type Position,
  type PurchaseLot,
  type SaleTransaction,
  type UniverseResponse,
  type UniverseRow,
} from "./api";
import type { ChartColorScheme } from "./chartTheme";
import ChartsPanel from "./ChartsPanel";
import WalletPanel from "./WalletPanel";

type Tab = "positions" | "universe" | "wallet" | "charts" | "settings";

type ThemeMode = "dark" | "light";

const NAV_ITEMS: { id: Tab; label: string; short: string; icon: LucideIcon }[] = [
  { id: "positions", label: "Pozycje", short: "Pozycje", icon: LayoutDashboard },
  { id: "universe", label: "Lista spółek", short: "Universe", icon: Globe },
  { id: "wallet", label: "Portfel PLN", short: "Portfel", icon: Wallet },
  { id: "charts", label: "Wykresy", short: "Wykresy", icon: LineChartIcon },
  { id: "settings", label: "Ustawienia", short: "Ustaw.", icon: SettingsIcon },
];

function readInitialTheme(): ThemeMode {
  if (typeof window === "undefined") return "dark";
  const saved = window.localStorage.getItem("theme");
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function readSidebarCollapsed(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem("sidebarNavCollapsed") === "1";
}

function tabPageMeta(tab: Tab): { eyebrow: string; title: string; description: string } {
  switch (tab) {
    case "positions":
      return {
        eyebrow: "Pulpit",
        title: "Pozycje i transakcje",
        description:
          "Dodawaj loty, odświeżaj ceny z Yahoo i śledź koszt vs rynek. „Odśwież ceny” aktualizuje też wykresy w czasie.",
      };
    case "universe":
      return {
        eyebrow: "Filtry",
        title: "Lista spółek dywidendowych",
        description:
          "Przegląd universe z Yahoo: region, próg dywidendy, trend i średnia dla wybranego okresu.",
      };
    case "wallet":
      return {
        eyebrow: "Gotówka",
        title: "Portfel PLN",
        description:
          "Wpłaty, dywidendy w PLN, gotówka dostępna i prognoza z historii wypłat (szacunek).",
      };
    case "charts":
      return {
        eyebrow: "Analityka",
        title: "Wykresy portfela",
        description:
          "Snapshoty zapisane przy odświeżaniu cen i zmianach portfela — ostatni punkt pokazuje aktualną wartość.",
      };
    case "settings":
      return {
        eyebrow: "Konfiguracja",
        title: "Ustawienia i kopie zapasowe",
        description:
          "Kursy NBP / ręcznie, alerty, ntfy, harmonogram odświeżania oraz eksport i import kopii.",
      };
    default:
      return { eyebrow: "", title: "", description: "" };
  }
}
type TrendPeriod = "1d" | "1w" | "1m" | "1y" | "5y";

function regionClass(r: string) {
  if (r === "pl") return "badge-pl";
  if (r === "eu") return "badge-eu";
  return "badge-us";
}

function pickChange(row: UniverseRow, p: TrendPeriod): number | null {
  switch (p) {
    case "1d":
      return row.change_1d_pct;
    case "1w":
      return row.change_1w_pct;
    case "1m":
      return row.change_1m_pct;
    case "1y":
      return row.change_1y_pct;
    case "5y":
      return row.change_5y_pct;
    default:
      return null;
  }
}

function pickAvgPrice(row: UniverseRow, p: TrendPeriod): number | null {
  switch (p) {
    case "1d":
      return row.avg_price_1d;
    case "1w":
      return row.avg_price_1w;
    case "1m":
      return row.avg_price_1m;
    case "1y":
      return row.avg_price_1y;
    case "5y":
      return row.avg_price_5y;
    default:
      return null;
  }
}

function periodLabel(p: TrendPeriod): string {
  switch (p) {
    case "1d":
      return "1D";
    case "1w":
      return "1T";
    case "1m":
      return "1M";
    case "1y":
      return "1R";
    case "5y":
      return "5L";
    default:
      return p;
  }
}

function TrendCell({ v }: { v: number | null }) {
  if (v == null) return <td className="muted">—</td>;
  const up = v > 0;
  const down = v < 0;
  return (
    <td className={up ? "trend-up" : down ? "trend-down" : "muted"}>
      {up ? "▲ " : down ? "▼ " : ""}
      {v.toFixed(2)} %
    </td>
  );
}

type UniverseSortKey =
  | "ticker"
  | "name"
  | "sector"
  | "region"
  | "price"
  | "dividend"
  | "dividend_forward"
  | "change"
  | "avg_price_period";

function compareUniverseRows(
  a: UniverseRow,
  b: UniverseRow,
  key: UniverseSortKey,
  ascending: boolean,
  trendPeriod: TrendPeriod,
): number {
  const str = (x: string, y: string) => {
    const c = x.localeCompare(y, "pl", { sensitivity: "base" });
    return ascending ? c : -c;
  };
  const num = (x: number | null, y: number | null) => {
    if (x == null && y == null) return 0;
    if (x == null) return 1;
    if (y == null) return -1;
    return ascending ? x - y : y - x;
  };
  switch (key) {
    case "ticker":
      return str(a.ticker, b.ticker);
    case "name":
      return str(a.name, b.name);
    case "sector":
      return str(a.sector ?? "", b.sector ?? "");
    case "region":
      return str(a.region, b.region);
    case "price":
      return num(a.price, b.price);
    case "dividend":
      return num(a.dividend_yield_pct, b.dividend_yield_pct);
    case "dividend_forward":
      return num(a.dividend_yield_forward_pct, b.dividend_yield_forward_pct);
    case "change":
      return num(pickChange(a, trendPeriod), pickChange(b, trendPeriod));
    case "avg_price_period":
      return num(pickAvgPrice(a, trendPeriod), pickAvgPrice(b, trendPeriod));
    default:
      return 0;
  }
}

function SortTh({
  label,
  sortKey,
  activeKey,
  ascending,
  onSort,
}: {
  label: string;
  sortKey: UniverseSortKey;
  activeKey: UniverseSortKey;
  ascending: boolean;
  onSort: (k: UniverseSortKey) => void;
}) {
  const active = activeKey === sortKey;
  return (
    <th scope="col">
      <button
        type="button"
        className="th-sort"
        onClick={() => onSort(sortKey)}
        aria-sort={active ? (ascending ? "ascending" : "descending") : "none"}
      >
        {label}
        {active ? <span className="sort-ind">{ascending ? "▲" : "▼"}</span> : null}
      </button>
    </th>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("positions");
  const [universeData, setUniverseData] = useState<UniverseResponse | null>(null);
  const [trendPeriod, setTrendPeriod] = useState<TrendPeriod>("1d");
  const [universeSort, setUniverseSort] = useState<{ key: UniverseSortKey; asc: boolean }>({
    key: "ticker",
    asc: true,
  });
  const [positions, setPositions] = useState<Position[]>([]);
  const [lots, setLots] = useState<PurchaseLot[]>([]);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [regionFilter, setRegionFilter] = useState<string>("");
  const [minDividendPct, setMinDividendPct] = useState<string>("5");
  const [loading, setLoading] = useState(true);
  /** Tekst pod spinnerem — widać, na którym etapie jest start (dev + zwykły). */
  const [bootStatus, setBootStatus] = useState("Start…");
  const [err, setErr] = useState<string | null>(null);
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null);

  const [lotTicker, setLotTicker] = useState("");
  const [lotQty, setLotQty] = useState("1");
  const [lotPrice, setLotPrice] = useState("");
  const [tradeSide, setTradeSide] = useState<"buy" | "sell">("buy");
  const [sales, setSales] = useState<SaleTransaction[]>([]);
  const [portfolioBackups, setPortfolioBackups] = useState<BackupFile[]>([]);
  const [pricesBackups, setPricesBackups] = useState<BackupFile[]>([]);
  const [selectedPortfolioBackup, setSelectedPortfolioBackup] = useState<string>("");
  const [selectedPricesBackup, setSelectedPricesBackup] = useState<string>("");
  const [portfolioImportFile, setPortfolioImportFile] = useState<File | null>(null);
  const [pricesImportFile, setPricesImportFile] = useState<File | null>(null);
  const [serverBuild, setServerBuild] = useState<string | null>(null);
  const [buildUpdate, setBuildUpdate] = useState<BuildUpdate | null>(null);
  const [theme, setTheme] = useState<ThemeMode>(() => readInitialTheme());
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => readSidebarCollapsed());
  const [toastErrDismissed, setToastErrDismissed] = useState(false);
  const [toastOkDismissed, setToastOkDismissed] = useState(false);

  const chartScheme: ChartColorScheme = theme === "light" ? "light" : "dark";

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem("theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  useEffect(() => {
    try {
      window.localStorage.setItem("sidebarNavCollapsed", sidebarCollapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [sidebarCollapsed]);

  useEffect(() => {
    setToastErrDismissed(false);
  }, [err]);

  useEffect(() => {
    setToastOkDismissed(false);
  }, [refreshMsg]);

  const loadCore = useCallback(async () => {
    setErr(null);
    const [u, p, l, s, sl] = await Promise.all([
      api.universe(),
      api.positions(),
      api.lots(),
      api.settings(),
      api.sales(),
    ]);
    setUniverseData(u);
    setPositions(p);
    setLots(l);
    setSettings(s);
    setSales(sl);
  }, []);

  useEffect(() => {
    void api
      .version()
      .then((v) => {
        const sha = v.git_sha && v.git_sha.length >= 7 ? v.git_sha.slice(0, 7) : null;
        setServerBuild(sha ? `${v.version} · ${sha}` : v.version);
      })
      .catch(() => setServerBuild("nieznana (brak /api/version)"));
    let refreshGitHub = false;
    try {
      refreshGitHub = !sessionStorage.getItem("fnd-version-check-bust-v2");
      if (refreshGitHub) {
        sessionStorage.setItem("fnd-version-check-bust-v2", "1");
      }
    } catch {
      refreshGitHub = true;
    }
    const vLog = "[FineNetDash] sprawdzanie wersji / aktualizacji";
    console.log(`${vLog}: żądanie`, { refreshGitHub, url: `/api/version/update${refreshGitHub ? "?refresh=1" : ""}` });
    void api
      .versionUpdate({ refresh: refreshGitHub })
      .then((bu) => {
        console.log(`${vLog}: odpowiedź`, {
          current_version: bu.current_version,
          latest_version: bu.latest_version,
          update_available: bu.update_available,
          error: bu.error,
          checked_at_utc: bu.checked_at_utc,
        });
        setBuildUpdate(bu);
      })
      .catch((e) => {
        console.warn(`${vLog}: błąd (UI ukryje komunikat o update)`, e);
        setBuildUpdate(null);
      });
  }, []);

  useEffect(() => {
    setLoading(true);
    setBootStatus("Wywołuję /api/health…");
    const bootTimeoutMs = 90_000;
    let tid: ReturnType<typeof setTimeout> | undefined;
    const bootTimeout = new Promise<never>((_, reject) => {
      tid = setTimeout(
        () =>
          reject(
            new Error(
              `Przekroczono ${bootTimeoutMs / 1000} s oczekiwania na dane z API (np. /api/universe). ` +
                "Sprawdź, czy backend na porcie 8000 działa i czy nie ma zablokowanego wyjścia do sieci (Yahoo).",
            ),
          ),
        bootTimeoutMs,
      );
    });
    void api
      .health()
      .then(() => {
        setBootStatus("Health OK — pobieram universe, pozycje, loty, ustawienia (może chwilę potrwać)…");
        const core = loadCore();
        void core.catch(() => {});
        return Promise.race([core, bootTimeout]);
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : String(e);
        setBootStatus(`Błąd startu: ${msg.slice(0, 200)}`);
        setErr(
          msg.includes("Failed to fetch") || msg.includes("NetworkError")
            ? "Brak połączenia z serwerem (sprawdź, czy backend działa i czy adres w przeglądarce jest poprawny)."
            : msg,
        );
      })
      .finally(() => {
        if (tid != null) {
          clearTimeout(tid);
        }
        setLoading(false);
        setBootStatus((prev) => (prev.startsWith("Błąd startu:") ? prev : "Dane wczytane — możesz korzystać z aplikacji."));
      });
  }, [loadCore]);

  useEffect(() => {
    if (!import.meta.env.DEV) {
      return;
    }
    const w = window as unknown as { __FND_DEBUG__?: object };
    w.__FND_DEBUG__ = {
      bootStatus,
      loading,
      err,
      buildUpdate,
      hint: "W konsoli: filtr FineNetDash albo wpisz __FND_DEBUG__",
    };
  }, [bootStatus, loading, err, buildUpdate]);

  const loadUniverseFiltered = useCallback(async () => {
    try {
      const min = parseFloat(minDividendPct.replace(",", "."));
      const minVal = Number.isFinite(min) && min > 0 ? min : undefined;
      const u = await api.universe(regionFilter || undefined, minVal);
      setUniverseData(u);
    } catch (e) {
      setErr(String(e));
    }
  }, [regionFilter, minDividendPct]);

  useEffect(() => {
    if (tab === "universe") void loadUniverseFiltered();
  }, [tab, regionFilter, minDividendPct, loadUniverseFiltered]);

  async function onRefreshPrices() {
    setRefreshMsg(null);
    try {
      const r = await api.refreshPrices();
      setRefreshMsg(`Zaktualizowano ${r.updated} tickerów.`);
      if (r.failed.length) setRefreshMsg((m) => `${m} Błędy: ${r.failed.slice(0, 5).join(", ")}`);
      await loadCore();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onFetchFxFromNbp() {
    setErr(null);
    setRefreshMsg(null);
    try {
      const r = await api.refreshFx(true);
      const s = await api.settings();
      setSettings(s);
      setRefreshMsg(
        `NBP (${r.effective_date}): USD ${r.usd_pln_rate.toFixed(4)}, EUR ${r.eur_pln_rate.toFixed(4)}.` +
          (r.fx_nbp_auto ? " Tryb automatyczny (1× dziennie) jest włączony." : ""),
      );
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onAddLot(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    const qty = parseFloat(lotQty.replace(",", "."));
    const price = parseFloat(lotPrice.replace(",", "."));
    if (!lotTicker.trim() || !(qty > 0) || !(price > 0)) {
      setErr("Uzupełnij ticker, ilość i cenę.");
      return;
    }
    try {
      const r = await api.addLot({
        ticker: lotTicker.trim(),
        quantity: qty,
        price_per_share: price,
        side: tradeSide,
      });
      setLotTicker("");
      setLotQty("1");
      setLotPrice("");
      if (r.side === "sell") {
        setRefreshMsg(
          `Sprzedaż ${r.ticker}: zrealizowany wynik ${Number(r.realized_pln ?? 0).toFixed(2)} PLN, ` +
            `pozostało ${Number(r.remaining_shares ?? 0).toFixed(6)} szt.`,
        );
      } else {
        setRefreshMsg(`Zapisano zakup ${r.ticker}.`);
      }
      await loadCore();
    } catch (ex) {
      setErr(String(ex));
    }
  }

  async function onDeleteLot(id: number) {
    try {
      await api.deleteLot(id);
      await loadCore();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function saveThreshold(pct: number) {
    if (!settings) return;
    try {
      const s = await api.patchSettings({ alert_threshold_percent: pct });
      setSettings(s);
    } catch (e) {
      setErr(String(e));
    }
  }

  async function saveSettingsPartial(p: Partial<AppSettings>) {
    try {
      const s = await api.patchSettings(p);
      setSettings(s);
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onTestNtfyPing() {
    setRefreshMsg(null);
    setErr(null);
    try {
      const r = await api.testNtfy();
      if (r.ok) {
        setRefreshMsg(r.message);
      } else {
        setErr(r.message);
      }
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onCheckBuyAlerts() {
    setRefreshMsg(null);
    setErr(null);
    try {
      const r = await api.checkAlerts();
      const skip = r.skipped.length ? r.skipped.join(", ") : "—";
      const note = (r.notes && r.notes.length ? ` ${r.notes.join(" ")}` : "").trim();
      setRefreshMsg(`Warunki dokupu: wysłano ${r.sent}, pominięto: ${skip}.${note ? ` ${note}` : ""}`);
    } catch (e) {
      setErr(String(e));
    }
  }

  const loadBackupLists = useCallback(async () => {
    try {
      const [p, pr] = await Promise.all([api.listPortfolioBackups(), api.listPricesBackups()]);
      setPortfolioBackups(p.files);
      setPricesBackups(pr.files);
      if (p.files.length && !selectedPortfolioBackup) {
        // Lista z API: najpierw kopie z największą liczbą lotów, na końcu *before_restore*.
        const preferred =
          p.files.find((f) => !f.file_name.includes("before_restore")) ?? p.files[0];
        setSelectedPortfolioBackup(preferred.file_name);
      }
      if (pr.files.length && !selectedPricesBackup) setSelectedPricesBackup(pr.files[0].file_name);
    } catch (e) {
      setErr(String(e));
    }
  }, [selectedPortfolioBackup, selectedPricesBackup]);

  useEffect(() => {
    if (tab === "settings") void loadBackupLists();
  }, [tab, loadBackupLists]);

  async function onCreatePortfolioBackup() {
    try {
      const r = await api.createPortfolioBackup();
      setRefreshMsg(r.message);
      await loadBackupLists();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onExportPortfolioBackup() {
    if (!selectedPortfolioBackup) {
      setErr("Wybierz kopię portfela do eksportu.");
      return;
    }
    try {
      const blob = await api.exportPortfolioBackup(selectedPortfolioBackup);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = selectedPortfolioBackup;
      a.click();
      URL.revokeObjectURL(url);
      setRefreshMsg(`Pobrano kopię portfela: ${selectedPortfolioBackup}`);
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onImportPortfolioBackup() {
    if (!portfolioImportFile) {
      setErr("Wybierz plik kopii portfela do importu.");
      return;
    }
    try {
      const r = await api.importPortfolioBackup(portfolioImportFile);
      setRefreshMsg(r.message);
      setPortfolioImportFile(null);
      await loadBackupLists();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onRestorePortfolioBackup() {
    if (!selectedPortfolioBackup) {
      setErr("Wybierz kopię portfela do przywrócenia.");
      return;
    }
    const ok = window.confirm(
      "Przywrócenie portfela nadpisze bieżące loty/wpłaty/dywidendy/sprzedaże. Kontynuować?",
    );
    if (!ok) return;
    try {
      const r = await api.restorePortfolioBackup(selectedPortfolioBackup);
      setRefreshMsg(`${r.message}${r.records != null ? ` Rekordy: ${r.records}.` : ""}`);
      await loadCore();
      await loadBackupLists();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onCreatePricesBackup() {
    try {
      const r = await api.createPricesBackup();
      setRefreshMsg(r.message);
      await loadBackupLists();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onExportPricesBackup() {
    if (!selectedPricesBackup) {
      setErr("Wybierz kopię listy spółek do eksportu.");
      return;
    }
    try {
      const blob = await api.exportPricesBackup(selectedPricesBackup);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = selectedPricesBackup;
      a.click();
      URL.revokeObjectURL(url);
      setRefreshMsg(`Pobrano kopię listy spółek: ${selectedPricesBackup}`);
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onImportPricesBackup() {
    if (!pricesImportFile) {
      setErr("Wybierz plik kopii listy spółek do importu.");
      return;
    }
    try {
      const r = await api.importPricesBackup(pricesImportFile);
      setRefreshMsg(r.message);
      setPricesImportFile(null);
      await loadBackupLists();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onRestorePricesBackup() {
    if (!selectedPricesBackup) {
      setErr("Wybierz kopię listy spółek do przywrócenia.");
      return;
    }
    const ok = window.confirm(
      "Przywrócenie listy spółek odtworzy cache cen z wybranej kopii. Kontynuować?",
    );
    if (!ok) return;
    try {
      const r = await api.restorePricesBackup(selectedPricesBackup);
      setRefreshMsg(`${r.message}${r.records != null ? ` Rekordy: ${r.records}.` : ""}`);
      await loadCore();
      await loadBackupLists();
    } catch (e) {
      setErr(String(e));
    }
  }

  const stocks = universeData?.stocks ?? [];
  const sortedUniverseStocks = useMemo(() => {
    const list = [...stocks];
    list.sort((a, b) =>
      compareUniverseRows(a, b, universeSort.key, universeSort.asc, trendPeriod),
    );
    return list;
  }, [stocks, universeSort, trendPeriod]);

  const onUniverseSort = useCallback((key: UniverseSortKey) => {
    setUniverseSort((prev) =>
      prev.key === key ? { key, asc: !prev.asc } : { key, asc: true },
    );
  }, []);

  const lastPx = universeData?.last_prices_update
    ? new Date(universeData.last_prices_update).toLocaleString("pl-PL")
    : null;

  const page = tabPageMeta(tab);
  const mobileTitle = NAV_ITEMS.find((n) => n.id === tab)?.label ?? "";

  if (loading && !settings) {
    return (
      <div className="shell-loading">
        <div className="shell-loading__card">
          <div className="shell-loading__spinner" aria-hidden />
          <p className="muted" style={{ margin: 0 }}>
            Łączenie z API…
          </p>
          <p className="muted" style={{ margin: "0.75rem 0 0", fontSize: "0.82rem", lineHeight: 1.45 }}>
            {bootStatus}
          </p>
          <p className="muted" style={{ margin: "0.5rem 0 0", fontSize: "0.75rem", lineHeight: 1.4 }}>
            Backend musi działać na <strong>http://127.0.0.1:8000</strong> (Vite proxy z portu 5173/5174).
            W konsoli (F12) wpisz <code style={{ fontSize: "0.85em" }}>__FND_DEBUG__</code> — obiekt diagnostyczny
            (tryb dev).
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
    <div className={`app-shell${sidebarCollapsed ? " app-shell--nav-collapsed" : ""}`}>
      <aside className="app-sidebar" aria-label="Nawigacja główna">
        <div className="app-sidebar__brand">
          <div className="app-sidebar__brand-top">
            <div className="app-sidebar__logo" aria-hidden>
              PD
            </div>
            <button
              type="button"
              className="sidebar-collapse-btn"
              onClick={() => setSidebarCollapsed((c) => !c)}
              aria-pressed={sidebarCollapsed}
              aria-label={sidebarCollapsed ? "Rozwiń panel boczny" : "Zwiń panel boczny (same ikony)"}
              title={sidebarCollapsed ? "Rozwiń panel" : "Zwiń panel — same ikony"}
            >
              {sidebarCollapsed ? (
                <PanelLeft size={18} strokeWidth={2} aria-hidden />
              ) : (
                <PanelLeftClose size={18} strokeWidth={2} aria-hidden />
              )}
            </button>
          </div>
          <div className="app-sidebar__titles">
            <h1>Portfel dywidendowy</h1>
            <p>Yahoo Finance, NBP — uruchomienie lokalne</p>
          </div>
        </div>
        <nav className="app-nav">
          {NAV_ITEMS.map(({ id, label, short, icon: Icon }) => (
            <button
              key={id}
              type="button"
              className={`app-nav__btn${tab === id ? " is-active" : ""}`}
              onClick={() => setTab(id)}
              title={label}
              aria-label={label}
            >
              <Icon size={20} strokeWidth={2} aria-hidden />
              <span className="nav-label-full" aria-hidden="true">
                {label}
              </span>
              <span className="nav-label-mobile" aria-hidden="true">
                {short}
              </span>
            </button>
          ))}
        </nav>
        <div className="app-sidebar__footer">
          <div className="app-sidebar__version-block">
            {buildUpdate?.update_available ? (
              <div
                className="app-update-notice"
                role="status"
                aria-live="polite"
                aria-label={`Dostępna aktualizacja, wersja ${buildUpdate.latest_version ?? "nowsza"}`}
              >
                <span className="app-update-notice__text">
                  <span className="app-update-notice__eyebrow">Dostępna aktualizacja</span>
                  <span className="app-update-notice__version">{buildUpdate.latest_version ?? "nowsza wersja"}</span>
                </span>
              </div>
            ) : null}
            <div className="app-build-pill" role="status" title={serverBuild ?? undefined}>
              <strong>Build</strong> {serverBuild ?? "…"}
            </div>
          </div>
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            aria-label={theme === "dark" ? "Włącz tryb jasny" : "Włącz tryb ciemny"}
            title={theme === "dark" ? "Tryb jasny" : "Tryb ciemny"}
          >
            {theme === "dark" ? <Sun size={16} strokeWidth={2} aria-hidden /> : <Moon size={16} strokeWidth={2} aria-hidden />}
            <span className="theme-toggle__label" aria-hidden="true">
              {theme === "dark" ? "Tryb jasny" : "Tryb ciemny"}
            </span>
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div className="app-topbar__row">
            <span className="app-topbar__title">{mobileTitle}</span>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
              aria-label={theme === "dark" ? "Włącz tryb jasny" : "Włącz tryb ciemny"}
            >
              {theme === "dark" ? <Sun size={18} strokeWidth={2} /> : <Moon size={18} strokeWidth={2} />}
            </button>
          </div>
          <div className="app-topbar__version" aria-label="Wersja aplikacji">
            {buildUpdate?.update_available ? (
              <div
                className="app-update-notice app-update-notice--topbar"
                role="status"
                aria-live="polite"
                aria-label={`Dostępna aktualizacja, wersja ${buildUpdate.latest_version ?? "nowsza"}`}
              >
                <span className="app-update-notice__text">
                  <span className="app-update-notice__eyebrow">Dostępna aktualizacja</span>
                  <span className="app-update-notice__version">{buildUpdate.latest_version ?? "nowsza wersja"}</span>
                </span>
              </div>
            ) : null}
            <div className="app-build-pill app-build-pill--topbar" role="status" title={serverBuild ?? undefined}>
              <strong>Build</strong> {serverBuild ?? "…"}
            </div>
          </div>
        </header>

        <div className="app-main__inner">
          <div className="pre-alpha-banner" role="status">
            <strong>Wersja robocza (pre-alfa).</strong> Uruchamiaj lokalnie lub w zaufanej sieci — nie udostępniaj
            publicznie bez zabezpieczeń (brak logowania do API). Szczegóły w repozytorium.
          </div>

          <div className="page-header">
            <p className="page-header__eyebrow">{page.eyebrow}</p>
            <h2>{page.title}</h2>
            <p>{page.description}</p>
          </div>

      {tab === "positions" && (
        <>
          <div className="card">
            <h2>Transakcja (kupno / sprzedaż)</h2>
            <form onSubmit={onAddLot}>
              <div className="row">
                <div className="field" style={{ flex: "0 1 150px" }}>
                  <label htmlFor="side">Tryb</label>
                  <select
                    id="side"
                    value={tradeSide}
                    onChange={(e) => setTradeSide(e.target.value as "buy" | "sell")}
                  >
                    <option value="buy">Kupno</option>
                    <option value="sell">Sprzedaż</option>
                  </select>
                </div>
                <div className="field" style={{ flex: "1 1 140px" }}>
                  <label htmlFor="ticker">Ticker</label>
                  <input
                    id="ticker"
                    value={lotTicker}
                    onChange={(e) => setLotTicker(e.target.value)}
                    placeholder="PZU.WA"
                  />
                </div>
                <div className="field" style={{ flex: "0 1 120px" }}>
                  <label htmlFor="qty">Ilość</label>
                  <input
                    id="qty"
                    value={lotQty}
                    onChange={(e) => setLotQty(e.target.value)}
                    inputMode="decimal"
                  />
                </div>
                <div className="field" style={{ flex: "0 1 140px" }}>
                  <label htmlFor="price">Cena / szt. (waluta tickera)</label>
                  <input
                    id="price"
                    value={lotPrice}
                    onChange={(e) => setLotPrice(e.target.value)}
                    inputMode="decimal"
                    placeholder="0.00"
                  />
                </div>
                <button type="submit" className="btn btn-primary">
                  {tradeSide === "buy" ? "Zapisz zakup" : "Zapisz sprzedaż"}
                </button>
                <button type="button" className="btn btn-ghost" onClick={() => void onRefreshPrices()}>
                  Odśwież ceny
                </button>
              </div>
            </form>
          </div>

          <div className="card">
            <h2>Podsumowanie pozycji</h2>
            {positions.length === 0 ? (
              <p className="muted">Brak pozycji — dodaj pierwszy zakup.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead>
                    <tr>
                      <th>Ticker</th>
                      <th>Ilość</th>
                      <th>Śr. kupno</th>
                      <th>Cena</th>
                      <th>vs średnia</th>
                      <th>Koszt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((p) => (
                      <tr key={p.ticker}>
                        <td>
                          <strong>{p.ticker}</strong>
                        </td>
                        <td>{p.total_shares}</td>
                        <td>{p.avg_buy_price.toFixed(4)}</td>
                        <td>{p.current_price != null ? p.current_price.toFixed(4) : "—"}</td>
                        <td
                          className={
                            p.pct_vs_avg != null && p.pct_vs_avg < 0 ? "pct-good" : "pct-bad"
                          }
                        >
                          {p.pct_vs_avg != null ? `${p.pct_vs_avg.toFixed(2)} %` : "—"}
                        </td>
                        <td>{p.total_cost.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="muted" style={{ marginTop: "0.75rem" }}>
              Ujemny % vs średnia = cena poniżej średniego kosztu otwartych lotów.
            </p>
          </div>

          <div className="card">
            <h2>Historia lotów</h2>
            {lots.length === 0 ? (
              <p className="muted">Brak zapisanych lotów.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Ilość</th>
                    <th>Cena</th>
                    <th>Data</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {lots.map((l) => (
                    <tr key={l.id}>
                      <td>{l.ticker}</td>
                      <td>{l.quantity}</td>
                      <td>
                        {l.price_per_share} {l.currency ? <span className="muted">{l.currency}</span> : null}
                      </td>
                      <td className="muted">{new Date(l.purchased_at).toLocaleString("pl-PL")}</td>
                      <td>
                        <button type="button" className="btn-danger" onClick={() => void onDeleteLot(l.id)}>
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
            <h2>Historia sprzedaży (FIFO)</h2>
            {sales.length === 0 ? (
              <p className="muted">Brak sprzedaży.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Ilość</th>
                    <th>Cena</th>
                    <th>Wpływ PLN</th>
                    <th>Koszt FIFO PLN</th>
                    <th>Wynik PLN</th>
                    <th>Data</th>
                  </tr>
                </thead>
                <tbody>
                  {sales.map((s) => (
                    <tr key={s.id}>
                      <td>{s.ticker}</td>
                      <td>{s.quantity}</td>
                      <td>
                        {s.price_per_share} {s.currency ?? ""}
                      </td>
                      <td>{s.proceeds_pln.toFixed(2)}</td>
                      <td>{s.cost_basis_pln.toFixed(2)}</td>
                      <td className={s.realized_pln >= 0 ? "trend-up" : "trend-down"}>
                        {s.realized_pln.toFixed(2)}
                      </td>
                      <td className="muted">{new Date(s.sold_at).toLocaleString("pl-PL")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {tab === "universe" && (
        <div className="card">
          <h2>Lista spółek ({stocks.length})</h2>
          <p className="muted">
            Ostatnie pobranie cen (globalnie):{" "}
            <strong>{lastPx ?? "brak — kliknij Odśwież ceny na pozycjach"}</strong>
          </p>
          <div className="row" style={{ marginBottom: "1rem", alignItems: "center", flexWrap: "wrap" }}>
            <div className="field" style={{ marginBottom: 0, flex: "0 1 200px" }}>
              <label htmlFor="reg">Region</label>
              <select
                id="reg"
                value={regionFilter}
                onChange={(e) => setRegionFilter(e.target.value)}
              >
                <option value="">Wszystkie</option>
                <option value="pl">PL</option>
                <option value="eu">Europa</option>
                <option value="us">USA</option>
              </select>
            </div>
            <div className="field" style={{ marginBottom: 0, flex: "0 1 140px" }}>
              <label htmlFor="mindiv">Min dywidenda %</label>
              <input
                id="mindiv"
                type="number"
                min={0}
                max={50}
                step={0.5}
                value={minDividendPct}
                onChange={(e) => setMinDividendPct(e.target.value)}
                placeholder="5"
              />
            </div>
            <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
              <span className="muted" style={{ marginRight: "0.25rem" }}>
                Zwrot / trend
              </span>
              <div className="segmented" role="group" aria-label="Okres trendu">
                {(["1d", "1w", "1m", "1y", "5y"] as const).map((p) => (
                  <button
                    key={p}
                    type="button"
                    className={trendPeriod === p ? "btn btn-primary" : "btn btn-ghost"}
                    onClick={() => setTrendPeriod(p)}
                  >
                    {periodLabel(p)}
                  </button>
                ))}
              </div>
            </div>
            <button type="button" className="btn btn-ghost" onClick={() => void loadUniverseFiltered()}>
              Odśwież tabelę
            </button>
          </div>
          <p className="muted" style={{ marginBottom: "0.75rem" }}>
            Domyślnie widać tylko spółki z dywidendą ≥ 5% (wg Yahoo trailing po odświeżeniu cen). Wpisz 0 lub wyczyść
            pole min., żeby zobaczyć całe universe. „Zwrot” to zmiana ceny %, a „Śr. cena” to średnia cena zamknięcia
            dla wybranego okresu (1D/1M/1R/5L).
          </p>
          <div style={{ overflowX: "auto", maxHeight: "72vh", overflowY: "auto" }}>
            <table>
              <thead>
                <tr>
                  <SortTh
                    label="Ticker"
                    sortKey="ticker"
                    activeKey={universeSort.key}
                    ascending={universeSort.asc}
                    onSort={onUniverseSort}
                  />
                  <SortTh
                    label="Nazwa"
                    sortKey="name"
                    activeKey={universeSort.key}
                    ascending={universeSort.asc}
                    onSort={onUniverseSort}
                  />
                  <SortTh
                    label="Sektor"
                    sortKey="sector"
                    activeKey={universeSort.key}
                    ascending={universeSort.asc}
                    onSort={onUniverseSort}
                  />
                  <SortTh
                    label="Region"
                    sortKey="region"
                    activeKey={universeSort.key}
                    ascending={universeSort.asc}
                    onSort={onUniverseSort}
                  />
                  <SortTh
                    label="Cena"
                    sortKey="price"
                    activeKey={universeSort.key}
                    ascending={universeSort.asc}
                    onSort={onUniverseSort}
                  />
                  <SortTh
                    label="Dywidenda % (poprz.)"
                    sortKey="dividend"
                    activeKey={universeSort.key}
                    ascending={universeSort.asc}
                    onSort={onUniverseSort}
                  />
                  <SortTh
                    label="Dywidenda % (plan.)"
                    sortKey="dividend_forward"
                    activeKey={universeSort.key}
                    ascending={universeSort.asc}
                    onSort={onUniverseSort}
                  />
                  <SortTh
                    label={`Zwrot ${periodLabel(trendPeriod)}`}
                    sortKey="change"
                    activeKey={universeSort.key}
                    ascending={universeSort.asc}
                    onSort={onUniverseSort}
                  />
                  <SortTh
                    label={`Śr. cena ${periodLabel(trendPeriod)}`}
                    sortKey="avg_price_period"
                    activeKey={universeSort.key}
                    ascending={universeSort.asc}
                    onSort={onUniverseSort}
                  />
                </tr>
              </thead>
              <tbody>
                {sortedUniverseStocks.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <strong>{s.ticker}</strong>
                    </td>
                    <td>{s.name}</td>
                    <td className="muted">{s.sector ?? "—"}</td>
                    <td>
                      <span className={`badge ${regionClass(s.region)}`}>{s.region}</span>
                    </td>
                    <td>
                      {s.price != null ? (
                        <>
                          {s.price.toFixed(4)} {s.currency ? <span className="muted">{s.currency}</span> : null}
                        </>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>{s.dividend_yield_pct != null ? `${s.dividend_yield_pct.toFixed(2)} %` : "—"}</td>
                    <td>
                      {s.dividend_yield_forward_pct != null ? `${s.dividend_yield_forward_pct.toFixed(2)} %` : "—"}
                    </td>
                    <TrendCell v={pickChange(s, trendPeriod)} />
                    <td>
                      {pickAvgPrice(s, trendPeriod) != null ? (
                        <>
                          {pickAvgPrice(s, trendPeriod)?.toFixed(4)}{" "}
                          {s.currency ? <span className="muted">{s.currency}</span> : null}
                        </>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "wallet" && <WalletPanel onChanged={loadCore} />}

      {tab === "charts" && <ChartsPanel colorScheme={chartScheme} />}

      {tab === "settings" && settings && (
        <>
          <div className="card">
            <h2>Kursy do PLN (wartość portfela)</h2>
            <p className="muted">
              Używane przy przeliczaniu akcji w USD/EUR na PLN na wykresach i w podsumowaniu. Możesz pobrać średnie
              NBP lub ustawić ręcznie (np. zbliżone do XTB).
            </p>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                marginBottom: "0.75rem",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={settings.fx_nbp_auto}
                onChange={(e) => void saveSettingsPartial({ fx_nbp_auto: e.target.checked })}
              />
              <span>
                Automatycznie pobieraj kursy z NBP <strong>1× dziennie</strong> (kalendarz PL, przy sprawdzaniu cen)
              </span>
            </label>
            {settings.fx_nbp_last_run_date ? (
              <p className="muted" style={{ marginTop: 0, marginBottom: "0.75rem" }}>
                Ostatnie pobranie NBP (dzień): <strong>{settings.fx_nbp_last_run_date}</strong>
              </p>
            ) : null}
            <div className="row">
              <div className="field" style={{ flex: "0 1 140px" }}>
                <label>USD → PLN</label>
                <input
                  type="number"
                  step="0.01"
                  value={settings.usd_pln_rate}
                  onChange={(e) =>
                    setSettings({ ...settings, usd_pln_rate: parseFloat(e.target.value) || 0 })
                  }
                />
              </div>
              <div className="field" style={{ flex: "0 1 140px" }}>
                <label>EUR → PLN</label>
                <input
                  type="number"
                  step="0.01"
                  value={settings.eur_pln_rate}
                  onChange={(e) =>
                    setSettings({ ...settings, eur_pln_rate: parseFloat(e.target.value) || 0 })
                  }
                />
              </div>
              <button
                type="button"
                className="btn btn-primary"
                style={{ alignSelf: "flex-end" }}
                onClick={() =>
                  void saveSettingsPartial({
                    usd_pln_rate: settings.usd_pln_rate,
                    eur_pln_rate: settings.eur_pln_rate,
                  })
                }
              >
                Zapisz kursy
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                style={{ alignSelf: "flex-end" }}
                onClick={() => void onFetchFxFromNbp()}
              >
                Pobierz z NBP teraz (+ włącz auto)
              </button>
            </div>
            <p className="muted" style={{ marginTop: "0.5rem" }}>
              Przycisk ustawia kursy i włącza tryb automatyczny; wyłącz go odznaczając pole powyżej.
            </p>
          </div>

          <div className="card">
            <h2>Próg alertu (globalny)</h2>
            <p className="muted">
              Powiadomienie, gdy cena spadnie o co najmniej ten procent poniżej średniej ceny kupna (łącznie z
              lotami).
            </p>
            <div className="slider-row" style={{ marginTop: "1rem" }}>
              <input
                type="range"
                min={0.5}
                max={25}
                step={0.5}
                value={settings.alert_threshold_percent}
                onChange={(e) =>
                  setSettings({ ...settings, alert_threshold_percent: parseFloat(e.target.value) })
                }
                onMouseUp={() => void saveThreshold(settings.alert_threshold_percent)}
                onTouchEnd={() => void saveThreshold(settings.alert_threshold_percent)}
              />
              <strong>{settings.alert_threshold_percent} %</strong>
            </div>
            <button
              type="button"
              className="btn btn-ghost"
              style={{ marginTop: "0.5rem" }}
              onClick={() => void saveThreshold(settings.alert_threshold_percent)}
            >
              Zapisz próg
            </button>
          </div>

          <div className="card">
            <h2>Powiadomienia (ntfy)</h2>
            <p className="muted">
              Aplikacja <strong>ntfy</strong> na iPhone, unikalny temat, zapisz poniżej.
            </p>
            <div className="field">
              <label htmlFor="ntfy">Temat ntfy</label>
              <input
                id="ntfy"
                value={settings.ntfy_topic ?? ""}
                onChange={(e) => setSettings({ ...settings, ntfy_topic: e.target.value })}
                placeholder="moj-temat"
              />
            </div>
            <div className="field">
              <label htmlFor="ntfyurl">URL serwera ntfy</label>
              <input
                id="ntfyurl"
                value={settings.ntfy_server_url}
                onChange={(e) => setSettings({ ...settings, ntfy_server_url: e.target.value })}
              />
            </div>
            <div className="row">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() =>
                  void saveSettingsPartial({ ntfy_topic: settings.ntfy_topic, ntfy_server_url: settings.ntfy_server_url })
                }
              >
                Zapisz ntfy
              </button>
              <button type="button" className="btn btn-primary" onClick={() => void onTestNtfyPing()}>
                Test ntfy (ping)
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => void onCheckBuyAlerts()}>
                Sprawdź warunki dokupu
              </button>
            </div>
            <p className="muted" style={{ marginTop: "0.75rem" }}>
              Ping = test kanału. Warunki dokupu wysyłają tylko przy spadku ceny vs średnia.
            </p>
          </div>

          <div className="card">
            <h2>Automatyczne sprawdzanie cen</h2>
            <p className="muted" style={{ marginBottom: "1rem" }}>
              <strong>Pozycje</strong> (tickery z lotów) — częściej, żeby wartość portfela i alerty były aktualne.{" "}
              <strong>Lista spółek</strong> (reszta universe) — rzadziej, mniej obciąża Yahoo.
            </p>
            <div className="row" style={{ gap: "1rem", flexWrap: "wrap", alignItems: "flex-end" }}>
              <div className="field" style={{ flex: "0 1 160px", marginBottom: 0 }}>
                <label htmlFor="int-port">Pozycje co (min)</label>
                <input
                  id="int-port"
                  type="number"
                  min={5}
                  max={1440}
                  value={settings.price_check_interval_minutes}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      price_check_interval_minutes: parseInt(e.target.value, 10) || 30,
                    })
                  }
                />
              </div>
              <div className="field" style={{ flex: "0 1 160px", marginBottom: 0 }}>
                <label htmlFor="int-uni">Lista spółek co (min)</label>
                <input
                  id="int-uni"
                  type="number"
                  min={15}
                  max={1440}
                  value={settings.universe_price_interval_minutes ?? 120}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      universe_price_interval_minutes: parseInt(e.target.value, 10) || 120,
                    })
                  }
                />
              </div>
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
              <input
                type="checkbox"
                checked={settings.alerts_enabled}
                onChange={(e) => setSettings({ ...settings, alerts_enabled: e.target.checked })}
              />
              Alerty włączone
            </label>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() =>
                void saveSettingsPartial({
                  price_check_interval_minutes: settings.price_check_interval_minutes,
                  universe_price_interval_minutes: settings.universe_price_interval_minutes,
                  alerts_enabled: settings.alerts_enabled,
                })
              }
            >
              Zapisz harmonogram
            </button>
          </div>

          <div className="card">
            <h2>Kopie zapasowe</h2>
            <p className="muted" style={{ marginBottom: "0.5rem" }}>
              Osobne kopie: portfel oraz lista spółek.
            </p>
            <p className="muted" style={{ marginBottom: "0.65rem", fontSize: "0.82rem" }}>
              Pliki <strong>*before_restore*</strong> to automatyczna migawka <strong>tuż przed</strong> ostatnim
              przywróceniem (stan z tej chwili) — zwykle nie chcesz ich przywracać, jeśli szukasz starszej dobrej kopii.
            </p>

            <div className="backup-block">
              <div className="field backup-select">
                <label htmlFor="backup-portfolio">Kopie portfela</label>
                <select
                  id="backup-portfolio"
                  value={selectedPortfolioBackup}
                  onChange={(e) => setSelectedPortfolioBackup(e.target.value)}
                >
                  <option value="">— wybierz kopię —</option>
                  {portfolioBackups.map((b) => (
                    <option key={b.file_name} value={b.file_name}>
                      {new Date(b.created_at).toLocaleString("pl-PL")} | {(b.size_bytes / 1024).toFixed(1)} KB |{" "}
                      {b.purchase_lots_count != null ? `${b.purchase_lots_count} lot. | ` : ""}
                      {b.file_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="backup-actions">
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void onCreatePortfolioBackup()}>
                  Wymuś kopię portfela
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void onExportPortfolioBackup()}>
                  Eksportuj wybraną
                </button>
                <button type="button" className="btn btn-primary btn-sm" onClick={() => void onRestorePortfolioBackup()}>
                  Przywróć portfel
                </button>
              </div>
              <div className="backup-import">
                <input
                  type="file"
                  accept=".db,application/octet-stream"
                  onChange={(e) => setPortfolioImportFile(e.target.files?.[0] ?? null)}
                />
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void onImportPortfolioBackup()}>
                  Importuj kopię portfela
                </button>
              </div>
            </div>

            <div className="backup-block">
              <div className="field backup-select">
                <label htmlFor="backup-prices">Kopie listy spółek</label>
                <select
                  id="backup-prices"
                  value={selectedPricesBackup}
                  onChange={(e) => setSelectedPricesBackup(e.target.value)}
                >
                  <option value="">— wybierz kopię —</option>
                  {pricesBackups.map((b) => (
                    <option key={b.file_name} value={b.file_name}>
                      {new Date(b.created_at).toLocaleString("pl-PL")} | {(b.size_bytes / 1024).toFixed(1)} KB |{" "}
                      {b.file_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="backup-actions">
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void onCreatePricesBackup()}>
                  Wymuś kopię listy spółek
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void onExportPricesBackup()}>
                  Eksportuj wybraną
                </button>
                <button type="button" className="btn btn-primary btn-sm" onClick={() => void onRestorePricesBackup()}>
                  Przywróć listę spółek
                </button>
              </div>
              <div className="backup-import">
                <input
                  type="file"
                  accept=".json,application/json"
                  onChange={(e) => setPricesImportFile(e.target.files?.[0] ?? null)}
                />
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => void onImportPricesBackup()}>
                  Importuj kopię listy spółek
                </button>
              </div>
            </div>
          </div>
        </>
      )}
        </div>
      </div>

      <div className="toast-stack" aria-live="polite">
        {err && !toastErrDismissed ? (
          <div className="toast toast--error" role="alert">
            <div className="toast__body">
              <strong>Błąd</strong>
              {err}
            </div>
            <button
              type="button"
              className="toast__close"
              onClick={() => setToastErrDismissed(true)}
              aria-label="Zamknij komunikat"
            >
              ×
            </button>
          </div>
        ) : null}
        {refreshMsg && !toastOkDismissed ? (
          <div className="toast toast--success">
            <div className="toast__body">
              <strong>Informacja</strong>
              {refreshMsg}
            </div>
            <button
              type="button"
              className="toast__close"
              onClick={() => setToastOkDismissed(true)}
              aria-label="Zamknij komunikat"
            >
              ×
            </button>
          </div>
        ) : null}
      </div>
    </div>
    {import.meta.env.DEV ? (
      <div
        className="dev-debug-hud"
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 9999,
          fontSize: "11px",
          lineHeight: 1.35,
          padding: "6px 10px",
          background: "rgba(15, 23, 42, 0.88)",
          color: "#e2e8f0",
          fontFamily: "var(--font-mono, ui-monospace, monospace)",
          borderTop: "1px solid rgba(148, 163, 184, 0.35)",
          pointerEvents: "none",
        }}
      >
        <strong>DEV</strong> — boot: {bootStatus}
        {" · "}
        update:{" "}
        {buildUpdate
          ? `cur=${buildUpdate.current_version} latest=${buildUpdate.latest_version} avail=${String(buildUpdate.update_available)} err=${buildUpdate.error ?? "—"}`
          : "brak odpowiedzi /api/version/update"}
        {" · "}wpisz <strong>__FND_DEBUG__</strong> w konsoli
      </div>
    ) : null}
    </>
  );
}
