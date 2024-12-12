import os
import sys
import signal
import subprocess
import psutil

def kill_bot():
    """Останавливает все процессы бота"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and 'bot.py' in cmdline[-1]:
                    os.kill(proc.info['pid'], signal.SIGTERM)
                    print(f"Stopped bot process {proc.info['pid']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def run_bot():
    """Запускает бота"""
    kill_bot()  # Сначала останавливаем существующие процессы
    print("Starting bot...")
    subprocess.Popen([sys.executable, 'bot.py'])

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'stop':
        kill_bot()
    else:
        run_bot() 