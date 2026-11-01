// Deploy-on-demand Microsoft Web IQ account.
// Official contract: https://learn.microsoft.com/en-us/web-iq/get-started/deploy-azure-cli
// Do not apply this against a Microsoft corporate tenant or an Azure-credits subscription.
// Web IQ requires a paid subscription. This file does not create a resource by itself.

@description('Globally unique Web IQ account name. Supply this at deploy time; do not hardcode a subscription.')
param accountName string

@description('Web IQ accounts use the global location.')
param location string = 'global'

@description('Official quickstart sets statisticsEnabled to false.')
param statisticsEnabled bool = false

resource account 'Microsoft.WebIQ/accounts@2026-06-01-preview' = {
  name: accountName
  location: location
  kind: 'WebIQ.Grounding'
  sku: {
    name: 'G3'
  }
  properties: {
    statisticsEnabled: statisticsEnabled
  }
}

output accountId string = account.id
output endpoint string = 'https://api.microsoft.ai'
