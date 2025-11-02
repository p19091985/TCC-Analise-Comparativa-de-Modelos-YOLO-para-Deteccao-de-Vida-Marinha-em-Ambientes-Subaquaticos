                       

import os
import sys
import logging
import shutil
import yaml

ROOT_DIR_FOR_IMPORT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR_FOR_IMPORT)

from config.paths import UNZIPPED_DIR, ROOT_DIR
from utils.logger_config import setup_logging

UNIFIED_DATASET_NAME = 'unificacaoDosOceanos'
UNIFIED_DATASET_DIR = os.path.join(UNZIPPED_DIR, UNIFIED_DATASET_NAME)

CLASS_MERGE_MAP = {
    'stingray': 'ray'
}

def create_unified_structure(logger: logging.Logger):
    """Cria a estrutura de diretórios para o dataset unificado."""
    logger.info(f"Criando a estrutura de diretórios em '{UNIFIED_DATASET_DIR}'...")
    if os.path.exists(UNIFIED_DATASET_DIR):
        logger.warning(
            f"O diretório '{UNIFIED_DATASET_DIR}' já existe. Ele será removido e recriado para garantir uma unificação limpa.")
        shutil.rmtree(UNIFIED_DATASET_DIR)

    for split in ['train', 'valid', 'test']:
        os.makedirs(os.path.join(UNIFIED_DATASET_DIR, split, 'images'), exist_ok=True)
        os.makedirs(os.path.join(UNIFIED_DATASET_DIR, split, 'labels'), exist_ok=True)
    logger.info("Estrutura de diretórios criada com sucesso.")

