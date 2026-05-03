const base = "";

export type UniverseRow = {
  id: number;
  ticker: string;
  name: string;
  region: string;
  sector: string | null;
  notes: string | null;
  price: number | null;
  currency: string | null;
  dividend_yield_pct: number | null;
  change_1d_pct: number | null;
  change_1w_pct: number | null;
  change_1m_pct: number | null;
  change_1y_pct: number | null;
  change_5y_pct: number | null;
  avg_price_1d: number | null;
  avg_price_1w: number | null;
  avg_price_1m: number | null;
  avg_price_1y: number | null;
  avg_price_5y: number | null;
  updated_at: string | null;
};

export type UniverseResponse = {
  stocks: UniverseRow[];
  last_prices_update: string | null;
};

export type PurchaseLot = {
  id: number;
  ticker: string;
  quantity: number;
  price_per_share: number;
  currency: string | null;
  purchased_at: string;
};

export type SaleTransaction = {
  id: number;
  ticker: string;
  quantity: number;
  price_per_share: number;
  currency: string | null;
  proceeds_pln: number;
  cost_basis_pln: number;
  realized_pln: number;
  sold_at: string;
};

export type TradeResult = {
  side: "buy" | "sell";
  ticker: string;
  quantity: number;
  price_per_share: number;
  currency: string | null;
  proceeds_pln?: number | null;
  cost_basis_pln?: number | null;
  realized_pln?: number | null;
  remaining_shares?: number | null;
  sold_at?: string | null;
};

export type Position = {
  ticker: string;
  total_shares: number;
  avg_buy_price: number;
  total_cost: number;
  current_price: number | null;
  currency: string | null;
  pct_vs_avg: number | null;
};

export type AppSettings = {
  alert_threshold_percent: number;
  alerts_enabled: boolean;
  ntfy_topic: string | null;
  ntfy_server_url: string;
  price_check_interval_minutes: number;
  universe_price_interval_minutes: number;
  usd_pln_rate: number;
  eur_pln_rate: number;
  fx_nbp_auto: boolean;
  fx_nbp_last_run_date: string | null;
};

export type FxRefreshResult = {
  usd_pln_rate: number;
  eur_pln_rate: number;
  source: string;
  effective_date: string;
  fx_nbp_auto: boolean;
  fx_nbp_last_run_date: string | null;
};

export type WalletSummary = {
  deposits_total_pln: number;
  dividends_total_pln: number;
  invested_pln: number;
  cash_available_pln: number;
  holdings_market_pln: number;
  total_equity_pln: number;
  sales_proceeds_total_pln: number;
  realized_pnl_total_pln: number;
};

export type CashDeposit = {
  id: number;
  amount_pln: number;
  received_at: string;
  note: string | null;
};

export type DividendReceipt = {
  id: number;
  ticker: string;
  amount_pln: number;
  received_at: string;
  note: string | null;
};

export type DividendForecastPayment = {
  estimated_date: string;
  amount_pln_estimate: number;
};

export type DividendForecastHolding = {
  ticker: string;
  shares: number;
  currency: string | null;
  trailing_12m_per_share: number;
  trailing_12m_pln_estimate: number;
  median_days_between_payments: number | null;
  avg_recent_payment_per_share: number | null;
  upcoming: DividendForecastPayment[];
  note: string | null;
};

export type DividendForecastResponse = {
  holdings: DividendForecastHolding[];
  total_trailing_12m_pln_estimate: number;
  total_upcoming_horizon_pln_estimate: number;
  horizon_days: number;
  disclaimer: string;
};

export type BackupFile = {
  file_name: string;
  size_bytes: number;
  created_at: string;
  kind: string;
};

export type BackupListResponse = {
  files: BackupFile[];
};

export type BackupActionResponse = {
  created?: boolean;
  restored?: boolean;
  file_name?: string | null;
  message: string;
  records?: number | null;
};

