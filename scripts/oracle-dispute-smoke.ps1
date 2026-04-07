param(
  [string]$ApiBaseUrl = "http://localhost:8000",
  [string]$OracleSecret = "",
  [string]$SlugPrefix = "oracle-smoke",
  [string]$AdminUserId = "",
  [string]$AdminUsername = "smoke_admin",
  [string]$AdminDisplayName = "Smoke Admin",
  [string]$UserAId = "",
  [string]$UserAUsername = "smoke_user_a",
  [string]$UserADisplayName = "Smoke User A",
  [string]$UserBId = "",
  [string]$UserBUsername = "smoke_user_b",
  [string]$UserBDisplayName = "Smoke User B",
  [switch]$SkipOrders
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($OracleSecret)) {
  if (-not [string]::IsNullOrWhiteSpace($env:ORACLE_CALLBACK_SECRET)) {
    $OracleSecret = $env:ORACLE_CALLBACK_SECRET
  } elseif (-not [string]::IsNullOrWhiteSpace($env:SATTA_ORACLE_CALLBACK_SECRET)) {
    $OracleSecret = $env:SATTA_ORACLE_CALLBACK_SECRET
  } else {
    $OracleSecret = "dev-oracle-secret"
  }
}

function ConvertTo-JsonBody {
  param([Parameter(ValueFromPipeline = $true)]$Value)
  process {
    return ($Value | ConvertTo-Json -Depth 12)
  }
}

function Invoke-SattaApi {
  param(
    [string]$Method = "GET",
    [string]$Path,
    [hashtable]$Headers = @{},
    $Body = $null
  )

  $uri = "$ApiBaseUrl$Path"
  $jsonBody = $null
  if ($null -ne $Body) {
    $jsonBody = $Body | ConvertTo-JsonBody
  }

  try {
    if ($null -ne $jsonBody) {
      $response = Invoke-WebRequest -Method $Method -Uri $uri -Headers $Headers -Body $jsonBody -ContentType "application/json" -UseBasicParsing
    } else {
      $response = Invoke-WebRequest -Method $Method -Uri $uri -Headers $Headers -UseBasicParsing
    }
  } catch {
    $errorResponse = $_.Exception.Response
    if ($null -ne $errorResponse -and $errorResponse.GetResponseStream()) {
      $statusCode = [int]$errorResponse.StatusCode
      $reader = New-Object System.IO.StreamReader($errorResponse.GetResponseStream())
      $rawError = $reader.ReadToEnd()
      try {
        $parsedError = $rawError | ConvertFrom-Json
        $detail = if ($parsedError.detail) { $parsedError.detail } else { $rawError }
      } catch {
        $detail = $rawError
      }
      throw "API $Method $Path failed with status ${statusCode}: $detail"
    }
    throw
  }

  if ([string]::IsNullOrWhiteSpace($response.Content)) {
    return $null
  }

  try {
    return $response.Content | ConvertFrom-Json
  } catch {
    return $response.Content
  }
}

function New-DevActorHeaders {
  param(
    [string]$UserId,
    [string]$Username,
    [string]$DisplayName,
    [bool]$IsAdmin
  )

  return @{
    "X-Satta-User-Id" = $UserId
    "X-Satta-Username" = $Username
    "X-Satta-Display-Name" = $DisplayName
    "X-Satta-Is-Admin" = $IsAdmin.ToString().ToLowerInvariant()
  }
}

function Resolve-RequiredUserId {
  param(
    [string]$ProvidedValue,
    [string]$EnvName,
    [string]$Label
  )

  if (-not [string]::IsNullOrWhiteSpace($ProvidedValue)) {
    return $ProvidedValue
  }

  $envValue = [Environment]::GetEnvironmentVariable($EnvName)
  if (-not [string]::IsNullOrWhiteSpace($envValue)) {
    return $envValue
  }

  throw "$Label is required in postgres mode. Pass -$Label or set $EnvName."
}

$AdminUserId = Resolve-RequiredUserId -ProvidedValue $AdminUserId -EnvName "DEV_AUTH_USER_ID" -Label "AdminUserId"
if (-not $SkipOrders) {
  $UserAId = Resolve-RequiredUserId -ProvidedValue $UserAId -EnvName "SATTA_SMOKE_USER_A_ID" -Label "UserAId"
  $UserBId = Resolve-RequiredUserId -ProvidedValue $UserBId -EnvName "SATTA_SMOKE_USER_B_ID" -Label "UserBId"
}
if ([string]::IsNullOrWhiteSpace($UserAId)) {
  $UserAId = $AdminUserId
}
if ([string]::IsNullOrWhiteSpace($UserBId)) {
  $UserBId = $AdminUserId
}

