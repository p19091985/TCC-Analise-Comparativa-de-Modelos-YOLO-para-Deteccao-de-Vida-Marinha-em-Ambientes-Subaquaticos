"""
Painel de Controle Central e Integrado para o Pipeline de Análise.
Oferece controle granular sobre a execução de cada script individualmente.

MODIFICADO:
- Lança o visualizador Streamlit via navegador.
- Exibe o Módulo 3 na árvore de scripts.
- Permite executar o Módulo 3 a partir da árvore (via "Executar Selecionado(s)").
"""
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import queue
import subprocess
import sys
import os
import json
import importlib

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from utils.logger_config import setup_logging

# --- INÍCIO DA MODIFICAÇÃO (MÓDULO 3 ADICIONADO DE VOLTA) ---
PIPELINE_SCRIPTS = {
    "Módulo 1: Pré-processamento": [
        "01_data_preprocessing/01_download_datasets.py",
        "01_data_preprocessing/02_sync_yamls.py",
        "01_data_preprocessing/03_reduce_datasets.py",
        "01_data_preprocessing/04_merge_datasets.py",
    ],
    "Módulo 2: Treinamento": [
        "02_model_training/05_train_yolo_models.py",
        "02_model_training/06_train_rtdetr_models.py",
        "02_model_training/07_evaluate_models_on_test_set.py",
    ],
    "Módulo 3: Avaliação Final": [
        "03_results_analysis/08_streamlit_results_viewer.py",
    ]
}
# --- FIM DA MODIFICAÇÃO ---

