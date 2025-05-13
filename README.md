# Google Maps Business Scraper

A Python-based scraper that automatically extracts business information from Google Maps based on search terms. The scraper collects details such as business names, ratings, reviews, addresses, websites, and phone numbers.

## Features

- Automated scraping of Google Maps business listings
- Batch processing with automatic data saving
- Progress tracking to resume interrupted scraping
- CSV output format for easy data analysis

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
- Make sure you comply with Google's terms of service when using this scraper