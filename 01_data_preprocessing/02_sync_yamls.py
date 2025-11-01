                       
"""
Módulo 1, Etapa 2: Sincronização de arquivos de configuração YAML.
Esta versão gera os arquivos data.yaml com caminhos RELATIVOS corretos
a partir da raiz do projeto, garantindo portabilidade.
"""
import os
import sys
import logging
import yaml

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from config.paths import UNZIPPED_DIR, YAML_REPO_DIR, ROOT_DIR
from utils.logger_config import setup_logging

def main():
    """Função principal que executa a lógica de sincronização dos YAMLs."""
    logger = setup_logging('YamlSyncLogger', __file__)

    try:
        logger.info("=" * 60)
        logger.info("INICIANDO SCRIPT DE SINCRONIZAÇÃO INTELIGENTE DE YAMLs (COM CAMINHOS RELATIVOS)")
        logger.info("=" * 60)

        if not os.path.exists(YAML_REPO_DIR):
            logger.error(f"ERRO: O repositório de YAMLs '{YAML_REPO_DIR}' não foi encontrado. Abortando.")
            return

        if not os.path.exists(UNZIPPED_DIR):
            logger.error(f"ERRO: O diretório de datasets '{UNZIPPED_DIR}' não foi encontrado. Abortando.")
            return

        sync_count = 0
        error_count = 0

        for source_yaml_name in os.listdir(YAML_REPO_DIR):
            if not source_yaml_name.endswith('.yaml'):
                continue

            source_yaml_path = os.path.join(YAML_REPO_DIR, source_yaml_name)
            target_dataset_name = os.path.splitext(source_yaml_name)[0]
            target_dataset_dir = os.path.join(UNZIPPED_DIR, target_dataset_name)

            logger.info(f"\n--- Processando: {source_yaml_name} ---")

            if not os.path.exists(target_dataset_dir):
                logger.warning(f"  [AVISO] Diretório de destino '{target_dataset_dir}' não existe. Pulando.")
                continue

            target_yaml_path = os.path.join(target_dataset_dir, 'data.yaml')

            try:
                with open(source_yaml_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                relative_path = os.path.relpath(target_dataset_dir, ROOT_DIR)
                                                                                              
                data['path'] = relative_path.replace(os.sep, '/')

                data['train'] = 'train/images'
                data['val'] = 'valid/images'
                data['test'] = 'test/images'

                with open(target_yaml_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, sort_keys=False, default_flow_style=None)

                logger.info(
                    f"  [SINCRONIZADO] Arquivo '{target_yaml_path}' gerado com caminho relativo: '{data['path']}'")
                sync_count += 1

            except Exception as e:
                logger.error(f"  [ERRO] Falha ao processar e salvar '{source_yaml_name}': {e}")
                error_count += 1

    except Exception as e:
        logger.critical(f"Ocorreu um erro fatal e inesperado durante a execução: {e}", exc_info=True)
    finally:
        logger.info("\n" + "=" * 60)
        logger.info("PROCESSO DE SINCRONIZAÇÃO FINALIZADO")
        if 'sync_count' in locals():
            logger.info(f"Resumo: {sync_count} arquivos sincronizados, {error_count} erros.")
        logger.info("=" * 60)

if __name__ == "__main__":
    main()