class MainDashboard(tk.Tk):

    def __init__(self):
        super().__init__()
        self.logger = setup_logging('MainDashboardLogger', __file__)
        self.title("Painel de Controle do Pipeline de Análise")
        self.geometry("1000x750")

        self.execution_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()

        self.setup_ui()
        self.process_log_queue()

    def setup_ui(self):
        main_paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        controls_frame = ttk.Frame(main_paned_window, padding=10)
        self.create_scripts_tree(controls_frame)
        self.create_action_buttons(controls_frame)
        main_paned_window.add(controls_frame, weight=1)

        log_frame = ttk.Frame(main_paned_window, padding=10)
        self.create_log_area(log_frame)
        main_paned_window.add(log_frame, weight=3)

    def create_scripts_tree(self, parent):
        tree_frame = ttk.LabelFrame(parent, text="Etapas do Pipeline", padding=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.scripts_tree = ttk.Treeview(tree_frame, columns=('status'), show='tree headings', selectmode='extended')
        self.scripts_tree.heading('#0', text='Módulo / Script')
        self.scripts_tree.heading('status', text='Status')
        self.scripts_tree.column('status', width=100, anchor='center')
        for module, scripts in PIPELINE_SCRIPTS.items():
            module_id = self.scripts_tree.insert('', 'end', text=module, open=True)
            for script_path in scripts:
                # Modificação para Módulo 3
                status = 'Pendente'
                if module == "Módulo 3: Avaliação Final":
                    status = 'Visualizar' # Status customizado
                self.scripts_tree.insert(module_id, 'end', text=script_path, values=(status,))
        self.scripts_tree.pack(fill=tk.BOTH, expand=True)

    def create_action_buttons(self, parent):
        actions_frame = ttk.Frame(parent, padding=(0, 10))
        actions_frame.pack(fill=tk.X)
        self.run_selected_button = ttk.Button(actions_frame, text="▶️ Executar Selecionado(s)",
                                              command=self.run_selected_scripts)
        self.run_selected_button.pack(fill=tk.X, pady=2)
        self.run_all_button = ttk.Button(actions_frame, text="🚀 Executar Módulos 1 e 2",
                                         command=self.run_all_scripts)
        self.run_all_button.pack(fill=tk.X, pady=2)
        self.stop_button = ttk.Button(actions_frame, text="🛑 Parar Execução", command=self.stop_execution,
                                      state=tk.DISABLED)
        self.stop_button.pack(fill=tk.X, pady=10)
        ttk.Separator(actions_frame, orient='horizontal').pack(fill='x', pady=10)
        self.analysis_button = ttk.Button(actions_frame, text="📊 Visualizar Resultados (Streamlit)",
                                          command=self.open_results_viewer)
        self.analysis_button.pack(fill=tk.X, pady=5)

    def create_log_area(self, parent):
        log_label = ttk.Label(parent, text="Saída da Execução:", font=('Helvetica', 11, 'bold'))
        log_label.pack(anchor="w")
        self.log_area = scrolledtext.ScrolledText(parent, wrap=tk.WORD, state="disabled", font=("Courier New", 10),
                                                  bg="#2b2b2b", fg="#d3d3d3")
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=(5, 5))
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        self.progress_bar = ttk.Progressbar(bottom_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.copy_button = ttk.Button(bottom_frame, text="📋 Copiar Saída", command=self.copy_log_to_clipboard)
        self.copy_button.pack(side=tk.RIGHT, padx=(10, 0))
        self.progress_label = ttk.Label(parent, text="")
        self.progress_label.pack(anchor="w", pady=(5, 0))

    def process_log_queue(self):
        try:
            while not self.log_queue.empty():
                msg_type, msg_value = self.log_queue.get_nowait()
                if msg_type == "LOG":
                    self.log_area.configure(state="normal")
                    self.log_area.insert(tk.END, str(msg_value) + "\n")
                    self.log_area.configure(state="disabled")
                    self.log_area.see(tk.END)
                elif msg_type == "PROGRESS_DOWNLOAD":
                    self.progress_bar['value'] = msg_value
                    self.progress_label.config(text=f"Download em andamento: {msg_value}%")
                elif msg_type == "PROGRESS_STEP":
                    self.progress_bar['value'] = msg_value[0]
                    self.progress_label.config(text=f"Executando etapa {msg_value[0] + 1}/{msg_value[1]}...")
                elif msg_type == "PROGRESS_COMPLETE":
                    self.progress_bar['value'] = self.progress_bar['maximum']
                    self.progress_label.config(text="Execução finalizada.")
                elif msg_type == "STATUS_UPDATE":
                    item_id, status = msg_value
                    if self.scripts_tree.exists(item_id):
                        self.scripts_tree.set(item_id, 'status', status)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_log_queue)

    def log_to_gui(self, message):
        self.log_queue.put(("LOG", message))

    def copy_log_to_clipboard(self):
        try:
            log_content = self.log_area.get("1.0", tk.END)
            self.clipboard_clear()
            self.clipboard_append(log_content)
            self.logger.info("Conteúdo do log copiado para a área de transferência.")
            original_text = self.copy_button.cget("text")
            self.copy_button.config(text="Copiado!")
            self.after(1500, lambda: self.copy_button.config(text=original_text))
        except Exception as e:
            self.logger.error(f"Falha ao copiar log para a área de transferência: {e}")
            messagebox.showerror("Erro ao Copiar", f"Não foi possível copiar o conteúdo:\n{e}")

    # --- INÍCIO DA MODIFICAÇÃO ---
    # Atualizado para ignorar o Módulo 3
    def get_all_script_ids(self):
        """Pega todos os IDs de scripts, exceto os do Módulo 3."""
        script_ids = []
        for module_id in self.scripts_tree.get_children():
            module_text = self.scripts_tree.item(module_id, 'text')
            # Filtro para "Executar Tudo" não incluir o visualizador
            if module_text == "Módulo 3: Avaliação Final":
                continue
            script_ids.extend(self.scripts_tree.get_children(module_id))
        return script_ids
    # --- FIM DA MODIFICAÇÃO ---

    # --- INÍCIO DA MODIFICAÇÃO ---
    # Atualizado para lidar com a seleção do Módulo 3
    def run_selected_scripts(self):
        selected_ids = self.scripts_tree.selection()
        if not selected_ids:
            messagebox.showinfo("Nenhum Script Selecionado",
                                "Por favor, selecione um ou mais scripts na lista para executar.")
            return

        # Separa os scripts normais do script do Streamlit
        script_ids_to_run = [item_id for item_id in selected_ids if self.scripts_tree.parent(item_id)]

        streamlit_script_path = "03_results_analysis/08_streamlit_results_viewer.py"
        normal_scripts = []
        streamlit_scripts = []

        for item_id in script_ids_to_run:
            script_text = self.scripts_tree.item(item_id, 'text')
            if script_text == streamlit_script_path:
                streamlit_scripts.append(item_id)
            else:
                normal_scripts.append(item_id)

        # Mensagem se o usuário selecionou apenas um módulo (pasta)
        if not normal_scripts and not streamlit_scripts and selected_ids:
             messagebox.showinfo("Nenhuma Ação", "Seleção inválida. Por favor, selecione os scripts individuais, não as pastas de Módulo.")
             return

        # Executa os scripts normais em background
        if normal_scripts:
            self.start_execution_thread(normal_scripts)

        # Lança o visualizador (não bloqueia a thread)
        if streamlit_scripts:
            self.open_results_viewer()
    # --- FIM DA MODIFICAÇÃO ---

    def run_all_scripts(self):
        # get_all_script_ids() já está modificado para excluir o Módulo 3
        script_ids_to_run = self.get_all_script_ids()
        self.start_execution_thread(script_ids_to_run)

    def start_execution_thread(self, script_ids_to_run):
        if self.execution_thread and self.execution_thread.is_alive():
            messagebox.showwarning("Aviso", "A execução já está em andamento.")
            return
        self.log_area.config(state="normal")
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state="disabled")
        self.stop_event.clear()
        self.toggle_controls_state(tk.DISABLED)

        # Reseta o status apenas dos scripts que serão executados
        for item_id in script_ids_to_run:
             if self.scripts_tree.exists(item_id):
                self.scripts_tree.set(item_id, 'status', 'Pendente')

        self.execution_thread = threading.Thread(target=self.execute_scripts, args=(script_ids_to_run,), daemon=True)
        self.execution_thread.start()

    def execute_scripts(self, script_ids_to_run):
        total_scripts = len(script_ids_to_run)
        self.progress_bar['maximum'] = total_scripts
        self.progress_bar['value'] = 0
        scripts_succeeded = True
        for i, item_id in enumerate(script_ids_to_run):
            if self.stop_event.is_set():
                self.log_to_gui("🛑 Execução em lote interrompida pelo usuário.")
                scripts_succeeded = False
                break
            script_path = self.scripts_tree.item(item_id, 'text')
            self.log_queue.put(("STATUS_UPDATE", (item_id, '⏳ Em Execução')))
            self.log_queue.put(("PROGRESS_STEP", (i, total_scripts)))
            success = self.run_single_script(script_path)
            status_icon = '✅ Sucesso' if success else '❌ Falha'
            self.log_queue.put(("STATUS_UPDATE", (item_id, status_icon)))
            if not success:
                self.log_to_gui("\n🛑 A execução em lote foi interrompida devido a um erro.")
                scripts_succeeded = False
                break
        if scripts_succeeded:
            self.log_queue.put(("PROGRESS_COMPLETE", None))
        self.toggle_controls_state(tk.NORMAL)

    def run_single_script(self, script_path):
        self.log_to_gui("─" * 80)
        self.log_to_gui(f"▶️  Executando: {script_path}")
        try:
            command = [sys.executable, script_path]
            process = subprocess.Popen(command, cwd=ROOT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1)
            for line in iter(process.stdout.readline, ''):
                if self.stop_event.is_set():
                    process.terminate()
                    return False
                line = line.strip()
                try:
                    progress_data = json.loads(line)
                    if isinstance(progress_data, dict) and progress_data.get("type") == "progress":
                        self.log_queue.put(("PROGRESS_DOWNLOAD", progress_data.get("value", 0)))
                        continue
                except json.JSONDecodeError:
                    pass
                self.log_to_gui(line)
            _, stderr = process.communicate()
            if stderr:
                self.log_to_gui(f"\n[ERROS - stderr]:\n{stderr.strip()}")
            if process.returncode == 0:
                self.log_to_gui(f"✅ '{script_path}' concluído com sucesso!")
                return True
            else:
                self.log_to_gui(f"❌ ERRO: '{script_path}' terminou com o código de erro {process.returncode}.")
                return False
        except Exception as e:
            self.log_to_gui(f"❌ ERRO CRÍTICO ao executar '{script_path}': {e}")
            return False

    def toggle_controls_state(self, state):
        for button in [self.run_selected_button, self.run_all_button, self.analysis_button]:
            button.config(state=state)
        self.stop_button.config(state="normal" if state == "disabled" else "disabled")

    def stop_execution(self):
        if self.execution_thread and self.execution_thread.is_alive():
            self.log_to_gui("--- Recebido sinal de parada. Finalizando após a etapa atual... ---")
            self.logger.warning("Sinal de parada recebido do usuário.")
            self.stop_event.set()
            self.stop_button.config(state=tk.DISABLED)

    def open_results_viewer(self):
        """Lança o painel Streamlit em um processo separado."""
        self.log_to_gui("--- 🚀 Lançando o Painel de Resultados Streamlit... ---")
        self.log_to_gui("--- O painel abrirá no seu navegador padrão. ---")

        # Caminho corrigido para o novo nome do script
        script_path = os.path.join(ROOT_DIR, "03_results_analysis", "08_streamlit_results_viewer.py")

        command = [sys.executable, "-m", "streamlit", "run", script_path]
        try:
            # Usa Popen para não bloquear a GUI
            subprocess.Popen(command, cwd=ROOT_DIR)
            self.log_to_gui(f"--- Comando executado: {' '.join(command)} ---")
        except Exception as e:
            self.log_to_gui(f"❌ ERRO CRÍTICO ao lançar Streamlit: {e}")
            messagebox.showerror("Erro ao Lançar", f"Não foi possível iniciar o Streamlit:\n{e}")

if __name__ == "__main__":
    app = MainDashboard()
    app.mainloop()