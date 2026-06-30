# Run this in VS Code terminal first if needed:
# py -m pip install pandas geopandas openpyxl pyogrio matplotlib

import pandas as pd
import geopandas as gpd
import gc
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


# Find files inside the project folder.
def find_file(filename):
    matches = list(BASE_DIR.rglob(filename))
    return str(matches[0]) if len(matches) > 0 else None


def find_file_contains(text):
    matches = [
        file for file in BASE_DIR.rglob("*")
        if file.is_file() and text.lower() in file.name.lower()
    ]
    return str(matches[0]) if len(matches) > 0 else None


# Clean numeric columns that may contain commas, percent signs, or dollar signs.
def clean_numeric(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("$", "", regex=False),
        errors="coerce"
    )


# Extract the county FIPS from Census GEO_ID values.
def extract_county_fips_from_geo_id(series):
    return series.astype(str).str.extract(r"US(\d{5})")[0]


# Make sure merge datasets have one row per key before joining.
def deduplicate_before_merge(df, key_cols):
    if isinstance(key_cols, str):
        key_cols = [key_cols]

    duplicate_count = df.duplicated(subset=key_cols).sum()

    if duplicate_count > 0:
        value_cols = [col for col in df.columns if col not in key_cols]

        if len(value_cols) == 0:
            return df.drop_duplicates(subset=key_cols, keep="first").copy()

        agg_dict = {}

        for col in value_cols:
            if pd.api.types.is_numeric_dtype(df[col]):
                agg_dict[col] = "mean"
            else:
                agg_dict[col] = "first"

        df = df.groupby(key_cols, as_index=False, dropna=False).agg(agg_dict)

    return df


# Merge safely without allowing row duplication.
def safe_merge(master_df, right_df, on=None, left_on=None, right_on=None):
    before_rows = len(master_df)

    if right_on is not None:
        right_keys = right_on
    else:
        right_keys = on

    right_df = deduplicate_before_merge(right_df, right_keys)

    if on is not None:
        merged_df = master_df.merge(
            right_df,
            on=on,
            how="left",
            validate="m:1"
        )
    else:
        merged_df = master_df.merge(
            right_df,
            left_on=left_on,
            right_on=right_on,
            how="left",
            validate="m:1"
        )

    after_rows = len(merged_df)

    if after_rows != before_rows:
        raise ValueError(
            f"Merge changed row count from {before_rows} to {after_rows}. "
            "This means the merge is duplicating rows."
        )

    return merged_df


# Check that all required local files are available.
def test_required_files():
    required_files = {
        "Heat shapefile": find_file("EJScreen_HI.shp"),
        "Drought shapefile": find_file("Census_Tract.shp"),
        "County Health Rankings": find_file_contains("2025 County Health Rankings Data"),
        "LEAD energy data": find_file_contains("LEAD Tool Data Census Tracts"),
        "Nighttime light pollution": find_file_contains("ALAN_VIIRS_CONUS"),
        "CDC PLACES data": find_file_contains("PLACES__Census_Tract_Data"),
        "Census DP05 demographics": find_file_contains("ACSDP5Y2023.DP05"),
        "Census S1501 education": find_file_contains("ACSST5Y2024.S1501"),
        "Census S1701 poverty": find_file_contains("ACSST5Y2024.S1701"),
        "Census S1901 income": find_file_contains("ACSST5Y2024.S1901")
    }

    missing = [name for name, path in required_files.items() if path is None]

    if len(missing) > 0:
        raise FileNotFoundError(
            f"Missing files: {missing}. Make sure this Python file is saved "
            "inside the main data folder and the files/folders are inside it."
        )


test_required_files()


# Load county boundaries as the base dataset.
counties = gpd.read_file(
    "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_20m.zip"
).to_crs(epsg=4326)

counties["FIPS"] = counties["GEOID"].astype(str).str.zfill(5)

territory_statefps = ["60", "66", "69", "72", "78"]
counties = counties[~counties["STATEFP"].isin(territory_statefps)].copy()
counties = counties.drop_duplicates(subset=["FIPS"], keep="first").copy()

master = counties[
    ["FIPS", "STATEFP", "STATE_NAME", "NAME", "NAMELSAD", "ALAND", "geometry"]
].copy()

