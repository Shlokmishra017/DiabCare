"""
Database seed script for demo patients.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Src.database import init_db, seed_patients

DB_PATH = "DATA/diabcare.db"

if __name__ == "__main__":
    print(f"Initializing database at {DB_PATH}...")
    init_db(DB_PATH)

    print("Seeding demo patients...")
    ids = seed_patients(
        db_path=DB_PATH,
        cleaned_csv="DATA/CleanedDiabetic_data.csv",
        original_csv="DATA/diabetic_data.csv",
        n_patients=6,
    )

    print(f"Seeded {len(ids)} patients:")
    for pid in ids:
        print(f"  patient_id: {pid}")

