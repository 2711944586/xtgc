from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
import pandas as pd

from .config import DATA_DIR, INTERIM_DIR, PROCESSED_DIR, RAW_DIR, ensure_dirs, load_base_config
from .utils import sha256_file, write_json


BTS_COLUMNS = [
    "Year",
    "Quarter",
    "Month",
    "DayofMonth",
    "DayOfWeek",
    "FlightDate",
    "Reporting_Airline",
    "DOT_ID_Reporting_Airline",
    "IATA_CODE_Reporting_Airline",
    "Tail_Number",
    "Flight_Number_Reporting_Airline",
    "Origin",
    "OriginCityName",
    "OriginState",
    "Dest",
    "DestCityName",
    "DestState",
    "CRSDepTime",
    "DepTime",
    "DepDelay",
    "DepDelayMinutes",
    "DepDel15",
    "CRSArrTime",
    "ArrTime",
    "ArrDelay",
    "ArrDelayMinutes",
    "ArrDel15",
    "Cancelled",
    "CancellationCode",
    "Diverted",
    "CRSElapsedTime",
    "ActualElapsedTime",
    "AirTime",
    "Flights",
    "Distance",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
]


@dataclass(frozen=True)
class DataPaths:
    raw_manifest: Path = DATA_DIR / "data_manifest.csv"
    cleaned: Path = PROCESSED_DIR / "flights_clean.parquet"
    featured: Path = PROCESSED_DIR / "flights_features.parquet"
    data_dictionary: Path = DATA_DIR / "data_dictionary.csv"
    audit: Path = DATA_DIR / "data_audit.json"


def bts_zip_name(year: int, month: int) -> str:
    return f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"


def download_bts_month(year: int, month: int, force: bool = False) -> Path:
    ensure_dirs()
    cfg = load_base_config()
    url = cfg["raw_url_template"].format(year=year, month=month)
    out = RAW_DIR / bts_zip_name(year, month)
    if out.exists() and out.stat().st_size > 0 and not force:
        return out
    urlretrieve(url, out)
    return out


def _read_bts_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError(f"No CSV found in {path}")
        with zf.open(csv_names[0]) as raw:
            # BTS files may include a trailing unnamed column. Use the fields that
            # exist in the file and keep only project-relevant columns.
            head = raw.readline()
            raw.seek(0)
            cols = pd.read_csv(io.BytesIO(head), nrows=0).columns.tolist()
            usecols = [c for c in BTS_COLUMNS if c in cols]
            return pd.read_csv(raw, usecols=usecols, low_memory=False)


