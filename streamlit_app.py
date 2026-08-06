"""Deployment entrypoint for Streamlit Community Cloud.

Streamlit Cloud auto-detects ``streamlit_app.py`` at the repo root, so this is
the file to point a deployment at. It simply launches the real dashboard.
"""

from edgepulse.dashboard.app import main

main()
