"""Custom collectstatic command that compiles the React/Vite frontend before collecting static files."""

import os
import subprocess
from django.contrib.staticfiles.management.commands import collectstatic

class Command(collectstatic.Command):
    """
    Custom collectstatic command that automatically builds the React/Vite frontend
    if the source code is present, ensuring frontend changes take effect immediately.
    """
    
    def handle(self, *args, **options):
        """
        Main execution handler for the command.
        
        Checks if the React/Vite frontend source directory exists, installs dependencies
        if necessary (missing node_modules), runs npm run build, and then executes
        the standard Django collectstatic logic.
        
        Args:
            *args: Variable length argument list.
            **options: Arbitrary keyword arguments.
        """
        # Locate the frontend directory
        app_root = os.environ.get('RENGINE_HOME', '/usr/src/app')
        frontend_dir = os.path.join(app_root, 'frontend')
        
        if os.path.exists(frontend_dir):
            self.stdout.write("Building React/Vite frontend inside container...")
            try:
                # Install node_modules if not present
                node_modules_path = os.path.join(frontend_dir, 'node_modules')
                if not os.path.exists(node_modules_path):
                    self.stdout.write("node_modules not found. Running npm install...")
                    subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
                
                # Execute production build
                subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
                self.stdout.write("React/Vite frontend built successfully!")
            except Exception as e:
                self.stderr.write(f"Failed to build React/Vite frontend: {e}")
        else:
            self.stdout.write("Frontend directory not found. Skipping frontend build.")
            
        # Execute the default Django collectstatic logic
        super().handle(*args, **options)
