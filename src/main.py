# -------------------------------------------------------------------
# This file reads patients_sample.csv, stores relevant fields
# into SQLite, lets you search by patient name or ID, and builds
# a UNC string
# Author: Trey Springer (8/25/2025 last update)
# -------------------------------------------------------------------

import csv, sqlite3, os, time, logging

from concurrent.futures import ThreadPoolExecutor, as_completed


# Path constants
DB = "patients.db" # SQLite database file
CSV_FILE = os.path.join("data","patients_sample.csv")
UNC_PREFIX = r"..\PatientData" # this will be changed to the folder where the patient data lives (Example: r"\\SERVER01\EpicMigration)
# and then the code makes paths like path = fr"{UNC_PREFIX}\{pid}"
ROOT_DIRS = ["PatientData"] # Folder with patient xml/pdf files
PATIENT_DATA_ROOT = r"..\Patient_Lookup_Tool\PatientData"

print("USING DB:", os.path.abspath("patients.db"))

# Create logs directory if it doesn’t exist
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/patient_lookup.log", mode="a", encoding="utf-8"),
        logging.StreamHandler()  # also log to console
    ]
)

def init_db(reset_db=False):
    """Create or reset the patients table in SQLite."""
    if reset_db and os.path.exists(DB):
        os.remove(DB)
        print("Database reset. New one will be created")

    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute("DROP TABLE IF EXISTS patients")

    # Key fields + path for UNC strings
    cur.execute("""
        CREATE TABLE patients(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            name TEXT,
            ssn TEXT,
            sex TEXT,
            birth_date TEXT,
            address TEXT,
            path TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT,
            patient_id TEXT,
            details TEXT
        )
    """)
    con.commit()
    con.close()
    print("Database initialized")

def find_patient_file(patient_id):
    """Recursively find the first file in PatientData that starts with the patient id."""
    for root, dirs, files, in os.walk(PATIENT_DATA_ROOT):
        for f in files:
            if f.startswith(patient_id):
                return os.path.join(root,f)
    return None


def build_file_index(root_dirs):
    """
    Walks root directories and maps patient ID (from filename prefix) -> list of file paths.
    """
    index = {}
    for root_dir in root_dirs:
        for dirpath, _, files in os.walk(root_dir):
            for f in files:
                if f.lower().endswith((".pdf", ".xml")):
                    file_patient_id = f.split("_", 1)[0].strip().lstrip("0")
                    full_path = os.path.abspath(os.path.join(dirpath, f))
                    index.setdefault(file_patient_id, []).append(full_path)
    return index



def find_pdfs_for_patient(patient_id, file_index):
    """Return UNC paths for all PDFs matching this patient ID."""
    return [f"\\\\server\\share\\{path}" for path in file_index.get(patient_id, [])]

