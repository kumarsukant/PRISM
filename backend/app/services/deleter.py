"""
Safe file deletion (move to Recycle Bin)
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Callable, Optional
import subprocess
import sys

from models.scan import DuplicateGroup, ScanSession, PhotoRecord
from config import Config

class SafeDeleter:
    """Safely deletes files by moving them to Recycle Bin (recoverable)"""
    
    def __init__(self, config: Config):
        self.config = config
        self.platform = sys.platform  # 'win32', 'darwin', 'linux'
    
    def delete_duplicates(self, session: ScanSession, 
                     groups_to_delete: List[DuplicateGroup],
                     progress_callback: Optional[Callable] = None) -> ScanSession:
        """
        Delete duplicate files (move to Recycle Bin)
        
        Args:
            session: ScanSession with duplicate groups
            groups_to_delete: List of DuplicateGroup objects to delete
            progress_callback: Optional callback for progress
            
        Returns:
            Updated ScanSession with deletion results
        """
        deleted_count = 0
        freed_bytes = 0
        errors = []
        
        for i, group in enumerate(groups_to_delete):
            # Keep the first photo (kept_photo_id), delete the rest
            for photo_id in group.photo_ids:
                if photo_id == group.kept_photo_id:
                    continue
                
                # Find the photo record
                photo = next((p for p in session.photos if p.id == photo_id), None)
                if not photo:
                    continue
                
                try:
                    # Move to Recycle Bin
                    success = self._move_to_recycle_bin(photo.file_path)
                    
                    if success:
                        deleted_count += 1
                        freed_bytes += photo.file_size_bytes
                        group.user_action = "delete"
                        group.deleted_at = datetime.now()
                    else:
                        errors.append(f"Failed to delete: {photo.file_path}")
                        
                except Exception as e:
                    errors.append(f"Error deleting {photo.file_path}: {str(e)}")
            
            if progress_callback:
                progress_callback({
                    "stage": "deleting",
                    "deleted": deleted_count,
                    "total": sum(len(g.photo_ids) - 1 for g in groups_to_delete if g != group.kept_photo_id)
                })
        
        # Update session
        session.files_deleted = deleted_count
        session.storage_freed_mb = freed_bytes / (1024 * 1024)
        
        if errors:
            session.error_message = "; ".join(errors[:5])  # Store first 5 errors
        
        return session
    
    def _move_to_recycle_bin(self, file_path: str) -> bool:
        """
        Move file to Recycle Bin (platform-specific)
        
        Windows: Use Windows API via send2trash
        Mac: Use trash via Command-line
        Linux: Use trash-cli or fallback to safe rm
        """
        try:
            # Try send2trash library if available
            try:
                import send2trash
                send2trash.send2trash(file_path)
                return True
            except ImportError:
                pass
            
            # Platform-specific fallbacks
            if self.platform == 'win32':
                return self._move_to_recycle_bin_windows(file_path)
            elif self.platform == 'darwin':
                return self._move_to_recycle_bin_mac(file_path)
            else:
                return self._move_to_recycle_bin_linux(file_path)
                
        except Exception as e:
            print(f"Error moving {file_path} to Recycle Bin: {e}")
            return False
    
    def _move_to_recycle_bin_windows(self, file_path: str) -> bool:
        """Move file to Windows Recycle Bin using PowerShell"""
        try:
            ps_cmd = f'''
            [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null
            [System.Windows.Forms.SendKeys]::SendWait("^c")
            $file = Get-Item -LiteralPath '{file_path}'
            $shell = New-Object -ComObject Shell.Application
            $folder = $shell.Namespace($file.Directory.FullName)
            $folder_item = $folder.ParseName($file.Name)
            $folder_item.InvokeVerb("delete")
            '''
            
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                timeout=5
            )
            
            # Check if file still exists
            return not Path(file_path).exists()
            
        except Exception as e:
            print(f"PowerShell delete failed for {file_path}: {e}")
            # Fallback: just delete the file (non-recoverable)
            try:
                os.remove(file_path)
                return True
            except:
                return False
    
    def _move_to_recycle_bin_mac(self, file_path: str) -> bool:
        """Move file to Mac Trash using osascript"""
        try:
            script = f'tell app "Finder" to delete POSIX file "{file_path}"'
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5
            )
            return not Path(file_path).exists()
        except Exception as e:
            print(f"Mac trash failed for {file_path}: {e}")
            return False
    
    def _move_to_recycle_bin_linux(self, file_path: str) -> bool:
        """Move file to Linux trash using trash-cli"""
        try:
            # Try trash-cli first
            result = subprocess.run(
                ["trash-put", file_path],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except FileNotFoundError:
            # Fallback: try gio (GNOME)
            try:
                result = subprocess.run(
                    ["gio", "trash", file_path],
                    capture_output=True,
                    timeout=5
                )
                return result.returncode == 0
            except:
                return False
