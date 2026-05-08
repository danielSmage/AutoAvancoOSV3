# modulos/interface.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import sys
import os

# Importa os outros módulos
from modulos.seguranca import AutenticadorFirebase
from modulos.ai_core import MotorInteligencia
from modulos.rpa_bot import RoboOperador

# Configurações globais de aparência
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AppReposicao(ctk.CTk):
    def __init__(self, operador_logado):
        super().__init__()

        self.operador_logado = operador_logado
        self.title(f"AVANÇO PRO SYSTEM V2 - {operador_logado.upper()}")
        self.geometry("500x700")
        
        # Inicializa o motor e o robô
        self.preparar_motores()

        # Layout Principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # 1. Cabeçalho
        self.lbl_titulo = ctk.CTkLabel(self, text="AVANÇO PRO", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_titulo.grid(row=0, column=0, padx=20, pady=(20, 5))

        self.lbl_subtitulo = ctk.CTkLabel(self, text=f"Sessão Ativa: {operador_logado.title()}", text_color="gray")
        self.lbl_subtitulo.grid(row=1, column=0, padx=20, pady=(0, 20))

        # 2. Configurações de Modo (Card)
        self.frame_modo = ctk.CTkFrame(self)
        self.frame_modo.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.frame_modo.grid_columnconfigure(0, weight=1)

        self.lbl_config = ctk.CTkLabel(self.frame_modo, text="MODO DE OPERAÇÃO", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_config.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        self.modo_var = ctk.IntVar(value=1)
        
        self.rb_normal = ctk.CTkRadioButton(self.frame_modo, text="Distribuição Padrão (IA)", variable=self.modo_var, value=1)
        self.rb_normal.grid(row=1, column=0, padx=15, pady=5, sticky="w")

        self.rb_zerados = ctk.CTkRadioButton(self.frame_modo, text="Focar Lojas Zeradas (Urgência)", variable=self.modo_var, value=2)
        self.rb_zerados.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="w")

        # 3. Entrada de Códigos
        self.lbl_codigos = ctk.CTkLabel(self, text="CÓDIGOS DOS PRODUTOS", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_codigos.grid(row=3, column=0, padx=20, pady=(15, 5), sticky="w")

        self.txt_codigos = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.txt_codigos.grid(row=4, column=0, padx=20, pady=5, sticky="nsew")

        # 4. Botão de Início
        self.btn_iniciar = ctk.CTkButton(self, text="EXECUTAR RPA", height=50, font=ctk.CTkFont(size=16, weight="bold"),
                                        fg_color="#1f538d", hover_color="#14375e", command=self.ao_clicar_iniciar)
        self.btn_iniciar.grid(row=5, column=0, padx=20, pady=20, sticky="ew")

        # 5. Barra de Status
        self.lbl_status = ctk.CTkLabel(self, text="Pronto para iniciar.", text_color="gray", font=ctk.CTkFont(size=11))
        self.lbl_status.grid(row=6, column=0, padx=20, pady=(0, 10))

    def preparar_motores(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path_db = os.path.join(base_dir, 'dados', 'DB.txt')
        path_estoque = os.path.join(base_dir, 'dados', 'estoque99.csv')

        try:
            self.motor = MotorInteligencia(path_db, path_estoque)
            self.robo = RoboOperador(self.operador_logado)
        except Exception as e:
            messagebox.showerror("Erro Fatal", f"Erro ao inicializar sistemas:\n{str(e)}")
            sys.exit()

    def ao_clicar_iniciar(self):
        texto = self.txt_codigos.get("1.0", "end-1c").strip()
        if not texto:
            messagebox.showwarning("Aviso", "Insira pelo menos um código.")
            return

        self.btn_iniciar.configure(state="disabled", text="EM EXECUÇÃO...")
        self.lbl_status.configure(text="Aguardando 5 segundos para início...", text_color="#ffcc00")
        
        threading.Thread(target=self.processar_automacao, args=(texto,), daemon=True).start()

    def processar_automacao(self, codigos_texto):
        try:
            self.robo.contador_sessao = 0 # Reset para ignorar setinhas no 1º item
            codigos = [int(x.strip()) for x in codigos_texto.split() if x.strip().isdigit()]
            modo = self.modo_var.get()
            
            time.sleep(5)
            
            for i, cod in enumerate(codigos):
                self.lbl_status.configure(text=f"Processando Item {i+1}/{len(codigos)}: {cod}")
                
                # Chamada corrigida (consistentemente com ai_core.py)
                distribuicao, cd_total, status = self.motor.calcular_distribuicao(cod, modo=modo)
                
                if distribuicao:
                    self.robo.executar_item(cod, distribuicao, cd_total, status)
                else:
                    print(f"Item {cod} ignorado: {status}")

            self.robo.gerar_relatorio_csv()
            self.lbl_status.configure(text="Processamento Finalizado!", text_color="#44ff44")
            messagebox.showinfo("Sucesso", "RPA finalizado com sucesso!")
        
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Falha na automação:\n{str(e)}")
        finally:
            self.btn_iniciar.configure(state="normal", text="EXECUTAR RPA")

def abrir_tela_principal(operador):
    app = AppReposicao(operador)
    app.mainloop()

def abrir_tela_login():
    auth = AutenticadorFirebase()
    
    # Design da tela de login
    login = ctk.CTk()
    login.title("Avanço Pro - Login")
    login.geometry("350x450")
    login.eval('tk::PlaceWindow . center')

    ctk.CTkLabel(login, text="ACESSO RESTRITO", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(40, 30))

    entry_email = ctk.CTkEntry(login, placeholder_text="Seu E-mail", width=250, height=40)
    entry_email.pack(pady=10)

    entry_senha = ctk.CTkEntry(login, placeholder_text="Sua Senha", width=250, height=40, show="*")
    entry_senha.pack(pady=10)

    def executar_login():
        email = entry_email.get().strip()
        senha = entry_senha.get()
        
        btn_login.configure(state="disabled", text="Verificando...")
        
        sucesso, msg = auth.login_usuario(email, senha)
        if sucesso:
            sucesso_per, info_per = auth.verificar_usuario_ativo()
            if sucesso_per:
                login.destroy()
                abrir_tela_principal(email.split('@')[0])
            else:
                messagebox.showerror("Acesso", info_per)
                btn_login.configure(state="normal", text="ENTRAR")
        else:
            messagebox.showerror("Erro", msg)
            btn_login.configure(state="normal", text="ENTRAR")

    btn_login = ctk.CTkButton(login, text="ENTRAR", width=250, height=45, font=ctk.CTkFont(weight="bold"), command=executar_login)
    btn_login.pack(pady=30)

    login.mainloop()