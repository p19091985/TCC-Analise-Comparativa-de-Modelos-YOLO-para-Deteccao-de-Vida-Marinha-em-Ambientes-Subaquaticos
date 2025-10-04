# modal/modal_um.py
from .base_modal import BaseAnalysisModal
from pathlib import Path
import pandas as pd
import queue
import traceback

# Funções de processamento de dados do gui_analyse.py movidas para cá
def carregar_dados_txt(diretorio: Path) -> list[pd.DataFrame]:
    caminhos = [p for p in diretorio.glob("relatorio_metricas_absolutas_*.txt") if not p.name.startswith("analise_")]
    return [pd.read_csv(c, delimiter=';') for c in caminhos]

def preparar_dataframe_txt(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    if not dfs: return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True).drop_duplicates()
    df = df[df['status'] == 'SUCESSO'].copy()
    if df.empty: return pd.DataFrame()
    df['Modelo'] = df['nome_run'].apply(lambda x: x.split('_on_')[0])
    df.rename(columns={'dataset_nome': 'Dataset', 'precisao': 'Precisão (P)', 'recall': 'Recall (R)', 'mAP50_95': 'mAP50-95'}, inplace=True)
    metricas = ['mAP50-95', 'mAP50', 'Precisão (P)', 'Recall (R)', 'velocidade_inference_ms']
    for col in metricas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(subset=['mAP50-95', 'mAP50', 'Precisão (P)', 'Recall (R)'], inplace=True)
    return df

class JanelaModalUm(BaseAnalysisModal):
    """Janela de diálogo para análise específica de arquivos TXT."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Ferramenta de Análise de Relatórios (.txt)")
        self.grab_set()

    def get_worker_function(self):
        """Retorna a função worker que processa os arquivos TXT."""
        def worker(diretorio, result_queue):
            try:
                dfs = carregar_dados_txt(diretorio)
                if not dfs:
                    result_queue.put(("info", "Nenhum arquivo .txt de relatório encontrado no diretório."))
                    return
                df_final = preparar_dataframe_txt(dfs)
                if df_final.empty:
                    result_queue.put(("info", "Nenhum dado válido de 'SUCESSO' encontrado nos arquivos .txt."))
                    return
                result_queue.put(("result", df_final))
            except Exception:
                result_queue.put(("error", traceback.format_exc()))
        return worker