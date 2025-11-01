"""
Módulo 3: Visualizador de Resultados em Streamlit.

Portabilidade do 'results_viewer.py' para uma interface web interativa
com Streamlit, mantendo a lógica de visualização "Padrão" e "Orientador".

MODIFICAÇÃO (UX/UI v3.1 - "Estado da Arte"):
- Corrigidos todos os avisos de depreciação (DeprecationWarning) do Streamlit
  removendo 'use_container_width' dos gráficos Altair.
- Corrigido o aviso futuro (FutureWarning) do Pandas ao adicionar
  'future_stack=True' na função .stack().
"""
import streamlit as st
import pandas as pd
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
import altair as alt

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

try:
    from config.paths import REPORTS_DIR
except ImportError:
    st.error("Erro Crítico: Não foi possível importar 'config.paths'. Verifique se o script está na pasta '03_results_analysis/'.")
    st.stop()

def generate_orientador_html(export_df: pd.DataFrame, raw_df: pd.DataFrame) -> str:
    """
    Gera HTML no formato específico para o modo orientador.
    """
    try:
        if export_df is None or export_df.empty:
            return ""

        data_atual = datetime.now().strftime("%d/%m/%Y")
        metricas = ['mAP50-95', 'mAP50', 'Precision', 'Recall', 'Inferencia (ms)']

        html_parts = []

        html_parts.append(f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Tabela de Resultados</title>
    <style>
        body {{ font-family: 'Times New Roman', Times, serif; font-size: 12pt; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; margin-bottom: 10px; }}
        th, td {{ border: 1px solid black; padding: 4px 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        td.model-cell {{ text-align: left; font-weight: bold; }}
        caption {{ caption-side: top; font-weight: bold; font-size: 12pt; padding-bottom: 10px; text-align: center; }}
        .footer {{ font-size: 10pt; text-align: left; margin-top: 10px; }}
        b {{ color: #00008B; }} /* destaque sutil para melhores valores */
    </style>
</head>
<body>
<caption>Tabela 1 - Resumo Comparativo dos Resultados da Validação (gerado em {data_atual})</caption>
<table>
    <thead>
        <tr>
            <th rowspan="2" style="vertical-align: middle;">Modelo</th>""")

        datasets = sorted(raw_df['dataset_nome'].unique())
        for dataset in datasets:
            html_parts.append(f'            <th colspan="{len(metricas)}">{dataset}</th>')
        html_parts.append("        </tr>\n        <tr>")

        for dataset in datasets:
            for metrica in metricas:
                html_parts.append(f'            <th>{metrica}</th>')
        html_parts.append("        </tr>\n    </thead>\n    <tbody>")

        modelos = sorted(export_df.index)
        for modelo in modelos:
            html_parts.append(f'        <tr>\n            <td class="model-cell">{modelo}</td>')
            for dataset in datasets:
                for metrica in metricas:
                    try:
                        valor = export_df.loc[modelo, (dataset, metrica)]
                        if pd.isna(valor):
                            html_parts.append('            <td>-</td>')
                        else:
                                                                 
                            valores_metrica = [export_df.loc[m, (dataset, metrica)]
                                             for m in modelos
                                             if not pd.isna(export_df.loc[m, (dataset, metrica)])]

                            if valores_metrica:
                                if metrica == 'Inferencia (ms)':                  
                                    melhor_valor = min(valores_metrica)
                                else:                  
                                    melhor_valor = max(valores_metrica)

                                if abs(valor - melhor_valor) < 0.001:
                                    html_parts.append(f'            <td><b>{valor:.3f}</b></td>')
                                else:
                                    html_parts.append(f'            <td>{valor:.3f}</td>')
                            else:
                                html_parts.append(f'            <td>{valor:.3f}</td>')
                    except KeyError:
                        html_parts.append('            <td>-</td>')
            html_parts.append('        </tr>')

        html_parts.append("""    </tbody>
</table>
<div class="footer">Fonte: Elaborado pelo autor (2025).</div>
</body>
</html>""")
        return '\n'.join(html_parts)
    except Exception as e:
        st.error(f"Erro ao gerar HTML orientador: {e}")
        return ""

def generate_flat_html(export_df: pd.DataFrame) -> str:
    """
    Gera HTML no formato padrão para modo flat.
    """
    html_string = export_df.to_html(border=1, justify='center', na_rep="",
                                     float_format=lambda x: f'{x:.3f}')
    data_atual = datetime.now().strftime("%d/%m/%Y")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>Tabela de Resultados</title>
        <style>
            body {{ font-family: 'Times New Roman', Times, serif; font-size: 12pt; }}
            table {{ border-collapse: collapse; width: auto; margin: 20px auto; }}
            th, td {{ border: 1px solid black; padding: 4px 8px; text-align: center; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            caption {{ caption-side: top; font-weight: bold; font-size: 12pt; padding-bottom: 10px; text-align: center; }}
        </style>
    </head>
    <body>
    <caption>Tabela - Resumo Comparativo dos Resultados da Validação (gerado em {data_atual})</caption>
    {html_string}
    </body>
    </html>
    """
    return html_content

@st.cache_data
def get_available_reports() -> List[Path]:
    """
    Busca todos os arquivos de relatório e os ordena do mais recente ao mais antigo.
    """
    report_path = Path(REPORTS_DIR)
    txt_files = list(report_path.glob('relatorio_metricas_absolutas_*.txt'))

    txt_files_sorted = sorted(txt_files, key=lambda f: f.name, reverse=True)
    return txt_files_sorted

@st.cache_data(show_spinner="Carregando dados do relatório...")
def load_raw_data(filenames_to_load: Tuple[str, ...]) -> pd.DataFrame:
    """
    Carrega e consolida um ou mais relatórios TXT com base nos
    nomes de arquivos fornecidos.
    """
    report_path = Path(REPORTS_DIR)
    df_list = []

    for filename in filenames_to_load:
        f = report_path / filename
        if not f.exists():
            st.error(f"Arquivo selecionado não encontrado: {filename}")
            continue
        try:
            df_list.append(pd.read_csv(f, delimiter=';'))
        except Exception as e:
            st.error(f"Falha ao ler o arquivo TXT {f.name}: {e}")

    if not df_list:
        return None

    raw_df = pd.concat(df_list, ignore_index=True)
    return raw_df

@st.cache_data
def process_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Processa o DataFrame bruto, extraindo 'Modelo' e renomeando colunas.
    """
    if raw_df is None or raw_df.empty:
        return None

    processed_df = raw_df.copy()

    processed_df['Modelo'] = processed_df['nome_run'].apply(lambda x: x.split('_')[0])

    processed_df.rename(columns={
        'mAP50_95': 'mAP50-95',
        'precisao': 'Precision',
        'recall': 'Recall',
        'velocidade_inference_ms': 'Inferencia (ms)'
    }, inplace=True)

    num_cols = ['mAP50-95', 'mAP50', 'mAP75', 'Precision', 'Recall', 'Inferencia (ms)']
    for col in num_cols:
        if col in processed_df.columns:
            processed_df[col] = pd.to_numeric(processed_df[col], errors='coerce')

    return processed_df

@st.cache_data
def get_flat_view(processed_df: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame):
    """
    Prepara o DataFrame para a visualização padrão (plana).
    """
    flat_cols = [
        'Modelo', 'dataset_nome', 'mAP50-95', 'mAP50', 'Precision', 'Recall', 'Inferencia (ms)',
        'mAP75', 'nome_run', 'status', 'velocidade_preprocess_ms', 'velocidade_postprocess_ms', 'mensagem_erro'
    ]

    existing_cols = [col for col in flat_cols if col in processed_df.columns]
    display_df = processed_df[existing_cols].copy()
    export_df = display_df.copy()
    return display_df, export_df

@st.cache_data
def get_pivot_view(processed_df: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame):
    """
    Prepara o DataFrame para a visualização Orientador (pivot).
    """
    try:
        metrics_to_pivot = ['mAP50-95', 'mAP50', 'Precision', 'Recall', 'Inferencia (ms)']
        df_copy = processed_df.copy()

        existing_metrics = [m for m in metrics_to_pivot if m in df_copy.columns]
        if not existing_metrics:
            st.error("Nenhuma coluna de métrica (mAP50-95, mAP50, etc.) encontrada para pivotar.")
            return None, None

        pivot_df = df_copy.pivot_table(
            index='Modelo',
            columns='dataset_nome',
            values=existing_metrics,
            aggfunc='mean'
        )

        pivot_df = pivot_df.swaplevel(0, 1, axis=1)

        dataset_order = sorted([d for d in df_copy['dataset_nome'].unique() if d in pivot_df.columns.get_level_values(0)])
        metric_order = [m for m in metrics_to_pivot if m in pivot_df.columns.get_level_values(1)]
        pivot_df = pivot_df.reindex(columns=dataset_order, level=0)
        pivot_df = pivot_df.reindex(columns=metric_order, level=1)
        pivot_df = pivot_df.round(3)

        export_df = pivot_df.copy()

        display_df = pivot_df.reset_index()
        flat_cols = ['Modelo']
        for col in display_df.columns:
            if col[0] == 'Modelo':
                continue
            dataset_name = col[0]
            metric_name = col[1]
            flat_cols.append(f"{dataset_name} - {metric_name}")

        display_df.columns = flat_cols
        return display_df, export_df

    except Exception as e:
        st.error(f"Erro ao criar a visualização Orientador: {e}")
        return None, None

def render_graphics_tab(df: pd.DataFrame, pivot_df: pd.DataFrame):
    """Renderiza todo o conteúdo da aba 'Análise Gráfica'."""

    st.header("Análise Gráfica Comparativa dos Modelos")

    if df is None or df.empty:
        st.warning("Não há dados processados para exibir gráficos.")
        return

    df_mean = df.groupby('Modelo')[['mAP50-95', 'mAP50', 'Precision', 'Recall', 'Inferencia (ms)']].mean().reset_index()

    tab_overview, tab_dataset, tab_model, tab_matrix, tab_dist = st.tabs([
        "🚀 Visão Geral",
        "📊 Por Dataset",
        "🤖 Por Modelo",
        "🔲 Matrizes e Heatmaps",
        "📉 Distribuições"
    ])

    with tab_overview:
        st.subheader("Visão Geral: Performance Média dos Modelos")
        st.markdown("Resultados médios de cada modelo, consolidados de todos os datasets.")

        chart_map_vs_speed = alt.Chart(df_mean).mark_circle(size=100).encode(
            x=alt.X('Inferencia (ms)', scale=alt.Scale(zero=False)),
            y=alt.Y('mAP50-95', scale=alt.Scale(zero=False)),
            color='Modelo',
            tooltip=['Modelo', 'mAP50-95', 'Inferencia (ms)']
        ).properties(
            title='Visão Geral: mAP50-95 vs. Velocidade de Inferência (Média)'
        ).interactive()
                                   
        st.altair_chart(chart_map_vs_speed)

        col1, col2 = st.columns(2)

        with col1:
                                                    
            chart_avg_map = alt.Chart(df_mean).mark_bar().encode(
                x=alt.X('mAP50-95', title='mAP50-95 (Média)'),
                y=alt.Y('Modelo', sort='-x'),
                color='Modelo',
                tooltip=['Modelo', 'mAP50-95', 'Inferencia (ms)']
            ).properties(
                title='Ranking de mAP50-95 (Média)'
            )
                                       
            st.altair_chart(chart_avg_map)

            chart_box_map = alt.Chart(df).mark_boxplot().encode(
                x=alt.X('mAP50-95', title='mAP50-95'),
                y=alt.Y('Modelo'),
                color='Modelo'
            ).properties(
                title='Distribuição de mAP50-95 por Modelo (todos datasets)'
            )
                                       
            st.altair_chart(chart_box_map)

        with col2:
                                                      
            chart_avg_speed = alt.Chart(df_mean).mark_bar().encode(
                x=alt.X('Inferencia (ms)', title='Inferencia (ms, Média)'),
                y=alt.Y('Modelo', sort='x'),                     
                color='Modelo',
                tooltip=['Modelo', 'mAP50-95', 'Inferencia (ms)']
            ).properties(
                title='Ranking de Velocidade de Inferência (Média)'
            )
                                       
            st.altair_chart(chart_avg_speed)

            chart_box_speed = alt.Chart(df).mark_boxplot().encode(
                x=alt.X('Inferencia (ms)'),
                y=alt.Y('Modelo'),
                color='Modelo'
            ).properties(
                title='Distribuição de Inferência (ms) por Modelo (todos datasets)'
            )
                                       
            st.altair_chart(chart_box_speed)

    with tab_dataset:
        st.subheader("Análise Detalhada por Dataset")

        dataset_list = sorted(df['dataset_nome'].unique())
        selected_dataset = st.selectbox("Selecione um Dataset:", dataset_list)

        if selected_dataset:
            df_filtered = df[df['dataset_nome'] == selected_dataset]

            chart_ds_map_vs_speed = alt.Chart(df_filtered).mark_circle(size=100).encode(
                x=alt.X('Inferencia (ms)', scale=alt.Scale(zero=False)),
                y=alt.Y('mAP50-95', scale=alt.Scale(zero=False)),
                color='Modelo',
                tooltip=['Modelo', 'mAP50-95', 'Inferencia (ms)']
            ).properties(
                title=f'mAP50-95 vs. Velocidade em "{selected_dataset}"'
            ).interactive()
                                       
            st.altair_chart(chart_ds_map_vs_speed)

            col1, col2 = st.columns(2)

            with col1:
                                                 
                chart_ds_map95 = alt.Chart(df_filtered).mark_bar().encode(
                    x=alt.X('mAP50-95'),
                    y=alt.Y('Modelo', sort='-x'),
                    color='Modelo',
                    tooltip=['Modelo', 'mAP50-95', 'mAP50', 'Inferencia (ms)']
                ).properties(title=f'mAP50-95 em "{selected_dataset}"')
                                           
                st.altair_chart(chart_ds_map95)

                chart_ds_map50 = alt.Chart(df_filtered).mark_bar().encode(
                    x=alt.X('mAP50'),
                    y=alt.Y('Modelo', sort='-x'),
                    color='Modelo',
                    tooltip=['Modelo', 'mAP50-95', 'mAP50', 'Inferencia (ms)']
                ).properties(title=f'mAP50 em "{selected_dataset}"')
                                           
                st.altair_chart(chart_ds_map50)

            with col2:
                                                
                df_pr = df_filtered.melt(id_vars='Modelo', value_vars=['Precision', 'Recall'], var_name='Métrica', value_name='Valor')
                chart_ds_pr = alt.Chart(df_pr).mark_bar().encode(
                    x=alt.X('Valor', title='Valor', scale=alt.Scale(domain=[0, 1])),
                    y=alt.Y('Modelo', sort='-x'),
                    color='Métrica',
                    row='Métrica',
                    tooltip=['Modelo', 'Métrica', 'Valor']
                ).properties(title=f'Precision vs. Recall em "{selected_dataset}"')
                                           
                st.altair_chart(chart_ds_pr)

                chart_ds_speed = alt.Chart(df_filtered).mark_bar().encode(
                    x=alt.X('Inferencia (ms)'),
                    y=alt.Y('Modelo', sort='x'),
                    color='Modelo',
                    tooltip=['Modelo', 'Inferencia (ms)']
                ).properties(title=f'Velocidade em "{selected_dataset}"')
                                           
                st.altair_chart(chart_ds_speed)

    with tab_model:
        st.subheader("Análise Detalhada por Modelo")

        model_list = sorted(df['Modelo'].unique())
        selected_model = st.selectbox("Selecione um Modelo:", model_list)

        if selected_model:
            df_filtered = df[df['Modelo'] == selected_model]

            chart_model_map95 = alt.Chart(df_filtered).mark_bar().encode(
                x=alt.X('mAP50-95'),
                y=alt.Y('dataset_nome', title='Dataset', sort='-x'),
                color='dataset_nome',
                tooltip=['dataset_nome', 'mAP50-95', 'mAP50', 'Inferencia (ms)']
            ).properties(title=f'Performance de {selected_model}: mAP50-95')
                                       
            st.altair_chart(chart_model_map95)

            col1, col2 = st.columns(2)
            with col1:
                                              
                chart_model_map50 = alt.Chart(df_filtered).mark_bar().encode(
                    x=alt.X('mAP50'),
                    y=alt.Y('dataset_nome', title='Dataset', sort='-x'),
                    color='dataset_nome',
                    tooltip=['dataset_nome', 'mAP50-95', 'mAP50']
                ).properties(title=f'Performance de {selected_model}: mAP50')
                                           
                st.altair_chart(chart_model_map50)

                chart_model_p = alt.Chart(df_filtered).mark_bar().encode(
                    x=alt.X('Precision'),
                    y=alt.Y('dataset_nome', title='Dataset', sort='-x'),
                    color='dataset_nome',
                    tooltip=['dataset_nome', 'Precision']
                ).properties(title=f'Performance de {selected_model}: Precision')
                                           
                st.altair_chart(chart_model_p)

            with col2:
                                               
                chart_model_r = alt.Chart(df_filtered).mark_bar().encode(
                    x=alt.X('Recall'),
                    y=alt.Y('dataset_nome', title='Dataset', sort='-x'),
                    color='dataset_nome',
                    tooltip=['dataset_nome', 'Recall']
                ).properties(title=f'Performance de {selected_model}: Recall')
                                           
                st.altair_chart(chart_model_r)

                chart_model_speed = alt.Chart(df_filtered).mark_bar().encode(
                    x=alt.X('Inferencia (ms)'),
                    y=alt.Y('dataset_nome', title='Dataset', sort='x'),
                    color='dataset_nome',
                    tooltip=['dataset_nome', 'Inferencia (ms)']
                ).properties(title=f'Velocidade de {selected_model} por Dataset')
                                           
                st.altair_chart(chart_model_speed)

    with tab_matrix:
        st.subheader("Matrizes e Heatmaps")

        if pivot_df is not None and not pivot_df.empty:
                                                           
            pivot_long = pivot_df.stack(level=[0, 1], future_stack=True).reset_index()
            pivot_long.columns = ['Modelo', 'dataset_nome', 'Metrica', 'Valor']

            heatmap_map95 = alt.Chart(pivot_long[pivot_long['Metrica'] == 'mAP50-95']).mark_rect().encode(
                x=alt.X('dataset_nome', title='Dataset'),
                y=alt.Y('Modelo'),
                color=alt.Color('Valor', title='mAP50-95', scale=alt.Scale(range='heatmap')),
                tooltip=['Modelo', 'dataset_nome', 'Valor']
            ).properties(
                title='Heatmap: Performance mAP50-95 (Modelo vs. Dataset)'
            )
                                       
            st.altair_chart(heatmap_map95)

            heatmap_speed = alt.Chart(pivot_long[pivot_long['Metrica'] == 'Inferencia (ms)']).mark_rect().encode(
                x=alt.X('dataset_nome', title='Dataset'),
                y=alt.Y('Modelo'),
                color=alt.Color('Valor', title='Inferencia (ms)', scale=alt.Scale(range='heatmap', reverse=True)),                             
                tooltip=['Modelo', 'dataset_nome', 'Valor']
            ).properties(
                title='Heatmap: Velocidade de Inferência (Modelo vs. Dataset)'
            )
                                       
            st.altair_chart(heatmap_speed)
        else:
            st.warning("Heatmaps requerem o 'Modo Orientador', mas os dados pivotados não puderam ser gerados.")

        corr_df = df[['mAP50-95', 'mAP50', 'mAP75', 'Precision', 'Recall', 'Inferencia (ms)']].corr().stack().reset_index()
        corr_df.columns = ['Var1', 'Var2', 'Correlação']

        base = alt.Chart(corr_df).encode(
            x=alt.X('Var1', title=None),
            y=alt.Y('Var2', title=None),
            tooltip=['Var1', 'Var2', alt.Tooltip('Correlação', format='.2f')]
        ).properties(
            title='Matriz de Correlação entre Métricas'
        )
        heatmap_corr = base.mark_rect().encode(
            color=alt.Color('Correlação', scale=alt.Scale(range='diverging', domain=[-1, 1]))
        )
        text_corr = base.mark_text().encode(
            text=alt.Text('Correlação', format='.2f'),
            color=alt.value('black')
        )
                                   
        st.altair_chart(heatmap_corr + text_corr)

    with tab_dist:
        st.subheader("Distribuição das Métricas (Todos os Resultados)")

        col1, col2 = st.columns(2)
        with col1:
                                             
            hist_map95 = alt.Chart(df).mark_bar().encode(
                x=alt.X('mAP50-95', bin=alt.Bin(maxbins=20), title='mAP50-95'),
                y=alt.Y('count()', title='Contagem')
            ).properties(title='Distribuição de mAP50-95')
                                       
            st.altair_chart(hist_map95)

            hist_p = alt.Chart(df).mark_bar().encode(
                x=alt.X('Precision', bin=alt.Bin(maxbins=20), title='Precision'),
                y=alt.Y('count()', title='Contagem')
            ).properties(title='Distribuição de Precision')
                                       
            st.altair_chart(hist_p)

        with col2:
                                                    
            hist_speed = alt.Chart(df).mark_bar().encode(
                x=alt.X('Inferencia (ms)', bin=alt.Bin(maxbins=20), title='Inferencia (ms)'),
                y=alt.Y('count()', title='Contagem')
            ).properties(title='Distribuição de Velocidade de Inferência')
                                       
            st.altair_chart(hist_speed)

            hist_r = alt.Chart(df).mark_bar().encode(
                x=alt.X('Recall', bin=alt.Bin(maxbins=20), title='Recall'),
                y=alt.Y('count()', title='Contagem')
            ).properties(title='Distribuição de Recall')
                                       
            st.altair_chart(hist_r)

def render_data_table_tab(processed_df, raw_df, pivot_export_df, view_mode, show_details, selection_key):
    """Renderiza todo o conteúdo da aba 'Tabela de Dados'."""

    try:
        st.subheader("🚀 Visão Geral (Melhores Resultados)")
        st.markdown(f"**Fonte de Dados:** `{selection_key}`")
        kpi_cols = st.columns(3)

        df_valid_map = processed_df['mAP50-95'].dropna()
        best_map_idx = df_valid_map.idxmax() if not df_valid_map.empty else None

        df_valid_speed = processed_df['Inferencia (ms)'].dropna()
        fastest_idx = df_valid_speed.idxmin() if not df_valid_speed.empty else None

        df_valid_map50 = processed_df['mAP50'].dropna()
        best_map50_idx = df_valid_map50.idxmax() if not df_valid_map50.empty else None

        if best_map_idx is not None:
            best_map_row = processed_df.loc[best_map_idx]
            kpi_cols[0].metric(
                label=f"Melhor mAP50-95 (Dataset: {best_map_row['dataset_nome']})",
                value=f"{best_map_row['mAP50-95']:.3f}",
                help=f"Modelo: {best_map_row['Modelo']}"
            )
        else:
            kpi_cols[0].metric("Melhor mAP50-95", "N/A")

        if best_map50_idx is not None:
            best_map50_row = processed_df.loc[best_map50_idx]
            kpi_cols[1].metric(
                label=f"Melhor mAP50 (Dataset: {best_map50_row['dataset_nome']})",
                value=f"{best_map50_row['mAP50']:.3f}",
                help=f"Modelo: {best_map50_row['Modelo']}"
            )
        else:
             kpi_cols[1].metric("Melhor mAP50", "N/A")

        if fastest_idx is not None:
            fastest_row = processed_df.loc[fastest_idx]
            kpi_cols[2].metric(
                label=f"Menor Latência (Dataset: {fastest_row['dataset_nome']})",
                value=f"{fastest_row['Inferencia (ms)']:.1f} ms",
                help=f"Modelo: {fastest_row['Modelo']}",
                delta_color="inverse"
            )
        else:
            kpi_cols[2].metric("Menor Latência", "N/A")

    except Exception as e:
        st.warning(f"Não foi possível gerar os KPIs: {e}")

    st.divider()

    export_df = None
    html_content = ""
    current_view_mode = 'flat'

    if view_mode == "Modo Padrão (Plano)":
        st.subheader("Modo Padrão (Plano)")
        st.markdown("Cada linha representa um único *run* de avaliação. Tabela interativa (clique nos cabeçalhos para ordenar).")
        display_df, export_df = get_flat_view(processed_df)
        current_view_mode = 'flat'
        if display_df is not None:
            html_content = generate_flat_html(export_df)
        else:
            st.error("Não foi possível gerar a visualização 'Modo Padrão'.")

    elif view_mode == "Modo Orientador (Pivot)":
        st.subheader("Modo Orientador (Pivot)")
        st.markdown("Tabela dinâmica com **Modelos** nas linhas e **Datasets/Métricas** nas colunas (agregados pela média).")

        display_df, export_df = get_pivot_view(processed_df)
        current_view_mode = 'pivot'
        if export_df is not None:
            html_content = generate_orientador_html(export_df, raw_df)
        else:
            st.error("Não foi possível gerar a visualização 'Modo Orientador'.")

    if export_df is not None and not export_df.empty:
        with st.container():
            col1, col2 = st.columns(2)

            csv_data = export_df.to_csv(
                index=(current_view_mode == 'pivot')
            ).encode('utf-8')

            with col1:
                st.download_button(
                    label="💾 Exportar para CSV",
                    data=csv_data,
                    file_name=f"resultados_{current_view_mode}.csv",
                    mime="text/csv",
                    width='stretch'                   
                )

            with col2:
                st.download_button(
                    label="🌐 Exportar para HTML",
                    data=html_content.encode('utf-8'),
                    file_name=f"resultados_{current_view_mode}.html",
                    mime="text/html",
                    width='stretch'                   
                )

            with st.expander("📋 Ver/Copiar Dados (CSV com Tabulação)"):
                st.code(
                    export_df.to_csv(
                        sep='\t',
                        index=(current_view_mode == 'pivot')
                    ),
                    language="csv"
                )
        st.divider()

    if view_mode == "Modo Padrão (Plano)" and display_df is not None:
        if show_details:
            cols_to_show = display_df.columns
        else:
            cols_to_show = ['Modelo', 'dataset_nome', 'mAP50-95', 'mAP50', 'Precision', 'Recall', 'Inferencia (ms)']
            cols_to_show = [col for col in cols_to_show if col in display_df.columns]

        st.dataframe(display_df[cols_to_show], width='stretch', hide_index=True)                   

    elif view_mode == "Modo Orientador (Pivot)" and html_content:
        st.markdown(html_content, unsafe_allow_html=True)

    elif display_df is None and html_content == "":
        st.warning("Não foi possível carregar ou processar dados para exibição.")

def main():
    st.set_page_config(layout="wide", page_title="Visualizador de Resultados")
    st.title("📊 Painel de Análise Comparativa (TCC-YOLO)")

    st.sidebar.title("Opções de Visualização")

    st.sidebar.header("1. Fonte de Dados")

    report_files_list = get_available_reports()

    if not report_files_list:
        st.error(f"Nenhum arquivo 'relatorio_metricas_absolutas_*.txt' encontrado em {REPORTS_DIR}.")
        st.stop()

    most_recent_name = report_files_list[0].name
    key_recent = f"Mais Recente ({most_recent_name})"
    key_all = "Todos os Relatórios (Consolidado)"

    files_map = {
        key_recent: (most_recent_name,),
        key_all: tuple(f.name for f in report_files_list)
    }
    for f in report_files_list:
        files_map[f.name] = (f.name,)

    selection_key = st.sidebar.selectbox(
        "Selecionar Relatório",
        options=files_map.keys(),
        key="report_selector"
    )

    if st.sidebar.button("🔄 Recarregar Dados"):
        st.cache_data.clear()
        st.success("Cache de dados limpo. Os dados serão recarregados.")
        st.rerun()

    st.sidebar.header("2. Modo de Exibição")
    view_mode = st.sidebar.radio(
        "Modo de Visualização",
        ["Modo Padrão (Plano)", "Modo Orientador (Pivot)"],
        key="view_toggle",
        horizontal=True
    )

    show_details = False
    if view_mode == "Modo Padrão (Plano)":
        show_details = st.sidebar.toggle("Mostrar colunas detalhadas", value=False,
                                        help="Exibe colunas extras como 'nome_run', 'status', 'velocidade_preprocess_ms', etc.")

    filenames_to_load = files_map[selection_key]
    raw_df = load_raw_data(filenames_to_load)
    if raw_df is None:
        st.error("Nenhum dado foi carregado. Verifique os arquivos de relatório.")
        st.stop()

    processed_df = process_data(raw_df)
    if processed_df is None:
        st.error("Falha no processamento dos dados.")
        st.stop()

    _, pivot_export_df = get_pivot_view(processed_df)

    tab_charts, tab_data = st.tabs(["📊 Análise Gráfica", "🗃️ Tabela de Dados"])

    with tab_charts:
        render_graphics_tab(processed_df, pivot_export_df)

    with tab_data:
        render_data_table_tab(
            processed_df=processed_df,
            raw_df=raw_df,
            pivot_export_df=pivot_export_df,
            view_mode=view_mode,
            show_details=show_details,
            selection_key=selection_key
        )

if __name__ == "__main__":
    main()