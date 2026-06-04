"""
CSV parsing utilities for batch uploads
"""
import csv
import io
from typing import List, Dict

def parse_csv(csv_content: str) -> List[Dict[str, str]]:
    """
    Parse CSV content into list of dicts.
    Expected columns: phone_number, first_name, company, message
    """
    rows = []
    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        for row in reader:
            rows.append(row)
        return rows
    except Exception as e:
        raise ValueError(f"CSV parsing error: {str(e)}")
