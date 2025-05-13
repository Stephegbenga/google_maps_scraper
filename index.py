
from playwright.sync_api import sync_playwright
from scrape_email import scrape_website_for_emails
import time, re, csv, os
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Lock

def read_search_terms():
    with open('search_terms.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()]

def read_completed_terms():
    if os.path.exists('completed_search_term.txt'):
        with open('completed_search_term.txt', 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def read_processed_ids(csv_filename):
    processed_ids = set()
    if os.path.exists(csv_filename):
        with open(csv_filename, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed_ids.add(row['id'])
    return processed_ids

def mark_search_completed(search_term):
    with open('completed_search_term.txt', 'a') as f:
        f.write(f"{search_term}\n")


def process_website_for_emails(place_data):
    if not place_data.get('website'):
        return place_data
    try:
        emails = scrape_website_for_emails(place_data['website'], max_depth=1)
        place_data['email'] = ','.join(emails) if emails else ''
        print(place_data)
    except Exception as e:
        print(f"Error scraping emails from {place_data['website']}: {e}")
        place_data['email'] = ''
    return place_data

def save_to_csv(data, filename):
    if not data:
        return
    
    fieldnames = ['id', 'name', 'rating', 'reviews', 'address', 'website', 'phone', 'search_term', 'email']
    file_exists = os.path.exists(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(data)


def scrape_google_maps_hotels():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        search_terms = read_search_terms()
        completed_terms = read_completed_terms()
        
        for search_term in search_terms:
            if search_term in completed_terms:
                print(f"Skipping already completed search: {search_term}")
                continue
                
            print(f"Processing search term: {search_term}")
            csv_filename = f"{search_term.replace(' ', '_')}.csv"
            batch_data = []
            processed_ids = read_processed_ids(csv_filename)
            
            page.goto(f"https://www.google.com/maps/search/{search_term}")


            page.wait_for_selector('div.Nv2PK')

            scroll_container_selector = 'div[role="feed"]'
            processed = set()
            force_scroll_attempts = 0
            max_force_scroll_attempts = 8
            previous_card_count = 0  # Initialize the variable before the loop



            while True:
                cards = page.query_selector_all('div.Nv2PK')

                for card in cards:
                    try:
                        card_id = ''.join(filter(str.isalpha, card.get_attribute('data-result-id') or card.inner_text()))
                        if card_id in processed or card_id in processed_ids:
                            continue

                        processed.add(card_id)
                        card.scroll_into_view_if_needed()
                        card.click()
                        page.wait_for_selector('div.aIFcqe h1.DUwDvf')

                        time.sleep(2)  # Wait for sidebar to fully render

                        name = page.query_selector('div.aIFcqe h1.DUwDvf')

                        # New extractions
                        address = page.query_selector('button[data-item-id="address"]')
                        website = page.query_selector('a[data-item-id="authority"]')
                        phone = page.query_selector('button[data-item-id^="phone"]')
                        phone = re.sub(r'[^\d+]', '', phone.inner_text())  # "+3905526261"

                        # Extract rating based on aria-label containing "stars"
                        # Extract rating based on aria-label containing "s
                        rating_span = page.query_selector('div.F7nice span[aria-label*="stars"]')
                        rating = rating_span.get_attribute('aria-label').split()[0] if rating_span else None
                        rating = float(rating) if rating else None

                        # Extract reviews based on aria-label containing "reviews"
                        reviews_span = page.query_selector('div.F7nice span[aria-label*="reviews"]')
                        reviews = reviews_span.inner_text() if reviews_span else None
                        reviews = re.sub(r'[^\d]', '', reviews)  # "2601"
                        reviews = int(reviews) if reviews else None

                        # Apply filters for rating and reviews
       
                        place_data = {
                            "id": card_id,
                            "name": name.inner_text() if name else None,
                            "rating": rating,
                            "reviews": reviews,
                            "address": address.inner_text() if address else None,
                            "website": website.get_attribute('href') if website else None,
                            "phone": phone,
                            "search_term": search_term
                        }

                        if (rating is None or rating < 4.0) or (reviews is None or reviews <= 15):
                            print(f"matches less than 4.0 rating or less than 15 reviews. Skipping...")
                        batch_data.append(place_data)

                        if len(batch_data) >= 50:
                            # Process emails concurrently using ThreadPoolExecutor
                            with ThreadPoolExecutor(max_workers=4) as executor:
                                processed_data = list(executor.map(process_website_for_emails, batch_data))
                            save_to_csv(processed_data, csv_filename)
                            batch_data = []

                    except Exception as e:
                        print("Error:", e)
                        pass
                
                # Check if we found any new cards
                current_card_count = len(processed)
                if current_card_count == previous_card_count:
                    force_scroll_attempts += 1
                    if force_scroll_attempts >= max_force_scroll_attempts:
                        print(f"No new cards found after {force_scroll_attempts} forced scroll attempts. Exiting...")
                        # Save any remaining data before breaking
                        if batch_data:
                            save_to_csv(batch_data, csv_filename)
                        mark_search_completed(search_term)
                        break
                else:
                    force_scroll_attempts = 0
                    previous_card_count = current_card_count

                # Force scroll regardless of position
                viewport_height = page.evaluate(f"document.querySelector('{scroll_container_selector}').clientHeight")
                page.evaluate(f"""
                    const container = document.querySelector('{scroll_container_selector}');
                    container.scrollBy({{top: {viewport_height}, behavior: 'smooth'}});
                """)
                
                # Wait for scroll and content to load
                time.sleep(2)
                print(f"Force-scrolled {force_scroll_attempts} times.")
                page.wait_for_timeout(1000)


scrape_google_maps_hotels()