$adminHeaders = New-DevActorHeaders -UserId $AdminUserId -Username $AdminUsername -DisplayName $AdminDisplayName -IsAdmin $true
$userAHeaders = New-DevActorHeaders -UserId $UserAId -Username $UserAUsername -DisplayName $UserADisplayName -IsAdmin $false
$userBHeaders = New-DevActorHeaders -UserId $UserBId -Username $UserBUsername -DisplayName $UserBDisplayName -IsAdmin $false
$oracleHeaders = @{
  "X-Satta-Oracle-Secret" = $OracleSecret
}

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$marketSlug = "$SlugPrefix-$stamp"

Write-Host "1. Loading community context..."
$communities = Invoke-SattaApi -Path "/api/v1/communities" -Headers $adminHeaders
if ($null -eq $communities -or $communities.Count -eq 0) {
  throw "No communities are available. Create a community before running the smoke script."
}
$community = $communities[0]

Write-Host "2. Creating market request..."
$requestPayload = @{
  title = "Will ETH close above 6k? [$stamp]"
  slug = $marketSlug
  question = "Will ETH close above 6k?"
  description = "Smoke test market for the oracle request, dispute, and finalization flow."
  template_key = "price_above"
  template_config = @{
    category = "Crypto"
    subcategory = "ETH"
    subject = "ETH"
    reference_asset = "ETH/USD"
    threshold_value = "6000"
    reference_source_label = "Chainlink Crypto Feeds"
    reference_label = "ETH/USD"
    contract_notes = "Generated by the oracle dispute smoke script."
  }
  market_access_mode = "public"
  requested_rail = "onchain"
  resolution_mode = "oracle"
  community_id = $community.id
  settlement_reference_url = "https://data.chain.link"
}
$request = Invoke-SattaApi -Method "POST" -Path "/api/v1/market-requests" -Headers $userAHeaders -Body $requestPayload

Write-Host "3. Submitting request for review..."
$submittedRequest = Invoke-SattaApi -Method "POST" -Path "/api/v1/market-requests/$($request.id)/submit" -Headers $userAHeaders

Write-Host "4. Publishing market as admin..."
$publishedMarket = Invoke-SattaApi -Method "POST" -Path "/api/v1/admin/market-requests/$($request.id)/publish" -Headers $adminHeaders -Body @{
  review_notes = "Smoke script publish."
}
$marketSlug = $publishedMarket.slug
$yesOutcome = $publishedMarket.outcomes | Where-Object { $_.label -eq "Yes" } | Select-Object -First 1
if ($null -eq $yesOutcome) {
  $yesOutcome = $publishedMarket.outcomes[0]
}

if (-not $SkipOrders) {
  Write-Host "5. Funding test users..."
  Invoke-SattaApi -Method "POST" -Path "/api/v1/admin/fund-balance" -Headers $adminHeaders -Body @{
    profile_id = $userAHeaders["X-Satta-User-Id"]
    asset_code = "USDC"
    rail_mode = "onchain"
    amount = "100"
    description = "Smoke funding for user A"
  } | Out-Null
  Invoke-SattaApi -Method "POST" -Path "/api/v1/admin/fund-balance" -Headers $adminHeaders -Body @{
    profile_id = $userBHeaders["X-Satta-User-Id"]
    asset_code = "USDC"
    rail_mode = "onchain"
    amount = "100"
    description = "Smoke funding for user B"
  } | Out-Null

  Write-Host "6. Placing opposite orders..."
  Invoke-SattaApi -Method "POST" -Path "/api/v1/markets/$marketSlug/orders" -Headers $userAHeaders -Body @{
    outcome_id = $yesOutcome.id
    side = "buy"
    order_type = "limit"
    quantity = "5"
    price = "0.55"
  } | Out-Null
  Invoke-SattaApi -Method "POST" -Path "/api/v1/markets/$marketSlug/orders" -Headers $userBHeaders -Body @{
    outcome_id = $yesOutcome.id
    side = "sell"
    order_type = "limit"
    quantity = "5"
    price = "0.55"
  } | Out-Null

  $matchedTrade = $false
  for ($attempt = 1; $attempt -le 10; $attempt++) {
    Start-Sleep -Seconds 1
    $shellSnapshot = Invoke-SattaApi -Path "/api/v1/markets/$marketSlug/trading-shell" -Headers $adminHeaders
    if ($shellSnapshot.recent_trades.Count -gt 0) {
      $matchedTrade = $true
      break
    }
  }

  if ($matchedTrade) {
    Write-Host "   Trade match observed."
  } else {
    Write-Warning "No trade match was observed within 10 seconds. Continue testing only if the matching engine is running."
  }
}

