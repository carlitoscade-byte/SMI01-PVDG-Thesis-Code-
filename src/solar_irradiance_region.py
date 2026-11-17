# -*- coding: utf-8 -*-
"""
Irradiancia para Asunción (PY) con curvas por estaciones (hemisferio sur) y proyección hasta 2030.
Backends: 'open-meteo' (sin key), 'nsrdb' (con key), 'pvgis' (via pvlib, sin key)
Salida SIEMPRE en la misma carpeta del script.
CSV: separador ';' y decimal ','.
"""

import os, io, time, argparse
from datetime import datetime
import numpy as np
import pandas as pd
import requests

# =================
# CONFIGURACIÓN
# =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # salida en carpeta del script
OUTDIR = BASE_DIR

DEFAULT_BACKEND = "open-meteo"   # opciones: open-meteo | nsrdb | pvgis

# Punto por defecto: Asunción, Paraguay
CITY_NAME = "Asunción"
LAT_DEFAULT = -25.2637
LON_DEFAULT = -57.5759

START_DATE = "2024-01-01"
END_DATE   = "2024-12-31"
TZ = "America/Asuncion"

# Proyección (inclusive)
PROJ_END_YEAR = 2030  # <- hasta este año se generan proyecciones

SEASON_KEYS = ["VERANO", "OTONO", "INVIERNO", "PRIMAVERA"]
SEASON_LABELS = {
    "VERANO": "Verano (Dic–Feb)",
    "OTONO": "Otoño (Mar–May)",
    "INVIERNO": "Invierno (Jun–Ago)",
    "PRIMAVERA": "Primavera (Sep–Nov)",
}
# Meses por estación (hemisferio sur)
SEASON_MONTHS = {
    "VERANO": {12, 1, 2},
    "OTONO": {3, 4, 5},
    "INVIERNO": {6, 7, 8},
    "PRIMAVERA": {9, 10, 11},
}

# =================
# HELPERS
# =================
def to_local_time(index_utc, tz):
    return index_utc.tz_localize("UTC").tz_convert(tz).tz_localize(None)

def hourly_to_daily_kwhm2(df, col="GHI_Wm2"):
    if col not in df.columns or df.empty:
        return pd.Series(dtype=float)
    wh = df[col].fillna(0) * 1.0           # W/m² * 1 h = Wh/m²
    daily = wh.resample("D").sum() / 1000.0  # kWh/m²/día
    daily.name = "GHI_kWhm2_dia"
    return daily

def hourly_to_monthly_kwhm2(df, col="GHI_Wm2"):
    daily = hourly_to_daily_kwhm2(df, col)
    monthly = daily.resample("MS").sum()     # kWh/m²/mes
    monthly.name = "GHI_kWhm2_mes"
    return monthly

def save_curves_plots(df_local, daily_kwh, monthly_kwh, png_path_prefix, title_prefix):
    import matplotlib.pyplot as plt

    # Perfil horario promedio (W/m²)
    if "GHI_Wm2" in df_local.columns and not df_local.empty:
        hourly_mean = df_local.groupby(df_local.index.hour)["GHI_Wm2"].mean()
        plt.figure()
        hourly_mean.plot(title=f"{title_prefix} - Perfil horario promedio GHI (W/m²)")
        plt.xlabel("Hora del día"); plt.ylabel("GHI (W/m²)")
        plt.tight_layout(); plt.savefig(f"{png_path_prefix}_perfil_horario.png"); plt.close()

    # Irradiación diaria (kWh/m²/día)
    if len(daily_kwh) > 0:
        plt.figure()
        daily_kwh.plot(title=f"{title_prefix} - Irradiación diaria GHI (kWh/m²/día)")
        plt.xlabel("Fecha"); plt.ylabel("kWh/m²/día")
        plt.tight_layout(); plt.savefig(f"{png_path_prefix}_diario.png"); plt.close()

    # Irradiación mensual (kWh/m²/mes)
    if len(monthly_kwh) > 0:
        plt.figure()
        monthly_kwh.plot(kind="bar", title=f"{title_prefix} - Irradiación mensual GHI (kWh/m²/mes)")
        plt.xlabel("Mes"); plt.ylabel("kWh/m²/mes")
        plt.tight_layout(); plt.savefig(f"{png_path_prefix}_mensual.png"); plt.close()

