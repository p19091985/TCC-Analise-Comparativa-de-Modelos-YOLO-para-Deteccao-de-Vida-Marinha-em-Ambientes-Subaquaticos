# modal/base_modal.py
import tkinter as tk
from tkinter import ttk, filedialog, font
import pandas as pd
from datetime import datetime
from pathlib import Path
import threading
import queue
import traceback
import os
import webbrowser


class BaseAnalysisModal(tk.Toplevel):
    """
    Classe base para uma janela de diálogo de análise de dados.
    Fornece a UI e a lógica de processamento em thread.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.resizable(False, False)

        self.data_frame: pd.DataFrame = None
        self.result_queue = queue.Queue()
        self.is_processing = False
        self.diretorio_selecionado = tk.StringVar(value=os.getcwd())

        self._build_ui()
        self.update_status("Pronto para iniciar.")

    def _build_ui(self):
        """Constrói a interface gráfica da janela modal."""
        self.geometry("1000x600")

        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        modal_width = 1000
        modal_height = 600
        pos_x = parent_x + (parent_width - modal_width) // 2
        pos_y = parent_y + (parent_height - modal_height) // 2
        self.geometry(f"{modal_width}x{modal_height}+{pos_x}+{pos_y}")

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)

        self._build_controls(main_frame)
        self._build_results_area(main_frame)
        self._build_status_bar()

    def _build_controls(self, parent):
        """Cria a seção de controles (selecionar pasta, rodar análise)."""
        frame = ttk.LabelFrame(parent, text="Controles", padding="10")
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Pasta de Análise:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        ttk.Entry(frame, textvariable=self.diretorio_selecionado, state="readonly").grid(row=0, column=1, sticky="ew")

        self.browse_button = ttk.Button(frame, text="Selecionar...", command=self.selecionar_diretorio)
        self.browse_button.grid(row=0, column=2, padx=5)

        self.run_button = ttk.Button(frame, text="Rodar Análise", command=self.start_analysis_thread,
                                     style='Accent.TButton')
        self.run_button.grid(row=0, column=3)

    def _build_results_area(self, parent):
        """Cria a área que exibe a tabela de resultados e os botões de exportar."""
        frame = ttk.LabelFrame(parent, text="Resumo dos Resultados da Validação", padding="10")
        frame.grid(row=1, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(frame, show='headings')
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        self.tree.tag_configure('best', background='#e6f3ff', font=('Segoe UI', 9, 'bold'))
        self.tree.tag_configure('fastest', background='#d4edda', font=('Segoe UI', 9, 'bold'))
        self.tree.tag_configure('evenrow', background='#f8f9fa')

        self.welcome_label = ttk.Label(frame, text="Selecione uma pasta e clique em 'Rodar Análise'.",
                                       font=('Segoe UI', 12), justify=tk.CENTER)
        self.welcome_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        export_frame = ttk.Frame(frame)
        export_frame.grid(row=2, column=0, columnspan=2, sticky="e", pady=(10, 0))

        self.btn_export_html = ttk.Button(export_frame, text="Exportar para HTML (ABNT)...", state="disabled",
                                          command=self.exportar_para_html)
        self.btn_export_html.pack(side=tk.RIGHT, padx=(5, 0))

        self.btn_export_csv = ttk.Button(export_frame, text="Exportar para CSV...", state="disabled",
                                         command=self.exportar_tabela_csv)
        self.btn_export_csv.pack(side=tk.RIGHT)

    def _build_status_bar(self):
        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, anchor=tk.W, padding=(5, 2), relief=tk.SUNKEN).pack(
            side=tk.BOTTOM, fill=tk.X)

    def selecionar_diretorio(self):
        dir_path = filedialog.askdirectory(initialdir=self.diretorio_selecionado.get())
        if dir_path: self.diretorio_selecionado.set(dir_path)

    def start_analysis_thread(self):
        if self.is_processing: return
        self.is_processing = True
        self.toggle_controls(False)
        self.update_status("Processando arquivos...")

        for item in self.tree.get_children(): self.tree.delete(item)
        self.welcome_label.lift()
        self.btn_export_csv.config(state="disabled")
        self.btn_export_html.config(state="disabled")

        worker_func = self.get_worker_function()
        diretorio = Path(self.diretorio_selecionado.get())

        threading.Thread(target=worker_func, args=(diretorio, self.result_queue), daemon=True).start()
        self.after(100, self.check_queue)

    def check_queue(self):
        try:
            msg_type, data = self.result_queue.get_nowait()
            if msg_type == "result":
                self.data_frame = data
                self.populate_treeview()
                self.btn_export_csv.config(state="normal")
                self.btn_export_html.config(state="normal")
                self.update_status("Análise concluída com sucesso.", 5000)
            elif msg_type == "error":
                self.welcome_label.config(text=f"Erro na análise:\n{data}")
                self.update_status("Ocorreu um erro durante a análise.", 5000)
            elif msg_type == "info":
                self.welcome_label.config(text=data)
                self.update_status("Aviso: Nenhum dado encontrado.", 5000)
        except queue.Empty:
            self.after(100, self.check_queue)
            return
        except Exception as e:
            self.update_status(f"Erro inesperado na UI: {e}", 5000)

        self.is_processing = False
        self.toggle_controls(True)

    def populate_treeview(self):
        if self.data_frame is None or self.data_frame.empty: return
        self.welcome_label.lower()

        df = self.data_frame.copy()
        df['Velocidade (inferência)'] = df['velocidade_inference_ms'].apply(
            lambda x: f"{x:.1f} ms" if pd.notna(x) and x != float('inf') else '-')

        cols = ['Modelo', 'Dataset', 'mAP50-95', 'mAP50', 'Precisão (P)', 'Recall (R)', 'Velocidade (inferência)']
        self.tree["columns"] = cols

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=font.Font().measure(col) + 40, anchor='w')

        df_sorted = df.sort_values(by=['Dataset', 'mAP50-95'], ascending=[True, False])
        best_map_indices = df_sorted.groupby('Dataset')['mAP50-95'].idxmax()
        fastest_inf_indices = df_sorted[df_sorted['velocidade_inference_ms'] != float('inf')].groupby('Dataset')[
            'velocidade_inference_ms'].idxmin()

        for i, (idx, row) in enumerate(df_sorted.iterrows()):
            tags = []
            if idx in best_map_indices.values: tags.append('best')
            if idx in fastest_inf_indices.values: tags.append('fastest')
            if i % 2 == 1 and not tags: tags.append('evenrow')

            values = []
            for col in cols:
                val = row.get(col, '')
                values.append(f"{val:.3f}" if isinstance(val, float) else val)
            self.tree.insert("", "end", values=values, tags=tags)

    def exportar_tabela_csv(self):
        """Exporta os dados da tabela para um arquivo CSV."""
        if self.data_frame is None or self.data_frame.empty: return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("Arquivos CSV", "*.csv")],
            initialfile=f"analise_resultados_{datetime.now().strftime('%Y-%m-%d')}.csv")
        if not filepath: return
        try:
            self.data_frame.to_csv(filepath, index=False, encoding='utf-8-sig', float_format='%.5f')
            self.update_status(f"Tabela exportada para '{Path(filepath).name}'", 5000)
        except Exception as e:
            self.update_status(f"Erro ao exportar CSV: {e}", 5000)

    def exportar_para_html(self):
        """Exporta os resultados para um arquivo HTML com formatação ABNT."""
        if self.data_frame is None or self.data_frame.empty: return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".html", filetypes=[("Arquivos HTML", "*.html")],
            initialfile=f"tabela_abnt_{datetime.now().strftime('%Y-%m-%d')}.html")
        if not filepath: return

        df = self.data_frame.copy()

        metricas_maior_melhor = ['mAP50-95', 'mAP50', 'Precisão (P)', 'Recall (R)']
        best_values = {}
        for group_name, group_df in df.groupby('Dataset'):
            best_values[group_name] = {
                'fastest_idx': group_df['velocidade_inference_ms'].idxmin() if pd.api.types.is_numeric_dtype(
                    group_df['velocidade_inference_ms']) else None
            }
            for metrica in metricas_maior_melhor:
                if metrica in group_df:
                    best_values[group_name][metrica + '_idx'] = group_df[metrica].idxmax()

        html = """
        <!DOCTYPE html>
        <html lang="pt-br">
        <head>
            <meta charset="UTF-8">
            <title>Tabela de Resultados</title>
            <style>
                body { font-family: 'Times New Roman', Times, serif; font-size: 12pt; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; margin-bottom: 10px; }
                th, td { border: 1px solid black; padding: 4px 8px; text-align: center; }
                th { background-color: #f2f2f2; }
                td.text-cell { text-align: left; }
                caption { caption-side: top; font-weight: bold; font-size: 12pt; padding-bottom: 10px; text-align: center; }
                .footer { font-size: 10pt; text-align: left; margin-top: 5px; }
            </style>
        </head>
        <body>
        """

        html += f"<caption>Tabela 1 - Resumo Comparativo dos Resultados da Validação (gerado em {datetime.now().strftime('%d/%m/%Y')})</caption>"
        html += "<table><thead><tr>"

        colunas_display = ['Modelo', 'Dataset', 'mAP50-95', 'mAP50', 'Precisão (P)', 'Recall (R)',
                           'Velocidade (inferência)']
        for col in colunas_display:
            html += f"<th>{col.replace('(inferência)', '(ms)')}</th>"
        html += "</tr></thead><tbody>"

        for _, row in df.sort_values(by=['Dataset', 'mAP50-95'], ascending=[True, False]).iterrows():
            html += "<tr>"
            dataset_atual = row['Dataset']

            for col in colunas_display:
                is_bold = False

                # --- INÍCIO DA CORREÇÃO ---
                # Pega o valor da coluna de forma segura, tratando o caso especial da velocidade
                if col == 'Velocidade (inferência)':
                    valor = row.get('velocidade_inference_ms')
                else:
                    valor = row.get(col)
                # --- FIM DA CORREÇÃO ---

                if col == 'Velocidade (inferência)' and row.name == best_values[dataset_atual].get('fastest_idx'):
                    is_bold = True
                elif col in metricas_maior_melhor and row.name == best_values[dataset_atual].get(col + '_idx'):
                    is_bold = True

                if pd.isna(valor) or valor == float('inf'):
                    valor_str = "-"
                elif isinstance(valor, float):
                    if col == 'Velocidade (inferência)':
                        valor_str = f"{valor:.1f}"
                    else:
                        valor_str = f"{valor:.3f}"
                else:
                    valor_str = str(valor)

                valor_final = f"<b>{valor_str}</b>" if is_bold else valor_str
                classe_css = " class='text-cell'" if col in ['Modelo', 'Dataset'] else ""
                html += f"<td{classe_css}>{valor_final}</td>"

            html += "</tr>"

        html += "</tbody></table>"
        html += f"<div class='footer'>Fonte: Elaborado pelo autor ({datetime.now().year}).</div>"
        html += "</body></html>"

        try:
            with open(filepath, "w", encoding='utf-8') as f:
                f.write(html)
            self.update_status(f"Tabela exportada para '{Path(filepath).name}'", 5000)
            webbrowser.open(f"file://{os.path.realpath(filepath)}")
        except Exception as e:
            self.update_status(f"Erro ao exportar HTML: {e}", 5000)

    def toggle_controls(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.browse_button.config(state=state)
        self.run_button.config(state=state, text="Rodar Análise" if enabled else "Processando...")
        self.config(cursor="" if enabled else "watch")

    def update_status(self, message: str, clear_after_ms: int = 0):
        self.status_var.set(message)
        if clear_after_ms > 0:
            self.after(clear_after_ms, lambda: self.status_var.set(""))

    def get_worker_function(self):
        raise NotImplementedError("As subclasses devem implementar este método.")