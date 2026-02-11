Author: Cristian Alemán Suárez

# TravelTech Ops Monitor

## Overview

This project demonstrates how public travel-related content signals can be automatically collected, processed and transformed into actionable insights for content and product teams in a TravelTech context.

It is designed as an operations-focused system that reduces manual analysis and supports recurring decision-making through automated reporting.

---

## Objective

The goal of this project is to monitor travel-related trends from public content sources, normalize heterogeneous data, compute relevant operational metrics and generate a recurring report with clear insights and recommendations for stakeholders.

Typical decisions supported by this system include:
- Identifying emerging destinations or topics
- Detecting saturated vs underexplored content areas
- Understanding publishing frequency and focus across sources

---

## How It Works

The pipeline follows a simple and reproducible operations-oriented flow:

1. **Data collection**  
   Public content sources are queried to extract raw travel-related data using `fetch.py`.  
   Raw data is stored in `data/raw/` for traceability and reproducibility.

2. **Normalization and processing**  
   `parse.py` transforms heterogeneous inputs into a unified and structured format.  
   Normalized datasets are stored in `data/processed/`.

3. **Metrics computation**  
   `metrics.py` calculates operational metrics and comparative signals relevant for content and trend analysis.

4. **Automated reporting**  
   `report.py` generates an automated report including summaries, tables and recommendations.  
   Reports are stored in the `reports/` directory.

---

## How to Run

It is recommended to use a virtual environment.

```bash
python -m venv .venv
```

Activate it:
```bash
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the pipeline:
```bash
python run_weekly.py
```

This command executes the full pipeline from data collection to report generation.

## Limitations and Future Improvements

- The pipeline is currently executed manually and simulates a weekly reporting cadence.
- Scheduling (e.g. cron or task scheduler) is not yet implemented.
- Engagement metrics are inferred from content signals and do not include private analytics data.
- The followed apporach overwrites previous versions of raw data. Some version control can be applied.

Despite these limitations, the system already automates the majority of the workflow and serves as a solid proof of concept for an operations-oriented monitoring tool.