                       
"""
Módulo 1, Etapa 3 (Opcional): Redução de datasets para testes rápidos.
(Baseado no arquivo original: reduzir_dataset.py)
"""
import os
import random
import sys
import logging
from typing import Dict, Set

from config.paths import UNZIPPED_DIR
from utils.logger_config import setup_logging

REDUCTION_FACTOR = 0.1

def get_class_map(labels_path: str) -> Dict[int, Set[str]]:
    """
    Escaneia todos os arquivos de anotação para mapear cada classe aos
    arquivos de imagem que a contêm.
    """
    class_map = {}
    if not os.path.exists(labels_path):
        return class_map

    for label_file in os.listdir(labels_path):
        if not label_file.endswith('.txt'):
            continue

        filepath = os.path.join(labels_path, label_file)
        base_name = os.path.splitext(label_file)[0]

        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if not lines:
                continue

            for line in lines:
                try:
                    class_id = int(line.split()[0])
                    if class_id not in class_map:
                        class_map[class_id] = set()
                    class_map[class_id].add(base_name)
                except (ValueError, IndexError):
                    continue
    return class_map

def reduce_split(dataset_path: str, split_name: str, logger: logging.Logger):
    """
    Reduz um único subconjunto (train, valid, test) de um dataset, garantindo
    a representação de todas as classes.
    """
    images_path = os.path.join(dataset_path, split_name, 'images')
    labels_path = os.path.join(dataset_path, split_name, 'labels')

    if not os.path.exists(images_path) or not os.path.exists(labels_path):
        logger.warning(f"  O subconjunto '{split_name}' não foi encontrado ou está incompleto. Pulando.")
        return

    all_image_files = [f for f in os.listdir(images_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not all_image_files:
        logger.info(f"  O subconjunto '{split_name}' não contém imagens. Pulando.")
        return

    original_count = len(all_image_files)
    target_count = max(1, int(original_count * REDUCTION_FACTOR))

    logger.info(f"  Processando '{split_name}': {original_count} imagens -> alvo de {target_count} imagens.")

    class_map = get_class_map(labels_path)
    files_to_keep_base_names: Set[str]

    if not class_map:
        logger.warning(f"  Nenhuma anotação encontrada em '{split_name}'. Realizando amostragem aleatória simples.")
        files_to_keep_base_names = {os.path.splitext(f)[0] for f in
                                    random.sample(all_image_files, min(target_count, original_count))}
    else:
        must_keep_base_names = set()
        for class_id, files in class_map.items():
            if files:
                chosen_file = random.choice(list(files))
                must_keep_base_names.add(chosen_file)

        remaining_files_pool = {os.path.splitext(f)[0] for f in all_image_files} - must_keep_base_names
        num_to_add = target_count - len(must_keep_base_names)

        if num_to_add > 0 and len(remaining_files_pool) > 0:
            num_to_sample = min(num_to_add, len(remaining_files_pool))
            randomly_added_files = random.sample(list(remaining_files_pool), num_to_sample)
            files_to_keep_base_names = must_keep_base_names.union(set(randomly_added_files))
        else:
            files_to_keep_base_names = must_keep_base_names

    images_deleted_count = 0
    labels_deleted_count = 0
    all_image_base_names = {os.path.splitext(f)[0] for f in all_image_files}

    for base_name in all_image_base_names:
        if base_name not in files_to_keep_base_names:
            for ext in ['.png', '.jpg', '.jpeg']:
                img_path_to_remove = os.path.join(images_path, base_name + ext)
                if os.path.exists(img_path_to_remove):
                    os.remove(img_path_to_remove)
                    images_deleted_count += 1
                    break

            label_file_path = os.path.join(labels_path, base_name + '.txt')
            if os.path.exists(label_file_path):
                os.remove(label_file_path)
                labels_deleted_count += 1

    final_count = original_count - images_deleted_count
    logger.info(
        f"  Redução concluída para '{split_name}': {images_deleted_count} imagens e {labels_deleted_count} anotações removidas.")
    logger.info(f"  -> Total final: {final_count} imagens.")

def main():
    """
    Função principal que executa a lógica de redução dos datasets.
    """
    logger = setup_logging('DatasetReducerLogger', __file__)

    try:
        logger.info("=" * 60)
        logger.info("INICIANDO SCRIPT DE REDUÇÃO INTELIGENTE DE DATASETS")
        logger.info(f"Os datasets serão reduzidos para manter aproximadamente {REDUCTION_FACTOR * 100:.0f}% dos dados.")
        logger.warning("ESTE SCRIPT MODIFICA OS DATASETS DIRETAMENTE.")
        logger.info("=" * 60)

        if not os.path.exists(UNZIPPED_DIR):
            logger.error(f"ERRO: Diretório de datasets '{UNZIPPED_DIR}' não encontrado.")
            return

        for dataset_name in sorted(os.listdir(UNZIPPED_DIR)):
            dataset_path = os.path.join(UNZIPPED_DIR, dataset_name)
            if not os.path.isdir(dataset_path):
                continue

            logger.info(f"\n--- Processando dataset: {dataset_name} ---")

            yaml_path = os.path.join(dataset_path, 'data.yaml')
            if not os.path.exists(yaml_path):
                logger.warning(
                    f"AVISO: Arquivo 'data.yaml' não encontrado em '{dataset_path}'. Pulando este diretório.")
                continue

            reduce_split(dataset_path, 'train', logger)
            reduce_split(dataset_path, 'valid', logger)
            reduce_split(dataset_path, 'test', logger)

    except Exception as e:
        logger.critical(f"Ocorreu um erro fatal e inesperado durante a execução: {e}", exc_info=True)
    finally:
        logger.info("\n" + "=" * 60)
        logger.info("PROCESSO DE REDUÇÃO DE DATASETS FINALIZADO")
        logger.info("=" * 60)

if __name__ == "__main__":
    main()