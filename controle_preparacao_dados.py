import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, font
import subprocess
import sys
import time
import threading
import queue
import os
import datetime
import logging
import platform

# --- CONFIGURAÇÃO PADRÃO ---
DEFAULT_SCRIPTS = [
    "preparação_de_dados.py",
    "sincronizar_yamls.py",
   # "reduzir_dataset.py",
    "fusao_dataset.py",
    "RT-DETR-L.py",
    "yoloV_5-11.py",
     "avaliacao_test_com_modelo.py"
     "analisador_datasets_gui.py",
]
# CORREÇÃO: Diretório de logs padronizado
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')


# --------------------

def setup_logging():
    """Configura o logger para salvar em arquivo e ser usado pela GUI."""
    os.makedirs(LOGS_DIR, exist_ok=True)

    script_name = os.path.splitext(os.path.basename(__file__))[0]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{script_name}_{timestamp}.log"
    log_filepath = os.path.join(LOGS_DIR, log_filename)

    logger = logging.getLogger('ScriptRunnerLogger')
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    log_format = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")

    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # Adiciona um handler para o console para debugging inicial
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_format)
    logger.addHandler(stream_handler)

    return logger


class ScriptRunnerApp:
    """A classe principal da aplicação GUI."""

    def __init__(self, root, scripts_to_manage, logger):
        self.root = root
        self.scripts_to_run = scripts_to_manage
        self.logger = logger
        self.logger.info("Inicializando a aplicação GUI.")

        self.root.title("Executor de Scripts com GUI Avançado")
        self.root.geometry("850x650")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.log_queue = queue.Queue()
        self.execution_thread = None
        self.stop_event = threading.Event()

        self.setup_style()
        self.setup_ui()
        self.process_queue()
        self.logger.info("UI configurada com sucesso.")

    def setup_style(self):
        """Configura o estilo dos widgets ttk com lógica avançada de detecção de SO."""
        self.style = ttk.Style()

        try:
            system = platform.system()
            available_themes = self.style.theme_names()
            theme_to_use = None
            self.logger.info(f"SO detectado: {system}. Temas disponíveis: {available_themes}")

            if system == "Windows":
                if 'vista' in available_themes:
                    theme_to_use = 'vista'
                elif 'xpnative' in available_themes:
                    theme_to_use = 'xpnative'
            elif system == "Darwin":
                if 'aqua' in available_themes: theme_to_use = 'aqua'
            elif system == "Linux":
                de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
                self.logger.info(f"Ambiente de Desktop (Linux) detectado: '{de}'")
                if 'kde' in de and 'breeze' in available_themes:
                    theme_to_use = 'breeze'
                elif ('gnome' in de or 'xfce' in de) and 'arc' in available_themes:
                    theme_to_use = 'arc'

            if not theme_to_use:
                for theme in ("clam", "alt", "default"):
                    if theme in available_themes:
                        theme_to_use = theme
                        break

            if theme_to_use:
                self.style.theme_use(theme_to_use)
                self.logger.info(f"Tema aplicado com sucesso: '{theme_to_use}'")
            else:
                self.logger.warning("Nenhum tema preferencial (vista, aqua, clam, etc.) foi encontrado.")

        except tk.TclError as e:
            self.logger.error(f"Erro ao aplicar o tema do sistema: {e}")

        self.style.configure("TButton", padding=5, font=('Helvetica', 10))
        self.style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))
        self.style.configure("Stop.TButton", foreground="red", background="#ffdddd")

    def setup_ui(self):
        """Constrói a interface gráfica principal."""
        self.create_menu()

        main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        controls_frame = ttk.Frame(main_paned_window, padding=10)
        self.create_scripts_tree(controls_frame)
        self.create_action_buttons(controls_frame)
        main_paned_window.add(controls_frame, weight=1)

        log_frame = ttk.Frame(main_paned_window, padding=10)
        self.create_log_area(log_frame)
        main_paned_window.add(log_frame, weight=3)

    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Arquivo", menu=file_menu)
        file_menu.add_command(label="Abrir Pasta de Logs", command=self.open_log_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.on_closing)
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Ajuda", menu=help_menu)
        help_menu.add_command(label="Sobre", command=self.show_about)

    def create_scripts_tree(self, parent):
        tree_frame = ttk.LabelFrame(parent, text="Scripts Disponíveis", padding=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        self.scripts_tree = ttk.Treeview(tree_frame, columns=('status'), show='tree headings')
        self.scripts_tree.heading('#0', text='Script')
        self.scripts_tree.heading('status', text='Status')
        self.scripts_tree.column('status', width=100, anchor='center')
        for script_name in self.scripts_to_run:
            self.scripts_tree.insert('', 'end', text=script_name, values=('Pendente',))
        self.scripts_tree.pack(fill=tk.BOTH, expand=True)

    def create_action_buttons(self, parent):
        actions_frame = ttk.Frame(parent, padding=(0, 10))
        actions_frame.pack(fill=tk.X)
        self.run_selected_button = ttk.Button(actions_frame, text="▶️ Executar Selecionado",
                                              command=self.run_selected_script)
        self.run_selected_button.pack(fill=tk.X, pady=2)
        self.run_all_button = ttk.Button(actions_frame, text="🚀 Executar Todos em Lote", command=self.run_all_scripts)
        self.run_all_button.pack(fill=tk.X, pady=2)
        self.stop_button = ttk.Button(actions_frame, text="🛑 Parar Execução", style="Stop.TButton",
                                      command=self.stop_execution, state=tk.DISABLED)
        self.stop_button.pack(fill=tk.X, pady=10)
        self.progress_bar = ttk.Progressbar(parent, orient='horizontal', mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)

    def create_log_area(self, parent):
        log_label = ttk.Label(parent, text="Saída da Execução:", font=('Helvetica', 11, 'bold'))
        log_label.pack(anchor="w")
        self.log_area = scrolledtext.ScrolledText(parent, wrap=tk.WORD, state="disabled", font=("Courier New", 10),
                                                  bg="#2b2b2b", fg="#d3d3d3", insertbackground="white")
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

    def log_to_gui(self, message):
        self.log_queue.put(message)

    def process_queue(self):
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.log_area.configure(state="normal")
                self.log_area.insert(tk.END, message + "\n")
                self.log_area.configure(state="disabled")
                self.log_area.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def toggle_controls_state(self, state):
        self.run_selected_button.config(state=state)
        self.run_all_button.config(state=state)
        self.scripts_tree.config(selectmode="browse" if state == "normal" else "none")
        self.stop_button.config(state="normal" if state == "disabled" else "disabled")

    # ADIÇÃO: Método para resetar status
    def reset_tree_statuses(self):
        """Reseta o status de todos os scripts na Treeview para 'Pendente'."""
        self.logger.info("Resetando status da Treeview.")
        for item_id in self.scripts_tree.get_children():
            self.scripts_tree.set(item_id, 'status', 'Pendente')

    def run_selected_script(self):
        selected_item = self.scripts_tree.focus()
        if not selected_item:
            messagebox.showinfo("Nenhum Script Selecionado", "Por favor, selecione um script na lista para executar.")
            return
        script_name = self.scripts_tree.item(selected_item, 'text')
        self.start_execution_thread([script_name])

    def run_all_scripts(self):
        self.start_execution_thread(self.scripts_to_run)

    def start_execution_thread(self, scripts_to_execute):
        if self.execution_thread and self.execution_thread.is_alive():
            messagebox.showwarning("Aviso", "A execução já está em andamento.")
            return

        self.stop_event.clear()
        self.toggle_controls_state(tk.DISABLED)

        # CORREÇÃO: Reseta os status antes de cada execução
        self.reset_tree_statuses()

        self.log_area.config(state="normal")
        self.log_area.delete('1.0', tk.END)
        self.log_area.config(state="disabled")

        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = len(scripts_to_execute)

        self.execution_thread = threading.Thread(target=self.execute_scripts, args=(scripts_to_execute,), daemon=True)
        self.execution_thread.start()

    def stop_execution(self):
        self.log_to_gui("--- Recebido sinal de parada. Finalizando após o script atual... ---")
        self.logger.warning("Sinal de parada recebido do usuário.")
        self.stop_event.set()
        self.stop_button.config(state=tk.DISABLED)

    def execute_scripts(self, scripts_to_execute):
        self.logger.info(f"Iniciando a execução de {len(scripts_to_execute)} script(s).")
        self.log_to_gui(f"🚀 Iniciando execução de {len(scripts_to_execute)} script(s)...")
        start_time = time.time()
        scripts_sucedidos = 0

        for script_name in scripts_to_execute:
            if self.stop_event.is_set():
                self.log_to_gui("🛑 Execução em lote interrompida pelo usuário.")
                self.logger.info("Execução em lote interrompida pelo usuário.")
                break

            # --- CORREÇÃO DO BUG DE ATUALIZAÇÃO DE STATUS ---
            item_id_to_update = None
            for item_id in self.scripts_tree.get_children():
                if self.scripts_tree.item(item_id, 'text') == script_name:
                    item_id_to_update = item_id
                    break

            if item_id_to_update:
                self.root.after(0, self.scripts_tree.set, item_id_to_update, 'status', '⏳ Em Execução')

            success = self.run_single_script(script_name)

            status_icon = '✅ Sucesso' if success else '❌ Falha'
            if item_id_to_update:
                self.root.after(0, self.scripts_tree.set, item_id_to_update, 'status', status_icon)

            if success:
                scripts_sucedidos += 1
            else:
                self.log_to_gui("\n🛑 A execução em lote foi interrompida devido a um erro.")
                self.logger.error("Execução em lote interrompida devido a um erro de script.")
                break

            self.root.after(0, self.progress_bar.step)

        duration = time.time() - start_time
        self.log_to_gui("=" * 70)
        self.log_to_gui("🏁 Execução finalizada.")
        self.log_to_gui(f"  - Resumo: {scripts_sucedidos}/{len(scripts_to_execute)} scripts executados com sucesso.")
        self.log_to_gui(f"  - Duração total: {duration:.2f} segundos")
        self.log_to_gui("=" * 70)
        self.logger.info(
            f"Execução finalizada. {scripts_sucedidos}/{len(scripts_to_execute)} com sucesso. Duração: {duration:.2f}s.")

        # CORREÇÃO: Reseta a barra de progresso no final
        self.root.after(0, self.progress_bar.config, {'value': 0})
        self.root.after(0, self.toggle_controls_state, tk.NORMAL)

    def run_single_script(self, script_name):
        self.log_to_gui("─" * 70)
        self.log_to_gui(f"▶️  Executando: {script_name}")
        self.logger.info(f"Executando script: '{script_name}'")

        try:
            command = [sys.executable, script_name]
            self.logger.info(f"Comando subprocess: {command}")
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                       encoding='utf-8', bufsize=1)

            for line in iter(process.stdout.readline, ''):
                self.log_to_gui(line.strip())

            stdout, stderr = process.communicate()
            if stderr:
                self.log_to_gui(f"\n⚠️ Saída de Erro (stderr):\n{stderr.strip()}")
                self.logger.warning(f"Script '{script_name}' produziu saída de erro (stderr): {stderr.strip()}")

            if process.returncode == 0:
                self.log_to_gui(f"\n✅ '{script_name}' concluído com sucesso!")
                self.logger.info(f"Script '{script_name}' concluído com sucesso (código de saída 0).")
                return True
            else:
                self.log_to_gui(f"\n❌ ERRO: '{script_name}' terminou com o código de erro {process.returncode}.")
                self.logger.error(f"Script '{script_name}' falhou com o código de erro {process.returncode}.")
                return False

        except FileNotFoundError:
            msg = f"ERRO: O arquivo '{script_name}' não foi encontrado."
            self.log_to_gui(f"❌ {msg}")
            self.logger.error(msg)
            return False
        except Exception as e:
            msg = f"ERRO: Um erro inesperado ocorreu ao executar '{script_name}': {e}"
            self.log_to_gui(f"❌ {msg}")
            self.logger.critical(msg, exc_info=True)
            return False

    def open_log_folder(self):
        self.logger.info("Usuário solicitou abrir a pasta de logs.")
        try:
            if sys.platform == "win32":
                os.startfile(LOGS_DIR)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", LOGS_DIR])
            else:
                subprocess.Popen(["xdg-open", LOGS_DIR])
        except Exception as e:
            self.logger.error(f"Não foi possível abrir a pasta de logs: {e}")
            messagebox.showerror("Erro",
                                 f"Não foi possível abrir a pasta de logs automaticamente.\n\nCaminho: {LOGS_DIR}")

    def show_about(self):
        messagebox.showinfo("Sobre o Executor de Scripts",
                            "Executor de Scripts com GUI Avançado\n\nVersão: 2.1 (Correções)\nDesenvolvido para executar e monitorar scripts Python de forma eficiente.")
        self.logger.info("Janela 'Sobre' exibida.")

    def on_closing(self):
        if self.execution_thread and self.execution_thread.is_alive():
            if messagebox.askyesno("Sair", "Uma execução está em andamento. Deseja realmente sair?"):
                self.stop_execution()
                self.logger.info("Usuário fechou a aplicação durante uma execução.")
                self.root.destroy()
            else:
                self.logger.info("Fechamento da aplicação cancelado pelo usuário.")
        else:
            self.logger.info("Aplicação fechada pelo usuário.")
            self.root.destroy()


def launch_gui(script_list=None):
    """Ponto de entrada para iniciar a GUI, pode ser importado."""
    logger = setup_logging()
    if script_list is None:
        script_list = DEFAULT_SCRIPTS
        logger.info("Nenhuma lista de scripts fornecida, usando a lista padrão.")
    else:
        logger.info(f"{len(script_list)} script(s) fornecidos para a GUI.")
    root = tk.Tk()
    app = ScriptRunnerApp(root, script_list, logger)
    root.mainloop()


if __name__ == "__main__":
    print("Iniciando a GUI em modo standalone...")
    launch_gui()
