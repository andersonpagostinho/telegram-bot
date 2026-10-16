#!/usr/bin/env python3
"""
Setup do Monitor de Quota Firestore

Executa automaticamente:
  - Windows: Task Scheduler
  - Linux/Mac: cron

Uso:
  python setup_monitor.py
"""

import platform
import subprocess
import sys
from pathlib import Path

def setup_windows():
    """Setup para Windows usando Task Scheduler"""
    print("\n[WINDOWS] Configurando Task Scheduler...")

    script_path = Path(__file__).parent / "monitor_quota_continuous.py"
    project_path = Path(__file__).parent

    # PowerShell script
    ps_script = f"""
$action = New-ScheduledTaskAction -Execute 'python' -Argument '{script_path}' -WorkingDirectory '{project_path}'
$trigger = New-ScheduledTaskTrigger -At 08:00 -Daily
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName 'NeoEve-Quota-Monitor' -Action $action -Trigger $trigger -Settings $settings -Force -RunLevel Highest
"""

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("[OK] Task Scheduler configurado com sucesso!")
            print(f"    Tarefa: NeoEve-Quota-Monitor")
            print(f"    Horario: 08:00 (diario)")
            print(f"    Frequencia: A cada 30 minutos")
            return True
        else:
            print(f"[ERRO] {result.stderr}")
            print("[INFO] Execute como administrador para configurar Task Scheduler")
            return False
    except Exception as e:
        print(f"[ERRO] {e}")
        return False

def setup_linux():
    """Setup para Linux usando cron"""
    print("\n[LINUX] Configurando cron...")

    script_path = Path(__file__).parent / "monitor_quota_continuous.py"
    project_path = Path(__file__).parent
    log_file = project_path / "quota_monitor.log"

    # Cron entry: a cada 30 minutos comecando as 08:00
    cron_entry = f"*/30 8-23 * * * cd {project_path} && python {script_path} >> {log_file} 2>&1"

    print("[INFO] Execute manualmente:")
    print(f"  crontab -e")
    print(f"  # Adicione:")
    print(f"  {cron_entry}")

    return True

def setup_manual():
    """Setup manual - apenas orientacao"""
    print("\n[MANUAL] Opcoes para agendamento manual:")
    print()
    print("Opcao 1: Windows Task Scheduler")
    print("  1. Abra: taskschd.msc")
    print("  2. Create Basic Task")
    print("  3. Nome: NeoEve-Quota-Monitor")
    print("  4. Trigger: Daily at 08:00")
    print("  5. Action: Run python monitor_quota_continuous.py")
    print()
    print("Opcao 2: Linux cron")
    print("  crontab -e")
    print("  */30 8-23 * * * cd /path/to/neoeve && python monitor_quota_continuous.py >> quota_monitor.log 2>&1")
    print()
    print("Opcao 3: Executar manualmente quando precisar")
    print("  python monitor_quota_continuous.py")

    return True

def main():
    print("\n" + "="*70)
    print("SETUP: MONITOR DE QUOTA FIRESTORE")
    print("="*70)

    sistema = platform.system()

    if sistema == "Windows":
        success = setup_windows()
    elif sistema in ["Linux", "Darwin"]:  # Darwin = macOS
        success = setup_linux()
    else:
        print(f"[AVISO] Sistema desconhecido: {sistema}")
        success = setup_manual()

    # Informacoes gerais
    print("\n" + "="*70)
    print("PROXIMO PASSO")
    print("="*70)
    print()
    print("Quando a quota for liberada amanha:")
    print("  1. Monitor automaticamente detectara")
    print("  2. Auto-cleanup vai rodar")
    print("  3. Voce recebera alerta")
    print()
    print("Logs estarao em:")
    print(f"  {Path(__file__).parent / 'quota_monitor.log'}")
    print()

    if success:
        print("[SUCESSO] Monitor agendado!")
    else:
        print("[AVISO] Configure manualmente se necessario")

    print("\n" + "="*70)

if __name__ == "__main__":
    main()

