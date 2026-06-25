import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union
from src.core.globals import (
                             INDICATORS_DIR,
                             SCANNER_DIR,
                             TICKERS_DIR,
                             SCREENSHOTS_DIR
                            )

class DataManager:

    def __init__(self, core):
        """Initialize with paths from global variables"""
        self.indicators_dir  = Path(core['INDICATORS_DIR'])
        self.scanner_dir     = Path(core['SCANNER_DIR'])
        self.tickers_dir     = Path(core['TICKERS_DIR'])
        self.screenshots_dir = Path(core['SCREENSHOTS_DIR'])

    # Core File Operations --------------------------------

    def save_version(self, buffer_dir: Path, version_name: str, pattern: str = "*.csv") -> None:
        """Save current buffer files to a version folder"""
        version_dir = buffer_dir / version_name
        version_dir.mkdir(exist_ok=True)

        # Clear existing version files
        for f in version_dir.glob('*'):
            f.unlink()

        # Copy matching files
        for f in buffer_dir.glob(pattern):
            if f.is_file():
                shutil.copy2(f, version_dir)
        print(f"  💾 Saved version '{version_name}'")

    def load_version(self, buffer_dir: Path, version_name: str, pattern: str = "*.csv") -> None:
        """Load version files into buffer"""
        version_dir = buffer_dir / version_name
        if not version_dir.exists():
            raise FileNotFoundError(f"Version '{version_name}' not found")
        
        self.clear_buffer(buffer_dir, pattern)
        for f in version_dir.glob(pattern):
            shutil.copy2(f, buffer_dir)
        print(f"  🔄 Loaded version '{version_name}\n'")

    def clear_buffer(self, buffer_dir: Path, pattern: str = "*.csv") -> None:
        """Clear buffer files matching pattern without counting"""
        # Special handling for screenshots directory
        if buffer_dir == self.screenshots_dir:
            # For screenshots, clear multiple image formats
            image_patterns = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']
            for img_pattern in image_patterns:
                for f in buffer_dir.glob(img_pattern):
                    if f.is_file():
                        f.unlink()
        else:
            # For other directories, use the provided pattern
            for f in buffer_dir.glob(pattern):
                if f.is_file():
                    f.unlink()
        
        print(f"\n  🧹 Cleared buffer files\n")

    # Specialized Operations -----------------------------

    def indicators_conf_dir(self, ind_conf) -> Path:
        """Return path for a specific ind_conf subdir"""
        return self.indicators_dir / f"ind_conf_{ind_conf}"

    def save_indicators(self, version_name: str, ind_conf=None) -> None:
        """Save current indicators (optionally from a specific conf subdir)"""
        source_dir = self.indicators_conf_dir(ind_conf) if ind_conf is not None else self.indicators_dir
        self.save_version(source_dir, version_name)

    def save_scans(self, version_name: str) -> None:
        """Save current scans"""
        self.save_version(self.scanner_dir, version_name, "scan_*.csv")

    def save_tickers(self, version_name: str) -> None:
        """Save current tickers"""
        self.save_version(self.tickers_dir, version_name)

    def clear_screenshots(self) -> None:
        """Clear screenshot files from screenshots directory"""
        print("\n=== CLEAR SCREENSHOTS ===\n")
        self.clear_buffer(self.screenshots_dir, "*.png")

    def clear_ind_conf(self, ind_conf=None) -> None:
        """Clear a specific ind_conf subdir, or all conf subdirs if ind_conf is None"""
        if ind_conf is not None:
            conf_dir = self.indicators_conf_dir(ind_conf)
            if conf_dir.exists():
                self.clear_buffer(conf_dir)
        else:
            for conf_dir in self.indicators_dir.glob("ind_conf_*/"):
                self.clear_buffer(conf_dir)

    def clear_all_buffers(self) -> None:
        """Clear all working directories while preserving versions"""
        print()
        self.clear_buffer(self.tickers_dir)
        self.clear_ind_conf()
        self.clear_buffer(self.scanner_dir, "scan_*.csv")
        self.clear_buffer(self.screenshots_dir, "*.png")
        print("\n  ✨ All buffers cleared (versions preserved)")

    def format_duration(self, seconds):
        """Convert seconds to human-readable string (hours, minutes, seconds)"""
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.2f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.2f} hours"

    # Version Management --------------------------------

    def list_versions(self, 
                      buffer_dir: Union[Path, str], 
                      version_type: str = "Versions", 
                      limit: int = 10) -> List[str]:
        """List available versions with pretty printing"""
        if isinstance(buffer_dir, str):
            buffer_dir = getattr(self, buffer_dir)
        
        versions = sorted([d.name for d in buffer_dir.iterdir() if d.is_dir()], reverse=True)
        
        print(f"\n  📚 {version_type} ({len(versions)}):\n")
        for i, version in enumerate(versions[:limit]):
            print(f"  {i+1}. {version}")
        if len(versions) > limit:
            print(f"  ... + {len(versions) - limit} more")
        print()
        
        return versions

    def delete_version(self, buffer_dir: Path, version_name: str) -> None:
        """Delete specific version"""
        version_dir = buffer_dir / version_name
        if not version_dir.exists():
            raise FileNotFoundError(f"Version '{version_name}' not found")
        
        shutil.rmtree(version_dir)
        print(f"\n  🗑️ Deleted version '{version_name}'\n")

    def delete_all_versions(self, buffer_dir: Path, confirm: bool = True) -> int:
        """Delete all versions, returns count deleted"""
        versions = [d for d in buffer_dir.iterdir() if d.is_dir()]
        if not versions:
            print("  No versions to delete")
            return 0
            
        if confirm:
            print(f"  ⚠️ This will delete {len(versions)} versions:")
            for v in versions: print(f"  - {v.name}")
            if input("\n  Type 'DELETE' to confirm: ").upper() != "DELETE":
                print("Operation cancelled")
                return 0
        
        for v in versions: shutil.rmtree(v)
        print(f"  🔥 Deleted {len(versions)} versions")
        return len(versions)

    # Listing Functions --------------------------------

    def list_files(self, directory: Union[Path, str], pattern: str = "*", 
                  limit: int = 10, sort_by: str = "mtime") -> List[Path]:
        """List files in directory with various options"""
        if isinstance(directory, str):
            directory = getattr(self, directory)
            
        files = list(directory.glob(pattern))
        
        if sort_by == "mtime":
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        elif sort_by == "name":
            files.sort(key=lambda f: f.name)
            
        return files[:limit] if limit else files

    def list_scans(self, limit: int = 10) -> None:
        """List scan files in buffer with nice formatting"""
        all_scans = sorted(self.scanner_dir.glob("scan_*.csv"))
        total_scans = len(all_scans)
        scans_to_show = all_scans[:limit]
        
        print(f"\n  SCANS in buffer (Total: {total_scans}, Showing first {limit}):\n")
        for i, scan in enumerate(scans_to_show, 1):
            print(f"  {i}. {scan.name}")
        if total_scans > limit:
            print(f"\n  ... + {total_scans - limit} more")
        print()

    def list_ind(self, limit: int = 10) -> None:
        """List indicator conf subdirs and their file counts"""
        conf_dirs = sorted(self.indicators_dir.glob("ind_conf_*/"))
        if not conf_dirs:
            print(f"\n  No indicator conf subdirs found in {self.indicators_dir}")
            return
        print(f"\n  INDICATOR BUFFERS ({len(conf_dirs)} conf(s)):\n")
        for conf_dir in conf_dirs:
            files = sorted(conf_dir.glob("*.csv"))
            total = len(files)
            print(f"  [{conf_dir.name}]  {total} file(s)")
            for f in files[:limit]:
                print(f"    {f.name}")
            if total > limit:
                print(f"    ... and {total - limit} more")
        print()

    def list_tickers(self, limit: int = 10, timeframe: Optional[str] = None) -> None:
        """List ticker files in buffer with nice formatting
        
        Parameters:
            limit: Maximum number of files to display
            timeframe: Optional filter for specific timeframe (e.g., 'daily', 'weekly')
        """
        pattern = "*.csv" if timeframe is None else f"*_{timeframe}.csv"
        all_tickers = sorted(self.tickers_dir.glob(pattern))
        total_tickers = len(all_tickers)
        tickers_to_show = all_tickers[:limit]
        
        timeframe_label = f" ({timeframe})" if timeframe else ""
        print(f"\n  TICKERS in buffer{timeframe_label} (Total: {total_tickers}, Showing first {limit}):\n")
        for i, ticker in enumerate(tickers_to_show, 1):
            print(f"  {i}. {ticker.name}")
        if total_tickers > limit:
            print(f"\n  ... + {total_tickers - limit} more")
        print()

    def list_screenshots(self, limit: int = 10) -> None:
        """List screenshot files in buffer with nice formatting"""
        # Get all image files
        screenshots = []
        image_patterns = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp']
        
        for pattern in image_patterns:
            screenshots.extend(self.screenshots_dir.glob(pattern))
        
        # Sort by modification time (newest first)
        screenshots.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        total_screenshots = len(screenshots)
        screenshots_to_show = screenshots[:limit]
        
        print(f"\n  Screenshots in buffer (Total: {total_screenshots}, Showing first {limit}):\n")
        
        if total_screenshots == 0:
            print("  No screenshots found")
            print()
            return
        
        for i, screenshot in enumerate(screenshots_to_show, 1):
            # Get file info
            size_bytes = screenshot.stat().st_size
            mtime = datetime.fromtimestamp(screenshot.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            
            # Convert size to appropriate unit
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes/1024:.1f} KB"
            else:
                size_str = f"{size_bytes/(1024*1024):.2f} MB"
            
            print(f"  {i}. {screenshot.name} ({size_str}, {mtime})")
        
        if total_screenshots > limit:
            print(f"\n  ... + {total_screenshots - limit} more")
        
        print(f"\n  Directory: {self.screenshots_dir}")
        print()

# Create instance of Class to export
dm = DataManager({
    'INDICATORS_DIR': INDICATORS_DIR,
    'SCANNER_DIR': SCANNER_DIR,
    'TICKERS_DIR': TICKERS_DIR,
    'SCREENSHOTS_DIR': SCREENSHOTS_DIR
})
