# Mutual Fund Analytics

> A production-ready Python capstone project for ingesting, validating,
> and analysing Indian mutual fund NAV data using public APIs.

---

## 📌 Project Objective

This project demonstrates end-to-end data engineering skills applied to the
Indian mutual fund industry. You will:

- Fetch live NAV (Net Asset Value) data from the **mfapi.in** public API
- Profile, validate, and clean raw CSV datasets
- Explore fund metadata (fund houses, categories, risk grades)
- Validate AMFI scheme codes for data integrity
- Build the foundation for advanced analytics and dashboards

---

## 🗂️ Folder Structure

```
MutualFundAnalytics/
├── data/
│   ├── raw/                  # Raw CSV files (NAV history, fund master)
│   └── processed/            # Cleaned, transformed datasets
├── notebooks/                # Jupyter notebooks for EDA and analysis
├── sql/                      # SQL scripts for database operations
├── dashboard/                # Dashboard assets (Plotly / Dash / Streamlit)
├── reports/                  # Auto-generated quality and validation reports
├── data_ingestion.py         # Profiles all CSVs in data/raw/
├── live_nav_fetch.py         # Fetches live NAV data from mfapi.in API
├── requirements.txt          # Python dependency list
└── README.md                 # This file
```

---

## ⚙️ Installation Steps

### 1. Clone the repository

```bash
git clone https://github.com/<YOUR_USERNAME>/MutualFundAnalytics.git
cd MutualFundAnalytics
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Execution Steps

### Step 1 – Fetch live NAV data

Downloads NAV history for 6 major large-cap mutual fund schemes and saves
them as CSV files in `data/raw/`.

```bash
python live_nav_fetch.py
```

**Schemes fetched:**

| Scheme Code | Fund Name                     | Output File               |
|-------------|-------------------------------|---------------------------|
| 125497      | HDFC Top 100 Fund             | hdfc_top100_nav.csv       |
| 119551      | SBI Bluechip Fund             | sbi_bluechip_nav.csv      |
| 120503      | ICICI Pru Bluechip Fund       | icici_bluechip_nav.csv    |
| 118632      | Nippon India Large Cap Fund   | nippon_largecap_nav.csv   |
| 119092      | Axis Bluechip Fund            | axis_bluechip_nav.csv     |
| 120841      | Kotak Bluechip Fund           | kotak_bluechip_nav.csv    |

### Step 2 – Run the data ingestion pipeline

Profiles every CSV in `data/raw/`, printing shape, dtypes, sample rows,
missing values, duplicates, and generating a quality score.

```bash
python data_ingestion.py
```

### Step 3 – Launch Jupyter for analysis (optional)

```bash
jupyter notebook notebooks/
```

---

## 🔌 API Reference

| Property  | Value                              |
|-----------|------------------------------------|
| Base URL  | `https://api.mfapi.in/mf`          |
| Method    | GET                                |
| Format    | JSON                               |
| Auth      | None (public API)                  |
| Endpoint  | `/mf/{scheme_code}`                |
| Example   | `https://api.mfapi.in/mf/125497`   |

---

## 📊 Data Quality Reports

Validation reports are auto-saved to the `reports/` folder:

- `reports/amfi_validation_report.txt` – AMFI scheme code reconciliation

---

## 🛠️ Git Workflow

### Initialise and push to GitHub

```bash
# 1. Initialise local repository
git init

# 2. Stage all files
git add .

# 3. Create the first commit
git commit -m "feat: Day-1 project setup – data ingestion and NAV fetch pipelines"

# 4. Rename branch to 'main'
git branch -M main

# 5. Link to remote (replace with your GitHub repo URL)
git remote add origin https://github.com/<YOUR_USERNAME>/MutualFundAnalytics.git

# 6. Push to GitHub
git push -u origin main
```

### Recommended branch strategy

| Branch      | Purpose                              |
|-------------|--------------------------------------|
| `main`      | Stable, production-ready code        |
| `dev`       | Active development                   |
| `feature/*` | Individual features / experiments    |

---

## 📋 Requirements

See [requirements.txt](requirements.txt) for the full dependency list.

Key packages:

| Package     | Purpose                              |
|-------------|--------------------------------------|
| pandas      | Data manipulation and profiling      |
| numpy       | Numerical computing                  |
| matplotlib  | Static visualisations                |
| seaborn     | Statistical plots                    |
| plotly      | Interactive charts                   |
| sqlalchemy  | Database ORM and connections         |
| requests    | HTTP API calls                       |
| scipy       | Statistical analysis                 |
| jupyter     | Notebook-based exploration           |

---

## 📄 License

This project is for educational purposes as part of a Data Engineering
capstone programme. No commercial use intended.

---

*Built with ❤️ by the Mutual Fund Analytics Team*

*(Last updated/reviewed: June 26, 2026)*

