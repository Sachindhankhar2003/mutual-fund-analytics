import shutil
import os
from pathlib import Path

# Paths
WORKSPACE_DIR = Path("c:/Users/HP/OneDrive/desktop/Mutual Fund Analytics")
SUBMISSION_DIR = Path("c:/Users/HP/OneDrive/desktop/Sachin_Submission")

def create_folders():
    folders = [
        "Source Code",
        "Source Code/sql",
        "Datasets",
        "Datasets/raw",
        "Datasets/processed",
        "Documentation",
        "Documentation/reports",
        "PPT or Slides",
        "Demo Video"
    ]
    
    for f in folders:
        path = SUBMISSION_DIR / f
        path.mkdir(parents=True, exist_ok=True)
    print("Created folder structure under Sachin_Submission/")

def copy_files():
    # 1. Copy Source Code
    src_files = [
        "clean_data.py",
        "csv_verify.py",
        "data_ingestion.py",
        "find_scheme_codes.py",
        "live_nav_fetch.py",
        "load_to_sqlite.py",
        "requirements.txt"
    ]
    for f in src_files:
        src = WORKSPACE_DIR / f
        if src.exists():
            shutil.copy2(src, SUBMISSION_DIR / "Source Code" / f)
            
    # Copy SQL
    sql_files = ["queries.sql", "schema.sql"]
    for f in sql_files:
        src = WORKSPACE_DIR / "sql" / f
        if src.exists():
            shutil.copy2(src, SUBMISSION_DIR / "Source Code" / "sql" / f)
            
    # 2. Copy Datasets
    # Raw CSVs
    raw_files = list((WORKSPACE_DIR / "data" / "raw").glob("*.csv"))
    for f in raw_files:
        shutil.copy2(f, SUBMISSION_DIR / "Datasets" / "raw" / f.name)
        
    # Processed CSVs
    processed_files = list((WORKSPACE_DIR / "data" / "processed").glob("*.csv"))
    for f in processed_files:
        shutil.copy2(f, SUBMISSION_DIR / "Datasets" / "processed" / f.name)
        
    # SQLite Database
    db_file = WORKSPACE_DIR / "bluestock_mf.db"
    if db_file.exists():
        shutil.copy2(db_file, SUBMISSION_DIR / "Datasets" / "bluestock_mf.db")
        
    # 3. Copy Documentation
    doc_files = ["README.md", "data_dictionary.md"]
    for f in doc_files:
        src = WORKSPACE_DIR / f
        if src.exists():
            shutil.copy2(src, SUBMISSION_DIR / "Documentation" / f)
            
    # Reports
    report_files = list((WORKSPACE_DIR / "reports").glob("*.txt"))
    for f in report_files:
        shutil.copy2(f, SUBMISSION_DIR / "Documentation" / "reports" / f.name)
        
    # 4. Placeholders for PPT and Video
    with open(SUBMISSION_DIR / "PPT or Slides" / "README.txt", "w") as f:
        f.write("Please upload your presentation slides (PPTX/PDF) into this folder before sharing the link.")
        
    with open(SUBMISSION_DIR / "Demo Video" / "README.txt", "w") as f:
        f.write("Please upload your demo video file (MP4/MKV) into this folder before sharing the link.")
        
    print("Successfully copied all submission files to their respective folders.")

if __name__ == "__main__":
    create_folders()
    copy_files()