def build_manifest(raw_files: list[Path], frames: list[pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for path, df in zip(raw_files, frames):
        rows.append(
            {
                "file_name": path.name,
                "source": "U.S. DOT BTS TranStats PREZIP monthly on-time performance file",
                "download_date": datetime.now().strftime("%Y-%m-%d"),
                "rows": len(df),
                "columns": len(df.columns),
                "file_size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "processing_script": "scripts/01_prepare_data.py",
            }
        )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(DATA_DIR / "data_manifest.csv", index=False, encoding="utf-8-sig")
    return manifest


def load_raw_months(force_download: bool = False) -> pd.DataFrame:
    cfg = load_base_config()
    raw_files = [download_bts_month(cfg["year"], int(month), force_download) for month in cfg["months"]]
    frames = [_read_bts_zip(path) for path in raw_files]
    build_manifest(raw_files, frames)
    return pd.concat(frames, ignore_index=True)


def _time_to_hour(value: object) -> float:
    if pd.isna(value):
        return np.nan
    try:
        ivalue = int(float(value))
    except (TypeError, ValueError):
        return np.nan
    if ivalue == 2400:
        ivalue = 0
    hour = ivalue // 100
    minute = ivalue % 100
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return np.nan
    return hour + minute / 60.0


def clean_flights(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cfg = load_base_config()
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    before = len(out)
    out = out.drop_duplicates()
    duplicate_count = before - len(out)

    out["FlightDate"] = pd.to_datetime(out["FlightDate"], errors="coerce")
    out = out[out["FlightDate"].notna()].copy()
    for col in [
        "CRSDepTime",
        "CRSArrTime",
        "DepDelay",
        "DepDelayMinutes",
        "DepDel15",
        "ArrDelay",
        "ArrDelayMinutes",
        "ArrDel15",
        "Cancelled",
        "Diverted",
        "CRSElapsedTime",
        "ActualElapsedTime",
        "AirTime",
        "Distance",
        "CarrierDelay",
        "WeatherDelay",
        "NASDelay",
        "SecurityDelay",
        "LateAircraftDelay",
    ]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    for col in ["Origin", "Dest", "Reporting_Airline"]:
        out[col] = out[col].astype(str).str.strip().str.upper()

    out["Cancelled"] = out.get("Cancelled", 0).fillna(0).astype(int)
    out["Diverted"] = out.get("Diverted", 0).fillna(0).astype(int)
    out["is_completed"] = (out["Cancelled"].eq(0) & out["Diverted"].eq(0)).astype(int)
    out["ArrDelayMinutes"] = out["ArrDelayMinutes"].clip(lower=0)
    out["ArrDel15_calc"] = (out["ArrDelayMinutes"].fillna(0) >= cfg["delay_threshold_minutes"]).astype(int)
    if "ArrDel15" in out.columns:
        out["ArrDel15"] = out["ArrDel15"].fillna(out["ArrDel15_calc"]).astype(int)
    else:
        out["ArrDel15"] = out["ArrDel15_calc"]
    out["arrdel15_consistent"] = out["ArrDel15"].eq(out["ArrDel15_calc"])
    out["route"] = out["Origin"] + "-" + out["Dest"]
    out["crs_dep_hour_float"] = out["CRSDepTime"].map(_time_to_hour)
    out["crs_arr_hour_float"] = out["CRSArrTime"].map(_time_to_hour)
    out["crs_dep_hour"] = np.floor(out["crs_dep_hour_float"]).fillna(-1).astype(int)
    out["is_weekend"] = out["DayOfWeek"].isin([6, 7]).astype(int)
    out["dep_time_block"] = pd.cut(
        out["crs_dep_hour"].clip(0, 23),
        bins=[-1, 5, 9, 15, 19, 23],
        labels=["night", "morning_peak", "midday", "evening_peak", "late"],
    ).astype(str)
    out["scheduled_datetime"] = out["FlightDate"] + pd.to_timedelta(out["crs_dep_hour_float"].fillna(0), unit="h")

    # Keep the project scope: completed flights in the selected top airport
    # network for prediction, but keep cancellation flags for aggregate metrics.
    airport_counts = pd.concat([out["Origin"], out["Dest"]]).value_counts()
    top_airports = airport_counts.head(int(cfg["top_airports"])).index.tolist()
    scoped = out[out["Origin"].isin(top_airports) & out["Dest"].isin(top_airports)].copy()
    scoped = scoped.sort_values(["FlightDate", "CRSDepTime", "Origin", "Dest"]).reset_index(drop=True)

    train_end = pd.Timestamp(cfg["train_end"])
    valid_end = pd.Timestamp(cfg["valid_end"])
    scoped["split"] = np.select(
        [
            scoped["FlightDate"] <= train_end,
            (scoped["FlightDate"] > train_end) & (scoped["FlightDate"] <= valid_end),
            scoped["FlightDate"] > valid_end,
        ],
        ["train", "valid", "test"],
        default="test",
    )

    audit = {
        "raw_rows": int(before),
        "duplicate_rows_removed": int(duplicate_count),
        "cleaned_rows_all_airports": int(len(out)),
        "scoped_rows_top_airports": int(len(scoped)),
        "top_airports": top_airports,
        "date_min": str(scoped["FlightDate"].min().date()) if len(scoped) else None,
        "date_max": str(scoped["FlightDate"].max().date()) if len(scoped) else None,
        "arrdel15_inconsistency_rate": float(1 - scoped["arrdel15_consistent"].mean()) if len(scoped) else 0,
        "cancelled_rate": float(scoped["Cancelled"].mean()) if len(scoped) else 0,
        "diverted_rate": float(scoped["Diverted"].mean()) if len(scoped) else 0,
        "split_counts": scoped["split"].value_counts().to_dict(),
        "missing_rate": scoped.isna().mean().sort_values(ascending=False).head(25).to_dict(),
    }
    return scoped, audit


def _train_means(train: pd.DataFrame, key: str, target: str = "ArrDel15") -> pd.Series:
    return train.groupby(key)[target].mean()


def add_leakage_safe_features(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    train = out[(out["split"] == "train") & (out["is_completed"] == 1)].copy()
    global_rate = float(train["ArrDel15"].mean()) if len(train) else 0.15

    mappings = {
        "origin_hist_delay_rate": _train_means(train, "Origin"),
        "dest_hist_delay_rate": _train_means(train, "Dest"),
        "route_hist_delay_rate": _train_means(train, "route"),
        "airline_hist_delay_rate": _train_means(train, "Reporting_Airline"),
        "origin_hour_hist_delay_rate": train.groupby(["Origin", "crs_dep_hour"])["ArrDel15"].mean(),
    }
    for name, mapping in mappings.items():
        if isinstance(mapping.index, pd.MultiIndex):
            keys = list(mapping.index.names)
            out[name] = out.set_index(keys).index.map(mapping).astype(float)
        else:
            key = {
                "origin_hist_delay_rate": "Origin",
                "dest_hist_delay_rate": "Dest",
                "route_hist_delay_rate": "route",
                "airline_hist_delay_rate": "Reporting_Airline",
            }[name]
            out[name] = out[key].map(mapping).astype(float)
        out[name] = out[name].fillna(global_rate)

    completed = out[out["is_completed"] == 1].copy().sort_values(["Origin", "scheduled_datetime"])
    completed["origin_rolling_3h_delay_rate"] = (
        completed.groupby("Origin", group_keys=False)
        .apply(lambda g: g.set_index("scheduled_datetime")["ArrDel15"].shift(1).rolling("3h", min_periods=1).mean())
        .reset_index(level=0, drop=True)
        .reindex(completed.index)
    )
    completed["origin_rolling_3h_volume"] = (
        completed.groupby("Origin", group_keys=False)
        .apply(lambda g: g.set_index("scheduled_datetime")["ArrDel15"].shift(1).rolling("3h", min_periods=1).count())
        .reset_index(level=0, drop=True)
        .reindex(completed.index)
    )
    out["origin_rolling_3h_delay_rate"] = completed["origin_rolling_3h_delay_rate"]
    out["origin_rolling_3h_volume"] = completed["origin_rolling_3h_volume"]
    out["origin_rolling_3h_delay_rate"] = out["origin_rolling_3h_delay_rate"].fillna(global_rate)
    out["origin_rolling_3h_volume"] = out["origin_rolling_3h_volume"].fillna(0)

    out["hour_sin"] = np.sin(2 * np.pi * out["crs_dep_hour"].clip(0, 23) / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["crs_dep_hour"].clip(0, 23) / 24)
    out["month_sin"] = np.sin(2 * np.pi * out["Month"] / 12)
    out["month_cos"] = np.cos(2 * np.pi * out["Month"] / 12)

    feature_meta = {
        "global_train_delay_rate": global_rate,
        "feature_time_policy": "Historical aggregate features are fitted on train split; rolling features use shifted prior flights only.",
        "forbidden_plan_stage_fields": [
            "DepTime",
            "DepDelay",
            "TaxiOut",
            "TaxiIn",
            "ArrTime",
            "ArrDelay",
            "CarrierDelay",
            "WeatherDelay",
            "NASDelay",
            "SecurityDelay",
            "LateAircraftDelay",
        ],
    }
    return out, feature_meta


def write_data_dictionary(df: pd.DataFrame, path: Path) -> None:
    descriptions = {
        "FlightDate": "Scheduled flight date.",
        "Reporting_Airline": "BTS reporting airline code.",
        "Origin": "Origin airport IATA code.",
        "Dest": "Destination airport IATA code.",
        "CRSDepTime": "Scheduled departure local time.",
        "CRSArrTime": "Scheduled arrival local time.",
        "ArrDel15": "Arrival delay >= 15 minutes indicator.",
        "ArrDelayMinutes": "Non-negative arrival delay minutes.",
        "Cancelled": "Flight cancellation indicator.",
        "Diverted": "Flight diversion indicator.",
        "route": "Origin-Dest route key.",
        "split": "Time-ordered train/valid/test split.",
    }
    rows = []
    for col in df.columns:
        rows.append(
            {
                "field": col,
                "dtype": str(df[col].dtype),
                "missing_rate": float(df[col].isna().mean()),
                "description": descriptions.get(col, "Derived or retained BTS project field."),
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def prepare_data(force_download: bool = False) -> tuple[pd.DataFrame, dict]:
    ensure_dirs()
    raw = load_raw_months(force_download=force_download)
    raw.to_parquet(INTERIM_DIR / "bts_raw_selected_months.parquet", index=False)
    cleaned, audit = clean_flights(raw)
    featured, feature_meta = add_leakage_safe_features(cleaned)
    cleaned.to_parquet(DataPaths.cleaned, index=False)
    featured.to_parquet(DataPaths.featured, index=False)
    write_data_dictionary(featured, DataPaths.data_dictionary)
    audit["feature_meta"] = feature_meta
    write_json(DataPaths.audit, audit)
    return featured, audit

