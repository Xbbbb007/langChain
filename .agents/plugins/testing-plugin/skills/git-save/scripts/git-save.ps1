param(
    [string]$CommitMessage = ""
)

# Set UTF-8 encoding for output
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 1. Check if git is initialized
if (!(Test-Path .git)) {
    Write-Output "Error: Git is not initialized in the current directory. Please run 'git init' first."
    exit 1
}

# 2. Check if there are changes
$status = git status --porcelain
if ([string]::IsNullOrEmpty($status)) {
    Write-Output "No changes detected. Workspace is already up to date."
    exit 0
}

# 3. Formulate commit message if not provided
if ([string]::IsNullOrEmpty($CommitMessage)) {
    # Generate list of modified files as summary
    $files = git diff --name-only
    if ([string]::IsNullOrEmpty($files)) {
        $files = git status --porcelain | ForEach-Object { $_.Substring(3) }
    }
    
    # Clean up empty entries
    $files = $files | Where-Object { $_ -ne "" }
    
    $filesSummary = ($files -join ", ")
    if ($filesSummary.Length -gt 60) {
        $filesSummary = $filesSummary.Substring(0, 57) + "..."
    }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $CommitMessage = "Auto-save [$timestamp]: Modified $filesSummary"
}

# 4. Stage all changes
Write-Output "Staging changes..."
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Output "Error: Failed to stage changes."
    exit 1
}

# 5. Commit changes
Write-Output "Committing changes: $CommitMessage"
git commit -m $CommitMessage
if ($LASTEXITCODE -ne 0) {
    Write-Output "Error: Failed to commit changes."
    exit 1
}

# 6. Push to remote
$branch = git branch --show-current
Write-Output "Pushing to origin $branch..."
git push origin $branch
if ($LASTEXITCODE -ne 0) {
    Write-Output "Error: Failed to push to remote repository. Please check your network and git configuration."
    exit 1
}

Write-Output "Successfully saved and pushed to GitHub!"
exit 0
