"""
Módulo 2, Etapa 1: Treinamento dos modelos da família RT-DETR.
(Baseado no arquivo original: RT-DETR-L.py)
"""
import sys
import logging
import datetime
import csv
import time
import os
from pathlib import Path
from typing import List, Dict, Any

try:
    import torch
    from ultralytics import YOLO, RTDETR
except ImportError:
    print("\n[ERRO] Bibliotecas essenciais não encontradas (torch, ultralytics).")
    print("[AÇÃO] Por favor, ative seu ambiente e instale as dependências: pip install torch ultralytics pyyaml")
    sys.exit(1)

# MODIFICAÇÃO: Adicionado RUNS_DIR
from config.paths import UNZIPPED_DIR, REPORTS_DIR, ROOT_DIR, RUNS_DIR
from config.training_params import RTDETR_CONFIG
from utils.logger_config import setup_logging

class PipelineTreinamentoRTDETR:
    """
    Classe para encapsular todo o pipeline de treinamento, validação e relatório para RT-DETR.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_dataset_dir = Path(UNZIPPED_DIR)
        self.reports_dir = Path(REPORTS_DIR)
        self.root_dir = Path(ROOT_DIR)
        # MODIFICAÇÃO: Adicionado self.runs_dir
        self.runs_dir = Path(RUNS_DIR)
        self.timestamp = datetime.datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
        self.logger = setup_logging('RTDETR_Training_Logger', __file__)
        self.resultados = []

    def _verificar_ambiente(self) -> str:
        """Verifica a disponibilidade de GPU, datasets e modelos."""
        self.logger.info("--- INICIANDO VERIFICAÇÃO DO AMBIENTE ---")
        device = '0' if torch.cuda.is_available() else 'cpu'
        if device == '0':
            free_mem = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)
            self.logger.info(f"[OK] GPU (CUDA) detectada. Memória livre: {free_mem / 1e9:.2f} GB")
        else:
            self.logger.warning("[AVISO] Nenhuma GPU (CUDA) foi detectada. Treinamento será na CPU.")

        erros_encontrados = False
        for dataset_name in self.config["DATASETS_TO_TRAIN"]:
            config_path = self.base_dataset_dir / dataset_name / 'data.yaml'
            if not config_path.exists():
                self.logger.critical(f"[FALHA] 'data.yaml' para o dataset '{dataset_name}' não encontrado.")
                erros_encontrados = True

        for job in self.config["TRAINING_JOBS"]:
            try:
                YOLO(job['base_model'])
                self.logger.info(f"[OK] Modelo '{job['base_model']}' disponível.")
            except Exception as e:
                self.logger.critical(f"[FALHA] Modelo '{job['base_model']}' não disponível: {e}")
                erros_encontrados = True

        if erros_encontrados:
            self.logger.critical("Verificação do ambiente falhou. Abortando execução.")
            sys.exit(1)

        self.logger.info("[OK] Verificação do ambiente concluída com sucesso.")
        return device

    def _medir_latencia(self, model_path: str, device: str) -> float:
        """Mede a latência de inferência de um modelo."""
        try:
            self.logger.info(f"  Iniciando medição de latência para '{Path(model_path).name}'...")
            inference_device = int(device) if device.isdigit() else device

            model = YOLO(model_path)
            model.to(inference_device)
            dummy_input = torch.randn(1, 3, self.config['IMG_SIZE'], self.config['IMG_SIZE']).to(inference_device)

            for _ in range(self.config['LATENCY_WARMUPS']):
                model(dummy_input, verbose=False)

            latencies = []
            for _ in range(self.config['LATENCY_RUNS']):
                start = time.perf_counter()
                model(dummy_input, verbose=False)
                end = time.perf_counter()
                latencies.append((end - start) * 1000)

            avg_latency = sum(latencies) / len(latencies)
            self.logger.info(f"  Latência média de inferência: {avg_latency:.2f} ms.")
            return avg_latency
        except Exception as e:
            self.logger.error(f"  Falha ao medir a latência: {e}")
            return 0.0

    def _executar_job(self, job: Dict[str, Any], dataset_name: str, device: str):
        """Executa um único job de treinamento e coleta os resultados."""
        start_time = time.time()
        modelo_with_params = f"{job['modelo']}_{self.config['IMG_SIZE']}px_{self.config['NUM_EPOCHS']}e"
        run_name = f"{modelo_with_params}_on_{dataset_name}_{self.timestamp}"

        absolute_data_config_path = self.base_dataset_dir / dataset_name / 'data.yaml'
        relative_data_config_path = os.path.relpath(absolute_data_config_path, self.root_dir)

        resultado_job = {
            "modelo": modelo_with_params, "Dataset": dataset_name, "Base_Model": job['base_model'],
            "Status": "Failed", "mAP50_95": 0.0, "mAP50": 0.0, "Precision": 0.0,
            "Recall": 0.0, "F1_Score": 0.0, "Latency_ms": 0.0, "Training_Time_Min": 0.0,
            "Output_Dir": "N/A", "Error": "N/A"
        }

        try:
            self.logger.info(f"Carregando modelo base: {job['base_model']}")
            model = RTDETR(job['base_model'])

            self.logger.info(f"Iniciando treinamento do job '{modelo_with_params}' em '{dataset_name}'...")

            results = model.train(
                data=str(relative_data_config_path),
                epochs=self.config['NUM_EPOCHS'],
                patience=self.config['PATIENCE_EPOCHS'],
                batch=self.config['BATCH_SIZE'],
                optimizer=self.config['OPTIMIZER'],
                lr0=self.config['LEARNING_RATE'],
                device=device,
                imgsz=self.config['IMG_SIZE'],
                # MODIFICAÇÃO: Adicionado 'project' para salvar em output/runs/detect
                project=str(self.runs_dir),
                name=run_name,
                exist_ok=True,
                verbose=True
            )

            final_metrics = results.results_dict
            precision = final_metrics.get('metrics/precision(B)', 0)
            recall = final_metrics.get('metrics/recall(B)', 0)
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            best_weights_path = Path(results.save_dir) / 'weights' / 'best.pt'
            latency = self._medir_latencia(str(best_weights_path), device) if best_weights_path.exists() else 0.0

            resultado_job.update({
                "Status": "Completed",
                "mAP50_95": final_metrics.get('metrics/mAP50-95(B)', 0),
                "mAP50": final_metrics.get('metrics/mAP50(B)', 0),
                "Precision": precision,
                "Recall": recall,
                "F1_Score": f1_score,
                "Latency_ms": latency,
                "Output_Dir": results.save_dir,
            })
            self.logger.info(f"Job '{modelo_with_params}' concluído com sucesso em '{dataset_name}'.")

        except Exception as e:
            self.logger.error(f"FALHA no job '{modelo_with_params}'. Motivo: {e}", exc_info=True)
            resultado_job["Error"] = str(e).replace('\n', ' ')

        finally:
            training_time_min = (time.time() - start_time) / 60
            resultado_job["Training_Time_Min"] = training_time_min
            self.resultados.append(resultado_job)

    def _gerar_relatorio(self):
        """Gera um arquivo CSV com o resumo de todos os treinamentos."""
        if not self.resultados:
            self.logger.warning("Nenhum resultado para gerar relatório.")
            return

        report_filename = f"rtdetr_resumo_comparativo_{self.timestamp}.csv"
        report_path = self.reports_dir / report_filename
        self.logger.info(f"Gerando relatório de resumo em '{report_path}'...")

        # --- INÍCIO DA CORREÇÃO ---
        # Garante que o diretório de relatórios exista
        os.makedirs(self.reports_dir, exist_ok=True)
        # --- FIM DA CORREÇÃO ---

        header = self.resultados[0].keys()

        try:
            with open(report_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                for row in self.resultados:
                    formatted_row = {k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in row.items()}
                    writer.writerow(formatted_row)
            self.logger.info("Relatório de resumo gerado com sucesso.")
        except Exception as e:
            self.logger.error(f"Não foi possível gerar o relatório CSV: {e}")

    def run(self):
        """Orquestra a execução de todo o pipeline."""
        self.logger.info("=" * 70)
        self.logger.info("INICIANDO PIPELINE DE TREINAMENTO RT-DETR AUTOMATIZADO")
        self.logger.info(f"Parâmetros: {self.config}")
        self.logger.info("=" * 70)

        device = self._verificar_ambiente()

        for dataset_name in self.config["DATASETS_TO_TRAIN"]:
            self.logger.info("#" * 70)
            self.logger.info(f"INICIANDO CICLO PARA O DATASET: {dataset_name}")
            self.logger.info("#" * 70)

            for i, job in enumerate(self.config["TRAINING_JOBS"]):
                self.logger.info("-" * 70)
                self.logger.info(
                    f"Job {i + 1}/{len(self.config['TRAINING_JOBS'])}: {job['modelo']} em {dataset_name}")
                self._executar_job(job, dataset_name, device)

        self._gerar_relatorio()

        self.logger.info("=" * 70)
        self.logger.info("PIPELINE DE TREINAMENTO RT-DETR FINALIZADO")
        self.logger.info("=" * 70)

def main():
    """Ponto de entrada do script."""
    pipeline = PipelineTreinamentoRTDETR(RTDETR_CONFIG)
    pipeline.run()

if __name__ == "__main__":
    main()