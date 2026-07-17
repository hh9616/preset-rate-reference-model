#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update preset-rate reference model data for GitHub Pages.

The script intentionally uses Python standard library only so it can run in
GitHub Actions without installing dependencies.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

MODEL_JSON = DATA_DIR / "model-data.json"
MODEL_JS = DATA_DIR / "model-data.js"
DEPOSIT_EVENTS = DATA_DIR / "deposit-rate-events.json"
LPR_EVENTS = DATA_DIR / "lpr-events.json"
ACTUAL_VALUES = DATA_DIR / "actual-reference-values.json"

CHINABOND_ENDPOINT = "https://yield.chinabond.com.cn/cbweb-mn/yc/searchYc"
CHINABOND_REFERER = "https://yield.chinabond.com.cn/cbweb-mn/yield_main?locale=zh_CN"

CURVES = {
    "gov10yYtm": ("国债", "2c9081e50a2f9606010a3068cae70001"),
    "cdb10yYtm": ("国开债", "8a8b2ca037a7ca910137bfaa94fa5057"),
    "adb10yYtm": ("农发行债", "2c9081e50a2f9606010a306abdde0003"),
    "exim10yYtm": ("进出口行债", "8a8b2ca0567e033b01567ea9c1d96af8"),
}

BJ = dt.timezone(dt.timedelta(hours=8))
DEFAULT_START = "2020-01-02"


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    tmp.replace(path)