def process_and_copy_files(source_dataset_name: str, split: str, local_class_map: dict, master_class_map: dict,
                           logger: logging.Logger):
    """Copia imagens e remapeia arquivos de anotação para um subconjunto."""
    logger.info(f"  Processando subconjunto '{split}' de '{source_dataset_name}'...")

    source_images_dir = os.path.join(UNZIPPED_DIR, source_dataset_name, split, 'images')
    source_labels_dir = os.path.join(UNZIPPED_DIR, source_dataset_name, split, 'labels')

    if not os.path.exists(source_images_dir):
        logger.warning(f"    Diretório de imagens não encontrado em '{source_images_dir}'. Pulando.")
        return

    image_files = [f for f in os.listdir(source_images_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    copied_count = 0
    for image_file in image_files:
        source_image_path = os.path.join(source_images_dir, image_file)
        new_image_name = f"{source_dataset_name}_{image_file}"
        dest_image_path = os.path.join(UNIFIED_DATASET_DIR, split, 'images', new_image_name)
        shutil.copy2(source_image_path, dest_image_path)

        base_name = os.path.splitext(image_file)[0]
        source_label_path = os.path.join(source_labels_dir, f"{base_name}.txt")

        if os.path.exists(source_label_path):
            new_label_name = f"{source_dataset_name}_{base_name}.txt"
            dest_label_path = os.path.join(UNIFIED_DATASET_DIR, split, 'labels', new_label_name)

            with open(source_label_path, 'r', encoding='utf-8') as f_in, open(dest_label_path, 'w',
                                                                              encoding='utf-8') as f_out:
                for line in f_in:
                    parts = line.strip().split()
                    if not parts: continue

                    try:
                        old_class_id = int(parts[0])
                        coords = " ".join(parts[1:])

                        unified_class_name = local_class_map.get(old_class_id)
                        if unified_class_name:
                            new_class_id = master_class_map[unified_class_name]
                            f_out.write(f"{new_class_id} {coords}\n")
                        else:
                            logger.warning(
                                f"ID de classe inválido ({old_class_id}) encontrado em '{source_label_path}'. Linha ignorada.")
                    except (ValueError, IndexError):
                        logger.warning(
                            f"Linha mal formatada em '{source_label_path}': '{line.strip()}'. Linha ignorada.")
        copied_count += 1

    logger.info(f"    Concluído: {copied_count} imagens e suas anotações foram processadas e copiadas.")

def main():
    """Função principal que executa a lógica de unificação dos datasets."""
    logger = setup_logging('DatasetUnifierLogger', __file__)

    try:
        logger.info("=" * 60)
        logger.info("INICIANDO SCRIPT DE UNIFICAÇÃO DE DATASETS YOLO")
        logger.info("=" * 60)

        if not os.path.exists(UNZIPPED_DIR):
            logger.error(f"ERRO: Diretório de origem '{UNZIPPED_DIR}' não foi encontrado. Abortando.")
            return

        logger.info("--- Etapa 1: Analisando datasets de origem e unificando classes ---")
        source_datasets_info = []
        all_class_names = set()

        dataset_names_to_process = [d for d in sorted(os.listdir(UNZIPPED_DIR)) if
                                    os.path.isdir(os.path.join(UNZIPPED_DIR, d))]

        if UNIFIED_DATASET_NAME in dataset_names_to_process:
            logger.info(
                f"Ignorando o diretório '{UNIFIED_DATASET_NAME}' previamente existente no processo de unificação.")
            dataset_names_to_process.remove(UNIFIED_DATASET_NAME)

        for dataset_name in dataset_names_to_process:
            yaml_path = os.path.join(UNZIPPED_DIR, dataset_name, 'data.yaml')
            if os.path.exists(yaml_path):
                logger.info(f"Lendo '{yaml_path}'...")
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    class_names = data.get('names', [])
                    if class_names:
                        local_class_map = {}
                        for i, name in enumerate(class_names):
                            processed_name = name.lower().strip()
                            final_name = CLASS_MERGE_MAP.get(processed_name, processed_name)
                            if final_name != processed_name:
                                logger.info(f"  -> Regra de fusão aplicada: '{processed_name}' -> '{final_name}'")
                            local_class_map[i] = final_name
                            all_class_names.add(final_name)
                        source_datasets_info.append({'name': dataset_name, 'local_map': local_class_map})
            else:
                logger.warning(f"AVISO: 'data.yaml' não encontrado para o dataset '{dataset_name}'. Ele será ignorado.")

        master_class_list = sorted(list(all_class_names))
        master_class_map = {name: i for i, name in enumerate(master_class_list)}

        logger.info(f"Unificação de classes concluída. Total de classes únicas: {len(master_class_list)}")
        logger.info(f"Lista de classes mestra: {master_class_list}")

        create_unified_structure(logger)

        logger.info("\n--- Etapa 2: Copiando imagens e remapeando anotações ---")
        for source_info in source_datasets_info:
            for split in ['train', 'valid', 'test']:
                process_and_copy_files(source_info['name'], split, source_info['local_map'], master_class_map, logger)

        logger.info("\n--- Etapa 3: Gerando arquivo 'data.yaml' para o dataset unificado ---")
        final_yaml_path = os.path.join(UNIFIED_DATASET_DIR, 'data.yaml')

        relative_path_to_unified_dir = os.path.relpath(UNIFIED_DATASET_DIR, ROOT_DIR)

        final_yaml_content = {
                                                                        
            'path': relative_path_to_unified_dir.replace(os.sep, '/'),
                                                       
            'train': 'train/images',
            'val': 'valid/images',
            'test': 'test/images',
            'nc': len(master_class_list),
            'names': master_class_list
        }

        with open(final_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(final_yaml_content, f, sort_keys=False, default_flow_style=False)
        logger.info(f"Arquivo '{final_yaml_path}' gerado com sucesso com caminho relativo.")

    except Exception as e:
        logger.critical(f"Ocorreu um erro fatal e inesperado durante a execução: {e}", exc_info=True)
    finally:
        logger.info("\n" + "=" * 60)
        logger.info("PROCESSO DE UNIFICAÇÃO DE DATASETS FINALIZADO")
        logger.info("=" * 60)

if __name__ == "__main__":
    main()