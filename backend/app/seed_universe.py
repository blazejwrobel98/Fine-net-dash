"""Lista spółek pod dywidendę, defensywne sektory (energia, utilities, zdrowie, paliwa, telekom). Tickery Yahoo."""

# (ticker, name, region, sector, notes)
UNIVERSE: list[tuple[str, str, str, str, str | None]] = [
    # Polska
    ("PGE.WA", "PGE", "pl", "Energetyka", "Dywidenda, regulowany sektor"),
    ("ENA.WA", "Enea", "pl", "Energetyka", None),
    ("TPE.WA", "Tauron", "pl", "Energetyka", "Yahoo: TPE.WA (nie TAU)"),
    ("PKN.WA", "Orlen", "pl", "Paliwa", "Koncern paliwowy"),
    ("PKO.WA", "PKO BP", "pl", "Bank", None),
    ("PEO.WA", "Pekao", "pl", "Bank", None),
    ("PZU.WA", "PZU", "pl", "Ubezpieczenia", None),
    ("MBK.WA", "mBank", "pl", "Bank", "Yahoo: MBK.WA (nie MBANK)"),
    ("MIL.WA", "Millennium", "pl", "Bank", None),
    ("ALR.WA", "Alior", "pl", "Bank", None),
    ("ATT.WA", "Grupa Azoty", "pl", "Chemia", "Przemysł"),
    # Europa — paliwa, utilities, farmacja, konsument
    ("BP.L", "BP", "eu", "Paliwa", None),
    ("SHEL.L", "Shell", "eu", "Paliwa", None),
    ("TTE.PA", "TotalEnergies", "eu", "Paliwa", None),
    ("ENGI.PA", "Engie", "eu", "Energetyka", "Utilities / multi"),
    ("RWE.DE", "RWE", "eu", "Energetyka", "Niemiecki utility"),
    ("EOAN.DE", "E.ON", "eu", "Energetyka", None),
    ("IBE.MC", "Iberdrola", "eu", "Energetyka", None),
    ("EDP.LS", "EDP", "eu", "Energetyka", "Lisbon"),
    ("GSK.L", "GSK", "eu", "Farmacja", None),
    ("AZN.L", "AstraZeneca", "eu", "Farmacja", None),
    ("SAN.PA", "Sanofi", "eu", "Farmacja", None),
    ("NOVO-B.CO", "Novo Nordisk", "eu", "Farmacja", None),
    ("ROG.SW", "Roche", "eu", "Farmacja", None),
    ("NESN.SW", "Nestlé", "eu", "Konsument", "Staples"),
    ("BATS.L", "BAT", "eu", "Tytoń", "Wysoka dywidenda"),
    ("VOD.L", "Vodafone", "eu", "Telekom", None),
    ("TEF.MC", "Telefónica", "eu", "Telekom", None),
    ("ISP.MI", "Intesa Sanpaolo", "eu", "Bank", None),
    ("DBK.DE", "Deutsche Bank", "eu", "Bank", None),
    ("INGA.AS", "ING", "eu", "Bank", None),
    ("DGE.L", "Diageo", "eu", "Konsument", "Alkohol"),
    ("ULVR.L", "Unilever", "eu", "Konsument", "LSE"),
    ("REL.L", "RELX", "eu", "Usługi", None),
    ("NG.L", "National Grid", "eu", "Energetyka", "UK sieci"),
    # USA — utilities, zdrowie, paliwa, konsument, REIT
    ("DUK", "Duke Energy", "us", "Energetyka", "Utility"),
    ("SO", "Southern Co", "us", "Energetyka", None),
    ("NEE", "NextEra Energy", "us", "Energetyka", None),
    ("AEP", "American Electric", "us", "Energetyka", None),
    ("WEC", "WEC Energy", "us", "Energetyka", None),
    ("XEL", "Xcel Energy", "us", "Energetyka", None),
    ("EXC", "Exelon", "us", "Energetyka", None),
    ("XOM", "Exxon Mobil", "us", "Paliwa", None),
    ("CVX", "Chevron", "us", "Paliwa", None),
    ("JNJ", "Johnson & Johnson", "us", "Farmacja", None),
    ("MRK", "Merck", "us", "Farmacja", None),
    ("PFE", "Pfizer", "us", "Farmacja", None),
    ("ABBV", "AbbVie", "us", "Farmacja", None),
    ("AMGN", "Amgen", "us", "Farmacja", None),
    ("BMY", "Bristol-Myers", "us", "Farmacja", None),
    ("KO", "Coca-Cola", "us", "Konsument", None),
    ("PEP", "PepsiCo", "us", "Konsument", None),
    ("PG", "Procter & Gamble", "us", "Konsument", None),
    ("CL", "Colgate", "us", "Konsument", None),
    ("KMB", "Kimberly-Clark", "us", "Konsument", None),
    ("WMT", "Walmart", "us", "Konsument", None),
    ("MO", "Altria", "us", "Tytoń", "Wysoka dywidenda"),
    ("PM", "Philip Morris", "us", "Tytoń", None),
    ("T", "AT&T", "us", "Telekom", None),
    ("VZ", "Verizon", "us", "Telekom", None),
    ("O", "Realty Income", "us", "REIT", "Miesięczna dywidenda"),
    ("SCHD", "Schwab US Dividend ETF", "us", "ETF", "Dywidendowy"),
    ("VYM", "Vanguard High Div Yield ETF", "us", "ETF", None),
    ("HD", "Home Depot", "us", "Retail", "Dywidenda"),
    ("LOW", "Lowe's", "us", "Retail", None),
    ("MMM", "3M", "us", "Przemysł", None),
    ("CSCO", "Cisco", "us", "Tech", "Dywidenda"),
    ("IBM", "IBM", "us", "Tech", None),
    # —— Rozszerzenie: więcej spółek dywidendowych / defensywnych (Yahoo tickery) ——
    # Polska
    ("KGH.WA", "KGHM Polska Miedź", "pl", "Górnictwo", None),
    ("JSW.WA", "JSW", "pl", "Górnictwo", None),
    ("DNP.WA", "Dino Polska", "pl", "Retail", None),
    ("BNP.WA", "BNP Paribas Bank Polska", "pl", "Bank", None),
    ("KRU.WA", "KRUK", "pl", "Finanse", "Windykacja"),
    ("LPP.WA", "LPP", "pl", "Retail", None),
    ("CDR.WA", "CD Projekt", "pl", "Gry", "Dywidenda zależna od polityki"),
    # Europa
    ("ENEL.MI", "Enel", "eu", "Energetyka", None),
    ("SNAM.MI", "Snam", "eu", "Energetyka", "Gazociągi"),
    ("TIT.MI", "Telecom Italia", "eu", "Telekom", None),
    ("REP.MC", "Repsol", "eu", "Paliwa", None),
    ("VIE.PA", "Veolia", "eu", "Energetyka", None),
    ("ORA.PA", "Orange", "eu", "Telekom", None),
    ("ALV.DE", "Allianz", "eu", "Ubezpieczenia", None),
    ("MUV2.DE", "Münchener Rück", "eu", "Ubezpieczenia", None),
    ("MBG.DE", "Mercedes-Benz Group", "eu", "Motoryzacja", None),
    ("SIE.DE", "Siemens", "eu", "Przemysł", None),
    ("BAYN.DE", "Bayer", "eu", "Farmacja", None),
    ("IMB.L", "Imperial Brands", "eu", "Tytoń", None),
    ("SSE.L", "SSE", "eu", "Energetyka", "UK utility"),
    ("BBVA.MC", "BBVA", "eu", "Bank", None),
    ("CABK.MC", "CaixaBank", "eu", "Bank", None),
    ("ABI.BR", "AB InBev", "eu", "Konsument", None),
    ("HEIA.AS", "Heineken", "eu", "Konsument", None),
    ("PHIA.AS", "Philips", "eu", "Zdrowie / Tech", None),
    ("UNA.AS", "Unilever", "eu", "Konsument", "Listing Amsterdam"),
    ("ATCO-B.ST", "Atlas Copco B", "eu", "Przemysł", "Szwecja"),
    ("SWED-A.ST", "Swedbank A", "eu", "Bank", "Szwecja"),
    ("NDA-SE.ST", "Nordea Bank", "eu", "Bank", "Szwecja"),
    ("BAS.DE", "BASF", "eu", "Chemia", None),
    ("AIR.PA", "Airbus", "eu", "Przemysł", None),
    ("MC.PA", "LVMH", "eu", "Luksus", "Dywidenda niższa niż 5% często"),
    # USA
    ("ED", "Consolidated Edison", "us", "Energetyka", None),
    ("PEG", "Public Service Enterprise", "us", "Energetyka", None),
    ("D", "Dominion Energy", "us", "Energetyka", None),
    ("CNP", "CenterPoint Energy", "us", "Energetyka", None),
    ("NI", "NiSource", "us", "Energetyka", None),
    ("FE", "FirstEnergy", "us", "Energetyka", None),
    ("PPL", "PPL Corp", "us", "Energetyka", None),
    ("AWK", "American Water Works", "us", "Utilities", None),
    ("EIX", "Edison International", "us", "Energetyka", None),
    ("ETR", "Entergy", "us", "Energetyka", None),
    ("WELL", "Welltower", "us", "REIT", "Healthcare"),
    ("VICI", "VICI Properties", "us", "REIT", None),
    ("SPG", "Simon Property Group", "us", "REIT", None),
    ("OHI", "Omega Healthcare", "us", "REIT", None),
    ("IRM", "Iron Mountain", "us", "REIT", None),
    ("EPR", "EPR Properties", "us", "REIT", None),
    ("STAG", "STAG Industrial", "us", "REIT", None),
    ("VTR", "Ventas", "us", "REIT", None),
    ("EPD", "Enterprise Products", "us", "Energetyka", "Pipeline / MLP"),
    ("KMI", "Kinder Morgan", "us", "Energetyka", None),
    ("ET", "Energy Transfer", "us", "Energetyka", None),
    ("BTI", "British American Tobacco (ADR)", "us", "Tytoń", None),
    ("CVS", "CVS Health", "us", "Zdrowie", None),
    ("GILD", "Gilead Sciences", "us", "Farmacja", None),
    ("MET", "MetLife", "us", "Ubezpieczenia", None),
    ("PRU", "Prudential Financial", "us", "Ubezpieczenia", None),
    ("TROW", "T. Rowe Price", "us", "Finanse", None),
    ("BEN", "Franklin Resources", "us", "Finanse", None),
    ("IVZ", "Invesco", "us", "Finanse", None),
    ("NTRS", "Northern Trust", "us", "Finanse", None),
    ("STX", "Seagate", "us", "Tech", None),
    ("HPQ", "HP Inc", "us", "Tech", None),
    ("F", "Ford", "us", "Motoryzacja", None),
    ("GM", "General Motors", "us", "Motoryzacja", None),
    ("IP", "International Paper", "us", "Materiały", None),
    ("PKG", "Packaging Corporation", "us", "Materiały", None),
    ("WY", "Weyerhaeuser", "us", "REIT", "Timber"),
    ("JEPI", "JPMorgan Equity Premium Income ETF", "us", "ETF", None),
    ("JEPQ", "JPMorgan Nasdaq Equity Premium ETF", "us", "ETF", None),
    ("DGRO", "iShares Core Dividend Growth ETF", "us", "ETF", None),
    ("NOBL", "ProShares S&P 500 Dividend Aristocrats", "us", "ETF", None),
    ("SDY", "SPDR S&P Dividend ETF", "us", "ETF", None),
]