master = master.rename(columns={"NAME": "County"})


# Add extreme heat data from EJScreen.
heat_path = find_file("EJScreen_HI.shp")

if heat_path is None:
    raise FileNotFoundError("EJScreen_HI.shp was not found.")

heat = gpd.read_file(heat_path).to_crs(epsg=4326)
heat_col = "Average_Da"

heat_points = heat.to_crs(epsg=5070).copy()
heat_points["geometry"] = heat_points.geometry.centroid
heat_points = heat_points.to_crs(epsg=4326)

heat_joined = gpd.sjoin(
    heat_points[[heat_col, "geometry"]],
    master[["FIPS", "geometry"]],
    how="inner",
    predicate="within"
)

heat_county = heat_joined.groupby("FIPS")[heat_col].mean().reset_index()
heat_county = heat_county.rename(columns={heat_col: "extreme_heat"})

master = safe_merge(master, heat_county, on="FIPS")

del heat, heat_points, heat_joined, heat_county
gc.collect()


# Add drought severity data from the Census tract shapefile.
drought_path = find_file("Census_Tract.shp")

if drought_path is None:
    raise FileNotFoundError("Census_Tract.shp was not found.")

drought = gpd.read_file(drought_path).to_crs(epsg=4326)
drought_col = "DRGT_AFREQ"

drought_points = drought.to_crs(epsg=5070).copy()
drought_points["geometry"] = drought_points.geometry.centroid
drought_points = drought_points.to_crs(epsg=4326)

drought_joined = gpd.sjoin(
    drought_points[[drought_col, "geometry"]],
    master[["FIPS", "geometry"]],
    how="inner",
    predicate="within"
)

drought_county = drought_joined.groupby("FIPS")[drought_col].mean().reset_index()
drought_county = drought_county.rename(columns={drought_col: "drought_severity"})

master = safe_merge(master, drought_county, on="FIPS")

del drought, drought_points, drought_joined, drought_county
gc.collect()


# Add County Health Rankings variables.
chr_file = find_file_contains("2025 County Health Rankings Data")

if chr_file is None:
    raise FileNotFoundError("County Health Rankings Excel file was not found.")

chr_data = pd.read_excel(
    chr_file,
    sheet_name="Select Measure Data",
    header=1
)

chr_data = chr_data[chr_data["County"].notna()].copy()

chr_data["FIPS"] = (
    chr_data["FIPS"]
    .astype(int)
    .astype(str)
    .str.zfill(5)
)

if "Presence of Water Violation" not in chr_data.columns:
    raise ValueError("Presence of Water Violation was not found in the County Health Rankings file.")

chr_columns = {
    "Average Daily PM2.5": "average_daily_pm25",
    "Presence of Water Violation": "drinking_water_violation",
    "% Severe Housing Problems": "percent_severe_housing_problems",
    "% Households with Broadband Access": "percent_households_broadband",
    "% Unemployed": "percent_unemployed",
    "Income Ratio": "income_inequality_ratio"
}

keep_cols = ["FIPS"]

for old_col in chr_columns:
    if old_col in chr_data.columns:
        keep_cols.append(old_col)

chr_clean = chr_data[keep_cols].copy()
chr_clean = chr_clean.rename(columns=chr_columns)

chr_clean["drinking_water_violation"] = (
    chr_clean["drinking_water_violation"]
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace(".0", "", regex=False)
    .map({
        "yes": "Yes",
        "no": "No",
        "y": "Yes",
        "n": "No",
        "1": "Yes",
        "0": "No",
        "true": "Yes",
        "false": "No",
        "violation": "Yes",
        "no violation": "No",
        "nan": ""
    })
)

for col in [
    "average_daily_pm25",
    "percent_severe_housing_problems",
    "percent_households_broadband",
    "percent_unemployed",
    "income_inequality_ratio"
]:
    if col in chr_clean.columns:
        chr_clean[col] = clean_numeric(chr_clean[col])

master = safe_merge(master, chr_clean, on="FIPS")

del chr_data, chr_clean
gc.collect()


# Add LEAD energy cost data using household-weighted county averages.
lead_file = find_file_contains("LEAD Tool Data Census Tracts")

