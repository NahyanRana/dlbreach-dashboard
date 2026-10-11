@echo off
REM Serves this folder locally so the browser version can be tested before
REM publishing. Opening index.html directly from disk does not work; it
REM must be served over http. Close this window to stop the server.
REM Served to this computer only (127.0.0.1), not to the network.
cd /d "%~dp0"
echo Serving the browser version at http://127.0.0.1:8000 (this computer only)
echo Open that address in Chrome or Edge. Close this window to stop.
start "" http://127.0.0.1:8000
python -m http.server 8000 --bind 127.0.0.1
