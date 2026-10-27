# Inchide taburile vechi ale programului in Chrome sau Edge, dupa ce s-a deschis unul nou (cerut de autor: o pornire noua
# le inchide pe cele vechi). Ordinea conteaza: inchise intai, fereastra ramanea goala si se inchidea, iar Chrome, pornit
# din nou pentru tabul nou, isi refacea sesiunea si aducea inapoi tabul vechi (doua „Acasa”).
# Pasii: tine minte taburile de acum, scrie „pregatit” (programul deschide atunci tabul nou), asteapta pana apare un tab
# nou al programului, apoi le inchide numai pe cele tinute minte. Fara tab nou in 20 de secunde nu inchide nimic.
# Numai taburile cu titlul „… — HarnessCraft”, numai in Chrome si Edge (VS Code are aceeasi clasa de fereastra).
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$A = [System.Windows.Automation.AutomationElement]
$copii = [System.Windows.Automation.TreeScope]::Children
$toate = [System.Windows.Automation.TreeScope]::Descendants
$clasa = New-Object System.Windows.Automation.PropertyCondition($A::ClassNameProperty, "Chrome_WidgetWin_1")
$tab = New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, [System.Windows.Automation.ControlType]::TabItem)
$buton = New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)

function Taburi {
  $r = @()
  foreach ($f in $A::RootElement.FindAll($copii, $clasa)) {
    $proces = (Get-Process -Id $f.Current.ProcessId -ErrorAction SilentlyContinue).ProcessName
    if ($proces -notin @("chrome", "msedge")) { continue }
    foreach ($t in @($f.FindAll($toate, $tab))) {
      if ($t.Current.Name -match ' [—–-] HarnessCraft( - |$)') { $r += $t }
    }
  }
  return $r
}

$vechi = @(Taburi)
$chei = @($vechi | ForEach-Object { ($_.GetRuntimeId() -join ".") })
"pregatit"
[Console]::Out.Flush()
$nou = $false
for ($i = 0; $i -lt 80 -and -not $nou; $i++) {
  Start-Sleep -Milliseconds 250
  $nou = @(Taburi | Where-Object { ($_.GetRuntimeId() -join ".") -notin $chei }).Count -gt 0
}
$n = 0
if ($nou) {
  foreach ($t in $vechi) {
    try {
      $b = $t.FindFirst($toate, $buton)
      if ($b) { $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); $n++; Start-Sleep -Milliseconds 200 }
    } catch {}
  }
}
$n