if lead_file is None:
    raise FileNotFoundError("LEAD Tool Data Census Tracts CSV file was not found.")

lead = pd.read_csv(
    lead_file,
    skiprows=8,
    low_memory=False
)

lead["FIPS"] = (
    lead["Geography ID"]
    .astype(str)
    .str.zfill(11)
    .str[:5]
)

lead["Total Households"] = clean_numeric(lead["Total Households"])

lead["Avg. Annual Energy Cost ($) (Electricity)"] = clean_numeric(
    lead["Avg. Annual Energy Cost ($) (Electricity)"]
)

lead["Avg. Annual Energy Cost ($) (Gas)"] = clean_numeric(
    lead["Avg. Annual Energy Cost ($) (Gas)"]
)

lead = lead[lead["Total Households"].notna()].copy()

lead["electricity_weighted"] = (
    lead["Avg. Annual Energy Cost ($) (Electricity)"]
    * lead["Total Households"]
)

lead["gas_weighted"] = (
    lead["Avg. Annual Energy Cost ($) (Gas)"]
    * lead["Total Households"]
)

lead_county = lead.groupby("FIPS").agg(
    electricity_weighted=("electricity_weighted", "sum"),
    gas_weighted=("gas_weighted", "sum"),
    total_households_lead=("Total Households", "sum")
).reset_index()

lead_county["electricity_price"] = (
    lead_county["electricity_weighted"]
    / lead_county["total_households_lead"]
)

lead_county["gas_price"] = (
    lead_county["gas_weighted"]
    / lead_county["total_households_lead"]
)

lead_county = lead_county[
    [
        "FIPS",
        "electricity_price",
        "gas_price"
    ]
].copy()

master = safe_merge(master, lead_county, on="FIPS")

del lead, lead_county
gc.collect()


# Add nighttime light pollution data from ALAN VIIRS.
alan_file = find_file_contains("ALAN_VIIRS_CONUS")

if alan_file is None:
    raise FileNotFoundError("ALAN VIIRS nighttime light pollution Excel file was not found.")

alan = pd.read_excel(
    alan_file,
    sheet_name="2020_boundary_ALAN_2012_to_2020"
)

alan["FIPS"] = (
    alan["county_ID"]
    .astype(str)
    .str.replace(".0", "", regex=False)
    .str.zfill(5)
)

alan["year"] = clean_numeric(alan["year"])
alan["nraster"] = clean_numeric(alan["nraster"])

if "rad_mean_imputed" in alan.columns:
    alan["night_light_value"] = clean_numeric(alan["rad_mean_imputed"])
else:
    alan["night_light_value"] = clean_numeric(alan["rad_mean"])

latest_year = alan["year"].max()

alan = alan[
    (alan["year"] == latest_year) &
    (alan["nraster"].notna()) &
    (alan["night_light_value"].notna())
].copy()

alan["night_light_weighted"] = (
    alan["night_light_value"] * alan["nraster"]
)

alan_county = alan.groupby("FIPS").agg(
    night_light_weighted=("night_light_weighted", "sum"),
    total_raster_cells=("nraster", "sum")
).reset_index()

alan_county["nighttime_light_pollution"] = (
    alan_county["night_light_weighted"]
    / alan_county["total_raster_cells"]
)

alan_county = alan_county[
    [
        "FIPS",
        "nighttime_light_pollution"
    ]
].copy()

master = safe_merge(master, alan_county, on="FIPS")

del alan, alan_county
gc.collect()


# Add PLACES health data using adult population-weighted averages.
places_file = find_file_contains("PLACES__Census_Tract_Data")

if places_file is None:
    raise FileNotFoundError("PLACES Census Tract CSV file was not found.")

places = pd.read_csv(
    places_file,
    low_memory=False
)

places["FIPS"] = (
    places["CountyFIPS"]
    .astype(str)
    .str.replace(".0", "", regex=False)
    .str.zfill(5)
)

places["TotalPop18plus"] = clean_numeric(places["TotalPop18plus"])

places_columns = {
    "SLEEP_CrudePrev": "percent_sleep_less_than_7_hours",
    "CASTHMA_CrudePrev": "percent_current_asthma",
    "MHLTH_CrudePrev": "percent_poor_mental_health",
    "DEPRESSION_CrudePrev": "percent_depression",
    "STROKE_CrudePrev": "percent_stroke",
    "COPD_CrudePrev": "percent_copd",
    "CHD_CrudePrev": "percent_coronary_heart_disease"
}

