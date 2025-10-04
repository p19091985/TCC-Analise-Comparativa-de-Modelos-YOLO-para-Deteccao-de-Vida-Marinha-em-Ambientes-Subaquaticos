import os
import sys
import requests
import zipfile
import logging
import datetime
import shutil

# --- CONFIGURAÇÃO GLOBAL ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
UNZIP_DESTINATION_DIR = os.path.join(ROOT_DIR, "dataset_descompactado")
LOGS_DIR = os.path.join(ROOT_DIR, 'logs')  # Pasta de logs centralizada

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


def setup_logging():
    """
    CORREÇÃO: Configura o logger para salvar em 'logs/nomeDoScript_timestamp.log'.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    log_filename = f"{script_name}_{timestamp}.log"
    log_filepath = os.path.join(LOGS_DIR, log_filename)

    log_format = "%(asctime)s - %(levelname)s - %(message)s"

    logger = logging.getLogger('DataPrepLogger')
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


def pre_check_sources(logger):
    logger.info("--- INICIANDO PRÉ-VERIFICAÇÃO DE FONTES DE DADOS ---")
    failed_links = []
    for dataset in DATASETS_CONFIG:
        name, source = dataset["name"], dataset["source"]
        try:
            response = requests.head(source, timeout=20, allow_redirects=True)
            response.raise_for_status()
            logger.info(f"VERIFICANDO [OK] - Link para '{name}' está acessível.")
        except requests.exceptions.RequestException as e:
            logger.error(f"VERIFICANDO [FALHA] - Link para '{name}' está inacessível.")
            logger.error(f"  -> Detalhes: {e}")
            failed_links.append(name)

    if failed_links:
        logger.error(f"--- PRÉ-VERIFICAÇÃO FALHOU: {len(failed_links)} FONTE(S) ESTÁ(ÃO) INACESSÍVEL(IS) ---")
        return False
    else:
        logger.info("--- PRÉ-VERIFICAÇÃO CONCLUÍDA: TODAS AS FONTES ESTÃO ACESSÍVEIS ---")
        return True


def download_dataset(dataset_info, logger):
    name = dataset_info['name']
    zip_path = os.path.join(ROOT_DIR, dataset_info['zip_name'])

    logger.info(f"Iniciando download de '{name}'...")
    try:
        with requests.get(dataset_info["source"], stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(zip_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.info(f"Download de '{name}' concluído com sucesso e salvo como '{dataset_info['zip_name']}'.")
        return True
    except Exception as e:
        logger.error(f"Ocorreu um erro crítico durante o download de '{name}': {e}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
            logger.info(f"Arquivo parcial '{dataset_info['zip_name']}' foi removido.")
        return False


def unzip_dataset(dataset_info, logger):
    zip_path = os.path.join(ROOT_DIR, dataset_info["zip_name"])
    final_folder_path = os.path.join(UNZIP_DESTINATION_DIR, dataset_info["unzipped_folder_name"])

    if os.path.exists(final_folder_path):
        logger.info(f"Pasta de destino '{dataset_info['unzipped_folder_name']}' já existe. Descompactação ignorada.")
        return

    temp_extract_dir = os.path.join(UNZIP_DESTINATION_DIR, f"__temp_{dataset_info['zip_name']}")

    logger.info(f"Iniciando descompactação de '{dataset_info['zip_name']}'...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)

        found_path = None
        for root, dirs, files in os.walk(temp_extract_dir):
            if dataset_info["unzipped_folder_name"] in dirs:
                found_path = os.path.join(root, dataset_info["unzipped_folder_name"])
                break

        if not found_path:
            extracted_items = os.listdir(temp_extract_dir)
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_extract_dir, extracted_items[0])):
                if extracted_items[0] == dataset_info["unzipped_folder_name"]:
                    found_path = os.path.join(temp_extract_dir, extracted_items[0])

        if not found_path or not os.path.exists(found_path):
            logger.error(
                f"ERRO: A pasta raiz '{dataset_info['unzipped_folder_name']}' não foi encontrada dentro do arquivo '{dataset_info['zip_name']}'.")
            return

        shutil.move(found_path, final_folder_path)
        logger.info(
            f"Arquivo '{dataset_info['zip_name']}' descompactado e organizado com sucesso em '{final_folder_path}'.")

    except zipfile.BadZipFile:
        logger.error(f"ERRO: O arquivo '{dataset_info['zip_name']}' está corrompido ou não é um ZIP válido.")
    except Exception as e:
        logger.error(f"ERRO: Ocorreu um erro inesperado ao descompactar '{dataset_info['zip_name']}': {e}")
    finally:
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)


def preparar_dados():
    logger = setup_logging()

    try:
        logger.info("=" * 60)
        logger.info("INICIANDO SCRIPT DE PREPARAÇÃO DE DADOS")
        logger.info("=" * 60)

        if ENABLE_PRE_CHECK:
            if not pre_check_sources(logger):
                while True:
                    resposta = input(
                        "AVISO: Um ou mais links falharam. Deseja tentar continuar mesmo assim? (s/n): ").lower().strip()
                    if resposta == 's':
                        logger.warning("Usuário escolheu continuar a execução apesar das falhas na pré-verificação.")
                        break
                    elif resposta == 'n':
                        logger.critical("Usuário escolheu abortar a execução.")
                        return
                    else:
                        print("Opção inválida. Por favor, digite 's' para sim ou 'n' para não.")
        else:
            logger.info("Pré-verificação de links está desabilitada.")

        os.makedirs(UNZIP_DESTINATION_DIR, exist_ok=True)

        for dataset in DATASETS_CONFIG:
            logger.info("-" * 50)
            zip_path = os.path.join(ROOT_DIR, dataset['zip_name'])

            if not os.path.exists(zip_path):
                download_success = download_dataset(dataset, logger)
                if not download_success:
                    logger.error(f"Download de '{dataset['name']}' falhou. Pulando para o próximo dataset.")
                    continue
            else:
                logger.info(f"Arquivo '{dataset['zip_name']}' já existe. Download ignorado.")

            unzip_dataset(dataset, logger)

    except Exception as e:
        logger.critical(f"Ocorreu um erro fatal e inesperado no script: {e}")
    finally:
        logger.info("=" * 60)
        logger.info("PROCESSO DE PREPARAÇÃO DE DADOS FINALIZADO")
        logger.info("=" * 60)


if __name__ == "__main__":
    preparar_dados()
