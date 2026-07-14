#!/usr/bin/env python3
"""
AnyDesk Configuration File Mover
Moves AnyDesk configuration files to backup folders in both Roaming and ProgramData locations.
"""

import os
import shutil
from pathlib import Path


def ensure_directory_exists(directory_path):
    """Create directory if it doesn't exist."""
    Path(directory_path).mkdir(parents=True, exist_ok=True)


def move_file(source_path, destination_dir):
    """Move a file from source to destination directory if it exists."""
    source = Path(source_path)
    if source.exists() and source.is_file():
        try:
            shutil.move(str(source), str(destination_dir))
            print(f"Moved: {source.name}")
            return True
        except Exception as e:
            print(f"Error moving {source.name}: {e}")
            return False
    else:
        print(f"File not found: {source_path}")
        return False


def main():
    """Main function to move AnyDesk configuration files."""
    # Set source and destination folders for the Roaming AnyDesk folder
    roaming_source = Path(os.environ.get('USERPROFILE', '')) / 'AppData' / 'Roaming' / 'AnyDesk'
    roaming_destination = roaming_source / 'old'
    
    # Set source and destination folders for the ProgramData AnyDesk folder
    program_data_source = Path('C:\\ProgramData\\AnyDesk')
    program_data_destination = program_data_source / 'old'
    
    # Files to move (user.conf is commented out in the original batch file)
    files_to_move = [
        # 'user.conf',  # Commented out in original batch file
        'service.conf',
        'system.conf'
    ]
    
    print("Starting AnyDesk configuration file backup...")
    print("-" * 50)
    
    # Process Roaming folder
    print(f"\nProcessing Roaming folder: {roaming_source}")
    if roaming_source.exists():
        ensure_directory_exists(roaming_destination)
        for filename in files_to_move:
            source_file = roaming_source / filename
            move_file(source_file, roaming_destination)
    else:
        print(f"Source folder not found: {roaming_source}")
    
    # Process ProgramData folder
    print(f"\nProcessing ProgramData folder: {program_data_source}")
    if program_data_source.exists():
        ensure_directory_exists(program_data_destination)
        for filename in files_to_move:
            source_file = program_data_source / filename
            move_file(source_file, program_data_destination)
    else:
        print(f"Source folder not found: {program_data_source}")
    
    print("-" * 50)
    print("\nFiles moved successfully from both locations!")
    
    # Pause (equivalent to batch file's pause command)
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()

