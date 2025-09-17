# Patient Lookup Tool

This project provides both a command-line interface (CLI) and a graphical user interface (GUI) for searching and opening patient records.
It is designed to:

Ingest patient demographic data from a CSV file.

Index corresponding patient files (PDF/XML) stored in a directory structure.

Search by MRN (patient ID) or name.

Open patient PDF files directly.

Benchmark ingestion/query times.

Provide a Tkinter GUI with double-click file opening.

---

### Project Structure
Patient_Lookup_Tool/ \
├── main.py         # Core logic: ingest CSV, search, open files (CLI) \
├── gui.py          # Tkinter-based GUI \
├── patients.db     # SQLite database (auto-generated after ingest) \
├── PatientData/    # Folder containing patient files (PDF/XML) \
├── patient_data.csv # Input CSV with demographic info \
└── README.md       # Documentation 

**Requirements** \
Python 3.8+

Standard library only (uses sqlite3, os, csv, time, tkinter, subprocess)

No external packages are required.

**Usage** 
1. Prepare Data

Place all patient files (PDFs, XMLs, etc.) inside the PatientData/ folder.

Ensure your CSV (patient_data.csv) has columns like:

ID (patient MRN)
Name
SSN
Sex
Birth Date
Address

2. Run the CLI

From the project root: \
`python src/main.py` 

**Features:**
Search patients by MRN or name. \
Open patient files directly from search results. \
Benchmark ingestion times (printed to console). 

**Example interaction:**
Search by ID or name: 2590972 \
Found patient: 2590972 - Abraham Xicotencatl-Munoz \
Enter patient ID to open file: 2590972 \
Opening: PatientData/XI/AB/197905/2590972_XICOTENCATL-MUNOZ_ABRAHAM_59114785_Appointment_2018_08_09.pdf

3. Run the GUI

`python src/gui.py` \
Features:

Search box to look up patients by MRN or name. \
Results displayed in a table. \
Double-click a patient → opens a pop-up listing all their associated PDFs. \
Select a file → it opens in the system’s default PDF viewer. 

---

### Database
Uses SQLite (patients.db) as the backend. 

Table schema: 

CREATE TABLE patients( \
        id INTEGER PRIMARY KEY AUTOINCREMENT, \
        patient_id TEXT, \
        name TEXT, \
        ssn TEXT, \
        sex TEXT, \
        birth_date TEXT, \
        address TEXT, \
        path TEXT \
    ) \
The path field holds all PDF file paths for each patient, separated by ;.


### Parallelized Ingestion
This project uses parallel batch ingestion to dramatically speed up loading patient records from CSV into SQLite.

How it works:

Batching:
CSV rows are grouped into chunks (e.g., 500 rows each).
Each batch can be processed independently.

Thread Pool:
A ThreadPoolExecutor runs multiple worker threads at the same time (default: 8).

Each Thread:
Parses its batch of rows.
Looks up file paths from a prebult in-memory index.
Inserts the rows into SQlite using executemany(...).

SQLite Handling: \
Each worker opens its own SQLite connection. \
SQLite serializes the actual writes internally, but CPU-bound work (row prep, lookups) happens fully in parallel. \
This keeps all CPU cores busy while avoiding database corruption. 

### Building the Application
To build the app:
First do pip install pyinstaller (if needed) \
Then do pyinstaller --onefile --windowed --icon=app.ico src/gui.py \

Build is sent to Patient_Lookup_Tool/dist be default.
Just put DB file inside /dist to use

### Future Work
More detailed logging for read/writes
