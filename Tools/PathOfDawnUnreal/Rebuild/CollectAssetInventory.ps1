#requires -Version 7.2
[CmdletBinding()]
param([string[]]$Roots, [string]$Output, [ValidateRange(1,100000)][int]$MaxFiles=20000)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if (-not $Roots) {
    $Roots=@((Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Unreal Projects'))
}
if (-not $Output) {
    $Output=Join-Path ([IO.Path]::GetTempPath()) ('WordJourney-asset-inventory-'+[guid]::NewGuid().ToString('N')+'.json')
}
if (Test-Path -LiteralPath $Output) { throw "Output already exists; choose a new file: $Output" }
$rows=[Collections.Generic.List[object]]::new()
$errors=[Collections.Generic.List[string]]::new()
$visited=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$queue=[Collections.Generic.Queue[string]]::new()
foreach ($root in $Roots) {
    if (Test-Path -LiteralPath $root -PathType Container) { $queue.Enqueue([IO.Path]::GetFullPath($root)) }
    else { $errors.Add("Directory not found: $root") }
}
$ignored=@('Binaries','Intermediate','DerivedDataCache','Saved','.git','node_modules','.vs')
$extensions=@('.uproject','.uasset','.umap','.fbx','.glb','.gltf','.bvh','.blend')
$truncated=$false
while ($queue.Count -gt 0) {
    $directory=$queue.Dequeue()
    if (-not $visited.Add($directory)) { continue }
    try { $children=@(Get-ChildItem -LiteralPath $directory -Force -ErrorAction Stop) }
    catch { $errors.Add("Cannot list directory: $directory"); continue }
    foreach ($child in $children) {
        if ($child.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
        if ($child.PSIsContainer) {
            if ($child.Name -notin $ignored) { $queue.Enqueue($child.FullName) }
            continue
        }
        if ($child.Extension.ToLowerInvariant() -notin $extensions) { continue }
        if ($rows.Count -ge $MaxFiles) { $truncated=$true; break }
        $lfs=$false; $packageHeader=$false
        try {
            $stream=[IO.File]::Open($child.FullName,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
            try {
                $header=[byte[]]::new(128)
                $count=$stream.Read($header,0,$header.Length)
                $lfs=[Text.Encoding]::ASCII.GetString($header,0,$count).StartsWith('version https://git-lfs.github.com/spec/v1')
                $packageHeader=$count -ge 4 -and [BitConverter]::ToUInt32($header,0) -eq 0x9E2A83C1L
            } finally { $stream.Dispose() }
        } catch { $errors.Add("Cannot inspect header: $($child.FullName)") }
        $rows.Add([ordered]@{path=$child.FullName;bytes=$child.Length;lfsPointer=$lfs;unrealPackageHeader=$packageHeader;unrealLoaded=$false;licenseVerified=$false})
    }
    if ($truncated) { break }
}
$parent=Split-Path -Parent ([IO.Path]::GetFullPath($Output))
[void][IO.Directory]::CreateDirectory($parent)
$report=[ordered]@{
    schemaVersion=1;checkedUtc=[DateTime]::UtcNow.ToString('O');roots=$Roots;truncated=$truncated
    scope='Read-only file inventory. No installs, content changes, licensing or Unreal load validation.'
    files=@($rows.ToArray());errors=@($errors.ToArray())
}
[IO.File]::WriteAllText([IO.Path]::GetFullPath($Output),($report | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Write-Host "Inventory: $Output ($($rows.Count) candidate files). Header/file presence does not establish usable characters or license rights."
if ($truncated) { Write-Warning 'File limit reached; this inventory is incomplete.' }
