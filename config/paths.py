"""
Centraliza todos os caminhos de diretórios para fácil manutenção e consistência.
"""
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(ROOT_DIR, "data")

DOWNLOADS_DIR = os.path.join(DATA_DIR, "downloads")

UNZIPPED_DIR = os.path.join(DATA_DIR, "dataset_descompactado")

YAML_REPO_DIR = os.path.join(ROOT_DIR, 'yamlRepositorio')

OUTPUT_DIR = os.path.join(ROOT_DIR, "output")

LOGS_DIR = os.path.join(OUTPUT_DIR, 'logs')

RUNS_DIR = os.path.join(OUTPUT_DIR, 'runs', 'detect')

REPORTS_DIR = os.path.join(OUTPUT_DIR, 'reports')

EVAL_DIR = os.path.join(OUTPUT_DIR, 'evaluations')

def create_project_structure():
    """
    Garante que toda a estrutura de diretórios necessária para o projeto exista.
    Deve ser chamada no início do pipeline principal.
    """
    print("Verificando e criando a estrutura de diretórios do projeto...")
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(UNZIPPED_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(RUNS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
                                   
    os.makedirs(EVAL_DIR, exist_ok=True)                                       
                                
    print("Estrutura de diretórios pronta.")