function formatApiError(status: number, statusText: string, raw: string): string {
  const trimmed = raw?.trim() ?? "";
  if (!trimmed) {
    return `Serwer zwrócił błąd ${status} (${statusText || "bez opisu"}).`;
  }
  if (trimmed.includes("<!DOCTYPE") || trimmed.includes("<html")) {
    return `Serwer zwrócił błąd ${status}. Sprawdź logi backendu lub spróbuj ponownie za chwilę.`;
  }
  if (status === 422 && trimmed.startsWith("{")) {
    try {
      const o = JSON.parse(trimmed) as { detail?: unknown };
      if (Array.isArray(o.detail)) {
        return o.detail
          .map((d: unknown) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: string }).msg) : JSON.stringify(d)))
          .join("; ");
      }
    } catch {
      /* fall through */
    }
  }
  if (trimmed.length > 400) {
    return `${trimmed.slice(0, 397)}…`;
  }
  return trimmed;
}

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const raw = await res.text();
    throw new Error(formatApiError(res.status, res.statusText, raw));
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetch(`${base}/api/health`).then((r) => j<{ ok: boolean }>(r)),
  universe: (region?: string, minDividendYieldPct?: number, requireDividendYield?: boolean) => {
    const params = new URLSearchParams();
    if (region) params.set("region", region);
    if (minDividendYieldPct != null && minDividendYieldPct > 0) {
      params.set("min_dividend_yield_pct", String(minDividendYieldPct));
    }
    if (requireDividendYield) {
      params.set("require_dividend_yield", "true");
    }
    const q = params.toString() ? `?${params.toString()}` : "";
    return fetch(`${base}/api/universe${q}`).then((r) => j<UniverseResponse>(r));
  },
  positions: () => fetch(`${base}/api/positions`).then((r) => j<Position[]>(r)),
  lots: () => fetch(`${base}/api/lots`).then((r) => j<PurchaseLot[]>(r)),
  addLot: (body: { ticker: string; quantity: number; price_per_share: number; side: "buy" | "sell" }) =>
    fetch(`${base}/api/lots`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => j<TradeResult>(r)),
  deleteLot: (id: number) =>
    fetch(`${base}/api/lots/${id}`, { method: "DELETE" }).then((r) => j<{ deleted: boolean }>(r)),
  sales: () => fetch(`${base}/api/lots/sales`).then((r) => j<SaleTransaction[]>(r)),
  settings: () => fetch(`${base}/api/settings`).then((r) => j<AppSettings>(r)),
  patchSettings: (body: Partial<AppSettings>) =>
    fetch(`${base}/api/settings`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => j<AppSettings>(r)),
  refreshFx: (enableAuto = true) =>
    fetch(`${base}/api/fx/refresh?enable_auto=${enableAuto ? "true" : "false"}`, { method: "POST" }).then(
      (r) => j<FxRefreshResult>(r),
    ),
  refreshPrices: () =>
    fetch(`${base}/api/prices/refresh`, { method: "POST" }).then((r) =>
      j<{ updated: number; failed: string[] }>(r)
    ),
  checkAlerts: () =>
    fetch(`${base}/api/alerts/check`, { method: "POST" }).then((r) =>
      j<{ sent: number; skipped: string[]; notes?: string[] }>(r)
    ),
  testNtfy: () =>
    fetch(`${base}/api/alerts/test-ntfy`, { method: "POST" }).then((r) =>
      j<{ ok: boolean; message: string }>(r)
    ),
  walletSummary: () => fetch(`${base}/api/wallet/summary`).then((r) => j<WalletSummary>(r)),
  deposits: () => fetch(`${base}/api/wallet/deposits`).then((r) => j<CashDeposit[]>(r)),
  addDeposit: (body: { amount_pln: number; note?: string | null }) =>
    fetch(`${base}/api/wallet/deposits`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => j<CashDeposit>(r)),
  deleteDeposit: (id: number) =>
    fetch(`${base}/api/wallet/deposits/${id}`, { method: "DELETE" }).then((r) => j<{ deleted: boolean }>(r)),
  dividends: () => fetch(`${base}/api/wallet/dividends`).then((r) => j<DividendReceipt[]>(r)),
  addDividend: (body: { ticker: string; amount_pln: number; note?: string | null }) =>
    fetch(`${base}/api/wallet/dividends`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => j<DividendReceipt>(r)),
  deleteDividend: (id: number) =>
    fetch(`${base}/api/wallet/dividends/${id}`, { method: "DELETE" }).then((r) => j<{ deleted: boolean }>(r)),
  dividendForecast: (horizonDays = 365) =>
    fetch(`${base}/api/dividends/forecast?horizon_days=${horizonDays}`).then((r) =>
      j<DividendForecastResponse>(r),
    ),
  chartTimeline: () => fetch(`${base}/api/charts/timeline`).then((r) => j<TimelinePayload>(r)),
  chartAllocation: () => fetch(`${base}/api/charts/allocation`).then((r) => j<AllocationPayload>(r)),
  listPortfolioBackups: () =>
    fetch(`${base}/api/backups/portfolio`).then((r) => j<BackupListResponse>(r)),
  createPortfolioBackup: () =>
    fetch(`${base}/api/backups/portfolio/create`, { method: "POST" }).then((r) =>
      j<BackupActionResponse>(r),
    ),
  restorePortfolioBackup: (fileName: string) =>
    fetch(`${base}/api/backups/portfolio/restore`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_name: fileName }),
    }).then((r) => j<BackupActionResponse>(r)),
  listPricesBackups: () => fetch(`${base}/api/backups/prices`).then((r) => j<BackupListResponse>(r)),
  createPricesBackup: () =>
    fetch(`${base}/api/backups/prices/create`, { method: "POST" }).then((r) =>
      j<BackupActionResponse>(r),
    ),
  restorePricesBackup: (fileName: string) =>
    fetch(`${base}/api/backups/prices/restore`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_name: fileName }),
    }).then((r) => j<BackupActionResponse>(r)),
};

export type TimelinePayload = {
  equity_series: {
    date: string;
    total_equity_pln: number;
    holdings_pln: number;
    cash_pln: number;
  }[];
  dividends: { date: string; amount_pln: number; ticker: string; note: string | null }[];
};

export type AllocationPayload = {
  slices: { ticker: string; label: string; value_pln: number; pct: number }[];
  total_pln: number;
};
