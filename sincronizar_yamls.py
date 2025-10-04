# -*- coding: utf-8 -*-

"""
Arquivo de Bloco 5 de Funções: Sincronização de Arquivos de Configuração YAML

Objetivo: Sincronizar os arquivos de configuração (.yaml) de um repositório
central ('yamlRepositorio') para as respectivas pastas de dataset dentro de
'dataset_descompactado'.

Lógica Inteligente: A sincronização é eficiente. O script utiliza um hash
(SHA-256) para comparar o conteúdo dos arquivos de origem e destino. A
substituição só ocorre se for detectada uma alteração, evitando operações
desnecessárias.

Modularidade: Construído com uma função principal 'executar_sincronizacao'
para permitir a fácil integração em outros sistemas ou pipelines.
"""

import os
import sys
import logging
import datetime
import shutil
import hashlib

# --- CONFIGURAÇÃO GLOBAL ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'dataset_descompactado')
YAML_REPO_DIR = os.path.join(BASE_DIR, 'yamlRepositorio')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')  # Pasta de logs centralizada


def setup_logging() -> logging.Logger:
    """
    CORREÇÃO: Configura o logger para salvar em 'logs/nomeDoScript_timestamp.log'.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    log_filename = f"{script_name}_{timestamp}.log"
    log_filepath = os.path.join(LOGS_DIR, log_filename)

    log_format = "%(asctime)s - %(levelname)s - %(message)s"

    logger = logging.getLogger('YamlSyncLogger')
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(stream_handler)

    logger.info(f"O log desta execução será salvo em: {log_filepath}")
    return logger


def calculate_hash(filepath: str) -> str:
    """Calcula o hash SHA-256 de um arquivo."""
    if not os.path.exists(filepath):
        return ""

    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def executar_sincronizacao(logger: logging.Logger):
    """Função principal que executa a lógica de sincronização dos YAMLs."""
    try:
        logger.info("=" * 60)
        logger.info("INICIANDO SCRIPT DE SINCRONIZAÇÃO DE ARQUIVOS YAML")
        logger.info("=" * 60)

        if not os.path.exists(YAML_REPO_DIR):
            logger.error(f"ERRO: O repositório de YAMLs '{YAML_REPO_DIR}' não foi encontrado. Abortando.")
            return

        if not os.path.exists(DATASET_DIR):
            logger.error(f"ERRO: O diretório de datasets '{DATASET_DIR}' não foi encontrado. Abortando.")
            return

        sync_count = 0
        skip_count = 0
        error_count = 0

        for source_yaml_name in os.listdir(YAML_REPO_DIR):
            if not source_yaml_name.endswith('.yaml'):
                continue

            source_yaml_path = os.path.join(YAML_REPO_DIR, source_yaml_name)
            target_dataset_name = os.path.splitext(source_yaml_name)[0]
            target_dataset_dir = os.path.join(DATASET_DIR, target_dataset_name)

            logger.info(f"\n--- Verificando: {source_yaml_name} ---")

            if not os.path.exists(target_dataset_dir):
                logger.warning(f"  [AVISO] Diretório de destino '{target_dataset_dir}' não existe. Pulando.")
                continue

            target_yaml_path = os.path.join(target_dataset_dir, 'data.yaml')

            source_hash = calculate_hash(source_yaml_path)
            target_hash = calculate_hash(target_yaml_path)

            if source_hash and source_hash == target_hash:
                logger.info(f"  [SEM ALTERAÇÕES] O arquivo '{target_yaml_path}' já está sincronizado.")
                skip_count += 1
            else:
                try:
                    shutil.copy2(source_yaml_path, target_yaml_path)
                    logger.info(f"  [SINCRONIZADO] Arquivo '{source_yaml_name}' foi copiado para '{target_yaml_path}'.")
                    sync_count += 1
                except Exception as e:
                    logger.error(f"  [ERRO] Falha ao copiar '{source_yaml_name}' para '{target_yaml_path}': {e}")
                    error_count += 1

    except Exception as e:
        logger.critical(f"Ocorreu um erro fatal e inesperado durante a execução: {e}", exc_info=True)
    finally:
        logger.info("\n" + "=" * 60)
        logger.info("PROCESSO DE SINCRONIZAÇÃO FINALIZADO")
        if 'sync_count' in locals():
            logger.info(
                f"Resumo: {sync_count} arquivos sincronizados, {skip_count} já atualizados, {error_count} erros.")
        logger.info("=" * 60)


def main():
    """Ponto de entrada para execução autônoma do script."""
    logger = setup_logging()
    executar_sincronizacao(logger)


if __name__ == "__main__":
    main()