def season_key_from_month(m):
    for key, months in SEASON_MONTHS.items():
        if m in months:
            return key
    return None

def add_season_column(df):
    if df.empty:
        df["season"] = pd.Series(dtype=object)
        return df
    seasons = df.index.month.map(season_key_from_month)
    df = df.copy()
    df["season"] = seasons.values
    return df

# =================
# BACKENDS
# =================
def fetch_open_meteo(lat, lon, start_date, end_date, tz):
    """Open-Meteo archive API (ERA5): shortwave_radiation (~GHI), direct_radiation, diffuse_radiation. Sin API key."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": [
    "shortwave_radiation",
    "direct_normal_irradiance",
    "diffuse_radiation"
],
        "timezone": "UTC"
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    times = data.get("hourly", {}).get("time", [])
    ghi   = data.get("hourly", {}).get("shortwave_radiation", [])
    dni = data.get("hourly", {}).get("direct_normal_irradiance", [])
    dhi   = data.get("hourly", {}).get("diffuse_radiation", [])

    df = pd.DataFrame({
        "time": pd.to_datetime(times),
        "GHI_Wm2": ghi if ghi else np.nan,
        "DNI_Wm2": dni if dni else np.nan,
        "DHI_Wm2": dhi if dhi else np.nan
    }).set_index("time").sort_index()

    df_local = df.copy()
    df_local.index = to_local_time(df_local.index, tz)
    return df_local

def fetch_nsrdb_psm3(lat, lon, start_date, end_date, email, api_key):
    """NSRDB PSM3 (NREL) CSV. Requiere API key y email válidos."""
    base = "https://developer.nrel.gov/api/nsrdb/v2/solar/psm3-2-2-download.csv"
    start_year = pd.to_datetime(start_date).year
    end_year   = pd.to_datetime(end_date).year

    params = {
        "api_key": api_key,
        "email": email,
        "wkt": f"POINT({lon} {lat})",
        "names": f"{start_year}-{end_year}",
        "interval": "60",
        "utc": "true",
        "full_name": "Research User",
        "attributes": "ghi,dhi,dni,air_temperature,wind_speed,solar_zenith_angle",
        "leap_day": "false",
    }
    r = requests.get(base, params=params, timeout=90)
    r.raise_for_status()

    df = pd.read_csv(io.StringIO(r.text), comment="#")
    cols = {c.lower(): c for c in df.columns}
    need = ["year","month","day","hour"]
    for n in need:
        if n not in cols:
            raise ValueError(f"Columna requerida no encontrada en NSRDB: {n}")
    minute_col = cols["minute"] if "minute" in cols else None

    if minute_col:
        dt = pd.to_datetime(df[[cols["year"], cols["month"], cols["day"], cols["hour"], minute_col]].rename(
            columns={cols["year"]:"Year", cols["month"]:"Month", cols["day"]:"Day", cols["hour"]:"Hour", minute_col:"Minute"}))
    else:
        tmp = df[[cols["year"], cols["month"], cols["day"], cols["hour"]]].rename(
            columns={cols["year"]:"Year", cols["month"]:"Month", cols["day"]:"Day", cols["hour"]:"Hour"})
        tmp["Minute"] = 0
        dt = pd.to_datetime(tmp)

    df.index = dt

    cols_map = {}
    for c in df.columns:
        cu = str(c).upper()
        if cu == "GHI": cols_map[c] = "GHI_Wm2"
        if cu == "DNI": cols_map[c] = "DNI_Wm2"
        if cu == "DHI": cols_map[c] = "DHI_Wm2"
    out = df.rename(columns=cols_map)
    keep = [c for c in ["GHI_Wm2","DNI_Wm2","DHI_Wm2"] if c in out.columns]
    out = out[keep].sort_index()

    start_ts = pd.to_datetime(start_date)
    end_ts   = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(minutes=1)
    out = out[(out.index >= start_ts) & (out.index <= end_ts)]

    out_local = out.copy()
    out_local.index = to_local_time(out_local.index, TZ)
    return out_local

def fetch_pvgis(lat, lon, start_date, end_date, tz):
    """PVGIS vía pvlib (si instalado). Sin API key."""
    try:
        from pvlib.iotools import get_pvgis_hourly
    except Exception as e:
        raise RuntimeError("pvlib no está instalado. Instale con: pip install pvlib") from e

    df, meta = get_pvgis_hourly(
        lat=lat, lon=lon,
        start=pd.to_datetime(start_date),
        end=pd.to_datetime(end_date),
        components=True, surface_tilt=0, surface_azimuth=0
    )

    candidates = [c for c in df.columns if "G(h)" in c or "G(i)_surface" in c]
    ghi_col = candidates[0] if candidates else df.columns[0]
    out = pd.DataFrame({"GHI_Wm2": df[ghi_col]})

    dni_cols = [c for c in df.columns if "Gb" in c or "DNI" in c]
    dhi_cols = [c for c in df.columns if "Gd" in c or "DHI" in c]
    if dni_cols: out["DNI_Wm2"] = df[dni_cols[0]]
    if dhi_cols: out["DHI_Wm2"] = df[dhi_cols[0]]

    out.index = out.index.tz_localize(None)
    out.index = to_local_time(out.index, tz)
    return out

# =================
# PROYECCIÓN
# =================
def build_projection_monthly(df_local, proj_end_year=PROJ_END_YEAR):
    """
    Genera proyección mensual (kWh/m²/mes) desde (último año + 1) hasta proj_end_year
    usando climatología mensual (promedio por mes del histórico disponible).
    Devuelve:
      - df_proj_monthly: filas (año, mes) desde next_year..proj_end_year
      - df_clim: climatología mensual (media y std) 1..12
      - df_proj_annual: suma anual por año proyectado
      - df_proj_seasonal: suma por estación (Verano/Otoño/Invierno/Primavera) por año proyectado
    """
    monthly = hourly_to_monthly_kwhm2(df_local, "GHI_Wm2").to_frame("GHI_kWhm2_mes")
    if monthly.empty:
        return (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

    monthly["year"] = monthly.index.year
    monthly["month"] = monthly.index.month

    # Climatología mensual
    clim = monthly.groupby("month")["GHI_kWhm2_mes"].agg(["mean", "std"])
    clim.index.name = "month"

    last_year = monthly["year"].max()
    next_year = last_year + 1
    if next_year > proj_end_year:
        # nada que proyectar
        return (pd.DataFrame(), clim, pd.DataFrame(), pd.DataFrame())

    records = []
    for y in range(next_year, proj_end_year + 1):
        for m in range(1, 13):
            mu = clim.loc[m, "mean"]
            records.append({"year": y, "month": m, "GHI_kWhm2_mes_proj": float(mu)})

    df_proj_monthly = pd.DataFrame(records)
    # Proyección anual
    df_proj_annual = df_proj_monthly.groupby("year")["GHI_kWhm2_mes_proj"].sum().to_frame("GHI_kWhm2_anual_proj").reset_index()

    # Proyección estacional por año
    def season_from_month(m):
        for k, sset in SEASON_MONTHS.items():
            if m in sset: return k
        return None

    df_proj_monthly["season"] = df_proj_monthly["month"].apply(season_from_month)
    df_proj_seasonal = df_proj_monthly.pivot_table(
        index="year", columns="season", values="GHI_kWhm2_mes_proj", aggfunc="sum"
    ).reset_index().rename_axis(None, axis=1)

    # Ordenar columnas de estaciones
    for key in SEASON_KEYS:
        if key not in df_proj_seasonal.columns:
            df_proj_seasonal[key] = np.nan
    df_proj_seasonal = df_proj_seasonal[["year"] + SEASON_KEYS]

    return (df_proj_monthly, clim.reset_index(), df_proj_annual, df_proj_seasonal)

# =================
# PIPELINE (4 estaciones + proyección)
# =================
def run_point_with_seasons(city, lat, lon, backend=DEFAULT_BACKEND,
                           start_date=START_DATE, end_date=END_DATE, tz=TZ,
                           nsrdb_email=None, nsrdb_api_key=None, outdir=OUTDIR,
                           proj_end_year=PROJ_END_YEAR):

    ts_label = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_tag = city.strip().replace(" ", "_")
    print(f"[INFO] {city} lat={lat}, lon={lon} | backend={backend} | {start_date}..{end_date}")

    # 1) Descarga serie horaria
    if backend == "open-meteo":
        df_local = fetch_open_meteo(lat, lon, start_date, end_date, tz)
    elif backend == "nsrdb":
        if not (nsrdb_email and nsrdb_api_key):
            raise ValueError("NSRDB requiere nsrdb_email y nsrdb_api_key")
        df_local = fetch_nsrdb_psm3(lat, lon, start_date, end_date, nsrdb_email, nsrdb_api_key)
    elif backend == "pvgis":
        df_local = fetch_pvgis(lat, lon, start_date, end_date, tz)
    else:
        raise ValueError("Backend no reconocido")

    tag_base = f"{backend}_{city_tag}_lat{str(lat).replace('.','p')}_lon{str(lon).replace('.','p')}"

    # 2) Guardar serie horaria completa (CSV crudo)
    csv_path = os.path.join(outdir, f"{ts_label}_{tag_base}.csv")
    df_local.to_csv(csv_path, sep=";", decimal=",", float_format="%.3f")
    print(f"  -> CSV: {csv_path}")

    # 3) Agregar columna de estación y dividir
    df_local = add_season_column(df_local)

    # 4) Curvas generales (anuales) + archivo combinado de perfiles por estación
    perfil_hor = df_local.groupby(df_local.index.hour)["GHI_Wm2"].mean().reindex(range(24))

    # Perfiles por estación (tabla combinada)
    perfiles_estacionales = pd.DataFrame({"hora": list(range(24))})
    for sk in SEASON_KEYS:
        df_s = df_local[df_local["season"] == sk]
        if df_s.empty or "GHI_Wm2" not in df_s.columns:
            perfiles_estacionales[f"GHI_Wm2_prom_hora_{sk}"] = np.nan
            continue
        perfiles_estacionales[f"GHI_Wm2_prom_hora_{sk}"] = df_s.groupby(df_s.index.hour)["GHI_Wm2"].mean().reindex(range(24)).values

    curvas_csv = os.path.join(outdir, f"{ts_label}_{tag_base}_curvas_horarias_estacionales.csv")
    perfiles_estacionales.to_csv(curvas_csv, sep=";", decimal=",", index=False, float_format="%.3f")
    print(f"  -> Curvas horarias por estación: {curvas_csv}")

    # 5) Cálculos y gráficos por estación
    seasonal_stats = {}
    for sk in SEASON_KEYS:
        df_s = df_local[df_local["season"] == sk]
        if df_s.empty:
            seasonal_stats[sk] = {"GHI_kWhm2_dia_prom": np.nan, "GHI_kWhm2_total_estacion": np.nan, "GHI_Wm2_max": np.nan}
            continue

        daily_kwh_s   = hourly_to_daily_kwhm2(df_s, "GHI_Wm2")
        monthly_kwh_s = hourly_to_monthly_kwhm2(df_s, "GHI_Wm2")

        # Guardar series estacionales (diario y mensual)
        diario_csv = os.path.join(outdir, f"{ts_label}_{tag_base}_diario_{sk}.csv")
        daily_kwh_s.to_csv(diario_csv, sep=";", decimal=",", float_format="%.3f")
        mensual_csv = os.path.join(outdir, f"{ts_label}_{tag_base}_mensual_{sk}.csv")
        monthly_kwh_s.to_csv(mensual_csv, sep=";", decimal=",", float_format="%.3f")

        # Gráficos de la estación
        png_prefix = os.path.join(outdir, f"{ts_label}_{tag_base}_{sk}")
        save_curves_plots(
            df_s,
            daily_kwh_s,
            monthly_kwh_s,
            png_prefix,
            title_prefix=f"{CITY_NAME} - {SEASON_LABELS[sk]}"
        )

        # Stats para consolidado
        seasonal_stats[sk] = {
            "GHI_kWhm2_dia_prom": float(daily_kwh_s.mean()) if len(daily_kwh_s)>0 else np.nan,
            "GHI_kWhm2_total_estacion": float(daily_kwh_s.sum()) if len(daily_kwh_s)>0 else np.nan,
            "GHI_Wm2_max": float(df_s["GHI_Wm2"].max()) if "GHI_Wm2" in df_s.columns else np.nan
        }

    # 6) Consolidado (una fila) con métricas anuales + por estación
    daily_kwh = hourly_to_daily_kwhm2(df_local, "GHI_Wm2")
    monthly_kwh = hourly_to_monthly_kwhm2(df_local, "GHI_Wm2")
    rec = {
        "ciudad": city,
        "lat": lat, "lon": lon,
        "GHI_kWhm2_dia_prom_anual": float(daily_kwh.mean()) if len(daily_kwh)>0 else np.nan,
        "GHI_kWhm2_total_anual": float(daily_kwh.sum()) if len(daily_kwh)>0 else np.nan,
        "GHI_Wm2_max_anual": float(df_local["GHI_Wm2"].max()) if "GHI_Wm2" in df_local.columns else np.nan
    }
    for sk in SEASON_KEYS:
        rec[f"GHI_kWhm2_dia_prom_{sk}"] = seasonal_stats[sk]["GHI_kWhm2_dia_prom"]
        rec[f"GHI_kWhm2_total_{sk}"] = seasonal_stats[sk]["GHI_kWhm2_total_estacion"]
        rec[f"GHI_Wm2_max_{sk}"] = seasonal_stats[sk]["GHI_Wm2_max"]

    consolidado = os.path.join(outdir, f"{ts_label}_consolidado_{backend}_{city_tag}_estaciones.csv")
    pd.DataFrame([rec]).to_csv(consolidado, sep=";", decimal=",", index=False, float_format="%.3f")
    print(f"[OK] Consolidado (anual + estaciones) guardado en {consolidado}")

    # 7) PROYECCIÓN HASTA 2030 (climatología mensual)
    df_proj_monthly, df_clim, df_proj_annual, df_proj_seasonal = build_projection_monthly(df_local, proj_end_year=proj_end_year)

    if not df_clim.empty:
        clim_csv = os.path.join(outdir, f"{ts_label}_{tag_base}_climatologia_mensual.csv")
        df_clim.rename(columns={"mean": "GHI_kWhm2_mes_media", "std": "GHI_kWhm2_mes_std"}).to_csv(
            clim_csv, sep=";", decimal=",", index=False, float_format="%.3f"
        )
        print(f"  -> Climatología mensual: {clim_csv}")

    if not df_proj_monthly.empty:
        proj_m_csv = os.path.join(outdir, f"{ts_label}_{tag_base}_proyeccion_mensual_{proj_end_year}.csv")
        df_proj_monthly.to_csv(proj_m_csv, sep=";", decimal=",", index=False, float_format="%.3f")
        print(f"  -> Proyección mensual hasta {proj_end_year}: {proj_m_csv}")

    if not df_proj_annual.empty:
        proj_a_csv = os.path.join(outdir, f"{ts_label}_{tag_base}_proyeccion_anual_{proj_end_year}.csv")
        df_proj_annual.to_csv(proj_a_csv, sep=";", decimal=",", index=False, float_format="%.3f")
        print(f"  -> Proyección anual hasta {proj_end_year}: {proj_a_csv}")

    if not df_proj_seasonal.empty:
        proj_s_csv = os.path.join(outdir, f"{ts_label}_{tag_base}_proyeccion_estacional_{proj_end_year}.csv")
        df_proj_seasonal.to_csv(proj_s_csv, sep=";", decimal=",", index=False, float_format="%.3f")
        print(f"  -> Proyección estacional hasta {proj_end_year}: {proj_s_csv}")

# =================
# MAIN (CLI)
# =================
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Irradiancia en Asunción (PY) con estaciones y proyección (salida en carpeta del script) | CSV con ';' y ','"
    )
    ap.add_argument("--backend", default=DEFAULT_BACKEND, choices=["open-meteo","nsrdb","pvgis"])
    ap.add_argument("--city", default=CITY_NAME, help="Etiqueta de ciudad")
    ap.add_argument("--lat", type=float, default=LAT_DEFAULT)
    ap.add_argument("--lon", type=float, default=LON_DEFAULT)
    ap.add_argument("--start", default=START_DATE)
    ap.add_argument("--end", default=END_DATE)
    ap.add_argument("--tz", default=TZ)
    ap.add_argument("--proj_end_year", type=int, default=PROJ_END_YEAR)
    ap.add_argument("--nsrdb_email", default=None)
    ap.add_argument("--nsrdb_api_key", default=None)
    args = ap.parse_args()

    run_point_with_seasons(
        city=args.city, lat=args.lat, lon=args.lon,
        backend=args.backend, start_date=args.start, end_date=args.end, tz=args.tz,
        nsrdb_email=args.nsrdb_email, nsrdb_api_key=args.nsrdb_api_key,
        outdir=OUTDIR, proj_end_year=args.proj_end_year
    )
