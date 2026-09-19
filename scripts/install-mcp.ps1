$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
& node (Join-Path $PSScriptRoot "install-mcp.mjs") @args
exit $LASTEXITCODE