Write-Host "7. Requesting oracle settlement..."
$settlementRequest = Invoke-SattaApi -Method "POST" -Path "/api/v1/markets/$marketSlug/settlement-requests" -Headers $userAHeaders -Body @{
  source_reference_url = "https://data.chain.link"
  notes = "Smoke test settlement request."
}
$reconciledResolutionState = Invoke-SattaApi -Method "POST" -Path "/api/v1/markets/$marketSlug/oracle/reconcile" -Headers $oracleHeaders -Body @{}
$resolutionState = Invoke-SattaApi -Path "/api/v1/markets/$marketSlug/resolution" -Headers $adminHeaders

Write-Host "8. Raising dispute..."
$dispute = Invoke-SattaApi -Method "POST" -Path "/api/v1/markets/$marketSlug/disputes" -Headers $userBHeaders -Body @{
  title = "Smoke dispute"
  reason = "Verifying the dispute and oracle review lifecycle."
}

Write-Host "9. Attaching dispute evidence..."
$disputeWithEvidence = Invoke-SattaApi -Method "POST" -Path "/api/v1/markets/$marketSlug/disputes/$($dispute.id)/evidence" -Headers $userBHeaders -Body @{
  evidence_type = "source_link"
  url = "https://example.com/evidence/$stamp"
  description = "Smoke-test evidence attachment."
  payload = @{
    source = "oracle-dispute-smoke"
  }
}

Write-Host "10. Reviewing dispute through oracle callback..."
$reviewedDispute = Invoke-SattaApi -Method "POST" -Path "/api/v1/markets/$marketSlug/oracle/disputes/$($dispute.id)/review" -Headers $oracleHeaders -Body @{
  status = "dismissed"
  review_notes = "Smoke review dismissed the dispute so finalization can continue."
}

Write-Host "11. Finalizing market..."
$finalizedResolution = Invoke-SattaApi -Method "POST" -Path "/api/v1/markets/$marketSlug/oracle/finalize" -Headers $oracleHeaders -Body @{
  winning_outcome_id = $yesOutcome.id
  candidate_id = $resolutionState.candidate_id
  source_reference_url = "https://data.chain.link"
  notes = "Smoke finalization completed."
}

Write-Host "12. Loading final market state..."
$finalMarket = Invoke-SattaApi -Path "/api/v1/markets/$marketSlug/trading-shell" -Headers $adminHeaders
$finalResolutionState = Invoke-SattaApi -Path "/api/v1/markets/$marketSlug/resolution" -Headers $adminHeaders

$summary = [ordered]@{
  request_id = $request.id
  market_slug = $marketSlug
  market_status = $finalMarket.market.status
  resolution_status = $finalResolutionState.current_status
  winning_outcome_id = $finalResolutionState.winning_outcome_id
  candidate_id = $finalResolutionState.candidate_id
  dispute_id = $dispute.id
  dispute_status = ($finalResolutionState.disputes | Select-Object -First 1).status
  history_events = $finalResolutionState.history.Count
  oracle_provider = $finalResolutionState.current_payload.provider
  oracle_assertion_id = $finalResolutionState.current_payload.assertion_id
  oracle_assertion_identifier = $finalResolutionState.current_payload.assertion_identifier
  oracle_chain_id = $finalResolutionState.current_payload.chain_id
  oracle_bond_wei = $finalResolutionState.current_payload.bond_wei
  oracle_reward_wei = $finalResolutionState.current_payload.reward_wei
  oracle_liveness_minutes = $finalResolutionState.current_payload.liveness_minutes
  oracle_submission_status = $finalResolutionState.current_payload.submission_status
  oracle_tx_hash = $finalResolutionState.current_payload.tx_hash
  oracle_receipt_status = $finalResolutionState.current_payload.receipt_status
  oracle_onchain_assertion_state = $finalResolutionState.current_payload.onchain_assertion_state
  oracle_last_reconciled_at = $finalResolutionState.current_payload.last_reconciled_at
}

Write-Host ""
Write-Host "Smoke flow completed:"
$summary | ConvertTo-Json -Depth 12
