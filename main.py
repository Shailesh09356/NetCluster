"""
NetCluster - Main entry point
Launches master or worker node
"""
import sys
import argparse


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='NetCluster - Distributed Network Security Platform')
    parser.add_argument('--master', action='store_true', help='Start master node')
    parser.add_argument('--worker', action='store_true', help='Start worker node')
    
    args = parser.parse_args()
    
    if args.master:
        # Start master node (backend + UI)
        from netcluster.core.master_backend import MasterBackend
        from netcluster.ui.app import LauncherWindow
        from PyQt5.QtWidgets import QApplication
        from netcluster.ui.theme import get_global_app_style
        
        # Initialize backend
        backend = MasterBackend()
        backend.start_server()
        
        # Start UI
        app = QApplication(sys.argv)
        app.setStyleSheet(get_global_app_style())
        
        # Create master window (will be launched from launcher)
        # For now, just show launcher
        win = LauncherWindow()
        win.show()
        
        # Store backend reference for later use
        # Frontend can access it via module-level variable or singleton pattern
        
        sys.exit(app.exec_())
    
    elif args.worker:
        # Start worker node (backend + UI)
        from netcluster.core.worker_backend import WorkerBackend
        from netcluster.core.worker import WorkerNodeWindow
        from PyQt5.QtWidgets import QApplication
        from netcluster.ui.theme import get_global_app_style
        
        # Initialize backend
        backend = WorkerBackend()
        
        # Start UI
        app = QApplication(sys.argv)
        app.setStyleSheet(get_global_app_style())
        
        # Create worker window
        win = WorkerNodeWindow()
        win.show()
        
        # Store backend reference
        win.backend = backend
        
        sys.exit(app.exec_())
    
    else:
        # Default: show launcher
        from netcluster.ui.app import main as ui_main
        ui_main()


if __name__ == "__main__":
    main()
