                       
"""
Módulo 1, Etapa 1: Download e descompactação de datasets.
(Baseado no arquivo original: preparação_de_dados.py)
VERSÃO COM LÓGICA DE DESCOMPACTAÇÃO CORRIGIDA.
"""
import os
import sys
import requests
import zipfile
import logging
import datetime
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from config.paths import DOWNLOADS_DIR, UNZIPPED_DIR
from utils.logger_config import setup_logging

ENABLE_PRE_CHECK = True

DATASETS_CONFIG = [
    {
        "name": "Underwater Object Detection",
        "source": "https://github.com/millercylindricalprojection/UnderwaterObjectDetectionDataset/raw/main/aquarium_pretrain.zip",
        "zip_name": "aquarium_pretrain.zip",
        "unzipped_folder_name": "aquarium_pretrain"
    },
    {
        "name": "FishInv Dataset",
        "source": "https://stpubtenakanclyw.blob.core.windows.net/marine-detect/FishInv-dataset.zip",
        "zip_name": "FishInv-dataset.zip",
        "unzipped_folder_name": "FishInvSplit"
    }
                                                 
]

def report_progress(percent_complete):
    """Função especial que imprime o progresso em um formato que a GUI pode ler."""
    import json
    print(json.dumps({"type": "progress", "value": percent_complete}))
    sys.stdout.flush()

def download_dataset(dataset_info, logger):
    name = dataset_info['name']
    zip_path = os.path.join(DOWNLOADS_DIR, dataset_info['zip_name'])

    logger.info(f"Iniciando download de '{name}'...")
    try:
        with requests.get(dataset_info["source"], stream=True, timeout=60) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded_size = 0
            chunk_size = 8192

            with open(zip_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        progress = int((downloaded_size / total_size) * 100)
                        if progress % 5 == 0:
                            report_progress(progress)

        report_progress(100)
        logger.info(f"Download de '{name}' concluído com sucesso.")
        return True
    except Exception as e:
        logger.error(f"Ocorreu um erro crítico durante o download de '{name}': {e}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return False

def unzip_dataset(dataset_info, logger):
    zip_path = os.path.join(DOWNLOADS_DIR, dataset_info["zip_name"])
    final_folder_path = os.path.join(UNZIPPED_DIR, dataset_info["unzipped_folder_name"])

    if os.path.exists(final_folder_path):
        logger.info(f"Pasta de destino '{dataset_info['unzipped_folder_name']}' já existe. Descompactação ignorada.")
        return

    temp_extract_dir = os.path.join(UNZIPPED_DIR, f"__temp_{dataset_info['zip_name']}")

    logger.info(f"Iniciando descompactação de '{dataset_info['zip_name']}' para diretório temporário...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)

        logger.info("Buscando pela pasta correta do dataset dentro da extração...")

        found_path = None
        for root, dirs, files in os.walk(temp_extract_dir):
            if dataset_info["unzipped_folder_name"] in dirs:
                found_path = os.path.join(root, dataset_info["unzipped_folder_name"])
                logger.info(f"Pasta do dataset encontrada em: {found_path}")
                break

        if not found_path:
                                                            
            extracted_items = os.listdir(temp_extract_dir)
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_extract_dir, extracted_items[0])):
                if extracted_items[0] == dataset_info["unzipped_folder_name"]:
                    found_path = os.path.join(temp_extract_dir, extracted_items[0])
                    logger.info(f"Pasta do dataset encontrada na raiz da extração: {found_path}")

        if not found_path or not os.path.exists(found_path):
            logger.error(
                f"ERRO CRÍTICO: A pasta do dataset '{dataset_info['unzipped_folder_name']}' não foi encontrada dentro do arquivo ZIP.")
            return

        shutil.move(found_path, final_folder_path)
        logger.info(f"Dataset organizado com sucesso em '{final_folder_path}'.")

    except zipfile.BadZipFile:
        logger.error(f"ERRO: O arquivo '{dataset_info['zip_name']}' está corrompido ou não é um ZIP válido.")
    except Exception as e:
        logger.error(f"ERRO: Ocorreu um erro inesperado ao descompactar '{dataset_info['zip_name']}': {e}",
                     exc_info=True)
    finally:
                                      
        if os.path.exists(temp_extract_dir):
            logger.info(f"Limpando diretório temporário '{temp_extract_dir}'...")
            shutil.rmtree(temp_extract_dir)

def main():
    """Função principal que orquestra o processo de preparação de dados."""
    logger = setup_logging('DataDownloadLogger', __file__)

    try:
        logger.info("=" * 60)
        logger.info("INICIANDO SCRIPT DE PREPARAÇÃO DE DADOS")
        logger.info("=" * 60)

        os.makedirs(UNZIPPED_DIR, exist_ok=True)
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)

        for dataset in DATASETS_CONFIG:
            logger.info("-" * 50)
            final_folder_path = os.path.join(UNZIPPED_DIR, dataset['unzipped_folder_name'])

            if not os.path.exists(final_folder_path):
                zip_path = os.path.join(DOWNLOADS_DIR, dataset['zip_name'])
                if not os.path.exists(zip_path):
                    download_success = download_dataset(dataset, logger)
                    if not download_success:
                        logger.error(f"Download de '{dataset['name']}' falhou. Pulando.")
                        continue
                else:
                    logger.info(f"Arquivo '{dataset['zip_name']}' já existe. Download ignorado.")

                unzip_dataset(dataset, logger)
            else:
                logger.info(f"Dataset '{dataset['unzipped_folder_name']}' já existe. Etapa ignorada.")

    except Exception as e:
        logger.critical(f"Ocorreu um erro fatal no script: {e}", exc_info=True)
    finally:
        logger.info("=" * 60)
        logger.info("PROCESSO DE PREPARAÇÃO DE DADOS FINALIZADO")
        logger.info("=" * 60)

if __name__ == "__main__":
    main()