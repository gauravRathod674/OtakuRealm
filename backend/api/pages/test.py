import shutil
import os

folder = os.path.expandvars(r"%appdata%\undetected_chromedriver")

if os.path.exists(folder):
    shutil.rmtree(folder)
    print("🧹 Cache cleared. Run again to let it rebuild.")
else:
    print("📂 Folder already doesn't exist.")
