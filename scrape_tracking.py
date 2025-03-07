from utils.gsheet_setup import setup_google_sheets
from bs4 import BeautifulSoup
import cloudscraper
import re
import os
import time
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("TRACKING_BASE_URL")

# create a session
def create_scraper_session():
    scraper = cloudscraper.create_scraper()
    return scraper

# scrape tracking numbers
def scrape_tracking_info(order_number, scraper):
    url = f"{BASE_URL}{order_number}"

    response = scraper.get(url)
    
    if response.status_code == 403:
        print(f"access denied for order {order_number}. cloudflare challenge failed.")
        return "Unknown", None  # return "Unknown" for vendor if session fails

    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    vendor_tag = soup.find("strong", string=re.compile(r"Shipment Vendor"))
    shipment_vendor = vendor_tag.next_sibling.strip() if vendor_tag else "Unknown"

    tracking_tag = soup.find("strong", string=re.compile(r"Shipment Tracking"))
    tracking_number = tracking_tag.find_next("a").text.strip() if tracking_tag else None

    return shipment_vendor, tracking_number

# update sheets with fulfillment info
# def update_sheet_with_tracking(sheet, scraper):
#     rows = sheet.get_all_values()

#     for i, row in enumerate(rows[1:], start=2):
#         order_number = row[1].strip() if len(row) > 1 else ""  # col B (order number)
#         shipment_vendor = row[2].strip() if len(row) > 2 else ""  # col C (carrier)
#         tracking_number = row[3].strip() if len(row) > 3 else ""  # col D (tracking number)

#         if order_number and not tracking_number:  # only if col B has an order number and D is blank
#             print(f"processing order number: {order_number}")
#             carrier, tracking_number = scrape_tracking_info(order_number, scraper)

#             if tracking_number:
#                 sheet.update_cell(i, 3, carrier)  # col C (carrrier)
#                 sheet.update_cell(i, 4, tracking_number)  # col D (tracking number)
#                 print(f"Updated row {i}: Carrier: {carrier}, Tracking Number: {tracking_number}")
#             else:
#                 print(f"No tracking number found for order: {order_number}")

def update_sheet_with_tracking(sheet, scraper):
    rows = sheet.get_all_values()

    batch_updates = []
    row_indices = []
    
    for i, row in enumerate(rows[1:], start=2):
        order_number = row[1].strip() if len(row) > 1 else ""  # col B (order number)
        shipment_vendor = row[2].strip() if len(row) > 2 else ""  # col C (carrier)
        tracking_number = row[3].strip() if len(row) > 3 else ""  # col D (tracking number)
        
        if order_number and not tracking_number:  # only if col B has an order number and D is blank
            print(f"processing order number: {order_number}")
            carrier, tracking_number = scrape_tracking_info(order_number, scraper)
            
            if tracking_number:
                # add to batch updates
                row_indices.append(i)
                batch_updates.append({'range': f'C{i}:D{i}', 'values': [[carrier, tracking_number]]})
                print(f"Queued update for row {i}: Carrier: {carrier}, Tracking Number: {tracking_number}")
            else:
                print(f"No tracking number found for order: {order_number}")
    
    #process batch updates in chunks to stay within googles quota limits
    chunk_size = 10
    for i in range(0, len(batch_updates), chunk_size):
        chunk = batch_updates[i:i+chunk_size]
        if chunk:
            # use batch_update for multiple updates at once
            sheet.batch_update(chunk)
            print(f"Processed batch update for rows: {row_indices[i:i+chunk_size]}")
            time.sleep(1)  #delay to avoid rate limits


def scrape_tracking():
    scraper = create_scraper_session()
    sheet = setup_google_sheets()
    update_sheet_with_tracking(sheet, scraper)
