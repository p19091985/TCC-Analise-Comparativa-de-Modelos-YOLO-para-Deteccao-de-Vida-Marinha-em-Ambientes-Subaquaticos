"""
Orquestrador principal para a execução completa do pipeline de análise.

Oferece dois modos de operação:
1. MODO MENU (Padrão): Execute `python gui/run_pipeline_refactored.py`
   Uma interface de console interativa para controle granular.

2. MODO FLAG (Legado): Execute com flags (ex: `python gui/run_pipeline_refactored.py --skip-training`)
   Executa o pipeline original baseado em flags.
"""
import argparse
import sys
import os
import importlib
import subprocess
import platform

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from config import paths
from utils.logger_config import setup_logging

try:
    download_main = importlib.import_module("01_data_preprocessing.01_download_datasets").main
    sync_yamls_main = importlib.import_module("01_data_preprocessing.02_sync_yamls").main
    reduce_datasets_main = importlib.import_module("01_data_preprocessing.03_reduce_datasets").main
    merge_datasets_main = importlib.import_module("01_data_preprocessing.04_merge_datasets").main

    train_yolo_main = importlib.import_module("02_model_training.05_train_yolo_models").main
    train_rtdetr_main = importlib.import_module("02_model_training.06_train_rtdetr_models").main
    evaluate_main = importlib.import_module("02_model_training.07_evaluate_models_on_test_set").main

except ImportError as e:
    print(
        f"ERRO: Não foi possível importar um módulo do pipeline. Verifique se a estrutura de diretórios e os nomes dos arquivos estão corretos.")
    print(f"Detalhe do erro: {e}")
    sys.exit(1)

MENU_SCRIPTS = {
    "11": ("(M1) Download de Datasets", download_main),
    "12": ("(M1) Sincronizar YAMLs", sync_yamls_main),
    "13": ("(M1) Reduzir Datasets (10%)", reduce_datasets_main),
    "14": ("(M1) Unificar Datasets", merge_datasets_main),
    "21": ("(M2) Treinar Modelos YOLO", train_yolo_main),
    "22": ("(M2) Treinar Modelos RT-DETR", train_rtdetr_main),
    "23": ("(M2) Avaliar Modelos no Test Set", evaluate_main),
}

PIPELINE_COMPLETO = [
    download_main, sync_yamls_main, reduce_datasets_main, merge_datasets_main,
    train_yolo_main, train_rtdetr_main, evaluate_main
]

def clear_screen():
    """Limpa a tela do console."""
    command = 'cls' if platform.system().lower() == "windows" else 'clear'
    os.system(command)

def run_script(main_func, logger):
    """Executa uma única função .main() e reporta o status."""
    script_name = main_func.__module__
    logger.info(f"--- Iniciando script: {script_name} ---")
    try:
        main_func()
        logger.info(f"--- ✅ Sucesso: {script_name} concluído ---")
        return True
    except Exception as e:
        logger.critical(f"--- ❌ FALHA CRÍTICA: {script_name} falhou ---", exc_info=True)
        return False

def launch_streamlit(logger):
    """Lança o painel Streamlit em um processo separado."""
    logger.info("--- 🚀 Lançando o Painel de Resultados Streamlit... ---")
    logger.info("--- O painel abrirá no seu navegador padrão. ---")

    script_path = os.path.join(ROOT_DIR, "03_results_analysis", "08_streamlit_results_viewer.py")
    command = [sys.executable, "-m", "streamlit", "run", script_path]
    try:
        subprocess.Popen(command, cwd=ROOT_DIR)
        logger.info(f"--- Comando executado: {' '.join(command)} ---")
    except Exception as e:
        logger.critical(f"--- ❌ ERRO CRÍTICO ao lançar Streamlit: {e} ---")

