# Data Center Environmental & Social Impact

*A Discovery Partners Institute research project*

**Authors:** Yahir Langumas (CS @ UIUC) · Akhilasri Arla (Econometrics & Psychology @ UIUC)
**Supervised by:** Dr. Anuj Tiwari, Senior Research Associate, Discovery Partners Institute, Chicago, IL

## Overview

The rapid growth of AI has driven a boom in U.S. data center construction, and these facilities place significant new demands on local electricity, water, and land. This project maps the locations of U.S. data center facilities against county-level environmental, socioeconomic, and public health data to ask: **are U.S. data centers disproportionately located in communities that already face elevated environmental hazards or economic/health vulnerability?**

## Data

The dataset covers **4,413 U.S. data center facilities**, geocoded and joined to their county via FIPS code. Each facility is layered against county-level indicators pulled from federal and public health sources:

| Category | Indicators | Source |
|---|---|---|
| Environmental | PM2.5 air quality, drinking water violations, drought severity, extreme heat, nighttime light pollution | County Health Rankings, FEMA National Risk Index, EPA EJScreen, NOAA VIIRS |
| Economic | Median household income, poverty rate, income inequality ratio, broadband access, unemployment, electricity/gas price | ACS 5-Year Estimates, County Health Rankings, DOE LEAD Tool |
| Demographic | Total population, population density, % children under 18, % older adults 65+, % people of color | 2020 Decennial Census, ACS |
| Public Health | Asthma, COPD, coronary heart disease, stroke, depression, poor mental health, insufficient sleep, severe housing problems | CDC PLACES, County Health Rankings |
| Noise | Existing transportation noise exposure | DOT National Transportation Noise Map |

Full citations are in the project report / presentation References slide.

## Repository Structure

Most indicators have two notebooks:

- **A county map notebook** (e.g. `Air_Pollution_PM2_5.ipynb`) — plots the indicator as a choropleth map with data center locations overlaid, binned into 5 severity tiers (Very Low → Very High) using the 2nd–98th percentile range.
- **A bar graph notebook** (e.g. `Air_Population_Bar_Graph.ipynb`) — shows the percentage of data center facilities falling into each severity tier.

Master merge scripts:

- `all_data_csv.ipynb` / `all_data_sets_geopandas.py` — merge every indicator into a single county-level dataset (`geopandas_all-datasets.csv`, 3,144 counties × 31 columns).

## Methodology

Each indicator was sourced from its original federal or public health agency and joined to U.S. Census county boundaries using FIPS codes (or a spatial join where no FIPS code was available). All processing was done in Python using GeoPandas, pandas, NumPy, Matplotlib, and openpyxl.

## Key Findings

- Data centers are **not** concentrated in economically vulnerable counties. Broadband access, income inequality, median household income, education level, and poverty rate all show the opposite: data centers cluster in wealthier, more educated, better-connected counties.
- Environmental hazard overlap is real but uneven: strongest for nighttime light pollution, moderate for PM2.5 and drinking water violations, weak for drought and extreme heat.
- Health outcome overlap is inconsistent: asthma and poor mental health appear sharply elevated near data centers, but COPD and coronary heart disease — also linked to air quality — don't show the same pattern, suggesting the first two reflect a data-scaling artifact rather than a genuine effect.

## Requirements

```
pandas
geopandas
numpy
matplotlib
openpyxl
```

## Acknowledgments

Thanks to Dr. Anuj Tiwari and the Discovery Partners Institute for supervision and support on this project.

## References

[1] U.S. Census Bureau. "American Community Survey 5-Year Estimates, 2019–2024." Accessed August 2026. https://data.census.gov/all.

[2] U.S. Census Bureau. "2020 Census, Table P1: Total Population." Accessed August 2026. https://data.census.gov/table/DECENNIALPL2020.P1.

[3] University of Wisconsin Population Health Institute. "2025 County Health Rankings National Data." County Health Rankings & Roadmaps. Accessed August 2026. https://www.countyhealthrankings.org/.

[4] Centers for Disease Control and Prevention. "PLACES: Local Data for Better Health." Accessed August 2026. https://www.cdc.gov/places/tools/interactive-map-tool.html.

[5] Federal Emergency Management Agency. "National Risk Index: Annualized Frequency of Drought." Accessed August 2026. https://resilience-fema.hub.arcgis.com/maps/FEMA::national-risk-index-annualized-frequency-drought/about.

[6] Fitzgerald, William, and Gretchen Gehrke. "EPA Environmental Justice Screening Tool (EJScreen) Data, 2015–2024." Version 1. Zenodo, January 29, 2025. https://doi.org/10.5281/zenodo.14767363.

[7] U.S. Environmental Protection Agency. "EJScreen Map Descriptions." Archived January 21, 2025. https://web.archive.org/web/20250121194843/https://www.epa.gov/ejscreen/ejscreen-map-descriptions#clim.

[8] U.S. Department of Energy, Office of State and Community Energy Programs. "Low-Income Energy Affordability Data (LEAD) Tool." Accessed August 2026. https://www.energy.gov/scep/slsc/lead-tool.

[9] National Oceanic and Atmospheric Administration. "Annual Summary of Artificial Light at Night from VIIRS/S-NPP at CONUS County and Census Tract Level." Data.gov. Accessed August 2026. https://catalog.data.gov/dataset/annual-summary-of-artificial-light-at-night-from-viirs-s-npp-at-conus-county-and-census-tr.

[10] U.S. Department of Transportation, Bureau of Transportation Statistics. "National Transportation Noise Map." Accessed August 2026. https://maps.dot.gov/BTS/NationalTransportationNoiseMap/.
