@echo off
REM Execute o setup como administrador automaticamente

echo.
echo ============================================================
echo ELEVANDO PRIVILEGIOS PARA ADMINISTRADOR...
echo ============================================================
echo.

REM Verificar se ja esta rodando como admin
net session >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo [OK] Ja esta rodando como Administrador
    cd /d "%~dp0"
    python setup_monitor.py
    pause
) else (
    echo [INFO] Solicitando privilegios de administrador...
    echo.

    REM Criar script temporario para executar como admin
    set "tempscript=%temp%\run_setup.vbs"

    (
        echo Set objShell = CreateObject^("Shell.Application"^)
        echo objShell.ShellExecute "cmd.exe", "/c cd /d %~dp0 && python setup_monitor.py && pause", "", "runas", 1
    ) > "%tempscript%"

    cscript //nologo "%tempscript%"
    del "%tempscript%"
)