def save_js(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write("window.MODEL_DATA = ")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    tmp.replace(path)


def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def today_beijing() -> dt.date:
    return dt.datetime.now(BJ).date()


def iter_weekdays(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            yield cur
        cur += dt.timedelta(days=1)


def subtract_months(day: dt.date, months: int) -> dt.date:
    month0 = day.month - 1 - months
    year = day.year + month0 // 12
    month = month0 % 12 + 1
    month_lengths = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                     31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return dt.date(year, month, min(day.day, month_lengths[month - 1]))


def value_from_events(events: list[dict], day: dt.date, key: str):
    chosen = None
    for item in sorted(events, key=lambda x: x["date"]):
        if parse_date(item["date"]) <= day and item.get(key) is not None:
            chosen = item[key]
        elif parse_date(item["date"]) > day:
            break
    return chosen


def fetch_chinabond_10y(yc_def_id: str, day: dt.date) -> float | None:
    params = {
        "xyzSelect": "txy",
        "workTimes": day.isoformat(),
        "dxbj": "0",
        "qxll": "0",
        "yqqxN": "N",
        "yqqxK": "K",
        "ycDefIds": yc_def_id,
        "wrjxCBFlag": "0",
        "locale": "zh_CN",
    }
    body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(
        CHINABOND_ENDPOINT,
        data=body,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": CHINABOND_REFERER,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not payload or not isinstance(payload, list):
        return None
    for tenor, value in payload[0].get("seriesData", []):
        if abs(float(tenor) - 10.0) < 1e-6:
            return round(float(value), 6)
    return None


def fetch_one_day(day: dt.date) -> tuple[str, dict, list[str]]:
    values: dict[str, float] = {}
    warnings: list[str] = []
    for field, (name, curve_id) in CURVES.items():
        for attempt in range(3):
            try:
                value = fetch_chinabond_10y(curve_id, day)
                if value is not None:
                    values[field] = value
                else:
                    warnings.append(f"{day} {name}无10Y数据")
                break
            except Exception as exc:  # network endpoint is occasionally flaky
                if attempt == 2:
                    warnings.append(f"{day} {name}抓取失败: {exc}")
                else:
                    time.sleep(1.5 * (attempt + 1))
    return day.isoformat(), values, warnings


def trailing_average(rows: list[dict], idx: int, key: str, window: int) -> float | None:
    vals = [r.get(key) for r in rows[max(0, idx - window + 1): idx + 1]]
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals:
        return None
    return statistics.fmean(vals)


def six_month_average(rows: list[dict], idx: int, key: str) -> float | None:
    end = parse_date(rows[idx]["date"])
    start = subtract_months(end, 6)
    vals = [
        r.get(key)
        for r in rows[: idx + 1]
        if parse_date(r["date"]) >= start and isinstance(r.get(key), (int, float))
    ]
    if not vals:
        return None
    return statistics.fmean(vals)


def round_or_none(value, digits=6):
    if value is None:
        return None
    return round(float(value), digits)


def build_model_rows(raw_rows: list[dict], actual_values: list[dict]) -> list[dict]:
    actual_by_date = {item["asOfDate"]: item for item in actual_values}
    rows = sorted(raw_rows, key=lambda r: r["date"])

    for row in rows:
        policy_values = [
            row.get("cdb10yYtm"),
            row.get("adb10yYtm"),
            row.get("exim10yYtm"),
        ]
        policy_values = [v for v in policy_values if isinstance(v, (int, float))]
        row["policy10yMean"] = round_or_none(statistics.fmean(policy_values)) if policy_values else None

    for idx, row in enumerate(rows):
        lpr_avg = six_month_average(rows, idx, "lpr5y")
        dep_avg = six_month_average(rows, idx, "deposit5yMean")
        row["liabilityAnchor"] = round_or_none((lpr_avg + dep_avg) / 2) if lpr_avg and dep_avg else None

        for key in ("cdb10yYtm", "adb10yYtm", "exim10yYtm", "policy10yMean"):
            ma250 = trailing_average(rows, idx, key, 250)
            ma750 = trailing_average(rows, idx, key, 750)
            base_key = key.replace("10yYtm", "").replace("policy10yMean", "mean")
            row[f"assetBaseReturn_{base_key}"] = round_or_none(min(ma250, ma750)) if ma250 and ma750 else None

        asset_base = row.get("assetBaseReturn_mean")
        liability = row.get("liabilityAnchor")
        row["assetBaseReturn"] = asset_base
        row["modelReferenceValue"] = round_or_none(min(liability, asset_base)) if liability and asset_base else None

        actual = actual_by_date.get(row["date"])
        if actual:
            row["actualReferenceValue"] = actual["value"]
            if row.get("modelReferenceValue") is not None:
                row["actualMinusModelBp"] = round((actual["value"] - row["modelReferenceValue"]) * 100, 2)
        else:
            row["actualReferenceValue"] = None
            row["actualMinusModelBp"] = None

    return rows


def main() -> int:
    start = parse_date(os.environ.get("START_DATE", DEFAULT_START))
    end = parse_date(os.environ.get("END_DATE", today_beijing().isoformat()))
    max_days = int(os.environ.get("MAX_FETCH_DAYS", "0") or "0")

    dates = list(iter_weekdays(start, end))
    if max_days > 0:
        dates = dates[-max_days:]

    deposit_events = load_json(DEPOSIT_EVENTS, [])
    lpr_events = load_json(LPR_EVENTS, [])
    actual_values = load_json(ACTUAL_VALUES, [])

    print(f"Fetching ChinaBond data for {len(dates)} weekdays: {dates[0] if dates else '-'} -> {dates[-1] if dates else '-'}")
    raw_by_date: dict[str, dict] = {}
    warnings: list[str] = []

    workers = int(os.environ.get("FETCH_WORKERS", "8"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fetch_one_day, day) for day in dates]
        for fut in concurrent.futures.as_completed(futures):
            date_str, values, day_warnings = fut.result()
            warnings.extend(day_warnings)
            if values:
                raw_by_date[date_str] = {"date": date_str, **values}

    rows: list[dict] = []
    for date_str in sorted(raw_by_date):
        day = parse_date(date_str)
        row = raw_by_date[date_str]
        for key in ("icbc5y", "abc5y", "boc5y", "ccb5y", "psbc5y", "bocom5y"):
            row[key] = value_from_events(deposit_events, day, key)
        dep_vals = [row.get(k) for k in ("icbc5y", "abc5y", "boc5y", "ccb5y", "psbc5y", "bocom5y")]
        dep_vals = [v for v in dep_vals if isinstance(v, (int, float))]
        row["deposit5yMean"] = round_or_none(statistics.fmean(dep_vals)) if dep_vals else None
        row["lpr5y"] = value_from_events(lpr_events, day, "lpr5y")
        rows.append(row)

    model_rows = build_model_rows(rows, actual_values)
    data = {
        "updatedAt": dt.datetime.now(BJ).isoformat(timespec="seconds"),
        "unit": "percent",
        "calculationMode": "official_ma6",
        "policyBondMode": "mean",
        "series": model_rows,
        "actualValues": actual_values,
        "sources": {
            "chinabond": CHINABOND_ENDPOINT,
            "lpr": "data/lpr-events.json maintenance table",
            "deposit": "data/deposit-rate-events.json maintenance table",
            "association": "data/actual-reference-values.json maintenance table",
        },
        "warnings": warnings[:200],
    }

    save_json(MODEL_JSON, data)
    save_js(MODEL_JS, data)

    print(f"Wrote {MODEL_JSON} with {len(model_rows)} rows")
    if warnings:
        print(f"Warnings: {len(warnings)}; first: {warnings[0]}")
    return 0 if model_rows else 1


if __name__ == "__main__":
    sys.exit(main())
