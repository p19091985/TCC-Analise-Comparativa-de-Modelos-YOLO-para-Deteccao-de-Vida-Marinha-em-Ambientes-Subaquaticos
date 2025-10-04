import subprocess
import datetime
import os

# lista de scripts Python que você quer executar
scripts = [
    "controle_preparacao_dados.py",
    "avaliacao_test_com_modelo.py",
     "main.py"]

# gera timestamp para o nome do log
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"logGeral_{timestamp}.txt"

with open(log_file, "w", encoding="utf-8") as log:
    for script in scripts:
        if not os.path.exists(script):
            log.write(f"[ERRO] Arquivo não encontrado: {script}\n\n")
            continue

        log.write(f"\n=== Executando {script} ===\n")
        try:
            result = subprocess.run(
                ["python", script],
                capture_output=True,
                text=True
            )
            log.write(result.stdout)
            if result.stderr:
                log.write("\n[STDERR]\n")
                log.write(result.stderr)
        except Exception as e:
            log.write(f"[ERRO AO EXECUTAR {script}]: {e}\n")

print(f"Execução finalizada. Log salvo em: {log_file}")
