# core/drive_controller.py

from services.google_drive_service import GoogleDriveService

def sync_drive_files():
    """sync Google Drive files, return whether it is successful"""
    try:
        service = GoogleDriveService()
        service.authenticate()
        return service.sync_drive_files()
    except Exception as e:
        print(f"❌ Google Drive sync failed: {str(e)}")
        return False


def is_drive_accessible():
    """check if Google Drive is accessible"""
    try:
        service = GoogleDriveService()
        service.authenticate()
        access, _ = service.verify_folder_access()
        return access
    except Exception as e:
        print(f"⚠️ cannot check Google Drive access permission: {str(e)}")
        return False
    
__all__ = ["sync_drive_files", "is_drive_accessible"]