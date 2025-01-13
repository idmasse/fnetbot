# Fragrance Net Order Processing Automation 

A python automation for placing orders on fragrance net. It looks for orders on an FTP folder and if it finds them it downloads the order files and processes the order data. When it's done it archives the order files, updates a google sheet with the PO number and FNet order number for shipment tracking purposes, then it sends a success email. The script is controlled by a plist, set to check for new orders every 60 minuutes.

## Features
- FTP Download: Downloads order CSV files from an FTP server.  
- Order Processing: Automatically places orders by filling web forms and handling payment information.  
- Order Confirmation Extraction: Extracts the order confirmation number from the order success message.  
- Google Sheets Integration: Logs PO_num and order number to a Google Sheet for shipment tracking.  
- Error Handling: Sends summary email reports of successful and failed orders.  
- File Archiving: Moves processed order files to an archive folder.  

## Environmet Variables  
* * if using the plist, DIRs must be absolute paths  

FTP_HOST=  
FTP_USER=  
FTP_PASS=  
LOGIN_URL=  
LOGIN_USERNAME=  
LOGIN_PASSWORD=  
CHECKOUT_PAGE_URL=  
SENDER_EMAIL=  
RECEIVER_EMAIL=  
EMAIL_PASSWORD=  
LOCAL_ORDERS_DIR=  
LOCAL_PROCESSED_DIR=  

## Dependencies
selenium: Undetected chrome driver for web automation.  
gspread: For Google Sheets API integration.  
google-auth: For Google API authentication.  
python-dotenv: For loading environment variables.  
shutil, csv, re, time: For file handling, regular expressions, and timing operations.  

## Potential Improvements
Add retries for failed network requests.  
Add retries for order placement.  
Include logging for more detailed debugging.   
Refactor order processing function  