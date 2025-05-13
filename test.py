# from playwright.sync_api import sync_playwright
# import time

# def scrape_google_maps_hotels():
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=False, slow_mo=100)
#         context = browser.new_context()
#         page = context.new_page()

#         page.goto("https://www.google.com/maps/search/hotels+in+Florence")
#         page.wait_for_selector('div.Nv2PK')  # Wait for cards to load

#         scroll_container_selector = 'div.m6QErb.DxyBCb.kA9KIf.dS8AEf'
#         processed = set()
#         last_height = 0

#         while True:
#             cards = page.query_selector_all('div.Nv2PK')

#             for card in cards:
#                 try:
#                     card_id = card.get_attribute('data-result-id') or card.inner_text()
#                     if card_id in processed:
#                         continue

#                     processed.add(card_id)
#                     card.scroll_into_view_if_needed()
#                     card.click()
#                     page.wait_for_selector('h1.DUwDvf')  # Wait for sidebar title

#                     time.sleep(2)  # Let sidebar load fully

#                     name = page.query_selector('h1.DUwDvf')
#                     rating = page.query_selector('span.MW4etd span.z5jxId')
#                     reviews = page.query_selector('span.MW4etd span.UY7F9')

#                     print({
#                         "name": name.inner_text() if name else None,
#                         "rating": rating.inner_text() if rating else None,
#                         "reviews": reviews.inner_text() if reviews else ,
#                         "address": "",
#                         "website": "",
#                         "phone": ""
#                     })

#                 except Exception as e:
#                     print("Error:", e)

#             # Scroll to load more cards
#             page.eval_on_selector(scroll_container_selector, 'el => el.scrollBy(0, el.offsetHeight)')
#             time.sleep(2)

#             # Break condition if no new cards are loaded
#             if len(cards) == len(processed):
#                 break

#         browser.close()
# scrape_google_maps_hotels()

from playwright.sync_api import sync_playwright
import time

def scrape_google_maps_hotels():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.google.com/maps/search/hotels+in+Florence")
        page.evaluate("document.body.style.zoom = '25%'")

        page.wait_for_selector('div.Nv2PK')

        scroll_container_selector = 'div.m6QErb.DxyBCb.kA9KIf.dS8AEf'
        processed = set()

        while True:
            cards = page.query_selector_all('div.Nv2PK')

            for card in cards:
                try:
                    card_id = card.get_attribute('data-result-id') or card.inner_text()
                    if card_id in processed:
                        continue

                    processed.add(card_id)
                    card.scroll_into_view_if_needed()
                    card.click()
                    page.wait_for_selector('h1.DUwDvf')

                    time.sleep(2)  # Wait for sidebar to fully render

                    name = page.query_selector('h1.DUwDvf')
                    rating = page.query_selector('span.MW4etd span.z5jxId')
                    reviews = page.query_selector('span.MW4etd span.UY7F9')

                    # New extractions
                    address = page.query_selector('button[data-item-id="address"]')
                    website = page.query_selector('a[data-item-id="authority"]')
                    phone = page.query_selector('button[data-item-id^="phone"]')

                    print({
                        "name": name.inner_text() if name else None,
                        "rating": rating.inner_text() if rating else None,
                        "reviews": reviews.inner_text() if reviews else None,
                        "address": address.inner_text() if address else None,
                        "website": website.get_attribute('href') if website else None,
                        "phone": phone.inner_text() if phone else None
                    })

                except Exception as e:
                    print("Error:", e)

            # Scroll to load more
            page.eval_on_selector(scroll_container_selector, 'el => el.scrollBy(0, el.offsetHeight)')
            time.sleep(2)

            if len(cards) == len(processed):
                break

        browser.close()

scrape_google_maps_hotels()
