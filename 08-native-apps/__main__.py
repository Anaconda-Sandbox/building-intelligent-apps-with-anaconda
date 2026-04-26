"""
src/lightcurve/__main__.py

Entry point for the Lightcurve Explorer Toga app.
Briefcase calls this module when the app launches on every platform.
"""

from lightcurve.app import main

if __name__ == "__main__":
    main().main_loop()
