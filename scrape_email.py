from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re
from urllib.parse import urljoin, urlparse
import time

# Regex to find email addresses (case-insensitive)
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

def extract_emails_from_text(text: str) -> set[str]:
    """Extracts email addresses from a given text using regex."""
    return set(re.findall(EMAIL_REGEX, text, re.IGNORECASE))

def get_relevant_internal_links(page, base_url: str, keywords: list[str]) -> list[str]:
    """
    Finds internal HTTP/HTTPS links on the page whose text or href contains specified keywords.
    """
    links = set()
    parsed_base_url = urlparse(base_url)
    
    try:
        link_elements = page.query_selector_all("a[href]")
        for link_el in link_elements:
            href = link_el.get_attribute("href")
            text = (link_el.inner_text() or "").lower()
            
            if not href or href.startswith(("javascript:", "#", "tel:", "data:")):
                continue

            full_url = urljoin(base_url, href)
            parsed_full_url = urlparse(full_url)

            if parsed_full_url.scheme not in ['http', 'https'] or not parsed_full_url.netloc.endswith(parsed_base_url.netloc):
                continue
            
            link_path_query = (parsed_full_url.path + "?" + parsed_full_url.query).lower()
            for keyword in keywords:
                if keyword in text or keyword in link_path_query:
                    links.add(full_url)
                    break 
                    
    except Exception as e:
        print(f"Error extracting links from {page.url}: {e}")
    return list(links)

