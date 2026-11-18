#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pv_capacity_by_neighborhood2.py
Genera: CSV global, 4 CSV por estación (por defecto), CSV por mes (si lo pides),
GeoJSONs, reporte TXT y JSON de parámetros. Incluye barrido de tilt 30–60°,
y ventanas de azimut hacia el Norte para estaciones/meses.

Ejemplos:
  python pv_capacity_by_neighborhood2.py --barrio "Ciudad Nueva, Asunción, Paraguay"
  # desactivar estaciones:
  python pv_capacity_by_neighborhood2.py --barrio "..." --no-export-seasons
  # generar meses:
  python pv_capacity_by_neighborhood2.py --barrio "..." --export-months
"""

from __future__ import annotations
import os, sys, io, json, time, math, zipfile, argparse, webbrowser, platform, subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

import requests
from shapely.geometry import shape, Polygon, MultiPolygon, box, mapping
from shapely.ops import unary_union, transform as shp_transform
from shapely.affinity import rotate, translate
from shapely.strtree import STRtree
from pyproj import CRS, Transformer

# ------------ Config por defecto ------------
DEFAULT_BARRIO = "Ciudad Nueva, Asunción, Paraguay"
DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
RESIDENTIAL_BUILDINGS = {"house","residential","apartments","detached","semidetached_house","terrace","farm","yes"}
LEVEL_TO_M = 3.0
DEFAULT_HEIGHTS = {"apartments":12.0,"residential":6.0,"house":6.0,"detached":6.0,"semidetached_house":6.0,"terrace":6.0,"farm":6.0,"yes":6.0}

# ------------ Utils ------------
def clear_screen():
    os.system("cls" if os.name=="nt" else "clear")

def script_dir() -> Path:
    # Fuerza SIEMPRE la carpeta donde está este .py
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path(sys.argv[0]).resolve().parent

def fmt_dec(x: float, nd=2) -> str:
    return f"{x:.{nd}f}".replace(".", ",")

def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def lonlat_to_utm_crs(lon: float, lat: float) -> CRS:
    zone = int((lon + 180) / 6) + 1
    epsg = (32700 if lat < 0 else 32600) + zone
    return CRS.from_epsg(epsg)

def project(geom, crs_from: CRS, crs_to: CRS):
    tr = Transformer.from_crs(crs_from, crs_to, always_xy=True)
    return shp_transform(lambda x,y,z=None: tr.transform(x,y), geom)

def negative_buffer(g: Polygon | MultiPolygon, d: float):
    try:
        gb = g.buffer(-abs(d))
        if gb.is_empty:
            return None
        return gb
    except Exception:
        return None

# ------------ Geocodificación y fuentes ------------
def geocode_neighborhood(query: str):
    headers = {"User-Agent": "pv-auto/1.8"}
    params = {"q": query, "format": "jsonv2", "polygon_geojson": 1, "addressdetails": 1}
    r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=60)
    r.raise_for_status()
    res = r.json()
    if not res:
        raise RuntimeError(f"No se encontró polígono para: {query}")

    def score(x):
        t = x.get("type","")
        imp = x.get("importance",0.0)
        bias = 0
        if t in ("neighbourhood","suburb"):
            bias += 2
        if "Asunción" in (x.get("display_name") or ""):
            bias += 1
        return (bias, imp)

    cand = sorted(res, key=score, reverse=True)[0]
    geom = shape(cand["geojson"])
    return unary_union(geom) if isinstance(geom, MultiPolygon) else geom

def overpass_buildings_within(polygon: Polygon|MultiPolygon, overpass_url: str) -> List[Dict[str,Any]]:
    poly = max(polygon.geoms, key=lambda g: g.area) if isinstance(polygon, MultiPolygon) else polygon
    x, y = poly.exterior.xy
    coord_list = [f"{yy} {xx}" for xx,yy in zip(x,y)]  # Overpass espera lat lon
    poly_str = " ".join(coord_list)
    res_re = f"^({'|'.join(sorted(RESIDENTIAL_BUILDINGS))})$"
    q = f"""[out:json][timeout:180];(way["building"~"{res_re}"](poly:"{poly_str}"););out tags geom;"""
    headers={"User-Agent":"pv-auto/1.8"}
    resp = requests.post(overpass_url, data={"data":q}, headers=headers, timeout=180)
    if resp.status_code in (429,504,502):
        time.sleep(55)
        resp = requests.post(overpass_url, data={"data":q}, headers=headers, timeout=180)
    resp.raise_for_status()
    data = resp.json()
    return [e for e in data.get("elements",[]) if e.get("type")=="way" and "geometry" in e]

def msfile_buildings_within(ms_zip: str, roi_ll: Polygon|MultiPolygon) -> List[Dict[str,Any]]:
    out=[]
    with zipfile.ZipFile(ms_zip) as z:
        names=[n for n in z.namelist() if n.lower().endswith((".geojsonl",".geojson"))]
        if not names:
            raise RuntimeError("Zip sin .geojsonl/.geojson")
        with z.open(names[0]) as f:
            if names[0].lower().endswith(".geojson"):
                data=json.load(io.TextIOWrapper(f,encoding="utf-8"))
                feats=data.get("features",[])
                for feat in feats:
                    g=shape(feat.get("geometry"))
                    if not g.is_valid or g.is_empty or not g.intersects(roi_ll):
                        continue
                    out.append({
                        "type":"way",
                        "id":feat.get("id") or feat.get("properties",{}).get("id"),
                        "tags":{"building":"yes"},
                        "geometry":[{"lon":x,"lat":y} for x,y in list(g.exterior.coords)]
                    })
            else:
                for line in io.TextIOWrapper(f,encoding="utf-8"):
                    if not line.strip():
                        continue
                    feat=json.loads(line)
                    g=shape(feat.get("geometry"))
                    if not g.is_valid or g.is_empty or not g.intersects(roi_ll):
                        continue
                    out.append({
                        "type":"way",
                        "id":feat.get("id") or feat.get("properties",{}).get("id"),
                        "tags":{"building":"yes"},
                        "geometry":[{"lon":x,"lat":y} for x,y in list(g.exterior.coords)]
                    })
    return out

# ------------ Alturas y sombras ------------
def estimate_height_m(tags: Dict[str,Any]) -> float:
    lv = tags.get("building:levels") or tags.get("levels")
    if lv:
        try:
            v=float(str(lv).split(";")[0].strip())
            if v>0:
                return v*LEVEL_TO_M
        except:
            pass
    b=(tags.get("building") or "yes").lower()
    return DEFAULT_HEIGHTS.get(b, DEFAULT_HEIGHTS["yes"])

def shadow_polygon(poly_m: Polygon, height_m: float, elev_deg: float, az_from_north_deg: float) -> Polygon:
    elev_deg = max(1.0, elev_deg)  # evita infinito
    L = height_m / math.tan(math.radians(elev_deg))
    az = math.radians(az_from_north_deg)
    dx, dy = -L*math.sin(az), -L*math.cos(az)  # sombra en contra del sol
    return translate(poly_m, xoff=dx, yoff=dy).buffer(0.05)

# ------------ Layout de paneles ------------
def required_row_spacing(panel_block_m: float, tilt_deg: float, shade_elev_deg: float) -> float:
    if shade_elev_deg <= 0 or tilt_deg <= 0:
        return 0.0
    h = panel_block_m * math.sin(math.radians(tilt_deg))
    den = math.tan(math.radians(shade_elev_deg))
    return 0.0 if den<=1e-9 else h/den

def place_panels(poly_m: Polygon, angle_deg: float, pw: float, pl: float, gap: float, row_spacing: float) -> Tuple[int, List[Polygon]]:
    pr = rotate(poly_m, -angle_deg, origin="centroid", use_radians=False)
    minx, miny, maxx, maxy = pr.bounds
    step_x = pw + gap
    step_y = pl + max(gap, row_spacing)
    rects=[]; n=0
    y = miny + pl/2.0
    while y + pl/2.0 <= maxy + 1e-9:
        x = minx + pw/2.0
        while x + pw/2.0 <= maxx + 1e-9:
            r = box(x - pw/2.0, y - pl/2.0, x + pw/2.0, y + pl/2.0)
            if r.within(pr):
                rects.append(r); n += 1
            x += step_x
        y += step_y
    rects = [rotate(r, angle_deg, origin=poly_m.centroid, use_radians=False) for r in rects]
    return n, rects

def frange(a: float, b: float, step: float):
    x=a
    while x <= b + 1e-9:
        yield round(x,6)
        x += step

def best_layout_for_angles_and_tilts(poly_m: Polygon, pw: float, pl: float, gap: float,
                                     shade_elev_deg: float, angles: List[float],
                                     tilt_min: float, tilt_max: float, tilt_step: float) -> Tuple[int,float,float,List[Polygon]]:
    """
    Evalúa combinaciones (ángulo, tilt) restringiendo tilt al rango [tilt_min, tilt_max].
    Devuelve: (n_paneles_max, angulo_opt, tilt_opt, rects_opt)
    """
    best = (0, 0.0, tilt_min, [])
    for tilt in frange(tilt_min, tilt_max, tilt_step):
        row_spacing = required_row_spacing(pl, tilt, shade_elev_deg)
        for ang in angles:
            n, rects = place_panels(poly_m, ang, pw, pl, gap, row_spacing)
            if n > best[0]:
                best = (n, float(ang), float(tilt), rects)
    return best

# ------------ STRtree helpers ------------
def make_id_map(geoms: List[Polygon]) -> Dict[int, int]:
    return {id(g): i for i, g in enumerate(geoms)}

def tree_query_indices(tree: STRtree, geoms: List[Polygon], qgeom: Polygon, id_map: Dict[int,int]) -> List[int]:
    res = tree.query(qgeom)
    if res is None:
        return []
    idxs=[]
    for item in res:
        if hasattr(item,"geom_type"):
            ii = id_map.get(id(item))
            if ii is not None:
                idxs.append(ii)
        else:
            try:
                idxs.append(int(item))
            except Exception:
                pass
    return idxs

# ------------ Ventanas de azimut Norte (estación/mes) ------------
def north_allowed_angles(lat_deg: float, month: Optional[int], season: str) -> List[float]:
    base = [-10.0, 0.0, 10.0]
    cool = [-15.0, -5.0, 0.0, 5.0, 15.0]  # meses fríos en el SH
    south = lat_deg < 0.0
    if month is not None and 1 <= month <= 12:
        if south and month in (3,4,5,6,7,8):
            return cool
        return base
    if season in ("autumn","winter"):
        return cool if south else base
    return base  # annual/spring/summer

# ----------- Popup (opcional) ------------
def popup_get_params(default_wp: float):
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except Exception:
        return None

    result = {"wp": None}

    root = tk.Tk()
    root.title("Parámetros FV")
    root.geometry("320x110")
    root.resizable(False, False)

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)

    ttk.Label(
        frm,
        text="Potencia por panel (kWp):"
    ).grid(row=0, column=0, sticky="w", pady=4)

    e_wp = ttk.Entry(frm)
    e_wp.grid(row=0, column=1, sticky="ew", pady=4)
    e_wp.insert(0, f"{default_wp:.2f}")

    frm.columnconfigure(1, weight=1)

    def on_ok():
        try:
            wp = float(e_wp.get().replace(",", "."))
            result["wp"] = wp
            root.destroy()
        except ValueError:
            messagebox.showerror(
                "Error",
                "Ingrese un valor numérico válido para la potencia del panel."
            )

    def on_cancel():
        root.destroy()

    btns = ttk.Frame(frm)
    btns.grid(row=1, column=0, columnspan=2, pady=(10, 0))

    ttk.Button(btns, text="Aceptar", command=on_ok).pack(side="left", padx=5)
    ttk.Button(btns, text="Cancelar", command=on_cancel).pack(side="left", padx=5)

    root.mainloop()

    return result["wp"]

# ------------ Export ------------
def write_csv_semicolon(path: Path, rows: List[Dict[str,Any]]):
    cols=["osmid","building","lon","lat","altura_m","area_post_setback_m2","area_sin_sombra_m2","n_paneles","kwp","energia_anual_kwh","angulo_deg","tilt_deg"]
    with path.open("w", encoding="utf-8") as f:
        f.write(";".join(cols)+"\n")
        for r in rows:
            vals=[]
            for c in cols:
                v=r.get(c,"")
                if isinstance(v,float):
                    nd=6 if c in ("lon","lat") else 2
                    vals.append(fmt_dec(v, nd))
                else:
                    vals.append(str(v))
            f.write(";".join(vals)+"\n")

def write_geojson(path: Path, feats: List[Dict[str,Any]]):
    gj={"type":"FeatureCollection","features":feats}
    path.write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")

def write_txt_report(path: Path, args, rows: List[Dict[str,Any]], params_json_path: Path):
    tot_kwp=sum(r['kwp'] for r in rows); tot_kwh=sum(r.get('energia_anual_kwh',0.0) for r in rows); tot_pan=sum(r['n_paneles'] for r in rows); n_bld=len(rows)
    top10=sorted(rows, key=lambda x: x['kwp'], reverse=True)[:10]
    lines=[]
    lines.append("===== REPORTE DE RESULTADOS PV =====")
    lines.append(f"Barrio: {args.barrio}")
    lines.append(f"Fuente: {args.source}")
    lines.append(f"Panel (m): {args.panel_w} x {args.panel_l} | Gap: {args.gap_m}")
    lines.append(f"Tilt: [{args.tilt_min_deg}–{args.tilt_max_deg}]° (paso {args.tilt_step_deg}°) | Elevación mínima sombra: {args.shade_elev_deg}°")
    lines.append(f"Setback: {args.setback_m} m | Sweep base: {args.sweep_deg}°")
    lines.append(f"North-only base: {'Sí' if args.north_only else 'No'} | Temporada: {args.season} | Mes: {args.month}")
    lines.append(f"Potencia por panel: {args.module_wp} kWp")
    lines.append(f"Specific yield: {args.specific_yield_kwhkwp} kWh/kWp·año")
    lines.append("")
    lines.append(f"Edificios procesados: {n_bld}")
    lines.append(f"Paneles totales: {tot_pan}")
    lines.append(f"kWp totales: {tot_kwp:.2f}")
    lines.append(f"Energía anual total (kWh): {tot_kwh:.0f}")
    lines.append("")
    lines.append("Top-10 edificios por kWp:")
    for i, r in enumerate(top10, start=1):
        lines.append(f"{i:02d}. osmid={r['osmid']} | kWp={r['kwp']:.2f} | kWh/año={r.get('energia_anual_kwh',0.0):.0f} | ángulo={r['angulo_deg']}° | tilt={r.get('tilt_deg',0.0):.1f}°")
    lines.append("")
    lines.append(f"Parámetros guardados: {params_json_path.name}")
    path.write_text("\n".join(lines), encoding="utf-8")

def open_text_file(path: Path):
    try:
        if os.name=="nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            if platform.system()=="Darwin": subprocess.Popen(["open", str(path)])
            else: subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        try: webbrowser.open(path.as_uri())
        except Exception: pass

# ------------ Núcleo reutilizable ------------
def compute_rows_for_angles(geoms_m: List[Polygon], geoms_ll: List[Polygon], heights: List[float], cents_m: List[Any],
                            crs_ll: CRS, crs_m: CRS, buildings_meta: List[Dict[str,Any]],
                            angles: List[float], panel_w: float, panel_l: float, gap_m: float,
                            shade_elev_deg: float, neighbor_ctrl: Dict[str,Any],
                            tilt_min: float, tilt_max: float, tilt_step: float,
                            module_wp: float, specific_yield: float, progress_n: int):
    rows=[]; roof_feats=[]; panel_feats=[]
    tree=neighbor_ctrl["tree"]; id_map=neighbor_ctrl["id_map"]
    neighbor_radius_m=neighbor_ctrl["neighbor_radius_m"]; max_neighbors=neighbor_ctrl["max_neighbors"]
    no_neighbor_shade=neighbor_ctrl["no_neighbor_shade"]; setback_m=neighbor_ctrl["setback_m"]; min_area_m2=neighbor_ctrl["min_area_m2"]
    az_list=[-60.0,0.0,60.0]; total=len(geoms_m); t0=time.time()
    for i, poly_m in enumerate(geoms_m):
        inner = negative_buffer(poly_m, setback_m) if setback_m>0 else poly_m
        if inner is None or inner.is_empty: continue
        if float(inner.area) < min_area_m2: continue
        usable = inner
        if not no_neighbor_shade and shade_elev_deg > 0:
            query_geom = cents_m[i].buffer(neighbor_radius_m)
            cand_idxs = tree_query_indices(tree, geoms_m, query_geom, id_map)
            cand_idxs = [j for j in cand_idxs if j != i]
            cand_idxs.sort(key=lambda j: cents_m[i].distance(cents_m[j]))
            if max_neighbors > 0 and len(cand_idxs) > max_neighbors:
                cand_idxs = cand_idxs[:max_neighbors]
            shades=[]; hi=heights[i]
            for j in cand_idxs:
                hj=heights[j]
                if hj <= hi*0.9:  # vecinos claramente más altos
                    continue
                gj=geoms_m[j]
                for az in az_list:
                    shades.append(shadow_polygon(gj, hj, shade_elev_deg, az))
            if shades:
                shade_union = unary_union(shades); diff = usable.difference(shade_union)
                usable = diff if not diff.is_empty else Polygon()
        if usable.is_empty:
            if (i+1) % progress_n == 0:
                dt=time.time()-t0; print(f"[{i+1}/{total}] sin área usable tras sombras | t={dt:.1f}s")
            continue
        best_n=0; best_a=0.0; best_tilt=tilt_min; all_rects=[]
        parts = [usable] if isinstance(usable, Polygon) else list(usable.geoms)
        for part in parts:
            if part.area<=0: continue
            n,a,tilt,rects = best_layout_for_angles_and_tilts(part, panel_w, panel_l, gap_m, shade_elev_deg,
                                                              angles, tilt_min, tilt_max, tilt_step)
            best_n += n
            if n>0:
                all_rects.extend(rects); best_a=a; best_tilt=tilt
        kwp = best_n * module_wp; energia_kwh = kwp * max(0.0, specific_yield)
        rows.append({"osmid":buildings_meta[i]["osmid"],"building":buildings_meta[i]["building"],
                     "lon":buildings_meta[i]["lon"],"lat":buildings_meta[i]["lat"],"altura_m":heights[i],
                     "area_post_setback_m2":float(inner.area),"area_sin_sombra_m2":float(usable.area),
                     "n_paneles":int(best_n),"kwp":float(kwp),"energia_anual_kwh":float(energia_kwh),
                     "angulo_deg":float(round(best_a,1)),"tilt_deg":float(round(best_tilt,1))})
        usable_ll = project(usable, crs_m, crs_ll)
        roof_feats.append({"type":"Feature","properties":{"osmid":buildings_meta[i]["osmid"]},"geometry": mapping(usable_ll)})
        for r in all_rects:
            r_ll = project(r, crs_m, crs_ll)
            panel_feats.append({"type":"Feature","properties":{"osmid":buildings_meta[i]["osmid"],"wp": module_wp},"geometry": mapping(r_ll)})
        if (i+1) % progress_n == 0:
            dt=time.time()-t0; print(f"[{i+1}/{total}] procesados | t={dt:.1f}s")
    return rows, roof_feats, panel_feats

# ------------ Main ------------
def main():
    clear_screen()

    ap = argparse.ArgumentParser(description="Layout PV por edificio + CSV global + CSVs por estación/mes (misma carpeta del script).")

    # Área de estudio
    ap.add_argument("--barrio", type=str, default=DEFAULT_BARRIO)
    ap.add_argument("--source", choices=["overpass","msfile"], default="overpass")
    ap.add_argument("--ms-file", type=str, help="Ruta a *.zip con Microsoft GBF para Paraguay")
    ap.add_argument("--overpass-url", type=str, default=DEFAULT_OVERPASS_URL)

    # Geometría / layout base
    ap.add_argument("--setback-m", type=float, default=0.60)
    ap.add_argument("--min-area-m2", type=float, default=5.0)
    ap.add_argument("--panel-w", type=float, default=1.10)
    ap.add_argument("--panel-l", type=float, default=1.80)
    ap.add_argument("--gap-m", type=float, default=0.02)

    # Potencia / energía
    ap.add_argument("--module-wp", type=float, default=0.41, help="Potencia por panel (kWp)")
    ap.add_argument("--specific-yield-kwhkwp", type=float, default=1650.0, help="Producción específica anual (kWh/kWp·año).")

    # Sombras y orientación
    ap.add_argument("--shade-elev-deg", type=float, default=30.0)
    ap.add_argument("--sweep-deg", type=int, default=5)

    # Barrido de tilt (prioridad 30–60° por defecto)
    ap.add_argument("--tilt-min-deg", type=float, default=30.0)
    ap.add_argument("--tilt-max-deg", type=float, default=60.0)
    ap.add_argument("--tilt-step-deg", type=float, default=5.0)

    # Orientación Norte (para la corrida base si querés limitar)
    ap.add_argument("--north-only", action="store_true", help="Restringe la corrida base a ventana alrededor del Norte.")
    ap.add_argument("--season", choices=["annual","summer","autumn","winter","spring"], default="annual")
    ap.add_argument("--month", type=int, default=None, help="Mes 1..12 (prioridad sobre season)")

    # Exportos adicionales
    ap.add_argument("--export-seasons", action="store_true", default=True,
                    help="(por defecto) Exportar 4 CSV por estación.")
    ap.add_argument("--no-export-seasons", action="store_true", default=False,
                    help="No exportar CSV por estación.")
    ap.add_argument("--export-months", action="store_true",
                    help="Generar CSV por cada mes (1..12).")

    # Performance
    ap.add_argument("--no-neighbor-shade", action="store_true", help="Desactivar sombras de vecinos")
    ap.add_argument("--neighbor-radius-m", type=float, default=40.0)
    ap.add_argument("--max-neighbors", type=int, default=60)
    ap.add_argument("--progress-n", type=int, default=50)
    ap.add_argument("--fast", action="store_true", help="Modo rápido: sin sombras y paso mayor")

    # Interactivo
    ap.add_argument("--interactive", action="store_true", help="Popup para potencia nominal del módulo")

    args = ap.parse_args()

    # Ajuste de flags estaciones: --no-export-seasons anula el default
    if args.no_export_seasons:
        args.export_seasons = False

    # Forzar que todo se escriba en la misma carpeta del script
    out_dir = script_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chdir(out_dir)
    except Exception:
        pass

    # Velocidad
    if args.fast:
        args.no_neighbor_shade = True
        args.sweep_deg = max(args.sweep_deg, 15)

    # Popup
   if args.interactive:
       wp = popup_get_params(args.module_wp)
       if wp is not None:
           args.module_wp = float(wp)

    print(f"[INFO] Carpeta de salida (script): {out_dir}")
    print(f"[INFO] Barrio: {args.barrio} | Fuente: {args.source}")
    print(f"[INFO] Panel {args.panel_w}x{args.panel_l} m | gap {args.gap_m} m | Setback {args.setback_m} m")
    print(f"[INFO] Tilt sweep: {args.tilt_min_deg}–{args.tilt_max_deg}° (paso {args.tilt_step_deg}°) | elev sombra {args.shade_elev_deg}°")
    print(f"[INFO] Wp/panel: {args.module_wp} kWp | Specific yield: {args.specific_yield_kwhkwp} kWh/kWp·año")
    print(f"[INFO] Exportar estaciones: {'Sí' if args.export_seasons else 'No'} | Exportar meses: {'Sí' if args.export_months else 'No'}")

    ts = stamp()
    slug = args.barrio.replace(",","").replace(" ","_")

    base_csv = out_dir / f"pv_buildings_{slug}_{ts}.csv"
    base_gj_roof = out_dir / f"roofs_usable_{slug}_{ts}.geojson"
    base_gj_pan = out_dir / f"pv_rects_{slug}_{ts}.geojson"
    barrio_gj = out_dir / f"barrio_{slug}_{ts}.geojson"
    base_txt = out_dir / f"pv_report_{slug}_{ts}.txt"
    params_json = out_dir / f"pv_params_{slug}_{ts}.json"

    # Guardar parámetros
    args_dict = vars(args).copy()
    params_json.write_text(json.dumps(args_dict, indent=2, ensure_ascii=False), encoding="utf-8")

    # Polígono barrio
    geom_ll = geocode_neighborhood(args.barrio)
    write_geojson(barrio_gj, [{"type":"Feature","properties":{},"geometry":geom_ll.__geo_interface__}])

    # Buildings
    if args.source=="overpass":
        ways = overpass_buildings_within(geom_ll, args.overpass_url)
    else:
        if not args.ms_file or not Path(args.ms_file).exists():
            raise RuntimeError("Indica --ms-file con el .zip de Microsoft.")
        ways = msfile_buildings_within(args.ms_file, geom_ll)

    print(f"[INFO] Footprints residenciales: {len(ways)}")
    if not ways:
        print("[INFO] Sin edificios. Salgo.")
        return

    # CRS y estructuras
    lons=[pt["lon"] for w in ways for pt in w["geometry"]]
    lats=[pt["lat"] for w in ways for pt in w["geometry"]]
    lon_c, lat_c = (sum(lons)/len(lons), sum(lats)/len(lats))
    crs_ll = CRS.from_epsg(4326)
    crs_m = lonlat_to_utm_crs(lon_c, lat_c)

    buildings=[]; geoms_ll=[]; geoms_m=[]; heights=[]; cents_m=[]
    for w in ways:
        coords=[(pt["lon"],pt["lat"]) for pt in w["geometry"]]
        if coords[0]!=coords[-1]: coords.append(coords[0])
        poly_ll = Polygon(coords)
        if not poly_ll.is_valid or poly_ll.area==0: continue
        gm = project(poly_ll, crs_ll, crs_m)
        geoms_ll.append(poly_ll); geoms_m.append(gm); heights.append(estimate_height_m(w.get("tags",{})))
        c_ll = poly_ll.centroid; c_m = gm.centroid; cents_m.append(c_m)
        buildings.append({"osmid":w.get("id"),"building":w.get("tags",{}).get("building",""),
                          "lon":float(c_ll.x),"lat":float(c_ll.y)})

    def angles_for(lat_c: float, month: Optional[int], season: str, north_only: bool, sweep_deg: int) -> List[float]:
        if north_only:  # ventana hacia el Norte
            return north_allowed_angles(lat_c, month, season)
        # barrido completo si no se restringe al Norte
        return [float(a) for a in range(0, 180, max(1, sweep_deg))]

    # Control de vecinos (compartido)
    tree = STRtree(geoms_m)
    id_map = make_id_map(geoms_m)
    neighbor_ctrl = {"tree":tree,"id_map":id_map,"neighbor_radius_m":args.neighbor_radius_m,"max_neighbors":args.max_neighbors,
                     "no_neighbor_shade":args.no_neighbor_shade,"setback_m":args.setback_m,"min_area_m2":args.min_area_m2}

    # ======= Corrida GLOBAL =======
    base_angles = angles_for(lat_c, args.month, args.season, args.north_only, args.sweep_deg)
    rows, roof_feats, panel_feats = compute_rows_for_angles(
        geoms_m, geoms_ll, heights, cents_m, crs_ll, crs_m, buildings,
        base_angles, args.panel_w, args.panel_l, args.gap_m, args.shade_elev_deg, neighbor_ctrl,
        args.tilt_min_deg, args.tilt_max_deg, args.tilt_step_deg, args.module_wp, args.specific_yield_kwhkwp, args.progress_n
    )
    write_csv_semicolon(base_csv, rows)
    write_geojson(base_gj_roof, roof_feats)
    write_geojson(base_gj_pan, panel_feats)
    write_txt_report(base_txt, args, rows, params_json)

    print("\n===== RESULTADOS BASE =====")
    print(f"[OK] CSV base: {base_csv}")
    print(f"[OK] GeoJSON techo utilizable: {base_gj_roof}")
    print(f"[OK] GeoJSON paneles: {base_gj_pan}")
    print(f"[OK] Polígono del barrio: {barrio_gj}")
    print(f"[OK] Reporte TXT: {base_txt}")
    print(f"[OK] Parámetros JSON: {params_json}")
    print(f"Edificios: {len(rows)} | Paneles: {sum(r['n_paneles'] for r in rows)} | kWp: {fmt_dec(sum(r['kwp'] for r in rows),2)} | kWh/año: {fmt_dec(sum(r['energia_anual_kwh'] for r in rows),0)}")

    # ======= CSVs por ESTACIÓN (por defecto activado) =======
    if args.export_seasons:
        for seas in ["summer","autumn","winter","spring"]:
            print(f"\n[SEASON] Generando CSV para {seas}...")
            angs = angles_for(lat_c, None, seas, True, args.sweep_deg)  # ventana Norte por estación
            s_rows, _, _ = compute_rows_for_angles(
                geoms_m, geoms_ll, heights, cents_m, crs_ll, crs_m, buildings,
                angs, args.panel_w, args.panel_l, args.gap_m, args.shade_elev_deg, neighbor_ctrl,
                args.tilt_min_deg, args.tilt_max_deg, args.tilt_step_deg, args.module_wp, args.specific_yield_kwhkwp, args.progress_n
            )
            out_csv = out_dir / f"pv_buildings_{slug}_{seas}_{ts}.csv"
            write_csv_semicolon(out_csv, s_rows)
            print(f"[OK] {seas}: {out_csv} | kWp={sum(r['kwp'] for r in s_rows):.2f} | kWh/año={sum(r['energia_anual_kwh'] for r in s_rows):.0f}")

    # ======= CSVs por MES (opcional) =======
    if args.export_months:
        for m in range(1,13):
            print(f"\n[MONTH] Generando CSV para mes {m}...")
            angs = angles_for(lat_c, m, "annual", True, args.sweep_deg)   # ventana Norte por mes
            m_rows, _, _ = compute_rows_for_angles(
                geoms_m, geoms_ll, heights, cents_m, crs_ll, crs_m, buildings,
                angs, args.panel_w, args.panel_l, args.gap_m, args.shade_elev_deg, neighbor_ctrl,
                args.tilt_min_deg, args.tilt_max_deg, args.tilt_step_deg, args.module_wp, args.specific_yield_kwhkwp, args.progress_n
            )
            out_csv = out_dir / f"pv_buildings_{slug}_M{m:02d}_{ts}.csv"
            write_csv_semicolon(out_csv, m_rows)
            print(f"[OK] Mes {m:02d}: {out_csv} | kWp={sum(r['kwp'] for r in m_rows):.2f} | kWh/año={sum(r['energia_anual_kwh'] for r in m_rows):.0f}")

    # Abrir reporte base para revisión rápida
    open_text_file(base_txt)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        sys.exit(1)
