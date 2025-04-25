import io
import pickle
import shutil
import re
import logging
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import streamlit as st
from datetime import datetime
from dateutil.parser import parse

from config.config import CREDENTIALS_PATH, TOKEN_PATH, DRIVE_FOLDER_ID
from utils.vectordb_utils import embed_single_file

class GoogleDriveService:
    """Google Drive service class, for handling interactions with Google Drive"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self):
        """Initialize Google Drive service"""
        self.creds = None
        self.service = None
        self.local_base_path = Path("data_base/knowledge_db")
        self.clean_cache()
        self.authenticate()
        
    @staticmethod
    def normalize_category_name(name: str) -> str:
        """
        Normalize category name, ensuring compliance with Chroma's naming requirements
        1. Convert to lowercase
        2. Replace spaces with underscores
        3. Remove illegal characters
        4. Ensure length is between 3 and 63
        5. Ensure it starts and ends with a letter or number
        """
        # Convert to lowercase
        name = name.lower()
        
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        
        # Only keep letters, numbers, underscores, and hyphens
        name = re.sub(r'[^a-z0-9_-]', '', name)
        
        # Ensure it starts and ends with a letter or number
        name = re.sub(r'^[^a-z0-9]+', '', name)
        name = re.sub(r'[^a-z0-9]+$', '', name)
        
        # If the name is too short, add a prefix
        if len(name) < 3:
            name = f"cat_{name}"
            
        # If the name is too long, truncate
        if len(name) > 63:
            name = name[:63]
            # Ensure the truncated name still ends with a letter or number
            name = re.sub(r'[^a-z0-9]+$', '', name)
            
        return name
        
    def clean_cache(self):
        """Clean cache files"""
        try:
            # Clean token
            if TOKEN_PATH.exists():
                TOKEN_PATH.unlink()
                logging.info("Token cache cleaned")
            
            # Clean Google API cache
            cache_dir = Path.home() / '.cache' / 'google-api-python-client'
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                logging.info("Google API cache cleaned")
                
        except Exception as e:
            logging.warning(f"Error cleaning cache: {str(e)}")

    def authenticate(self):
        """Handle Google Drive API authentication"""
        try:
            if TOKEN_PATH.exists():
                with open(TOKEN_PATH, 'rb') as token:
                    self.creds = pickle.load(token)
                    
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not CREDENTIALS_PATH.exists():
                        raise FileNotFoundError("client_secret.json file does not exist, please ensure the file is in the correct location")
                        
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(CREDENTIALS_PATH), self.SCOPES)
                    self.creds = flow.run_local_server(port=0)
                    
                # Save token for future use
                TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(TOKEN_PATH, 'wb') as token:
                    pickle.dump(self.creds, token)
                    
            self.service = build('drive', 'v3', credentials=self.creds)
            logging.info("Google Drive authentication successful")
            st.success("Google Drive authentication successful")
            
        except Exception as e:
            error_msg = f"Google Drive authentication failed: {str(e)}"
            logging.error(error_msg)
            st.error(error_msg)
            raise

    def verify_folder_access(self):
        """Verify if the specified Google Drive folder can be accessed"""
        try:
            folder = self.service.files().get(fileId=DRIVE_FOLDER_ID).execute()
            logging.info(f"Successfully accessed folder: {folder['name']}")
            return True, folder['name']
        except Exception as e:
            logging.error(f"Failed to access folder: {str(e)}")
            return False, None

    def download_file(self, service, file_id, local_path):
        """Download file to specified path"""
        try:
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            
            while not done:
                status, done = downloader.next_chunk()
                logging.info(f"Download progress: {int(status.progress() * 100)}%")
                
            fh.seek(0)
            with open(local_path, 'wb') as f:
                f.write(fh.read())
            logging.info(f"File downloaded successfully: {local_path}")
            return True
        except Exception as e:
            logging.error(f"File download failed: {str(e)}")
            return False

    def sync_folder_content(self, service, folder_id, local_folder_path, original_name):
        """Sync folder content"""
        try:
            # Create local folder
            local_folder_path.mkdir(parents=True, exist_ok=True)
            
            # Get all content in folder
            query = f"'{folder_id}' in parents and trashed=false"
            results = service.files().list(
                q=query,
                fields="files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            # Get list of existing files in local folder
            existing_files = set(f.name for f in local_folder_path.glob('*.*'))
            
            for item in results.get('files', []):
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Process subfolder
                    new_local_path = local_folder_path / item['name']
                    normalized_name = self.normalize_category_name(item['name'])
                    self.sync_folder_content(service, item['id'], new_local_path, item['name'])
                    
                elif item['mimeType'] in ['application/pdf', 'text/plain']:
                    # Process file
                    if item['name'] not in existing_files:
                        local_file_path = local_folder_path / item['name']
                        logging.info(f"Starting to download file: {item['name']}")
                        if self.download_file(service, item['id'], str(local_file_path)):
                            # Vectorize file, using normalized category name
                            category_name = self.normalize_category_name(original_name)
                            if embed_single_file(local_file_path, category_name):
                                logging.info(f"File vectorized successfully: {item['name']}")
                            else:
                                logging.warning(f"File vectorization failed: {item['name']}")
                
            return True
            
        except Exception as e:
            logging.error(f"Failed to sync folder content: {str(e)}")
            return False

    def sync_drive_files(self):
        """
        Synchronize files from Google Drive to local knowledge base.
        If a file already exists locally, it will be updated instead of creating a duplicate.
        """
        try:
            results = self.service.files().list(
                q="mimeType!='application/vnd.google-apps.folder'",
                fields="files(id, name, mimeType)"
            ).execute()
            files = results.get('files', [])
            
            for file in files:
                file_id = file['id']
                file_name = file['name']
                category = self.normalize_category_name(file_name)
                
                # Check if file already exists
                target_path = self.local_base_path / category / file_name
                
                # If file exists, compare modification times before updating
                if target_path.exists():
                    # Get local file's modification time
                    local_mtime = target_path.stat().st_mtime
                    
                    # Get Drive file's modification time
                    drive_file = self.service.files().get(
                        fileId=file_id, 
                        fields='modifiedTime'
                    ).execute()
                    drive_mtime = parse(drive_file['modifiedTime']).timestamp()
                    
                    # Skip if local file is newer
                    if local_mtime >= drive_mtime:
                        logging.info(f"Skipping {file_name} as local copy is up to date")
                        continue
                        
                # Download and save/update the file
                request = self.service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                # Ensure category directory exists
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save/update file
                with open(target_path, 'wb') as f:
                    f.write(fh.getvalue())
                
                logging.info(f"Successfully {'updated' if target_path.exists() else 'downloaded'} {file_name}")
                
            return True
            
        except Exception as e:
            logging.error(f"Error syncing files from Drive: {str(e)}")
            return False

def sync_from_drive():
    """
    Sync files from Google Drive to local knowledge base
    
    Returns:
        bool: Whether sync is successful
    """
    try:
        service = GoogleDriveService()
        return service.sync_drive_files()
    except Exception as e:
        error_msg = f"Google Drive sync failed: {str(e)}"
        logging.error(error_msg)
        st.error(error_msg)
        return False
