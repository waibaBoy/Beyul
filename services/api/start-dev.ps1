$ErrorActionPreference = "Stop"

$apiRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $apiRoot

# Keep the local app package ahead of vendored site-packages so uvicorn imports
# services/api/app instead of vendor_pkgs/app.
$env:PYTHONPATH = "$apiRoot;$apiRoot\vendor_pkgs"

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
