import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os, sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.join(BASE_DIR, "patients.db")

class PatientLookupGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Patient Lookup Tool")
        self.root.geometry("800x600")  # Start with a good window size
        self.root.configure(bg="#e6e5e5")  # Light background

        # Center window
        self.center_window(800, 600)

        # --- Search Bar ---
        search_frame = tk.Frame(root, bg="#e6e5e5")
        search_frame.pack(pady=10)

        tk.Label(search_frame, text="Search by ID or Name:", font=("Segoe UI", 12, "bold"), bg="#e6e5e5").pack(side="left", padx=5)

        self.search_entry = tk.Entry(search_frame, width=40, font=("Segoe UI", 11))
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda e: self.on_search())  # Press Enter to search

        tk.Button(search_frame, text="Search", command=self.on_search, font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)

        # --- Results with Scrollbar ---
        tk.Label(root, text="Patients", font=("Segoe UI", 12, "bold"), bg="#e6e5e5").pack(pady=(10,0))
        results_frame = tk.Frame(root)
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.results = tk.Listbox(results_frame, width=80, height=10, font=("Consolas", 11))
        self.results.pack(side="left", fill="both", expand=True)

        results_scrollbar = tk.Scrollbar(results_frame, orient="vertical", command=self.results.yview)
        results_scrollbar.pack(side="right", fill="y")
        self.results.config(yscrollcommand=results_scrollbar.set)
        self.results.bind("<Double-1>", self.on_double_click)

        # --- File List with Scrollbar ---
        tk.Label(root, text="Files", font=("Segoe UI", 12, "bold"), bg="#e6e5e5").pack(pady=(10,0))
        files_frame = tk.Frame(root)
        files_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.file_listbox = tk.Listbox(files_frame, width=80, height=10, font=("Consolas", 11))
        self.file_listbox.pack(side="left", fill="both", expand=True)

        file_scrollbar = tk.Scrollbar(files_frame, orient="vertical", command=self.file_listbox.yview)
        file_scrollbar.pack(side="right", fill="y")
        self.file_listbox.config(yscrollcommand=file_scrollbar.set)
        self.file_listbox.bind("<Double-1>", self.open_pdf)

        # --- Status Bar ---
        self.status = tk.Label(root, text="Ready", bd=1, relief="sunken", anchor="w", bg="#b9b7b7")
        self.status.pack(side="bottom", fill="x")

        # Shortcut: ESC to quit
        # self.root.bind("<Escape>", lambda e: self.root.quit())

    def center_window(self, w, h):
        """Center the window on the screen."""
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def on_search(self):
        query = self.search_entry.get().strip()
        self.results.delete(0, tk.END)

        if not query:
            messagebox.showwarning("Warning", "Please enter a search term.")
            return

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM patients WHERE id LIKE ? OR name LIKE ?", (f"%{query}%", f"%{query}%"))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            messagebox.showinfo("Not found", "No patients found.")
            self.status.config(text="No patients found")
            return

        for r in rows:
            self.results.insert(tk.END, f"{r[0]} - {r[1]}")

        self.status.config(text=f"Found {len(rows)} patients")

    def on_double_click(self, event):
        selection = self.results.curselection()
        if not selection:
            return

        patient_text = self.results.get(selection[0])
        pid = patient_text.split(" - ")[0]

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT path FROM patients WHERE id = ?", (pid,))
        row = cur.fetchone()
        conn.close()

        self.file_listbox.delete(0, tk.END)
        if row and row[0]:
            files = row[0].split(";")
            for f in files:
                self.file_listbox.insert(tk.END, f)
            self.status.config(text=f"Loaded {len(files)} files for patient {pid}")
        else:
            messagebox.showinfo("No Files", "No files found for this patient.")
            self.status.config(text=f"No files found for {pid}")

    def open_pdf(self, event):
        selection = self.file_listbox.curselection()
        if not selection:
            return
        path = self.file_listbox.get(selection[0])
        if os.path.exists(path):
            os.startfile(path)
            self.status.config(text=f"Opened: {os.path.basename(path)}")
        else:
            messagebox.showerror("Error", f"File not found:\n{path}")
            self.status.config(text="Error: file not found")

if __name__ == "__main__":
    root = tk.Tk()
    app = PatientLookupGUI(root)
    root.mainloop()