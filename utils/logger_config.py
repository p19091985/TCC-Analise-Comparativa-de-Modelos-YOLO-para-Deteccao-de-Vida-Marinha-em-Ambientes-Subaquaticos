                       
"""
Módulo centralizado para configuração de logs.
Evita a repetição do código de setup de logging em todos os scripts.
"""
import logging
import sys
import os
import datetime
from config.paths import LOGS_DIR

def setup_logging(logger_name: str, script_filename: str) -> logging.Logger:
    """
    Configura e retorna um logger que salva em arquivo e exibe no console.
    O nome do arquivo de log é derivado do nome do script que o chama.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)

    script_name_no_ext = os.path.splitext(os.path.basename(script_filename))[0]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{script_name_no_ext}_{timestamp}.log"
    log_filepath = os.path.join(LOGS_DIR, log_filename)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    log_format = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")

    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_format)
    logger.addHandler(stream_handler)

    logger.info(f"Logger configurado. Logs para esta execução serão salvos em: {log_filepath}")
    return logger