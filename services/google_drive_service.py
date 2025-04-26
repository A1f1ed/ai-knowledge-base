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
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import streamlit as st
from datetime import datetime
from dateutil.parser import parse

from config.config import CREDENTIALS_PATH, TOKEN_PATH, DRIVE_FOLDER_ID, VECTOR_DRIVE_FOLDER_ID, KNOWLEDGE_BASE_PATH, VECTOR_DB_PATH
from utils.vectordb_utils import embed_single_file

class GoogleDriveService:
    """Google Drive service class, for handling interactions with Google Drive"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/drive.file']
    
    def __init__(self):
        """Initialize Google Drive service"""
        self.creds = None
        self.service = None
        self.local_base_path = KNOWLEDGE_BASE_PATH  # 使用配置文件中的路径
        self.vector_db_path = VECTOR_DB_PATH  # 使用配置文件中的路径
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
            # 首先检查 client_secret.json 是否存在
            if not CREDENTIALS_PATH.exists():
                error_msg = "client_secret.json 文件不存在，请确保文件已放置在正确位置"
                st.error(error_msg)
                raise FileNotFoundError(error_msg)

            # 尝试从 Streamlit secrets 获取凭证
            from config.config import get_google_creds
            creds_dict = get_google_creds()
            
            if creds_dict:
                # 使用 Streamlit secrets 中的凭证
                self.creds = Credentials.from_authorized_user_info(creds_dict)
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
            else:
                # 回退到本地文件认证
                if TOKEN_PATH.exists():
                    try:
                        with open(TOKEN_PATH, 'rb') as token:
                            self.creds = pickle.load(token)
                    except Exception as e:
                        st.warning(f"读取token文件失败，将重新进行认证: {str(e)}")
                        self.creds = None
                    
                if not self.creds or not self.creds.valid:
                    if self.creds and self.creds.expired and self.creds.refresh_token:
                        try:
                            self.creds.refresh(Request())
                        except Exception as e:
                            st.warning(f"刷新token失败，将重新进行认证: {str(e)}")
                            self.creds = None
                    
                    if not self.creds:
                        st.info("正在启动Google Drive认证流程...")
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(CREDENTIALS_PATH), self.SCOPES)
                        self.creds = flow.run_local_server(port=0)
                        
                        # 确保目录存在
                        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
                        
                        # 保存新的token
                        try:
                            with open(TOKEN_PATH, 'wb') as token:
                                pickle.dump(self.creds, token)
                            st.success("认证成功，token已保存")
                        except Exception as e:
                            st.warning(f"保存token失败，但不影响当前会话的使用: {str(e)}")
                
            self.service = build('drive', 'v3', credentials=self.creds)
            st.success("✅ Google Drive 认证成功！")
            
        except Exception as e:
            error_msg = f"Google Drive认证失败: {str(e)}"
            st.error(error_msg)
            logging.error(error_msg)
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
            st.write(f"开始同步文件夹: {original_name}")
            # Create local folder
            local_folder_path.mkdir(parents=True, exist_ok=True)
            st.write(f"已创建本地文件夹: {local_folder_path}")
            
            # Get all content in folder
            query = f"'{folder_id}' in parents and trashed=false"
            st.write("正在从Google Drive获取文件列表...")
            results = service.files().list(
                q=query,
                fields="files(id, name, mimeType, modifiedTime)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            st.write(f"找到 {len(files)} 个文件/文件夹")
            
            # Get list of existing files in local folder
            existing_files = {f.name: f.stat().st_mtime for f in local_folder_path.glob('*.*')}
            st.write(f"本地已有 {len(existing_files)} 个文件")
            
            synced_files = False
            for item in files:
                st.write(f"处理: {item['name']} ({item['mimeType']})")
                drive_modified_time = parse(item['modifiedTime']).timestamp()
                
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Process subfolder
                    new_local_path = local_folder_path / item['name']
                    normalized_name = self.normalize_category_name(item['name'])
                    st.write(f"发现子文件夹: {item['name']}")
                    if self.sync_folder_content(service, item['id'], new_local_path, item['name']):
                        synced_files = True
                    
                elif item['mimeType'] in ['application/pdf', 'text/plain']:
                    # Check if file needs to be updated
                    should_download = True
                    if item['name'] in existing_files:
                        local_modified_time = existing_files[item['name']]
                        if local_modified_time >= drive_modified_time:
                            st.write(f"跳过 {item['name']} - 本地文件已是最新")
                            should_download = False
                    
                    if should_download:
                        local_file_path = local_folder_path / item['name']
                        st.write(f"开始下载: {item['name']}")
                        if self.download_file(service, item['id'], str(local_file_path)):
                            # Vectorize file, using normalized category name
                            category_name = self.normalize_category_name(original_name)
                            st.write(f"开始向量化: {item['name']}")
                            if embed_single_file(local_file_path, category_name):
                                st.write(f"成功向量化: {item['name']}")
                                synced_files = True
                            else:
                                st.error(f"向量化失败: {item['name']}")
                else:
                    st.write(f"跳过不支持的文件类型: {item['name']} ({item['mimeType']})")
            
            return synced_files
            
        except Exception as e:
            st.error(f"同步文件夹内容时出错: {str(e)}")
            logging.error(f"Error syncing folder content: {str(e)}")
            return False

    def sync_drive_files(self):
        """
        Synchronize files from ggbond_knowledge folder and its subfolders
        """
        try:
            # 使用 session_state 来保持同步状态
            if 'sync_status' not in st.session_state:
                st.session_state.sync_status = 'not_started'
            
            # 创建进度条容器
            progress_container = st.empty()
            status_container = st.empty()
            
            # 首先找到 ggbond_knowledge 文件夹
            status_container.info("正在查找 ggbond_knowledge 文件夹...")
            
            # 打印文件夹ID用于调试
            status_container.info(f"使用的文件夹ID: {DRIVE_FOLDER_ID}")
            
            # 直接使用配置的文件夹ID
            try:
                folder = self.service.files().get(fileId=DRIVE_FOLDER_ID).execute()
                root_folder_id = DRIVE_FOLDER_ID
                status_container.success(f"直接访问文件夹成功: {folder['name']}")
            except Exception as e:
                status_container.error(f"直接访问文件夹失败: {str(e)}")
                # 尝试搜索文件夹
                folder_results = self.service.files().list(
                    q=f"name='ggbond_knowledge' and mimeType='application/vnd.google-apps.folder'",
                    fields="files(id, name)",
                    spaces='drive',
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                
                folder_files = folder_results.get('files', [])
                if not folder_files:
                    error_msg = "找不到 ggbond_knowledge 文件夹，请确保文件夹存在且有正确的访问权限"
                    status_container.error(error_msg)
                    logging.warning(error_msg)
                    return False
                
                root_folder_id = folder_files[0]['id']
                status_container.success(f"通过搜索找到文件夹: {folder_files[0]['name']}")
            
            # 获取所有子文件夹
            status_container.info("正在获取分类文件夹...")
            subfolder_results = self.service.files().list(
                q=f"'{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)",
                spaces='drive',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            subfolders = subfolder_results.get('files', [])
            if not subfolders:
                status_container.warning("在 ggbond_knowledge 中没有找到任何分类文件夹")
                return True
            
            status_container.success(f"找到 {len(subfolders)} 个分类文件夹")
            
            # 显示找到的所有分类文件夹
            for folder in subfolders:
                status_container.info(f"发现分类: {folder['name']}")
            
            files_processed = False
            
            # 创建进度条
            progress_bar = progress_container.progress(0)
            total_folders = len(subfolders)
            
            # 处理每个子文件夹
            for folder_idx, subfolder in enumerate(subfolders):
                subfolder_id = subfolder['id']
                category_name = subfolder['name']
                status_container.info(f"正在处理分类: {category_name} ({folder_idx + 1}/{total_folders})")
                
                # 更新进度条
                progress_bar.progress((folder_idx + 0.5) / total_folders)
                
                # 获取子文件夹中的文件
                file_results = self.service.files().list(
                    q=f"'{subfolder_id}' in parents and (mimeType='application/pdf' or mimeType='text/plain')",
                    fields="files(id, name, mimeType, modifiedTime)",
                    spaces='drive',
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                
                files = file_results.get('files', [])
                if not files:
                    status_container.info(f"分类 {category_name} 中没有文件")
                    continue
                
                status_container.success(f"在分类 {category_name} 中找到 {len(files)} 个文件")
                
                # 确保本地目录存在
                local_category_path = self.local_base_path / "ggbond_knowledge" / category_name
                local_category_path.mkdir(parents=True, exist_ok=True)
                
                # 处理每个文件
                for file_idx, file in enumerate(files):
                    file_id = file['id']
                    file_name = file['name']
                    drive_mtime = parse(file['modifiedTime']).timestamp()
                    
                    # 设置目标路径
                    target_path = local_category_path / file_name
                    
                    # 如果文件存在且是最新的，跳过
                    if target_path.exists():
                        local_mtime = target_path.stat().st_mtime
                        if local_mtime >= drive_mtime:
                            status_container.info(f"跳过 {file_name} - 本地副本已是最新")
                            continue
                    
                    # 下载文件
                    status_container.info(f"正在下载: {file_name}")
                    try:
                        request = self.service.files().get_media(fileId=file_id)
                        fh = io.BytesIO()
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while done is False:
                            status, done = downloader.next_chunk()
                            status_container.info(f"下载进度: {int(status.progress() * 100)}%")
                        
                        # 保存文件
                        fh.seek(0)
                        with open(target_path, 'wb') as f:
                            f.write(fh.getvalue())
                        
                        status_container.success(f"已{'更新' if target_path.exists() else '下载'} {file_name}")
                        
                        # 处理文件并创建向量嵌入
                        status_container.info(f"开始向量化: {file_name}")
                        if embed_single_file(target_path, category_name):
                            status_container.success(f"已成功创建 {file_name} 的向量嵌入")
                            files_processed = True
                        else:
                            status_container.error(f"创建 {file_name} 的向量嵌入失败")
                    except Exception as e:
                        status_container.error(f"处理文件 {file_name} 时出错: {str(e)}")
                        continue
                
                # 更新进度条
                progress_bar.progress((folder_idx + 1) / total_folders)
            
            # 如果有文件被处理，同步向量存储到 Drive
            if files_processed:
                status_container.info("正在同步向量存储到 Drive...")
                for subfolder in subfolders:
                    category_name = subfolder['name']
                    if self.sync_vector_store(category_name):
                        status_container.success(f"分类 {category_name} 的向量存储已成功同步到 Drive")
                    else:
                        status_container.error(f"同步分类 {category_name} 的向量存储失败")
            
            # 完成同步
            progress_bar.progress(1.0)
            status_container.success("同步完成！")
            return True
            
        except Exception as e:
            error_msg = f"同步文件时出错: {str(e)}"
            logging.error(error_msg)
            st.error(error_msg)
            return False

    def sync_vector_store(self, category: str):
        """Sync vector store to Google Drive"""
        try:
            vector_store_path = self.vector_db_path / category
            if not vector_store_path.exists():
                logging.warning(f"No vector store found for category: {category}")
                return False

            # 创建压缩文件
            archive_path = f"{category}_vector_store.zip"
            shutil.make_archive(f"{category}_vector_store", 'zip', vector_store_path)

            # 上传到专门的向量库文件夹
            file_metadata = {
                'name': f"{category}_vector_store.zip",
                'parents': [VECTOR_DRIVE_FOLDER_ID]  # 使用向量库专用文件夹
            }

            # 检查是否已存在
            results = self.service.files().list(
                q=f"name='{file_metadata['name']}' and parents='{VECTOR_DRIVE_FOLDER_ID}'",
                fields="files(id)"
            ).execute()
            files = results.get('files', [])

            media = MediaIoBaseUpload(archive_path, mimetype='application/zip')
            
            if files:
                # 更新现有文件
                file = self.service.files().update(
                    fileId=files[0]['id'],
                    media_body=media
                ).execute()
            else:
                # 创建新文件
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media
                ).execute()

            # 清理临时文件
            Path(archive_path).unlink()
            logging.info(f"Vector store synced successfully for category: {category}")
            return True

        except Exception as e:
            logging.error(f"Failed to sync vector store: {str(e)}")
            return False

    def load_vector_store(self, category: str) -> bool:
        """Load vector store from Google Drive"""
        try:
            # 查找文件
            results = self.service.files().list(
                q=f"name='{category}_vector_store.zip' and parents='{DRIVE_FOLDER_ID}'",
                fields="files(id, name)"
            ).execute()
            files = results.get('files', [])

            if not files:
                logging.info(f"No vector store found for category: {category}")
                return False

            file_id = files[0]['id']
            vector_store_path = self.vector_db_path / category
            archive_path = f"{category}_vector_store.zip"

            # 下载文件
            request = self.service.files().get_media(fileId=file_id)
            with open(archive_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()

            # 解压文件
            vector_store_path.mkdir(parents=True, exist_ok=True)
            shutil.unpack_archive(archive_path, vector_store_path)

            # 清理临时文件
            Path(archive_path).unlink()
            
            logging.info(f"Vector store loaded successfully for category: {category}")
            return True

        except Exception as e:
            logging.error(f"Failed to load vector store: {str(e)}")
            return False

    def upload_file(self, source_file_path, category: str):
        """
        Upload file to Google Drive with support for multi-level category structure.
        
        Args:
            source_file_path: Path to the source file to upload
            category: Category path, can include multiple levels (e.g. 'category/subcategory')
            
        Returns:
            tuple: (status, drive_id) where status is a boolean indicating success,
                   and drive_id is either the file id on success or error message on failure
        """
        try:
            # Open file to upload
            with open(source_file_path, 'rb') as f:
                file_content = f.read()
            
            # Get the filename from the path
            filename = Path(source_file_path).name
            
            # Split category into parts for multi-level structure
            category_parts = category.split('/')
            
            # Start with the main knowledge base folder
            parent_id = DRIVE_FOLDER_ID
            current_path = ""
            
            # Create each folder in the path if it doesn't exist
            for part in category_parts:
                if not part:  # Skip empty parts
                    continue
                    
                current_path += f"/{part}" if current_path else part
                logging.info(f"Checking/creating folder: {current_path}")
                
                # Check if folder exists at this level
                query = f"name='{part}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                results = self.service.files().list(
                    q=query,
                    fields="files(id, name)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                
                files = results.get('files', [])
                if files:
                    # Folder exists, use as next parent
                    parent_id = files[0]['id']
                else:
                    # Create new folder at this level
                    folder_metadata = {
                        'name': part,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [parent_id]
                    }
                    folder = self.service.files().create(
                        body=folder_metadata,
                        fields='id',
                        supportsAllDrives=True
                    ).execute()
                    
                    logging.info(f"Created new folder: {part} in {current_path}")
                    parent_id = folder['id']
            
            # Now parent_id contains the ID of the deepest folder in the path
            
            # Prepare file metadata
            file_metadata = {
                'name': filename,
                'parents': [parent_id]
            }

            # Create media object
            fh = io.BytesIO(file_content)
            media = MediaIoBaseUpload(
                fh,
                mimetype='application/octet-stream',
                resumable=True
            )

            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            logging.info(f"File uploaded successfully: {filename} to {category}")
            return True, file['id']

        except Exception as e:
            error_msg = f"Failed to upload file: {str(e)}"
            logging.error(error_msg)
            return False, error_msg

def sync_from_drive():
    """Sync files from Google Drive"""
    try:
        st.write("开始同步Google Drive...")
        drive_service = GoogleDriveService()
        
        # 验证文件夹访问权限
        st.write("验证文件夹访问权限...")
        access_ok, folder_name = drive_service.verify_folder_access()
        if not access_ok:
            st.error("无法访问Google Drive文件夹")
            return False
        
        st.write(f"成功访问文件夹: {folder_name}")
            
        # 同步文件
        if drive_service.sync_drive_files():
            st.success("文件同步成功！")
            return True
        else:
            st.error("同步失败，请检查错误信息")
            return False
            
    except Exception as e:
        st.error(f"同步失败: {str(e)}")
        logging.error(f"Sync failed: {str(e)}")
        return False