for col in places_columns:
    places[col] = clean_numeric(places[col])
    places[col + "_weighted"] = places[col] * places["TotalPop18plus"]

places = places[places["TotalPop18plus"].notna()].copy()

agg_dict = {
    "total_pop_18plus_places": ("TotalPop18plus", "sum")
}

for old_col in places_columns:
    agg_dict[old_col + "_weighted"] = (old_col + "_weighted", "sum")

places_county = places.groupby("FIPS").agg(**agg_dict).reset_index()

for old_col, new_col in places_columns.items():
    places_county[new_col] = (
        places_county[old_col + "_weighted"]
        / places_county["total_pop_18plus_places"]
    )

places_county = places_county[
    ["FIPS"] + list(places_columns.values())
].copy()

master = safe_merge(master, places_county, on="FIPS")

del places, places_county
gc.collect()


# Add Census DP05 demographic variables.
dp05_file = find_file_contains("ACSDP5Y2023.DP05")

if dp05_file is None:
    raise FileNotFoundError("ACSDP5Y2023.DP05 Excel file was not found.")

acs_data = pd.read_excel(
    dp05_file,
    sheet_name="Data",
    header=None
)

total_pop_row = acs_data[acs_data[0] == "Total population"].index[0]
under18_row = acs_data[acs_data[0] == "Under 18 years"].index[0]
older65_row = acs_data[acs_data[0] == "65 years and over"].index[0]

white_alone_rows = acs_data[acs_data[0] == "White alone"].index
non_hispanic_white_row = white_alone_rows[-1]

county_columns = list(range(5, acs_data.shape[1], 4))

demo_data = []

for col in county_columns:
    county_state = acs_data.iloc[0, col]

    if pd.isna(county_state):
        continue

    county_state = str(county_state)

    if "," not in county_state:
        continue

    demo_data.append({
        "county_state": county_state,
        "total_population": acs_data.iloc[total_pop_row, col],
        "percent_children_under_18": acs_data.iloc[under18_row, col + 2],
        "percent_older_adults_65_plus": acs_data.iloc[older65_row, col + 2],
        "percent_non_hispanic_white": acs_data.iloc[non_hispanic_white_row, col + 2]
    })

demo = pd.DataFrame(demo_data)

demo[["county", "state"]] = demo["county_state"].str.rsplit(
    ", ",
    n=1,
    expand=True
)

demo["total_population"] = clean_numeric(demo["total_population"])
demo["percent_children_under_18"] = clean_numeric(demo["percent_children_under_18"])
demo["percent_older_adults_65_plus"] = clean_numeric(demo["percent_older_adults_65_plus"])
demo["percent_non_hispanic_white"] = clean_numeric(demo["percent_non_hispanic_white"])

demo["percent_people_of_color"] = (
    100 - demo["percent_non_hispanic_white"]
)

demo_clean = demo[
    [
        "county",
        "state",
        "total_population",
        "percent_children_under_18",
        "percent_older_adults_65_plus",
        "percent_people_of_color"
    ]
].copy()

master = safe_merge(
    master,
    demo_clean,
    left_on=["NAMELSAD", "STATE_NAME"],
    right_on=["county", "state"]
)

del acs_data, demo, demo_clean
gc.collect()


# Add Census S1501 education data.
s1501_file = find_file_contains("ACSST5Y2024.S1501")

if s1501_file is None:
    raise FileNotFoundError("ACSST5Y2024.S1501 education CSV file was not found.")

education = pd.read_csv(
    s1501_file,
    dtype=str,
    low_memory=False
)

education = education[education["GEO_ID"] != "Geography"].copy()

education["FIPS"] = extract_county_fips_from_geo_id(education["GEO_ID"])

education["percent_bachelors_degree_or_higher"] = clean_numeric(
    education["S1501_C02_015E"]
)

education_clean = education[
    [
        "FIPS",
        "percent_bachelors_degree_or_higher"
    ]
].copy()

education_clean = education_clean.dropna(subset=["FIPS"]).copy()

