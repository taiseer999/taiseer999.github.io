import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'lib'))

from backup_manager import BackupManager

if __name__ == '__main__':
    manager = BackupManager()
    manager.run()
