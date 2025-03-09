import os
import csv
import time
import shutil
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from utils.ftp_utils import connect_ftp, download_files, archive_files_on_ftp
from utils.selenium_setup import get_driver
from login import fnet_login
from scrape_tracking import scrape_tracking
from utils.email_utils import send_email
from utils.gsheet_setup import setup_google_sheets, add_po_num_fnet_num_to_sheet
import re

load_dotenv()

def extract_order_number(confirmation_text):
    match = re.search(r"#(\d+)", confirmation_text)
    if match:
        return match.group(1)
    else:
        return None

def place_orders():
    try:
        #setup sheets
        sheet = setup_google_sheets()

        # track success/failure
        successful_orders = []
        failed_orders = []

        # archive directory setup
        archive_dir = os.path.join(os.getenv('LOCAL_ORDERS_DIR'), 'processed')
        os.makedirs(archive_dir, exist_ok=True)

        # download files from ftp
        ftp = connect_ftp()    
        downloaded_files = []
        if ftp:
            try:
                downloaded_files = download_files(ftp)
                if downloaded_files:
                    print(f"downloaded files: {downloaded_files}")
                    archive_files_on_ftp(ftp, downloaded_files)
                    # print(f'archived files on ftp: {downloaded_files}')
                else:
                    print("no files downloaded")
            finally:
                ftp.quit()
                print("FTP connection closed")  
        else:
            print('could not connect to ftp')
            return
        
        if not downloaded_files:
            print('no files to download. exiting')
            return

        driver = get_driver() #init selenium driver

        # selenium shortcuts
        short_wait = WebDriverWait(driver, 10)
        long_wait = WebDriverWait(driver, 30)

        def short_wait_for_element(by, value, short_wait=short_wait):
            return short_wait.until(EC.element_to_be_clickable((by, value)))
        
        def long_wait_for_element(by, value, long_wait=long_wait):
            return long_wait.until(EC.element_to_be_clickable((by, value)))
        
        def exit_iframe():
            driver.switch_to.default_content()

        # login
        username = os.getenv("LOGIN_USERNAME")
        password = os.getenv("LOGIN_PASSWORD")
        login_success = fnet_login(driver, username, password)
        
        if not login_success:
            print("login failed.")
            driver.quit()
            return

        # process each file loop
        for file in downloaded_files:
            try:
                file_path = os.path.join(os.getenv('LOCAL_ORDERS_DIR'), file)
                with open(file_path, 'r') as f:
                    reader = csv.DictReader(f)
                    orders_data = list(reader)

                # group orders by PO
                grouped_orders = {}
                for row in orders_data:
                    po_num = row["PO_num"]
                    if po_num not in grouped_orders:
                        grouped_orders[po_num] = {
                            "shipping_info": {
                                "fname": row["First Name"],
                                "lname": row["Last Name"],
                                "address1": row["Ship To Address"],
                                "address2": row.get("Ship To Address 2", ""),
                                "city": row["Ship To City"],
                                "state": row["Ship To State"],
                                "zip": row["Ship To Zip"],
                            },
                            "items": []
                        }
                    grouped_orders[po_num]["items"].append({
                        "sku": row["SKU"],
                        "quantity": int(row["Qty"])
                    })

                # process each order loop
                for po_num, order in grouped_orders.items():
                    try:
                        print(f"processing PO_num: {po_num}")

                        # oos_items = False #OOS flag

                        # add items to cart loop
                        for item in order["items"]:
                            sku = item["sku"]
                            quantity = item["quantity"]

                            print(f"searching for sku {sku}")
                            search_input = long_wait_for_element(By.ID, "searchInput")
                            time.sleep(2)
                            search_input.clear()
                            print('search input cleared')
                            search_input.send_keys(sku)
                            print(f'sku: {sku} searched')
                            search_input.submit()
                            print('search button clicked waiting for item page to load')

                            long_wait.until(EC.presence_of_element_located((By.ID, "brandTitle")))
                            print('found item title')

                            #if item is OOS, skip it, send an email and go to next PO (if there is one)
                            # try:
                            #     oos_message = short_wait.until(EC.presence_of_element_located((By.ID, 'oos_message')))
                            #     if oos_message.is_displayed():
                            #         print(f'SKU: {sku} is out of stock. Skipping order submission for PO: {po_num}.')
                                    
                            #         subject = f'FNET Items OOS'
                            #         body = f'SKU: {sku} from PO: {po_num} in {file} is OOS.'
                            #         send_email(subject, body)

                            #         oos_items = True
                            #         break
                            # except NoSuchElementException:
                            #     pass

                            if quantity > 1:
                                print("inputting item quantity")
                                plus_qty = driver.find_element(By.ID, "quantBox")
                                plus_qty.clear()
                                plus_qty.send_keys(quantity)

                            print('adding item to cart')
                            add_to_cart_button = short_wait_for_element(By.ID, "addBagButton")
                            add_to_cart_button.click()
                            time.sleep(1)
                            print(f"Added {quantity} of {sku} to cart.")

                        # if oos_items:
                        #     failed_orders.append((file, po_num, 'OOS items found, entire PO skipped'))
                        #     continue

                        print(f"done attempting to add items for PO_num {po_num}")
                        
                        # checkout process
                        print("navigating to checkout page")
                        driver.get(os.getenv('CHECKOUT_PAGE_URL'))
                        shipping_info = order["shipping_info"]

                        short_wait_for_element(By.ID, 'shippingFields')

                        # fill shipping info
                        print('filling shipping info')
                        fields = {
                            'fname': shipping_info["fname"],
                            'lname': shipping_info["lname"],
                            'address1': shipping_info["address1"],
                            'address2': shipping_info["address2"],
                            'zip': shipping_info["zip"],
                            'city': shipping_info["city"]
                        }
                        
                        for field_id, value in fields.items():
                            field = short_wait_for_element(By.ID, field_id)
                            field.clear()
                            field.send_keys(value)

                        # state dropdown
                        print('filling state')
                        state_field = short_wait_for_element(By.ID, "ship_state_drop")
                        state_select = Select(state_field)
                        state_select.select_by_value(shipping_info["state"])

                        # continue throgh checkout
                        print('clicking continue to shipping button')
                        continue_to_shipping_btn = short_wait_for_element(By.ID, "shippingProceedButton")
                        continue_to_shipping_btn.click()

                        time.sleep(2) # frequent fail point, adding wait

                        print('selecting dropship shipping option')
                        dropship_shipping_btn = driver.find_element(By.ID, "DSP")
                        driver.execute_script("arguments[0].click();", dropship_shipping_btn)

                        print('clicking continue to payment button')
                        continue_to_payment_btn = short_wait_for_element(By.ID, "proceedCheckButton")
                        continue_to_payment_btn.click()

                        # payment iframes
                        iframes = WebDriverWait(driver, 30).until(
                            EC.presence_of_all_elements_located((By.CLASS_NAME, "js-iframe"))
                        )
                        time.sleep(2) #adding wait for slow site response point

                        # fill payment info
                        print('filling payment info')
                        driver.switch_to.frame(iframes[0])
                        card_field = long_wait_for_element(By.ID, "encryptedCardNumber")
                        card_field.clear()
                        card_field.send_keys(os.getenv('CC_NUM'))
                        exit_iframe()
                        time.sleep(1)

                        driver.switch_to.frame(iframes[1])
                        exp_field = short_wait_for_element(By.ID, "encryptedExpiryDate")
                        exp_field.clear()
                        exp_field.send_keys(os.getenv('CC_EXP_NUM'))
                        exit_iframe()
                        time.sleep(1)

                        driver.switch_to.frame(iframes[2])
                        csv_field = short_wait_for_element(By.ID, "encryptedSecurityCode")
                        csv_field.clear()
                        csv_field.send_keys(os.getenv('CC_CSV'))
                        exit_iframe()
                        time.sleep(1)

                        # submit order
                        print('submitting order')
                        submit_order_btn = short_wait_for_element(By.ID, "submitOrder")
                        submit_order_btn.click()
                        
                        # verify order confirmation
                        print("waiting for confirmation...")
                        order_confirmation = WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "h2.panel-title"))
                        )
                        print(f"confirmation found: {order_confirmation.text}")
                        print(f'PO_num {po_num} processed successfully')
                        
                        # add the order number to a google sheet for shipment tracking
                        print('adding order info to google sheet')
                        fnet_order_num = extract_order_number(order_confirmation.text)
                        if fnet_order_num:
                            add_po_num_fnet_num_to_sheet(sheet, po_num, fnet_order_num, po_num_col=1, fnet_num_col=2)
                            print(f"order number extracted: {fnet_order_num} and added to sheet")
                        else:
                            print('order number not found')
                        
                        # append file & po_num to success tracking
                        successful_orders.append((file, po_num))

                        time.sleep(5)

                    except Exception as e:
                        failed_orders.append((file, po_num, str(e)))
                        print(f"error processing order {po_num} from {file}: {e}")

            except Exception as e:
                print(f"error processing file {file}: {e}")

        # close browser
        driver.quit()
        print("browser closed")

        # archive the order files
        for file in downloaded_files:
            src = os.path.join(os.getenv('LOCAL_ORDERS_DIR'), file)
            dst = os.path.join(archive_dir, file)
            try:
                shutil.move(src, dst)
                print(f"moved {file} to archive")
            except Exception as e:
                print(f"failed to move {file}: {str(e)}")

        # files_to_archive = []
        # # determine which files were fully successful
        # for file in downloaded_files:
        #     if any(file == f for f, _, _ in failed_orders):
        #         print(f"skipping FTP archiving for {file} due to failed orders.")
        #     else:
        #         files_to_archive.append(file)

        # archive files locally
        # for file in files_to_archive:
        #     src = os.path.join(os.getenv('LOCAL_ORDERS_DIR'), file)
        #     dst = os.path.join(archive_dir, file)
        #     try:
        #         shutil.move(src, dst)
        #         print(f"moved {file} to local archive.")
        #     except Exception as e:
        #         print(f"failed to move {file}: {str(e)}")

        # archive files on FTP only if they were fully successful
        # ftp = connect_ftp()
        # if ftp and files_to_archive:
        #     try:
        #         archive_files_on_ftp(ftp, files_to_archive)
        #         print(f"archived files on FTP: {files_to_archive}")
        #     finally:
        #         ftp.quit()
        #         print("FTP connection closed")

        # send summary email
        print('sending summary email')
        subject = "FNET Order Summary"
        successful_msg = ', '.join(f'{po_num} ({f})' for f, po_num in successful_orders) if successful_orders else "None"
        # failed_msg = ', '.join(f'{po_num} ({f}): {e}' for f, po_num, e in failed_orders) if failed_orders else "None"
        # failed_msg = ', '.join(f'{po_num} ({f})' for f, po_num in failed_orders) if failed_orders else "None"
        failed_msg = ', '.join(f'{po_num} ({f})' for f, po_num, _ in failed_orders) if failed_orders else "None"


        body = f"""
        Successful orders: {len(successful_orders)}
        {successful_msg}

        Failed orders: {len(failed_orders)}
        {failed_msg}"""

        send_email(subject, body)

    except Exception as e:
        send_email("FNET Bot Failed", f"FNET bot failed with error: {str(e)}")
        raise

if __name__ == '__main__':
    place_orders()
    scrape_tracking()