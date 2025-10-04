# modal/modal_dois.py
from .base_modal import BaseAnalysisModal
from pathlib import Path
import pandas as pd
import queue
import traceback
import numpy as np  # Importa a biblioteca NumPy para usar np.nan


# Funções de processamento de dados do gui_analyse.py movidas para cá
def carregar_dados_csv(diretorio: Path) -> list[pd.DataFrame]:
    caminhos = [p for p in diretorio.glob("resumo_comparativo_*.csv") if not p.name.startswith("analise_")]
    return [pd.read_csv(c) for c in caminhos]


def preparar_dataframe_csv(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    if not dfs: return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True).drop_duplicates()

    # --- INÍCIO DA CORREÇÃO 1: Detecção Robusta do Nome do Modelo ---
    # Procura por diferentes nomes possíveis para a coluna do modelo
    nomes_possiveis_modelo = ['Job_Name', 'Modelo', 'model', 'modelo']
    coluna_modelo_encontrada = None
    for nome in nomes_possiveis_modelo:
        if nome in df.columns:
            coluna_modelo_encontrada = nome
            break

    if coluna_modelo_encontrada:
        df.rename(columns={coluna_modelo_encontrada: 'Modelo'}, inplace=True)
    else:
        # Se nenhuma coluna for encontrada, cria uma coluna vazia para evitar erros
        df['Modelo'] = '-'
    # --- FIM DA CORREÇÃO 1 ---

    df.rename(columns={'Precision': 'Precisão (P)', 'Recall': 'Recall (R)', 'mAP50_95': 'mAP50-95'}, inplace=True)

    metricas = ['mAP50-95', 'mAP50', 'Precisão (P)', 'Recall (R)']
    for col in metricas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(subset=metricas, inplace=True)

    # --- INÍCIO DA CORREÇÃO 2: Tratamento de Velocidade 0.0 ms ---
    # Procura por nomes de coluna de latência comuns
    nomes_possiveis_latencia = ['Latency_ms', 'velocidade_inference_ms']
    coluna_latencia_encontrada = None
    for nome in nomes_possiveis_latencia:
        if nome in df.columns:
            coluna_latencia_encontrada = nome
            break

    if coluna_latencia_encontrada:
        # Converte para numérico, forçando erros a virarem NaN (Not a Number)
        df['velocidade_inference_ms'] = pd.to_numeric(df[coluna_latencia_encontrada], errors='coerce')
        # Substitui valores 0 por NaN, para que sejam tratados como dados ausentes
        df['velocidade_inference_ms'].replace(0, np.nan, inplace=True)
    else:
        # Se a coluna não existir, preenche com infinito para indicar ausência
        df['velocidade_inference_ms'] = float('inf')
    # --- FIM DA CORREÇÃO 2 ---

    return df


class JanelaModalDois(BaseAnalysisModal):
    """Janela de diálogo para análise específica de arquivos CSV."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Ferramenta de Análise de Resumos (.csv)")
        self.grab_set()

    def get_worker_function(self):
        """Retorna a função worker que processa os arquivos CSV."""

        def worker(diretorio, result_queue):
            try:
                dfs = carregar_dados_csv(diretorio)
                if not dfs:
                    result_queue.put(("info", "Nenhum arquivo .csv de resumo encontrado no diretório."))
                    return
                df_final = preparar_dataframe_csv(dfs)
                if df_final.empty:
                    result_queue.put(("info", "Nenhum dado válido encontrado nos arquivos .csv."))
                    return
                result_queue.put(("result", df_final))
            except Exception:
                result_queue.put(("error", traceback.format_exc()))

        return worker