education_clean = education_clean.groupby("FIPS", as_index=False).agg(
    percent_bachelors_degree_or_higher=("percent_bachelors_degree_or_higher", "mean")
)

master = safe_merge(master, education_clean, on="FIPS")

del education, education_clean
gc.collect()


# Add Census S1701 poverty data.
s1701_file = find_file_contains("ACSST5Y2024.S1701")

if s1701_file is None:
    raise FileNotFoundError("ACSST5Y2024.S1701 poverty CSV file was not found.")

poverty = pd.read_csv(
    s1701_file,
    dtype=str,
    low_memory=False
)

poverty = poverty[poverty["GEO_ID"] != "Geography"].copy()

poverty["FIPS"] = extract_county_fips_from_geo_id(poverty["GEO_ID"])

poverty["poverty_rate"] = clean_numeric(
    poverty["S1701_C03_001E"]
)

poverty_clean = poverty[
    [
        "FIPS",
        "poverty_rate"
    ]
].copy()

poverty_clean = poverty_clean.dropna(subset=["FIPS"]).copy()

poverty_clean = poverty_clean.groupby("FIPS", as_index=False).agg(
    poverty_rate=("poverty_rate", "mean")
)

master = safe_merge(master, poverty_clean, on="FIPS")

del poverty, poverty_clean
gc.collect()


# Add Census S1901 median household income data.
s1901_file = find_file_contains("ACSST5Y2024.S1901")

if s1901_file is None:
    raise FileNotFoundError("ACSST5Y2024.S1901 income CSV file was not found.")

income = pd.read_csv(
    s1901_file,
    dtype=str,
    low_memory=False
)

income = income[income["GEO_ID"] != "Geography"].copy()

income["FIPS"] = extract_county_fips_from_geo_id(income["GEO_ID"])

income["median_household_income"] = clean_numeric(
    income["S1901_C01_012E"]
)

income_clean = income[
    [
        "FIPS",
        "median_household_income"
    ]
].copy()

income_clean = income_clean.dropna(subset=["FIPS"]).copy()

income_clean = income_clean.groupby("FIPS", as_index=False).agg(
    median_household_income=("median_household_income", "mean")
)

master = safe_merge(master, income_clean, on="FIPS")

del income, income_clean
gc.collect()


# Calculate land area and population density.
master["area_sq_miles"] = master["ALAND"] / 2589988.110336

master["population_density"] = (
    master["total_population"] / master["area_sq_miles"]
)


# Remove geometry and helper columns before saving.
final_csv = master.drop(
    columns=["geometry", "ALAND", "NAMELSAD", "county", "state"],
    errors="ignore"
).copy()

final_csv = final_csv.drop_duplicates(subset=["FIPS"], keep="first").copy()

needed_columns = [
    "drought_severity",
    "extreme_heat",
    "electricity_price",
    "gas_price",
    "nighttime_light_pollution",
    "drinking_water_violation",
    "percent_households_broadband",
    "percent_unemployed",
    "income_inequality_ratio",
    "percent_severe_housing_problems",
    "average_daily_pm25",
    "total_population",
    "population_density",
    "percent_children_under_18",
    "percent_older_adults_65_plus",
    "percent_people_of_color",
    "percent_bachelors_degree_or_higher",
    "poverty_rate",
    "median_household_income",
    "percent_sleep_less_than_7_hours",
    "percent_current_asthma",
    "percent_poor_mental_health",
    "percent_depression",
    "percent_stroke",
    "percent_copd",
    "percent_coronary_heart_disease"
]

missing_columns = [col for col in needed_columns if col not in final_csv.columns]

if len(missing_columns) > 0:
    raise ValueError(f"These columns are still missing: {missing_columns}")

final_csv["drinking_water_violation"] = (
    final_csv["drinking_water_violation"]
    .replace({
        1: "Yes",
        0: "No",
        1.0: "Yes",
        0.0: "No",
        "1": "Yes",
        "0": "No",
        "1.0": "Yes",
        "0.0": "No",
        "yes": "Yes",
        "no": "No",
        "YES": "Yes",
        "NO": "No"
    })
)

output_file = BASE_DIR / "yahir_geopandas_all-datasets.csv"

final_csv.to_csv(output_file, index=False)