@echo off
REM Setup para agendar monitor de quota no Windows Task Scheduler
REM Execute como administrador

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo CONFIGURANDO AGENDAMENTO DE QUOTA MONITOR
echo ============================================================
echo.

REM Obter caminho do projeto
set PROJECT_PATH=%~dp0
cd /d "%PROJECT_PATH%"

REM Criar tarefa agendada
echo [1] Criando tarefa no Task Scheduler...
echo.

powershell -Command "^
  $action = New-ScheduledTaskAction -Execute 'python' -Argument 'monitor_quota_continuous.py' -WorkingDirectory '%PROJECT_PATH%'; ^
  $trigger = New-ScheduledTaskTrigger -At 08:00 -Daily; ^
  $trigger2 = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Days 1) -At 08:00; ^
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; ^
  try { ^
    Register-ScheduledTask -TaskName 'NeoEve-Quota-Monitor' -Action $action -Trigger $trigger -Settings $settings -Force -RunLevel Highest; ^
    Write-Host '[OK] Tarefa agendada com sucesso!'; ^
  } catch { ^
    Write-Host '[ERRO] Falha ao criar tarefa: ' $_.Exception.Message; ^
    exit 1; ^
  } ^
"

echo.
echo ============================================================
echo CONFIGURACAO COMPLETA!
echo ============================================================
echo.
echo O monitor foi agendado para:
echo - Data: Todos os dias (a partir de amanha)
echo - Hora inicial: 08:00
echo - Frequencia: A cada 30 minutos
echo - Nome da tarefa: NeoEve-Quota-Monitor
echo.
echo Para verificar:
echo   1. Abra Task Scheduler (taskschd.msc)
echo   2. Procure por "NeoEve-Quota-Monitor"
echo.
echo Para desativar:
echo   1. Task Scheduler ^> NeoEve-Quota-Monitor ^> Desabilitar
echo   2. Ou execute: schtasks /delete /tn NeoEve-Quota-Monitor /f
echo.
echo Logs serao salvos em:
echo   %PROJECT_PATH%quota_monitor.log
echo.
pause