def scrape_website_for_emails(
    initial_url: str, 
    search_contact_pages: bool = True, 
    max_depth: int = 1,
    max_contact_links_per_page: int = 5,
    min_emails_required: int = None  # New parameter for early exit
) -> list[str]:
    """
    Scrapes a website for email addresses.

    Args:
        initial_url: The URL of the website to start scraping.
        search_contact_pages: Whether to search common contact/about pages.
        max_depth: How many levels of internal "contact-like" links to follow.
        max_contact_links_per_page: Max new contact-like links to explore from each page.
        min_emails_required: If set, stop scraping once this many unique emails are found.

    Returns:
        A list of unique email addresses found.
    """
    all_emails_found = set()
    visited_urls = set()
    early_exit_triggered = False # Flag to signal early exit

    if not initial_url.startswith(('http://', 'https://')):
        initial_url = 'https://' + initial_url

    parsed_initial_url = urlparse(initial_url)
    base_domain = parsed_initial_url.netloc

    urls_to_visit = [(initial_url, 0)]
    queued_urls_set = {initial_url} 

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
                java_script_enabled=True
            )
            context.set_default_navigation_timeout(30000)
            context.set_default_timeout(15000)
            page = context.new_page()

            while urls_to_visit:
                if early_exit_triggered: # If flag set in previous iteration, stop processing new URLs
                    print("Early exit condition met in previous URL processing. Halting crawl.")
                    break

                current_url, current_depth = urls_to_visit.pop(0)
                queued_urls_set.remove(current_url)

                if current_url in visited_urls:
                    continue
                
                if urlparse(current_url).netloc != base_domain:
                    print(f"Skipping {current_url} as it's off the initial domain {base_domain}.")
                    continue

                visited_urls.add(current_url)
                print(f"\nVisiting: {current_url} (Depth: {current_depth})")

                try:
                    page.goto(current_url, wait_until="domcontentloaded")
                    
                    cookie_selectors = [
                        "button:text-matches('Accept all', 'i')", "button:text-matches('Accept', 'i')",
                        "button:text-matches('Agree', 'i')", "button:text-matches('Allow all', 'i')",
                        "button:text-matches('Confirm', 'i')", "button:text-matches('OK', 'i')",
                        "button[aria-label*='close' i]", "button[aria-label*='accept' i]",
                        "div[id*='cookie'] button:text-matches('accept', 'i')"
                    ]
                    time.sleep(1)
                    for selector in cookie_selectors:
                        try:
                            button = page.locator(selector).first
                            if button.is_visible(timeout=1000):
                                print(f"Attempting to click cookie/popup button matching: {selector}")
                                button.click(timeout=3000)
                                time.sleep(0.5)
                                print("Clicked.")
                                break 
                        except PlaywrightTimeoutError: pass
                        except Exception as e_cookie: print(f"Minor error with cookie selector '{selector}': {e_cookie}")

                    page_content = page.content()
                    emails_from_content = extract_emails_from_text(page_content)
                    if emails_from_content:
                        print(f"  Found emails in content: {emails_from_content}")
                        all_emails_found.update(emails_from_content)
                        if min_emails_required is not None and len(all_emails_found) >= min_emails_required:
                            print(f"  Minimum required emails ({min_emails_required}) reached from content. Will stop after this page.")
                            early_exit_triggered = True

                    mailto_links = page.locator('a[href^="mailto:"]')
                    for i in range(mailto_links.count()):
                        mailto_link_element = mailto_links.nth(i)
                        href = mailto_link_element.get_attribute("href")
                        if href:
                            email = href.replace("mailto:", "", 1).split("?")[0].strip()
                            if re.fullmatch(EMAIL_REGEX, email):
                                print(f"  Found mailto email: {email.lower()}")
                                all_emails_found.add(email.lower())
                                if min_emails_required is not None and len(all_emails_found) >= min_emails_required:
                                    print(f"  Minimum required emails ({min_emails_required}) reached after mailto. Will stop after this page.")
                                    early_exit_triggered = True 
                                    # No break here, finish all mailtos on this page
                    
                    if not early_exit_triggered: # Only add new links if not already planning to exit
                        if search_contact_pages and current_depth < max_depth:
                            contact_keywords = ["contact", "about", "email", "mail", "impressum", "legal", "privacy", "terms", "support", "kontakt", "ueberuns", "team"]
                            candidate_links = get_relevant_internal_links(page, current_url, contact_keywords)
                            added_links_count = 0
                            for contact_url in candidate_links:
                                if contact_url not in visited_urls and contact_url not in queued_urls_set:
                                    if added_links_count < max_contact_links_per_page:
                                        urls_to_visit.append((contact_url, current_depth + 1))
                                        queued_urls_set.add(contact_url)
                                        added_links_count += 1
                                    else:
                                        print(f"  Reached max contact links ({max_contact_links_per_page}) to add from {current_url}")
                                        break
                            if candidate_links:
                                print(f"  Found {len(candidate_links)} potential contact-like links. Added {added_links_count} to queue.")

                except PlaywrightTimeoutError as e_timeout:
                    print(f"Timeout error loading or interacting with page: {current_url} - {e_timeout}")
                except Exception as e_page:
                    print(f"Error processing page {current_url}: {e_page}")
                
                if early_exit_triggered: # If flag was set during this page's processing, break main loop
                    print(f"Minimum email count ({len(all_emails_found)}/{min_emails_required if min_emails_required else 'N/A'}) met or exceeded. Stopping further URL visits.")
                    break 

                time.sleep(0.5)

            browser.close()

        except Exception as e_overall:
            print(f"An overall error occurred: {e_overall}")
            if 'browser' in locals() and browser.is_connected():
                browser.close()
                
        return sorted(list(all_emails_found))



# if __name__ == '__main__':
#     target_url = "https://plushostels.com/en/florence" 
#     # target_url = "https://www.python.org" # Good site for testing contact pages

#     print(f"Starting email extraction for: {target_url}\n")
    
#     # Example 1: Scrape with a minimum email requirement
#     print("--- Example 1: Searching for at least 1 email ---")
    
#     emails = scrape_website_for_emails(
#         target_url, 
#         search_contact_pages=True, 
#         max_depth=5, 
#         min_emails_required=1 # Stop once 1 email is found
#     )

#     print(f"\n--- Emails found (min_emails_required=1) on {target_url} ---")


#     if emails:
#         for email in emails:
#             print(email)
#         print(f"Total found: {len(emails_min_1)}")
#     else:
#         print("No emails found, or minimum not met before exhausting search.")

    