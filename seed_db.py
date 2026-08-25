"""
DiabCare AI — Database Seed Script
=====================================
Creates DATA/diabcare.db and populates it with 6 representative demo patients.

Run from project root:
  python seed_db.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Src.database import init_db, seed_patients

DB_PATH = "DATA/diabcare.db"

if __name__ == "__main__":
    print("=" * 50)
    print("  DiabCare AI -- Database Seeder")
    print("=" * 50)

    print(f"\n[1/2] Initialising database at {DB_PATH} ...")
    init_db(DB_PATH)
    print("      Tables created (or already exist).")

    print("\n[2/2] Seeding patients (6 representative patients) ...")
    ids = seed_patients(
        db_path=DB_PATH,
        cleaned_csv="DATA/CleanedDiabetic_data.csv",
        original_csv="DATA/diabetic_data.csv",
        n_patients=6,
    )

    print(f"\nDone. {len(ids)} patients seeded:")
    for pid in ids:
        print(f"  patient_id: {pid}")

    print("\n[OK] Database ready. Run: uvicorn main:app --reload")
