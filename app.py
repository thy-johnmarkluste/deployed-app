"""
Domain Connector — Application entry point.
Initializes the Tkinter root and hands off to the MainController (MVC).
"""
import tkinter as tk
from controllers.main_controller import MainController
from models.logger import setup_logging


def main():
    # Initialize logging when application starts
    setup_logging()
    
    root = tk.Tk()
    _app = MainController(root)  # noqa: F841  – prevent GC
    root.mainloop()


if __name__ == "__main__":
    main()