def run_menu():
    """Exibe o menu interativo principal."""
    paths.create_project_structure()
    logger = setup_logging('PipelineOrchestrator_Menu', __file__)

    while True:
        clear_screen()
        print("================================================================")
        print("###   Pipeline de Análise de Detecção Marinha (TCC-YOLO)   ###")
        print("================================================================")
        print("\nOpções Principais:")
        print("  [1] Executar Pipeline Completo (com Visualização no final)")
        print("  [2] Executar Pipeline Completo (sem Visualização)")

        print("\n--- Módulo 1: Pré-processamento ---")
        print("  [11] 01_download_datasets.py")
        print("  [12] 02_sync_yamls.py")
        print("  [13] 03_reduce_datasets.py (Opcional, 10% dos dados)")
        print("  [14] 04_merge_datasets.py")

        print("\n--- Módulo 2: Treinamento e Avaliação ---")
        print("  [21] 05_train_yolo_models.py")
        print("  [22] 06_train_rtdetr_models.py")
        print("  [23] 07_evaluate_models_on_test_set.py")

        print("\n--- Módulo 3: Análise de Resultados ---")
        print("  [31] Lançar Visualizador Streamlit")

        print("\n  [Q] Sair")
        print("================================================================")

        choice = input("Escolha uma opção: ").strip().lower()

        if choice == 'q':
            print("Saindo...")
            break

        elif choice == '1' or choice == '2':
                                        
            logger.info("############################################################")
            logger.info("### INICIANDO PIPELINE COMPLETO (MODO MENU) ###")
            logger.info("############################################################")
            success = True
            for main_func in PIPELINE_COMPLETO:
                if not run_script(main_func, logger):
                    success = False
                    logger.error("Pipeline interrompido devido a falha.")
                    break

            if success and choice == '1':
                logger.info("Pipeline concluído. Lançando visualizador...")
                launch_streamlit(logger)
            elif success and choice == '2':
                logger.info("Pipeline concluído (sem visualização).")

            input("\nPressione Enter para voltar ao menu...")

        elif choice == '31':
            launch_streamlit(logger)
            input("\nPressione Enter para voltar ao menu...")

        elif choice in MENU_SCRIPTS:
            script_name, main_func = MENU_SCRIPTS[choice]
            logger.info(f"--- Executando script individual: {script_name} ---")
            run_script(main_func, logger)
            input("\nPressione Enter para voltar ao menu...")

        else:
            print(f"Opção '{choice}' inválida. Tente novamente.")
            time.sleep(1)

def run_with_flags(args, logger):
    """
    Orquestra a execução do pipeline com base em flags CLI (modo legado).
    """
    logger.info("############################################################")
    logger.info("### INICIANDO PIPELINE (MODO FLAG) ###")
    logger.info("############################################################")
    logger.info(f"Argumentos recebidos: {args}")

    try:
        if not args.skip_preprocessing:
            logger.info("\n>>> EXECUTANDO MÓDULO 1: PRÉ-PROCESSAMENTO DE DADOS <<<\n")
            download_main()
            sync_yamls_main()
            if not args.no_reduce:
                reduce_datasets_main()
            else:
                logger.info("Etapa de redução de datasets pulada conforme solicitado (--no-reduce).")
            merge_datasets_main()
        else:
            logger.warning("MÓDULO 1: Pré-processamento de dados pulado conforme solicitado (--skip-preprocessing).")

        if not args.skip_training:
            logger.info("\n>>> EXECUTANDO MÓDULO 2: TREINAMENTO DE MODELOS <<<\n")
            train_yolo_main()
            train_rtdetr_main()
        else:
            logger.warning("MÓDULO 2: Treinamento de modelos pulado conforme solicitado (--skip-training).")

        if not args.skip_evaluation:
            logger.info("\n>>> EXECUTANDO MÓDULO 2 (Etapa Final): AVALIAÇÃO FINAL <<<\n")
            evaluate_main()
        else:
            logger.warning("AVALIAÇÃO FINAL: Etapa pulada conforme solicitado (--skip-evaluation).")

    except Exception as e:
        logger.critical("Ocorreu um erro fatal no pipeline!", exc_info=True)
        print(f"\nERRO FATAL: O pipeline foi interrompido. Verifique o último log em 'output/logs/' para detalhes.")
    finally:
        logger.info("\n############################################################")
        logger.info("### PIPELINE (MODO FLAG) FINALIZADO ###")
        logger.info("############################################################")

def main():
    """
    Ponto de entrada principal.
    Verifica se flags CLI foram passadas. Se sim, usa o modo flag.
    Se não, chama o modo menu.
    """

    if len(sys.argv) > 1:
                           
        paths.create_project_structure()
        logger = setup_logging('PipelineOrchestrator_Flags', __file__)

        parser = argparse.ArgumentParser(description="Pipeline para Análise Comparativa de Modelos de Detecção Marinha")
        parser.add_argument('--skip-preprocessing', action='store_true',
                            help="Pula todo o módulo de pré-processamento de dados.")
        parser.add_argument('--skip-training', action='store_true', help="Pula o módulo de treinamento de modelos.")
        parser.add_argument('--skip-evaluation', action='store_true',
                            help="Pula a avaliação final no conjunto de teste.")
        parser.add_argument('--no-reduce', action='store_true', help="Pula a etapa opcional de redução de datasets.")
        args = parser.parse_args()

        run_with_flags(args, logger)

    else:
                           
        run_menu()

if __name__ == "__main__":
    main()