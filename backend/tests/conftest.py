import os
import sys

if sys.platform == "win32":
    for gtk_path in [r"C:\Users\rajpu\GTK3\runtime_bin", r"C:\Program Files\GTK3-Runtime Win64\bin"]:
        if os.path.exists(gtk_path):
            os.environ["PATH"] = gtk_path + ";" + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(gtk_path)
                except Exception:
                    pass
