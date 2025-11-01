"""
Módulo 2, Etapa 2: Avaliação final dos modelos treinados no conjunto de teste.
(Baseado no arquivo original: avaliacao_test_com_modelo.py)
"""
import sys
import json
import logging
import platform
import datetime
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import torch
    import yaml
    from ultralytics import YOLO
    from ultralytics.utils import __version__ as ultralytics_version
except ImportError:
    print("\n[ERRO] Bibliotecas essenciais não encontradas (torch, ultralytics, pyyaml).")
    print("[AÇÃO] Por favor, ative seu ambiente e instale as dependências: pip install torch ultralytics pyyaml")
    sys.exit(1)

# --- INÍCIO DA MODIFICAÇÃO ---
# Adicionado EVAL_DIR à importação
from config.paths import RUNS_DIR, UNZIPPED_DIR, REPORTS_DIR, ROOT_DIR, EVAL_DIR
# --- FIM DA MODIFICAÇÃO ---
from utils.logger_config import setup_logging

class ValidadorAbsoluto:

    def __init__(self):
        # Este diretório é para LER os modelos treinados
        self.diretorio_runs = Path(RUNS_DIR)
        self.diretorio_datasets = Path(UNZIPPED_DIR)
        # Este diretório é para SALVAR o relatório .txt
        self.reports_dir = Path(REPORTS_DIR)
        self.root_dir = Path(ROOT_DIR)
        self.timestamp_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # --- INÍCIO DA MODIFICAÇÃO ---
        # Novo diretório para SALVAR os artefatos da avaliação (gráficos, etc.)
        self.eval_dir = Path(EVAL_DIR)
        # --- FIM DA MODIFICAÇÃO ---

        self.logger = setup_logging('FinalEvaluatorLogger', __file__)

        # Garante que as pastas de saída existam
        try:
            os.makedirs(self.reports_dir, exist_ok=True)
            # --- INÍCIO DA MODIFICAÇÃO ---
            os.makedirs(self.eval_dir, exist_ok=True) # Garante que a pasta de avaliação exista
            # --- FIM DA MODIFICAÇÃO ---
        except Exception as e:
            self.logger.critical(f"Não foi possível criar diretórios de saída: {e}", exc_info=True)
            sys.exit(1)

        self.artefato_final = self._criar_estrutura_artefato()

    def _obter_metadata_ambiente(self) -> Dict[str, Any]:
        gpu_disponivel = torch.cuda.is_available()
        return {
            "timestamp_execucao_utc": self.timestamp_utc,
            "plataforma": platform.system(),
            "arquitetura_plataforma": platform.machine(),
            "versao_python": platform.python_version(),
            "versao_torch": torch.__version__,
            "versao_ultralytics": ultralytics_version,
            "gpu_disponivel": gpu_disponivel,
            "dispositivo_torch": torch.cuda.get_device_name(0) if gpu_disponivel else "CPU",
            "versao_cuda_torch": torch.version.cuda if gpu_disponivel else "N/A"
        }

    def _criar_estrutura_artefato(self) -> Dict[str, Any]:
        return {
            "metadata_ambiente": self._obter_metadata_ambiente(),
            "resultados_validacao": []
        }

    def _identificar_candidatos(self) -> List[Dict[str, Path]]:
        self.logger.info(f"Iniciando varredura por candidatos em '{self.diretorio_runs}'")
        candidatos = []
        if not self.diretorio_runs.is_dir():
            self.logger.critical(f"O diretório de runs especificado não existe: '{self.diretorio_runs}'")
            return []

        for diretorio_run in self.diretorio_runs.iterdir():
            if not diretorio_run.is_dir():
                continue

            modelo_path = diretorio_run / 'weights' / 'best.pt'
            if modelo_path.is_file():
                candidatos.append({"run_dir": diretorio_run, "model_path": modelo_path})
                self.logger.info(f"Candidato identificado: {modelo_path}")
            else:
                self.logger.warning(f"Diretório '{diretorio_run.name}' não contém 'weights/best.pt'. Ignorando.")

        self.logger.info(f"Varredura concluída. Total de {len(candidatos)} candidatos identificados.")
        return candidatos

    def _extrair_nome_dataset(self, nome_diretorio_run: str) -> Optional[str]:
        try:
            parte_depois_on = nome_diretorio_run.split('_on_')[1]
            componentes = parte_depois_on.rsplit('_', 2)
            if len(componentes) > 1:
                nome_dataset = componentes[0]
                self.logger.info(f"Nome do dataset extraído: '{nome_dataset}' de '{nome_diretorio_run}'")
                return nome_dataset
            else:
                raise IndexError("Padrão de nome de pasta inesperado.")
        except IndexError:
            self.logger.warning(
                f"Não foi possível determinar o nome do dataset a partir de '{nome_diretorio_run}'.")
            return None
        except Exception:
            self.logger.exception(f"Erro inesperado ao extrair nome do dataset de '{nome_diretorio_run}'.")
            return None

    def _carregar_detalhes_dataset(self, nome_dataset: str) -> Optional[Dict[str, Any]]:
        caminho_yaml_absoluto = self.diretorio_datasets / nome_dataset / 'data.yaml'
        if not caminho_yaml_absoluto.is_file():
            self.logger.error(
                f"Arquivo de configuração '{caminho_yaml_absoluto}' para o dataset '{nome_dataset}' não foi encontrado.")
            return None
        try:
            with open(caminho_yaml_absoluto, 'r', encoding='utf-8') as f:
                config_dataset = yaml.safe_load(f)

            caminho_yaml_relativo = os.path.relpath(caminho_yaml_absoluto, self.root_dir)

            config_dataset['caminho_yaml_absoluto'] = str(caminho_yaml_absoluto)
            config_dataset['caminho_yaml_relativo'] = str(caminho_yaml_relativo)
            return config_dataset
        except yaml.YAMLError:
            self.logger.exception(f"Falha ao processar o arquivo YAML '{caminho_yaml_absoluto}'.")
            return None

    def _executar_validacao_para_candidato(self, candidato: Dict[str, Path]):
        run_dir = candidato['run_dir']
        model_path = candidato['model_path']
        dispositivo = '0' if self.artefato_final['metadata_ambiente']['gpu_disponivel'] else 'cpu'

        self.logger.info(f"--- Processando: {run_dir.name} ---")

        nome_dataset = self._extrair_nome_dataset(run_dir.name)
        if not nome_dataset:
            self._registrar_falha(run_dir.name, str(model_path), "Não foi possível determinar o dataset.")
            return

        detalhes_dataset = self._carregar_detalhes_dataset(nome_dataset)
        if not detalhes_dataset:
            self.logger.error(f"Falha ao carregar config do dataset '{nome_dataset}'.")
            self._registrar_falha(run_dir.name, str(model_path),
                                  f"Falha ao carregar config do dataset '{nome_dataset}'.")
            return

        resultado = {
            "status": "FALHA", "nome_run": run_dir.name, "caminho_modelo": str(model_path),
            "dataset": {"nome_identificado": nome_dataset,
                        "caminho_configuracao": detalhes_dataset.get('caminho_yaml_absoluto'),
                        "classes": detalhes_dataset.get('names', [])}
        }

        try:
            self.logger.info(f"Carregando modelo de '{model_path}'.")
            modelo = YOLO(str(model_path))

            self.logger.info(
                f"Iniciando validação no split 'test' do dataset '{nome_dataset}' usando dispositivo '{dispositivo}'.")

            # --- INÍCIO DA MODIFICAÇÃO ---
            # Define 'project' como o diretório de avaliação e 'name'
            # para criar uma subpasta com o nome do modelo que está sendo avaliado.
            metricas = modelo.val(data=detalhes_dataset['caminho_yaml_relativo'],
                                  split='test',
                                  device=dispositivo,
                                  project=str(self.eval_dir), # Salva em 'output/evaluations'
                                  name=f"{run_dir.name}_EVAL", # Subpasta ex: 'YOLOv5n_..._EVAL'
                                  exist_ok=True,
                                  verbose=False)
            # --- FIM DA MODIFICAÇÃO ---

            self.logger.info("Validação concluída com sucesso. Coletando métricas.")

            resultado.update({
                "status": "SUCESSO",
                "metricas_box": {"mAP50-95": metricas.box.map, "mAP50": metricas.box.map50, "mAP75": metricas.box.map75,
                                 "precisao": metricas.box.mp, "recall": metricas.box.mr},
                "metricas_velocidade_ms": metricas.speed
            })
            self.artefato_final["resultados_validacao"].append(resultado)
        except Exception as e:
            self.logger.error(f"Ocorreu um erro catastrófico durante a validação de '{run_dir.name}'.", exc_info=True)
            resultado["mensagem_erro"] = str(e)
            self.artefato_final["resultados_validacao"].append(resultado)

    def _registrar_falha(self, nome_run: str, caminho_modelo: str, motivo: str):
        self.logger.error(f"Falha registrada para '{nome_run}'. Motivo: {motivo}")
        self.artefato_final["resultados_validacao"].append({
            "status": "FALHA", "nome_run": nome_run, "caminho_modelo": caminho_modelo, "mensagem_erro": motivo
        })

    def _salvar_artefato(self):
        nome_base_relatorio = "relatorio_metricas_absolutas"
        nome_arquivo = f"{nome_base_relatorio}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        caminho_arquivo = self.reports_dir / nome_arquivo
        self.logger.info(f"Salvando relatório em formato TXT (CSV) em: {caminho_arquivo}")

        DELIMITADOR = ";"
        cabecalho = ["nome_run", "status", "dataset_nome", "mAP50_95", "mAP50", "mAP75", "precisao", "recall",
                     "velocidade_preprocess_ms", "velocidade_inference_ms", "velocidade_postprocess_ms",
                     "mensagem_erro"]

        try:
            with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                f.write(DELIMITADOR.join(cabecalho) + "\n")
                for resultado in self.artefato_final["resultados_validacao"]:
                    linha_dados = []
                    if resultado.get("status") == "SUCESSO":
                        metricas = resultado.get("metricas_box", {})
                        velocidade = resultado.get("metricas_velocidade_ms", {})
                        dataset_nome = resultado.get("dataset", {}).get("nome_identificado", "N/A")
                        linha_dados = [
                            resultado.get("nome_run", ""), resultado.get("status", "SUCESSO"), dataset_nome,
                            f"{metricas.get('mAP50-95', 0.0):.5f}", f"{metricas.get('mAP50', 0.0):.5f}",
                            f"{metricas.get('mAP75', 0.0):.5f}",
                            f"{metricas.get('precisao', 0.0):.5f}", f"{metricas.get('recall', 0.0):.5f}",
                            f"{velocidade.get('preprocess', 0.0):.3f}", f"{velocidade.get('inference', 0.0):.3f}",
                            f"{velocidade.get('postprocess', 0.0):.3f}", ""
                        ]
                        f.write(DELIMITADOR.join(linha_dados) + "\n") # Correção do erro de lógica anterior
                    else:
                        erro_msg = resultado.get('mensagem_erro', 'Erro desconhecido').replace("\n", " ").replace(
                            DELIMITADOR, ",")
                        dataset_nome = resultado.get("dataset", {}).get("nome_identificado", "N/A")
                        linha_dados = [
                            resultado.get("nome_run", ""), resultado.get("status", "FALHA"), dataset_nome,
                            "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", erro_msg
                        ]
                        # Correção do SyntaxError 'DELIMITA DOR'
                        f.write(DELIMITADOR.join(linha_dados) + "\n")
            self.logger.info("Relatório salvo com sucesso.")
        except Exception:
            self.logger.exception("Falha crítica ao salvar o relatório TXT.")

    def executar(self):
        self.logger.info("=" * 80)
        self.logger.info("INICIANDO PROCESSO DE VALIDAÇÃO ABSOLUTA")
        self.logger.info("=" * 80)
        candidatos = self._identificar_candidatos()
        if not candidatos:
            self.logger.warning("Nenhum candidato válido encontrado. O processo será encerrado.")
            return
        for idx, candidato in enumerate(candidatos):
            self.logger.info(f"Processando candidato {idx + 1}/{len(candidatos)}")
            self._executar_validacao_para_candidato(candidato)
            self.logger.info("-" * 80)
        self._salvar_artefato()
        self.logger.info("PROCESSO DE VALIDAÇÃO ABSOLUTA FINALIZADO")
        self.logger.info("=" * 80)

def main():
    """Ponto de entrada do script."""
    validador = ValidadorAbsoluto()
    validador.executar()

if __name__ == "__main__":
    main()