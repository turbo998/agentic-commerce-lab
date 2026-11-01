# Web IQ Browse passages and the Azure account template (2026-11-01)

🌐 **Language / 语言导航**: **[中文](2026-11-01-webiq-azure-browse-passage.md)** | **English (current)** | **[2026-10-26 sealed demo](2026-10-26-webiq-agentic-commerce-demo.en.md)**

## Finding

The existing Agentic Commerce × Web IQ workbench (`lab/webiq_commerce_demo.py`, sealed 2026-10-26) stays the runnable demo. This note only adds the official Browse contract and a deploy-on-demand template. No Azure resource was created, and the sealed metrics were not re-measured.

The official [Browse REST API](https://learn.microsoft.com/en-us/web-iq/reference/browse) (docs dated 2026-10-30) recommends `contentFormat=passage` for grounding. A passage request requires a non-blank `query` of 1..1000 characters. `text` / `html` / `markdown` remain full-document formats and need that entitlement. Browse itself is still AppID-gated; self-service access is not generally available.

## Azure

A read-only Resource Graph query of the signed-in Microsoft tenant found **zero** `Microsoft.WebIQ/accounts`. Web IQ requires a paid subscription, and Azure credits cannot create the account. This change does not run `az resource create` and does not hardcode a subscription ID.

Deploy-on-demand template: [`infra/webiq-account.bicep`](../../infra/webiq-account.bicep)

- Type: `Microsoft.WebIQ/accounts@2026-06-01-preview`
- `location=global`, `kind=WebIQ.Grounding`, `sku=G3`
- `properties.statisticsEnabled=false`
- Account name is a deploy-time parameter

[`scripts/webiq-account-dry-run.ps1`](../../scripts/webiq-account-dry-run.ps1) prints the contract and does not create a resource.

## Engine delta

- `BROWSE_CONTENT_FORMATS` now includes `passage`.
- `browse(..., query=)` rejects a blank query for `passage` and rejects any query longer than 1000 characters.
- Offline fixtures select a passage around the query and do not fabricate a return deadline when evidence is missing.
- `ground_return_policy_passage()` covers the return-policy scenario with passage grounding.
- The lab default for full-document Browse remains `markdown`, so the 2026-10-26 sealed scenarios keep their contract.

Sealed figures (P95 240ms, 18/18, 12/12, 1.52s vs 4.18s) stay labeled `sealed_demo` / 2026-10-26. They are not a new measurement.

## Publish

The personal site gets a new path and does not edit the homepage: `workshops/webiq-azure/`. Live calls remain optional via `--live` and `WEBIQ_API_KEY`. The default demo runs on offline fixtures.
