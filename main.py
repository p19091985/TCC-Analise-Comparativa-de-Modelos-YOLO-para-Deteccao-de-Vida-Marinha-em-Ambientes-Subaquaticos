# main.py
import tkinter as tk
from tkinter import ttk
from modal.modal_um import JanelaModalUm
from modal.modal_dois import JanelaModalDois
from util.style_manager import StyleManager


class AplicacaoPrincipal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lançador de Ferramentas de Análise")
        style_manager = StyleManager(self)
        style_manager.apply_system_theme()

        # Centraliza a janela principal
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        win_width = 500
        win_height = 300
        pos_x = (self.screen_width - win_width) // 2
        pos_y = (self.screen_height - win_height) // 2
        self.geometry(f"{win_width}x{win_height}+{pos_x}+{pos_y}")
        self.resizable(False, False)

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Selecione a ferramenta de análise:", font=('Segoe UI', 14)).pack(pady=(0, 20))

        btn_style = ttk.Style()
        btn_style.configure('Launch.TButton', font=('Segoe UI', 11))

        botao_modal_um = ttk.Button(main_frame, text="Analisar Relatórios (.txt)",
                                    command=self.abrir_modal_um, style='Launch.TButton', padding=10)
        botao_modal_um.pack(fill=tk.X, pady=5)

        botao_modal_dois = ttk.Button(main_frame, text="Analisar Resumos (.csv)",
                                      command=self.abrir_modal_dois, style='Launch.TButton', padding=10)
        botao_modal_dois.pack(fill=tk.X, pady=5)

    def abrir_modal_um(self):
        dialogo = JanelaModalUm(self)
        self.wait_window(dialogo)

    def abrir_modal_dois(self):
        dialogo = JanelaModalDois(self)
        self.wait_window(dialogo)


if __name__ == "__main__":
    app = AplicacaoPrincipal()
    app.mainloop()