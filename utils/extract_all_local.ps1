# Process all local captures one by one
$pcapDir = "data\raw\local_captures"
$outputDir = "data\processed\local_captures"

# Ensure output directory exists
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

# Get all PCAP files sorted by size (smallest first)
$pcapFiles = Get-ChildItem "$pcapDir\*.pcapng" | Sort-Object Length

Write-Host "=" * 80
Write-Host "BATCH FEATURE EXTRACTION - LOCAL CAPTURES"
Write-Host "=" * 80
Write-Host ""

$total = $pcapFiles.Count
$current = 0
$results = @()

foreach ($pcapFile in $pcapFiles) {
    $current++
    $sizeMB = [math]::Round($pcapFile.Length / 1MB, 2)
    $outputFile = Join-Path $outputDir "$($pcapFile.BaseName)_features.json"
    
    Write-Host "[$current/$total] Processing: $($pcapFile.Name)"
    Write-Host "  Size: $sizeMB MB"
    Write-Host "  Output: $($outputFile)"
    Write-Host ""
    
    $startTime = Get-Date
    
    # Run extraction
    $result = & ".\backend\features\rust_extractor\target\release\rust_extractor.exe" $pcapFile.FullName $outputFile 2>&1
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    # Check if output file was created
    if (Test-Path $outputFile) {
        $featureData = Get-Content $outputFile | ConvertFrom-Json
        $windows = $featureData.Count
        
        Write-Host "  ✓ SUCCESS: $windows windows extracted in $([math]::Round($duration, 1))s"
        
        $results += [PSCustomObject]@{
            File = $pcapFile.Name
            SizeMB = $sizeMB
            Windows = $windows
            DurationSec = [math]::Round($duration, 1)
            Status = "Success"
        }
    } else {
        Write-Host "  ✗ FAILED: No output file created"
        
        $results += [PSCustomObject]@{
            File = $pcapFile.Name
            SizeMB = $sizeMB
            Windows = 0
            DurationSec = [math]::Round($duration, 1)
            Status = "Failed"
        }
    }
    
    Write-Host ""
}

# Summary
Write-Host "=" * 80
Write-Host "EXTRACTION SUMMARY"
Write-Host "=" * 80
Write-Host ""

$results | Format-Table -AutoSize

$totalWindows = ($results | Measure-Object -Property Windows -Sum).Sum
$successCount = ($results | Where-Object { $_.Status -eq "Success" }).Count

Write-Host "Total files processed: $total"
Write-Host "Successful extractions: $successCount"
Write-Host "Total windows extracted: $totalWindows"
Write-Host ""
Write-Host "=" * 80
