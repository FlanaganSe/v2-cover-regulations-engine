"""Ingestion configuration: endpoint URLs and field mappings."""

# ArcGIS REST endpoints — all public, no auth required
ENDPOINTS = {
    "parcels": (
        "https://public.gis.lacounty.gov/public/rest/services"
        "/LACounty_Cache/LACounty_Parcel/MapServer/0"
    ),
    "zoning": (
        "https://maps.lacity.org/arcgis/rest/services"
        "/Mapping/NavigateLA/MapServer/71"
    ),
    "specific_plans": (
        "https://maps.lacity.org/arcgis/rest/services"
        "/Mapping/NavigateLA/MapServer/93"
    ),
    "hpoz": (
        "https://maps.lacity.org/arcgis/rest/services"
        "/Mapping/NavigateLA/MapServer/75"
    ),
    "community_plan_areas": (
        "https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services"
        "/Community_Plan_Areas/FeatureServer/0"
    ),
    "general_plan_lu": (
        "https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services"
        "/General_Plan_Land_Use/FeatureServer/1"
    ),
    "buildings": (
        "https://public.gis.lacounty.gov/public/rest/services"
        "/LACounty_Dynamic/LARIAC_Buildings_2020/MapServer/0"
    ),
    "city_boundaries": (
        "https://public.gis.lacounty.gov/public/rest/services"
        "/LACounty_Dynamic/Political_Boundaries/MapServer/19"
    ),
}

# Page sizes per endpoint (use each endpoint's maxRecordCount)
PAGE_SIZES = {
    "parcels": 1000,
    "zoning": 20000,
    "specific_plans": 1000,
    "hpoz": 1000,
    "community_plan_areas": 1000,
    "general_plan_lu": 1000,
    "buildings": 1000,
    "city_boundaries": 1000,
}

# Demo neighborhood bounding boxes for buildings (Silver Lake, Venice, Eagle Rock)
DEMO_BBOXES = {
    "silver_lake": {
        "xmin": -118.28,
        "ymin": 34.07,
        "xmax": -118.25,
        "ymax": 34.10,
    },
    "venice": {
        "xmin": -118.48,
        "ymin": 33.98,
        "xmax": -118.44,
        "ymax": 34.01,
    },
    "eagle_rock": {
        "xmin": -118.23,
        "ymin": 34.13,
        "xmax": -118.19,
        "ymax": 34.16,
    },
}