def ingest_csv(csv_path, db_path, file_index, batch_size=500):
    """Insert CSV rows into SQLite with placeholder path (filled later)."""
    import csv, sqlite3

    logging.info("Starting ingestion from %s", csv_path)

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    rows = []

    with open(csv_path, newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for r in reader:
            csv_patient_id = r["ID"].strip().lstrip("0")
            name = r["Patient Name"].strip()
            ssn = r["SSN"].strip()
            sex = r["Sex"].strip()
            birth_date = r["Birth Date"].strip()
            address = r["Address"].strip()

            # Placeholder path
            rows.append((csv_patient_id, name, ssn, sex, birth_date, address, ""))

            # Insert in batches
            if len(rows) >= batch_size:
                cur.executemany("""
                    INSERT INTO patients(patient_id, name, ssn, sex, birth_date, address, path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, rows)
                rows = []

        # Insert remaining
        if rows:
            cur.executemany("""
                INSERT INTO patients(patient_id, name, ssn, sex, birth_date, address, path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, rows)

        try:
            # your ingestion logic
            logging.info("Inserted %d patient records into database", len(rows))
        except Exception as e:
            logging.error("Error during ingestion: %s", e, exc_info=True)

    con.commit()
    con.close()
    print("CSV ingestion complete")
    

def find_patient_pdfs(pid, name, ssn, sex, bdate, addr):
    """Find all PDFs for a patient and return row tuple for DB insertion."""
    paths = []
    for root, _, files in os.walk(PATIENT_DATA_ROOT):
        for f in files:
            if f.startswith(pid) and f.lower().endswith(".pdf"):
                paths.append(os.path.join(root, f))

    all_paths = ";".join(paths) if paths else ""
    return (pid, name, ssn, sex, bdate, addr, all_paths)


def benchmark(func, *args, **kwargs):
    """Utility to time any function call."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    print(f"{func.__name__} took {end - start:.4f} seconds")
    return result


def search_patient(query):
    """Search patients by MRN (exact) or by name (substring)."""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(""" 
        SELECT patient_id, name
        FROM patients
        WHERE patient_id LIKE ? OR name LIKE ?
    """,(f"%{query}%", f"%{query}%"))
    rows = cur.fetchall()
    conn.close()
    return rows


def open_file(patient_id):
    """Open all PDF file paths for the given patient MRN."""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT path FROM patients WHERE patient_id = ?", (patient_id,))
    row = cur.fetchone()
    conn.close()

    if row is None or row[0] is None:
        print(f"No file paths found for patient MRN {patient_id}")
        return

    paths = row[0].split(";")
    pdfs = [p.strip() for p in paths if p.strip().lower().endswith(".pdf")]

    if not pdfs:
        print(f"No PDFs found for patient MRN {patient_id}")
        return

    for pdf in pdfs:
        if os.path.exists(pdf):
            os.startfile(pdf)
            print(f"Opened: {pdf}")
        else:
            print(f"Missing file on disk: {pdf}")


def update_paths(db_path, file_index):
    """Populate 'path' column in DB using the file_index."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT patient_id FROM patients")
    patient_ids = [row[0] for row in cur.fetchall()]

    for csv_patient_id in patient_ids:
        paths = file_index.get(csv_patient_id, [])
        if paths:
            all_paths = ";".join(paths)
            cur.execute("UPDATE patients SET path = ? WHERE patient_id = ?", (all_paths, csv_patient_id))

    conn.commit()
    conn.close()
    print("Paths updated for all patients")


def main():
    # Drop/recreate table
    init_db()

    # Build index of files
    print("Indexing files...")
    t0 = time.perf_counter()
    file_index = build_file_index(ROOT_DIRS)
    t1 = time.perf_counter()
    print(f"Indexed {len(file_index)} patient IDs in {t1 - t0:.2f} seconds")

    # Ingest CSV
    print("Ingesting CSV...")
    t2 = time.perf_counter()
    ingest_csv(CSV_FILE, DB, file_index, batch_size=500)
    
    t3 = time.perf_counter()
    print(f"CSV ingestion completed in {t3 - t2:.2f} seconds")

    # Count inserted rows
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM patients")
        total_rows = cur.fetchone()[0]
    print(f"CSV ingestion completed in {t3 - t2:.2f} seconds ({total_rows} rows inserted)")

    # Update paths
    print("Updating paths...")
    t4 = time.perf_counter()
    update_paths(DB, file_index)
    t5 = time.perf_counter()
    print(f"Path update completed in {t5 - t4:.2f} seconds")

    # Count how many rows have a path
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM patients WHERE path IS NOT NULL")
        path_rows = cur.fetchone()[0]
    print(f"Path update completed in {t5 - t4:.2f} seconds ({path_rows} rows with file paths)")

    total_time = t5 - t0
    print(f"--- Total pipeline completed in {total_time:.2f} seconds ---")


if __name__== "__main__":
    """Simple command-line interface for searching and opening patient files."""
    main()

    while True:
        print("Options: ")
        print("1. Search for patient")
        print("2. Open patient file")
        print("3. Exit")
        choice = input("Select an option: ").strip()

        if choice == "1":
            query = input("Enter the patients name or ID: ").strip()
            results = search_patient(query)
            for pid, name in results:
                print(f"{pid}: {name}")
        elif choice == "2":
            pid = input("Enter patient ID to open file: ").strip()
            open_file(pid)
        elif choice == "3":
            break
        else:
            print("Invalid option. Try again.")


