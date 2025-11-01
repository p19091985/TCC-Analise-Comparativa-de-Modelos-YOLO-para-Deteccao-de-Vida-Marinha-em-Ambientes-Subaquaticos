# Análise Comparativa de Modelos YOLO para Detecção de Vida Marinha

Este projeto contém o pipeline automatizado, modular e reprodutível para o artigo "Análise Comparativa de Modelos YOLO para Detecção de Vida Marinha em Ambientes Subaquáticos".

## Visão Geral

O objetivo deste pipeline é fornecer um fluxo de trabalho completo, desde a aquisição de dados até o treinamento e avaliação de diferentes modelos de detecção de objetos (YOLO e RT-DETR) para a tarefa de identificar vida marinha. A estrutura foi refatorada para máxima modularidade, manutenibilidade e clareza, alinhando-se diretamente com a metodologia da pesquisa.

## Estrutura do Projeto

* **`config/`**: Contém arquivos de configuração centralizados para caminhos (`paths.py`) e hiperparâmetros de treinamento (`training_params.py`).
* **`utils/`**: Módulos de utilidade, como a configuração centralizada de logs (`logger_config.py`).
* **`01_data_preprocessing/`**: Scripts para o Módulo 1 (Integração e Pré-processamento de Dados).
* **`02_model_training/`**: Scripts para o Módulo 2 (Treinamento de Modelos e Avaliação).
* **`03_results_analysis/`**: Scripts e ferramentas para o Módulo 3 (Análise e Visualização de Resultados), incluindo o visualizador de tabela.
* **`gui/`**: Contém o painel de controle principal da aplicação (`main_dashboard.py`).
* **`data/`**: (Gerado automaticamente) Contém os datasets baixados e processados.
* **`output/`**: (Gerado automaticamente) Contém todos os artefatos gerados: logs, relatórios e os resultados dos treinamentos (`runs`).

## Como Utilizar

### 1. Pré-requisitos
- Python 3.8+
- Git

### 2. Instalação

Clone o repositório e instale as dependências necessárias. É altamente recomendado usar um ambiente virtual.

```bash
# Clone o projeto
git clone <URL_DO_SEU_REPOSITORIO>
cd <NOME_DA_PASTA_DO_PROJETO>

# Crie e ative um ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate  # No Linux/macOS
# venv\Scripts\activate   # No Windows

# Instale as dependências
pip install -r requirements.txt