def seed_universe_if_empty(session, model_cls) -> int:
    from sqlalchemy import select

    count = session.execute(select(model_cls)).scalars().all()
    if len(count) > 0:
        return 0
    for ticker, name, region, sector, notes in UNIVERSE:
        session.add(
            model_cls(ticker=ticker, name=name, region=region, sector=sector, notes=notes)
        )
    session.commit()
    return len(UNIVERSE)


def sync_universe_additions(session, model_cls) -> int:
    """Dopisuje brakujące tickery z UNIVERSE (bez usuwania ręcznie dodanych wierszy)."""
    from sqlalchemy import select

    existing = set(session.execute(select(model_cls.ticker)).scalars().all())
    added = 0
    for ticker, name, region, sector, notes in UNIVERSE:
        if ticker in existing:
            continue
        session.add(model_cls(ticker=ticker, name=name, region=region, sector=sector, notes=notes))
        existing.add(ticker)
        added += 1
    if added:
        session.commit()
    return added


def ensure_default_settings(session, settings_cls) -> None:
    from sqlalchemy import select

    row = session.execute(select(settings_cls).where(settings_cls.id == 1)).scalar_one_or_none()
    if row is None:
        session.add(settings_cls(id=1))
        session.commit()
        return
    if getattr(row, "usd_pln_rate", None) is None:
        row.usd_pln_rate = 4.0
    if getattr(row, "eur_pln_rate", None) is None:
        row.eur_pln_rate = 4.3
    if getattr(row, "universe_price_interval_minutes", None) is None:
        row.universe_price_interval_minutes = 120
    session.commit()
