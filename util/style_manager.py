# util/style_manager.py
import tkinter as tk
from tkinter import ttk
import platform
import os


class StyleManager:
    """Gerencia o estilo e o tema da aplicação Tkinter."""

    def __init__(self, root):
        self.style = ttk.Style(root)

    def apply_system_theme(self):
        """
        Detecta o sistema operacional e aplica o tema mais apropriado
        disponível para a aplicação.
        """
        try:
            system = platform.system()
            available_themes = self.style.theme_names()
            theme_to_use = None
            print(f"SO detectado: {system}. Temas disponíveis: {available_themes}")

            if system == "Windows":
                if 'vista' in available_themes:
                    theme_to_use = 'vista'
                elif 'xpnative' in available_themes:
                    theme_to_use = 'xpnative'
            elif system == "Darwin":  # macOS
                if 'aqua' in available_themes:
                    theme_to_use = 'aqua'
            elif system == "Linux":
                # Tenta detectar o ambiente de desktop para um tema mais específico
                de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
                print(f"Ambiente de Desktop (Linux) detectado: '{de}'")
                if 'kde' in de and 'breeze' in available_themes:
                    theme_to_use = 'breeze'
                elif ('gnome' in de or 'xfce' in de) and 'arc' in available_themes:
                    theme_to_use = 'arc'

            # Se nenhum tema específico do SO for encontrado, usa um fallback
            if not theme_to_use:
                for theme in ("clam", "alt", "default"):
                    if theme in available_themes:
                        theme_to_use = theme
                        break

            if theme_to_use:
                self.style.theme_use(theme_to_use)
                print(f"Tema aplicado com sucesso: '{theme_to_use}'")
            else:
                print("Aviso: Nenhum tema preferencial (vista, aqua, clam, etc.) foi encontrado.")

        except tk.TclError as e:
            print(f"Erro ao aplicar o tema do sistema: {e}")

        # Configurações de estilo globais
        self.style.configure('TButton', padding=6, font=('Helvetica', 10))
        self.style.configure('Treeview.Heading', font=('Helvetica', 10, 'bold'))
        self.style.configure("Stop.TButton", foreground="red", background="#ffdddd")