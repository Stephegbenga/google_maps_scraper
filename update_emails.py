from playwright.sync_api import sync_playwright
from scrape_email import scrape_website_for_emails
import time
import re
import csv
import os
from concurrent.futures import ThreadPoolExecutor
from glob import glob

def read_csv_without_emails(csv_filename):
    """Read records from CSV that don't have emails or have empty email fields."""
    records_to_update = []
    with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get('email') and row.get('website'):
                records_to_update.append(row)
    return records_to_update

def process_website_for_emails(record):
    """Process a single record to find emails from its website."""
    if not record.get('website'):
        return record
    try:
        emails = scrape_website_for_emails(record['website'], max_depth=1, min_emails_required=2)
        record['email'] = ','.join(emails) if emails else ''
        print(f"Found emails for {record['name']}: {record['email']}")
    except Exception as e:
        print(f"Error scraping emails from {record['website']}: {e}")
        record['email'] = ''
    return record

def update_csv_with_emails(csv_filename, updated_records):
    """Update the CSV file with new email information."""
    if not updated_records:
        return

    # Read all records from the original file
    all_records = []
    with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            all_records.append(row)

    # Update records with new email information
    updated_ids = {record['id']: record for record in updated_records}
    for record in all_records:
        if record['id'] in updated_ids:
            record['email'] = updated_ids[record['id']]['email']

    # Write all records back to the file
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

def ensure_csv_has_email_column(csv_filename):
    """Ensure the CSV file has an email column, add if missing."""
    if not os.path.exists(csv_filename):
        return
    
    # Read the current CSV content
    rows = []
    fieldnames = None
    with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Check if email column exists
    if 'email' not in fieldnames:
        fieldnames.append('email')
        # Add empty email field to existing rows
        # Ensure all rows have the 'email' key
        for row in rows:
            if 'email' not in row:
                row['email'] = ''
        
        # Write back the updated content
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            print(f"Added email column to {csv_filename}")

def update_emails_in_csv():
    """Main function to update emails in all CSV files."""
    # Find all CSV files in the current directory
    csv_files = glob('results/*.csv')
    
    if not csv_files:
        print("No CSV files found in the current directory.")
        return

    for csv_filename in csv_files:
        print(f"\nProcessing {csv_filename}...")
        
        # Ensure the CSV has an email column
        ensure_csv_has_email_column(csv_filename)
        
        # Read records that need email updates
        records_to_update = read_csv_without_emails(csv_filename)
        
        if not records_to_update:
            print(f"No records without emails found in {csv_filename}")
            continue
            
        print(f"Found {len(records_to_update)} records without emails")
        
        # Process websites concurrently using ThreadPoolExecutor
        for i in range(0, len(records_to_update), 20):
            batch = records_to_update[i:i+20]
            with ThreadPoolExecutor(max_workers=4) as executor:
                updated_records = list(executor.map(process_website_for_emails, batch))
            update_csv_with_emails(csv_filename, updated_records)
            print(f"Updated {len(updated_records)} records in {csv_filename}")
            # Clear updated records to avoid duplication
            updated_records.clear()

if __name__ == '__main__':
    update_emails_in_csv()