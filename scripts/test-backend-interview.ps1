param(
    [string]$BaseUrl = "http://127.0.0.1:8080",
    [string]$Job = "backend",
    [string]$ReplyText = "Hello, I am ready. Here is a short introduction: I have three years of backend development experience with Go, PostgreSQL, Redis, message queues, API performance tuning, index optimization, and production troubleshooting."
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-CurlJson {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Method,
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [string]$Body,
        [string]$Token
    )

    $args = @(
        "-sS",
        "-X", $Method,
        $Url,
        "-H", "Accept: application/json"
    )

    if ($Token) {
        $args += @("-H", "Authorization: Bearer $Token")
    }

    $tempBodyPath = $null
    if ($PSBoundParameters.ContainsKey("Body")) {
        $tempBodyPath = [System.IO.Path]::GetTempFileName()
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($tempBodyPath, $Body, $utf8NoBom)

        $args += @(
            "-H", "Content-Type: application/json",
            "--data-binary", "@$tempBodyPath"
        )
    }

    $args += @("-w", "`nHTTPSTATUS:%{http_code}")

    try {
        $raw = & curl.exe @args
    }
    finally {
        if ($tempBodyPath -and (Test-Path $tempBodyPath)) {
            Remove-Item $tempBodyPath -Force
        }
    }
    if ($raw -is [array]) {
        $raw = $raw -join "`n"
    }

    $match = [regex]::Match($raw, '(?s)^(.*)HTTPSTATUS:(\d+)\s*$')
    if (-not $match.Success) {
        throw "Unable to parse curl output: $raw"
    }

    $status = [int]$match.Groups[2].Value
    $bodyText = $match.Groups[1].Value.Trim()

    $json = $null
    if ($bodyText) {
        try {
            $json = $bodyText | ConvertFrom-Json
        }
        catch {
            throw "Response is not valid JSON. HTTP $status body=$bodyText"
        }
    }

    [pscustomobject]@{
        Status = $status
        Body   = $bodyText
        Json   = $json
    }
}

function Assert-Success {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Step,
        [Parameter(Mandatory = $true)]
        $Response
    )

    if ($Response.Status -ne 200) {
        throw "$Step failed: HTTP $($Response.Status) body=$($Response.Body)"
    }
    if (-not $Response.Json.success) {
        throw "$Step failed: success=false message=$($Response.Json.message)"
    }
}

$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$account = "curltest_$timestamp@example.com"
$name = "CurlTest$timestamp"
$password = "Passw0rd!"

$signupBody = @{
    account  = $account
    name     = $name
    password = $password
} | ConvertTo-Json -Compress

$signup = Invoke-CurlJson -Method "POST" -Url "$BaseUrl/api/auth/signup" -Body $signupBody
Assert-Success -Step "signup" -Response $signup

$token = [string]$signup.Json.data
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "signup failed: empty token"
}

$profileBody = @{
    name            = $name
    job             = $Job
    resume          = "Three years of backend development experience with Go, PostgreSQL, Redis, message queues, and API performance optimization."
    personalization = "Focus on backend engineering, database design, performance tuning, and troubleshooting."
} | ConvertTo-Json -Compress

$profile = Invoke-CurlJson -Method "PUT" -Url "$BaseUrl/api/user/profile" -Body $profileBody -Token $token
Assert-Success -Step "profile" -Response $profile

$start = Invoke-CurlJson -Method "POST" -Url "$BaseUrl/api/interview/start" -Token $token
Assert-Success -Step "start" -Response $start

$interviewId = [string]$start.Json.data.id
if ([string]::IsNullOrWhiteSpace($interviewId)) {
    throw "start failed: empty interview id"
}

$replyBody = @{
    text = $ReplyText
} | ConvertTo-Json -Compress

$reply = Invoke-CurlJson -Method "POST" -Url "$BaseUrl/api/interview/reply?id=$interviewId" -Body $replyBody -Token $token
Assert-Success -Step "reply" -Response $reply

$stopBody = @{
    id = $interviewId
} | ConvertTo-Json -Compress

$stop = Invoke-CurlJson -Method "POST" -Url "$BaseUrl/api/interview/stop" -Body $stopBody -Token $token
Assert-Success -Step "stop" -Response $stop

$result = [pscustomobject]@{
    account = $account
    signup  = [pscustomobject]@{
        status       = $signup.Status
        message      = $signup.Json.message
        token_prefix = if ($token.Length -gt 24) { $token.Substring(0, 24) } else { $token }
    }
    profile = [pscustomobject]@{
        status  = $profile.Status
        message = $profile.Json.message
    }
    start   = [pscustomobject]@{
        status       = $start.Status
        message      = $start.Json.message
        interview_id = $interviewId
        reply        = $start.Json.data.reply
    }
    reply   = [pscustomobject]@{
        status  = $reply.Status
        message = $reply.Json.message
        reply   = $reply.Json.data.reply
        ending  = $reply.Json.data.ending
    }
    stop    = [pscustomobject]@{
        status  = $stop.Status
        message = $stop.Json.message
    }
}

$result | ConvertTo-Json -Depth 10
