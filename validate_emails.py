import dns.resolver
import re # Fixed import
import csv # Fixed import
import os
from typing import List, Set
import concurrent.futures
import multiprocessing # Added import
import time # Added for retry delay

# Cache for MX record lookups
MX_CACHE = {}
CACHE_EXPIRY_SECONDS = 300  # Cache results for 5 minutes

def load_disposable_domains() -> Set[str]:
    """Load disposable email domains from the disposable_domain_list.txt file."""
    domains = set()
    list_path = os.path.join(os.path.dirname(__file__), 'disposable_domain_list.txt')
    try:
        with open(list_path, 'r', encoding='utf-8') as f:
            for line in f:
                domain = line.strip().lower()
                if domain:
                    domains.add(domain)
        return domains
    except Exception as e:
        print(f"Error loading disposable domains list: {e}")
        return set()

# Load disposable domains from file
DISPOSABLE_DOMAINS = load_disposable_domains()

# Define max workers for the thread pool dynamically
# Sets a minimum of 1 worker, uses the number of CPU cores if available and less than/equal to 32,
# and caps the maximum number of workers at 32 to prevent resource exhaustion.
CPU_CORES = multiprocessing.cpu_count()
MAX_WORKERS = max(1, min(CPU_CORES, 32))

def is_disposable_domain(email: str) -> bool:
    """Check if the email domain is a known disposable email service."""
    try:
        domain = email.split('@')[1].lower()
        return domain in DISPOSABLE_DOMAINS
    except IndexError:
        return False

# Whitelist of popular domains that are assumed to have valid MX records
POPULAR_DOMAINS_WHITELIST = {
    "gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "aol.com", "icloud.com", "mail.com", "zoho.com", "protonmail.com",
    "gmx.com", "yandex.com"
}

def has_valid_mx_record(domain: str) -> bool:
    """Check if the domain has valid MX records using a custom resolver with retries, or if it's on the whitelist."""
    # Check if the domain is in the whitelist
    if domain.lower() in POPULAR_DOMAINS_WHITELIST:
        # print(f"Domain {domain} is whitelisted, skipping MX check.")
        return True

    resolver = dns.resolver.Resolver()
    resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1', '1.0.0.1'] # Google and Cloudflare DNS
    resolver.lifetime = 3  # Set timeout to 3 seconds for each query
    resolver.timeout = 1   # Set timeout for each individual server query to 1 second

    max_retries = 3
    # Check cache first
    if domain in MX_CACHE:
        cached_result, timestamp = MX_CACHE[domain]
        if time.time() - timestamp < CACHE_EXPIRY_SECONDS:
            # print(f"Returning cached MX record result for {domain}: {cached_result}")
            return cached_result

    for attempt in range(max_retries):
        try:
            resolver.resolve(domain, 'MX')
            MX_CACHE[domain] = (True, time.time()) # Cache positive result
            return True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            # These are definitive 'no MX record' or 'domain does not exist' answers
            # print(f"No MX record or domain not found for {domain} on attempt {attempt + 1}")
            MX_CACHE[domain] = (False, time.time()) # Cache negative result
            return False
        except dns.exception.Timeout:
            print(f"DNS query timed out for {domain} on attempt {attempt + 1}. Retrying if possible...")
            if attempt < max_retries - 1:
                time.sleep(0.5) # Wait a bit before retrying
            else:
                print(f"DNS query for {domain} failed after {max_retries} attempts due to timeout.")
                # Do not cache timeout errors as they might be transient
                return False
        except Exception as e:
            print(f"Error checking MX record for {domain} on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.5)
            else:
                print(f"DNS query for {domain} failed after {max_retries} attempts due to other errors.")
                # Do not cache other errors as they might be transient
                return False
    MX_CACHE[domain] = (False, time.time()) # Fallback, cache as false if all retries fail
    return False

def is_valid_email(email: str) -> bool:
    """Validate an email address by checking format, disposable domain, and MX record."""
    # Basic email format validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return False
    
    # Check if it's from a disposable domain
    if is_disposable_domain(email):
        return False
    
    # Check MX record
    domain = email.split('@')[1]
    return has_valid_mx_record(domain)

def ensure_valid_emails_column(csv_filename: str) -> None:
    """Ensure the CSV file has a valid_emails column, add if missing."""
    if not os.path.exists(csv_filename):
        return
    
    # Read the current CSV content
    rows = []
    fieldnames = None
    with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Check if valid_emails column exists
    if 'valid_emails' not in fieldnames:
        fieldnames.append('valid_emails')
        # Add empty valid_emails field to existing rows
        for row in rows:
            row['valid_emails'] = ''
        
        # Write back the updated content
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            print(f"Added valid_emails column to {csv_filename}")

def validate_emails_in_csv(csv_filename: str) -> None:
    """Process a CSV file to validate emails and update the valid_emails column using concurrency."""
    if not os.path.exists(csv_filename):
        print(f"File not found: {csv_filename}")
        return

    # Ensure the valid_emails column exists
    ensure_valid_emails_column(csv_filename)

    rows = []
    fieldnames = None # Initialize fieldnames
    with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames # Capture fieldnames here
        # Check if fieldnames is None (empty file) and handle
        if fieldnames is None:
            print(f"CSV file {csv_filename} is empty or has no header.")
            return
            
        for row in reader:
            email_str = row.get('email', '')
            if email_str:
                emails_to_validate = [e.strip() for e in email_str.split(',') if e.strip()]
                valid_emails = []
                if emails_to_validate:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        future_to_email = {executor.submit(is_valid_email, email): email for email in emails_to_validate}
                        for future in concurrent.futures.as_completed(future_to_email):
                            email = future_to_email[future]
                            try:
                                if future.result():
                                    valid_emails.append(email)
                            except Exception as exc:
                                print(f'{email} generated an exception: {exc}')
                row['valid_emails'] = ','.join(valid_emails) if valid_emails else ''
            else:
                row['valid_emails'] = ''
            rows.append(row)

    # Write the updated content back to the CSV
    # Ensure fieldnames is not None before using it
    if fieldnames:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            print(f"Updated valid emails in {csv_filename} using concurrent processing.")
    else:
        print(f"Could not write to {csv_filename} as fieldnames were not determined.")

def process_all_csv_files(directory: str) -> None:
    """Process all CSV files in the given directory."""
    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            csv_path = os.path.join(directory, filename)
            print(f"\nProcessing {filename}...")
            validate_emails_in_csv(csv_path)

if __name__ == '__main__':
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    if os.path.exists(results_dir):
        print(f"Starting email validation for CSV files in {results_dir}\n")
        process_all_csv_files(results_dir)
    else:
        print(f"Results directory not found: {results_dir}")

