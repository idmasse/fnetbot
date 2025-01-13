import gspread
from google.oauth2.service_account import Credentials

# google sheets API setup
def setup_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file('utils/gsheet_creds.json', scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("fnet tracking").sheet1  # open the first sheet
    return sheet

def add_po_num_fnet_num_to_sheet(sheet, po_num, order_number, po_num_col=1, fnet_num_col=2):
    next_row = len(sheet.get_all_values()) + 1 # find the next available row
    
    # Update the specific columns with values
    sheet.update_cell(next_row, po_num_col, po_num)
    sheet.update_cell(next_row, fnet_num_col, order_number)
