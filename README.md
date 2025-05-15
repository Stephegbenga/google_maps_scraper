# Google Maps Business Scraper

A Python-based scraper that automatically extracts business information from Google Maps based on search terms. The scraper collects details such as business names, ratings, reviews, addresses, websites, phone numbers, and email addresses from business websites.

## Features

- Automated scraping of Google Maps business listings
- Batch processing with automatic data saving
- Progress tracking to resume interrupted scraping
- CSV output format for easy data analysis
- Automated email extraction from business websites
- Multi-threaded processing for faster data collection

## Prerequisites

- Python 3.x
- Playwright

## Installation

1. Clone the repository or download the source code
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```bash
   playwright install
   ```

## Configuration

### search_terms.txt

Create a `search_terms.txt` file in the project directory with your search queries, one per line. For example:

```
Dentists in milan
Dentists in rome
Physiotherapists in milan
Physiotherapists in rome
```

### completed_search_term.txt

This file is automatically created and maintained by the scraper to track which search terms have been processed. You don't need to create or modify this file manually.

## Usage

Run the scraper:
```bash
python index.py
```

## Output

The scraper creates separate CSV files for each search term (e.g., `Dentists_in_milan.csv`). Each CSV file contains the following information:

- ID: Unique identifier for the business
- Name: Business name
- Rating: Google Maps rating (0-5)
- Reviews: Number of reviews
- Address: Business address
- Website: Business website URL (if available)
- Phone: Contact number
- Email: Business email addresses (extracted from website)
- Search Term: The search query used to find this business

## Batch Processing

The scraper processes data in batches of 50 entries to ensure data is saved regularly. This prevents data loss in case of interruptions and makes it easier to handle large datasets.

## Error Handling

- The scraper maintains a record of processed business IDs to avoid duplicates
- Failed scraping attempts for individual businesses are logged but don't stop the overall process
- The scraper can be safely interrupted and will resume from the last unprocessed search term

## Notes

- The scraper uses headless mode by default for better performance
- Rate limiting and delays are implemented to prevent blocking
- Multi-threaded email extraction with 4 worker threads for improved performance
- Make sure you comply with Google's terms of service when using this scraper

## Email Extraction and Validation

The scraper includes an automated email extraction and validation system that:
- Scans business websites to find email addresses
- Processes websites concurrently for faster data collection
- Updates CSV files with found email addresses
- Skips already processed websites to avoid duplicate work
- Validates extracted email addresses using multiple criteria

### Email Validation Features

- **Format Validation**: Ensures email addresses follow correct syntax
- **Disposable Email Detection**: Filters out temporary/disposable email addresses
- **MX Record Verification**: Validates domain mail server configuration
- **Popular Domain Whitelisting**: Fast-tracks validation for known reliable domains
- **Concurrent Processing**: Multi-threaded validation for improved performance
- **MX Record Caching**: Caches DNS lookup results to reduce API calls
- **Retry Mechanism**: Implements automatic retries for temporary DNS failures
- **Multiple DNS Providers**: Uses both Google and Cloudflare DNS servers for reliability

To update and validate email information in existing CSV files:
```bash
python validate_emails.py
```

The validation process adds a new 'valid_emails' column to CSV files, containing only the verified email addresses that passed all validation checks.