# -*- coding: utf-8 -*-
"""Curated product catalog. Users can always type any CMR short_name."""

# (short_name, version_hint, desc_zh, desc_en)
GROUPS = [
    ("MODIS Terra", [
        ("MOD13Q1", "6.1", "植被指数 NDVI/EVI，16天，250m", "Vegetation indices NDVI/EVI, 16-day, 250m"),
        ("MOD13A2", "6.1", "植被指数 NDVI/EVI，16天，1km", "Vegetation indices NDVI/EVI, 16-day, 1km"),
        ("MOD11A2", "6.1", "地表温度/发射率 LST，8天，1km", "Land surface temperature/emissivity, 8-day, 1km"),
        ("MOD09GA", "6.1", "地表反射率，日，1km", "Surface reflectance, daily, 1km"),
        ("MOD09GQ", "6.1", "地表反射率，日，250m", "Surface reflectance, daily, 250m"),
        ("MOD10A1", "6.1", "积雪覆盖，日，500m", "Snow cover, daily, 500m"),
        ("MOD17A2H", "6.1", "总初级生产力 GPP，8天，500m", "Gross primary productivity GPP, 8-day, 500m"),
        ("MOD17A3H", "6.1", "净初级生产力 NPP，年，500m", "Net primary productivity NPP, annual, 500m"),
    ]),
    ("MODIS Aqua", [
        ("MYD13Q1", "6.1", "植被指数 NDVI/EVI，16天，250m", "Vegetation indices NDVI/EVI, 16-day, 250m"),
        ("MYD11A2", "6.1", "地表温度/发射率 LST，8天，1km", "Land surface temperature/emissivity, 8-day, 1km"),
        ("MYD09GA", "6.1", "地表反射率，日，1km", "Surface reflectance, daily, 1km"),
        ("MYD10A1", "6.1", "积雪覆盖，日，500m", "Snow cover, daily, 500m"),
    ]),
    ("MODIS Combined", [
        ("MCD43A4", "6.1", "Nadir BRDF 反射率 NBAR，日，500m", "Nadir BRDF-adjusted reflectance, daily, 500m"),
        ("MCD43A3", "6.1", "反照率 Albedo，日，500m", "Albedo, daily, 500m"),
        ("MCD12Q1", "6.1", "土地覆盖类型，年，500m", "Land cover type, annual, 500m"),
        ("MCD64A1", "6.1", "火烧迹地，月，500m", "Burned area, monthly, 500m"),
    ]),
    ("VIIRS", [
        ("VNP46A1", "2", "夜间灯光/夜光 DNB 辐亮度（TOA），日，500m", "Nighttime lights DNB TOA radiance, daily, 500m"),
        ("VNP46A2", "2", "夜间灯光/夜光 VPDN（去云），日，500m", "Nighttime lights VPDN (cloud-free), daily, 500m"),
        ("VNP09GA", "2", "地表反射率，日，1km/500m", "Surface reflectance, daily, 1km/500m"),
        ("VNP13A1", "2", "植被指数 NDVI，16天，500m", "Vegetation indices NDVI, 16-day, 500m"),
    ]),
    ("MERRA-2 (GES DISC)", [
        ("M2T1NXSLV", "5.12.4", "单层2D 逐时 气象要素（风/温/湿/压）", "Hourly 2D single-level meteorology (wind/T/RH/PS)"),
        ("M2T1NXRAD", "5.12.4", "单层2D 逐时 辐射通量", "Hourly 2D single-level radiation fluxes"),
        ("M2T1NXAER", "5.12.4", "单层2D 逐时 气溶胶", "Hourly 2D single-level aerosol"),
        ("M2T1NXFLX", "5.12.4", "单层2D 逐时 湍流/通量", "Hourly 2D single-level turbulence fluxes"),
        ("M2I3NPASM", "5.12.4", "3D 逐时 同化态温压风湿", "Hourly 3D assimilated T/P/U/V/RH"),
        ("M2I3NPCLD", "5.12.4", "3D 逐时 云参数", "Hourly 3D cloud parameters"),
        ("M2C0NXLND", "5.12.4", "常数2D 陆地掩膜/网格", "Constant 2D land mask / grid"),
    ]),
]

GROUP_CUSTOM = "custom"


def _glass_group():
    """The GLASS group is generated from d3ltool/glass_registry.py (which is
    generated from the author's glass.sqdaitools R package) — verified
    variants first.  These ids route to the public glass.hku.hk directory
    search, not CMR, and never need an Earthdata sign-in."""
    from . import glass_registry as gr

    items = []
    for v in sorted(gr.VARIANTS.values(),
                    key=lambda v: (not v["verified"], v["variant_id"])):
        if v["temporal_res"]:
            res_zh = res_en = v["temporal_res"]
        elif v["layout"] == "flat":
            res_zh, res_en = "无时间维（固定层）", "no time dimension (static layer)"
        else:
            res_zh, res_en = "合成周期未核验", "cadence unverified"
        zh = f"{v['long_name']}，{res_zh}" + ("（已核验）" if v["verified"] else "")
        en = f"{v['long_name']}, {res_en}" + (" (verified)" if v["verified"] else "")
        items.append((v["variant_id"], v["version"] or "", zh, en))
    return ("GLASS", items)


GROUPS.append(_glass_group())


def find_product(short_name: str):
    short = short_name.strip().upper()
    for _, items in GROUPS:
        for p in items:
            if p[0] == short:
                return p
    return None


def version_hint(short_name: str) -> str:
    p = find_product(short_name)
    return p[1] if p else ""
