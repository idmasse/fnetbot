# Import required libraries for FTP operations, logging and env variables
import os
import logging
import sys
from dotenv import load_dotenv 
from ftplib import FTP, error_perm, error_temp, error_reply

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FTP_HOST = os.getenv('FTP_HOST')
FTP_USER = os.getenv('FTP_USER')
FTP_PASS = os.getenv('FTP_PASS')
LOCAL_ORDERS_DIR = os.getenv('LOCAL_ORDERS_DIR')

# remote FTP directories
REMOTE_ORDERS_DIR = '/out/orders'
REMOTE_ORDER_ARCHIVE_DIR = '/out/orders/archive' 
REMOTE_INVENTORY_DIR = '/in/inventory'

def connect_ftp():
   try:
       ftp = FTP(FTP_HOST)
       ftp.login(FTP_USER, FTP_PASS)
       logger.info(f"successfully connected to FTP server: {FTP_HOST}")
       return ftp
   except (error_perm, error_temp, error_reply, Exception) as e:
       logger.error(f"FTP connection error: {e}")
       return None

def download_files(ftp):
   downloaded_files = []
   try:
       ftp.cwd(REMOTE_ORDERS_DIR)
       files = ftp.nlst()
       logger.info(f"list of files in remote directory: {files}")
       
       csv_files = [f for f in files if f.endswith('.csv')]
       if not csv_files:
           return

       for file_name in csv_files:
           local_file_path = os.path.join(LOCAL_ORDERS_DIR, file_name)
           with open(local_file_path, 'wb') as local_file:
               ftp.retrbinary(f'RETR {file_name}', local_file.write)
           downloaded_files.append(file_name)
           logger.info(f"downloaded: {file_name}")

       return downloaded_files
   except Exception as e:
       logger.error(f"error during file download: {e}")
       return []

def upload_files(ftp, local_file_path, remote_file_name):
   try:
       ftp.cwd(REMOTE_INVENTORY_DIR)
       with open(local_file_path, 'rb') as local_file:
           ftp.storbinary(f'STOR {remote_file_name}', local_file)
   except Exception as e:
       logger.error(f"error during file upload: {e}")
       sys.exit(1)

def archive_files_on_ftp(ftp, files):
   try:
       try:
           ftp.cwd(REMOTE_ORDER_ARCHIVE_DIR) # cd to dir
       except error_perm:
           ftp.mkd(REMOTE_ORDER_ARCHIVE_DIR) # create archive dir if it doesn't exist

       ftp.cwd(REMOTE_ORDERS_DIR)
       for file_name in files:
           ftp.rename(file_name, f"{REMOTE_ORDER_ARCHIVE_DIR}/{file_name}") #move files from orders dir to archive dir
           logger.info(f"archived file on FTP: {file_name}")
   except Exception as e:
       logger.error(f"error archiving files on FTP: {e}")
       sys.exit(1)