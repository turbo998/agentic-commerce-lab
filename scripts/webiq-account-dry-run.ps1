# Dry-run printer for infra/webiq-account.bicep.
# This script never calls az resource create or az deployment.

param(
    [Parameter(Mandatory = $true)]
    [string] $AccountName,
    [string] $ResourceGroup = "<resource-group>",
    [string] $SubscriptionId = "<subscription-id>"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$bicep = Join-Path $repoRoot "infra\webiq-account.bicep"
if (-not (Test-Path $bicep)) {
    throw "Missing $bicep"
}

Write-Output "Web IQ deploy dry run only. No Azure resource will be created."
Write-Output "Paid subscription required. Azure credits do not work."
Write-Output "Subscription placeholder: $SubscriptionId"
Write-Output "Resource group placeholder: $ResourceGroup"
Write-Output "Account name: $AccountName"
Write-Output "Template: $bicep"
Write-Output "Contract: Microsoft.WebIQ/accounts, api-version 2026-06-01-preview, location global, kind WebIQ.Grounding, sku G3, statisticsEnabled false."
Write-Output "When an authorized paid subscription is available, deploy the Bicep yourself. Do not run this script expecting a create."
