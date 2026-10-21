# 五子棋 无头冒烟：编译后在 UiDriver 下跑几帧再退出。
#
# 验证三件事：exe 编译得过、启动后帧循环不崩、demo 标记能让对局场景跑起来
# （资源内嵌与查找路径通不通）。GUI 游戏没有断言式用例套件，这里的判据是
# "进程按脚本正常退出 + UiDriver 会话收尾"。
param(
    [string]$Compiler = $env:ZANC,
    [string]$PackageProject = ''
)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$repo = Split-Path -Parent $project
if (-not $Compiler) {
    $local = if ($env:ZAN_HOME) { Join-Path $env:ZAN_HOME 'build/zanc.exe' } else { '' }
    if ($local -and (Test-Path $local)) { $Compiler = $local } else { $Compiler = (Get-Command zanc -ErrorAction Stop).Source }
}
if (-not $PackageProject) { if ($env:ZAN_HOME) { $PackageProject = $env:ZAN_HOME } else { throw '需要 $env:ZAN_HOME 指向 zan-lang 仓库（公共包在它的 packages/ 下）' } }
$out = Join-Path $repo 'build/gomoku'
& (Join-Path $PSScriptRoot 'build.ps1') -Compiler $Compiler -PackageProject $PackageProject -Output $out
$exe = Join-Path $out 'Gomoku.exe'
if (-not (Test-Path $exe)) { throw "缺少可执行文件：$exe" }

# --- 设置用例：跑两遍验证真的落盘 ---
# 源码要**排除 main.zan**（它带 Main()，用例自己的 Main 才是入口）；
# 其余游戏源码全部带上——用例要直接读写项目的设置声明。
$caseSources = @(Get-ChildItem (Join-Path $project 'src') -Recurse -File -Filter *.zan |
    Where-Object { $_.Name -ne 'main.zan' } |
    Sort-Object FullName | ForEach-Object { $_.FullName })
$settingsCase = Join-Path $project 'tests/settings.zan'
$settingsExe = Join-Path $out 'settings.exe'
& $Compiler (@($settingsCase) + $caseSources +
    @('--auto-stdlib', '--package-project', $PackageProject, '-o', $settingsExe))
if ($LASTEXITCODE -ne 0) { throw "设置用例编译失败（zanc=$LASTEXITCODE）" }
$settingsFile = Join-Path $out 'gomoku_settings.json'
if (Test-Path $settingsFile) { Remove-Item $settingsFile -Force }
Push-Location $out
try {
    $first = & $settingsExe 2>&1 | Out-String
    $second = & $settingsExe 2>&1 | Out-String
} finally { Pop-Location }
if ($first -notmatch 'settings OK') { throw "设置用例首跑输出不对：`n$first" }
if ($second -notmatch 'settings OK') { throw "设置用例次跑输出不对：`n$second" }
if ($first -notmatch 'delay=500') { throw "设置默认值不对：`n$first" }
if ($second -notmatch 'delay=900') { throw "设置没有落盘（次跑仍读到默认值）：`n$second" }
Write-Host 'settings_OK'
# demo 标记：进对局自弈场景（比停在主菜单多跑一层玩法渲染）
[IO.File]::WriteAllText((Join-Path $out 'gomoku_demo.txt'), 'demo', [Text.UTF8Encoding]::new($false))
# UiDriver 脚本：等几帧 → dump → 退出（无头，不弹窗口）
$script = Join-Path $out 'ui.script'
[IO.File]::WriteAllText($script, "wait 300`ndump tree tree.txt`nquit`n", [Text.UTF8Encoding]::new($false))
$uidir = Join-Path $out 'uidrv'
$env:ZAN_UI_SCRIPT = $script
$env:ZAN_UI_OUT = $uidir
$proc = Start-Process -FilePath $exe -WorkingDirectory $out -PassThru -WindowStyle Hidden
if (-not $proc.WaitForExit(60000)) {
    $proc.Kill()
    throw '无头冒烟超时：应用没按 UiDriver 脚本退出'
}
if ($proc.ExitCode -ne 0) { throw "无头冒烟失败：exit=$($proc.ExitCode)" }
$log = Join-Path $uidir 'results.log'
if (-not (Test-Path $log)) { throw 'UiDriver 会话没有产出 results.log' }
if (-not (Select-String -Path $log -Pattern 'DONE' -Quiet)) { throw "UiDriver 会话未收尾：$log" }
Write-Host "gomoku_SMOKE_OK"