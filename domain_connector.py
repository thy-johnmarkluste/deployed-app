"""
Domain Connector - Server Subdomain Manager
Refactored into MVC.  Run ``python app.py`` directly, or use this file
as a backwards-compatible entry point.
"""
from app import main  # noqa: F401  – re-export for convenience


if __name__ == "__main__":
    main()

