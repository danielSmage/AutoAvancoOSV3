# modulos/interface.py
import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import sys
import os
import json

from modulos.seguranca import AutenticadorFirebase
from modulos.ai_core import MotorInteligencia
from modulos.rpa_bot import RoboOperador
from modulos.bot_telnet import BotTelnet

# Configurações globais de aparência
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Caminho do arquivo de configuração local
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_CONFIG = os.path.join(BASE_DIR, 'dados', 'config.json')

def carregar_config():
    """Carrega configurações salvas ou retorna padrões."""
    defaults = {"host": "", "porta": "23", "conexao": "pyautogui"}
    if os.path.exists(CAMINHO_CONFIG):
        try:
            with open(CAMINHO_CONFIG, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                defaults.update(dados)
        except Exception:
            pass
    return defaults

def salvar_config(cfg):
    """Salva configurações no arquivo local."""
    os.makedirs(os.path.dirname(CAMINHO_CONFIG), exist_ok=True)
    with open(CAMINHO_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ==========================================
# JANELA DE CONFIGURAÇÕES
# ==========================================
class JanelaConfiguracoes(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Configurações")
        self.geometry("380x320")
        self.resizable(False, False)
        self.grab_set()  # Bloqueia a janela principal enquanto estiver aberta

        cfg = carregar_config()

        ctk.CTkLabel(self, text="CONFIGURAÇÕES DE CONEXÃO", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 15))

        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20)

        ctk.CTkLabel(frame, text="Host / IP do Servidor:", anchor="w").grid(row=0, column=0, padx=10, pady=(10, 2), sticky="w")
        self.entry_host = ctk.CTkEntry(frame, placeholder_text="Ex: 192.168.0.50")
        self.entry_host.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.entry_host.insert(0, cfg.get("host", ""))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Porta:", anchor="w").grid(row=2, column=0, padx=10, pady=(0, 2), sticky="w")
        self.entry_porta = ctk.CTkEntry(frame, placeholder_text="23")
        self.entry_porta.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.entry_porta.insert(0, cfg.get("porta", "23"))

        ctk.CTkLabel(frame, text="Tipo de Conexão:", anchor="w").grid(row=4, column=0, padx=10, pady=(0, 2), sticky="w")
        self.opt_conexao = ctk.CTkOptionMenu(frame, values=["pyautogui", "telnet"])
        self.opt_conexao.grid(row=5, column=0, padx=10, pady=(0, 15), sticky="ew")
        self.opt_conexao.set(cfg.get("conexao", "pyautogui"))

        ctk.CTkButton(self, text="SALVAR", command=self._salvar).pack(pady=20, padx=20, fill="x")

    def _salvar(self):
        cfg = {
            "host": self.entry_host.get().strip(),
            "porta": self.entry_porta.get().strip() or "23",
            "conexao": self.opt_conexao.get()
        }
        salvar_config(cfg)
        
        # Atualiza a referência da janela principal para recarregar o robô
        self.master.preparar_motores()
        
        messagebox.showinfo("Configurações", "Salvo com sucesso!", parent=self)
        self.destroy()


# ==========================================
# TELA PRINCIPAL
# ==========================================
class AppReposicao(ctk.CTk):
    def __init__(self, operador_logado):
        super().__init__()

        self.operador_logado = operador_logado
        self.title(f"AVANÇO PRO SYSTEM V2 — {operador_logado.upper()}")
        self.geometry("520x780")

        self.preparar_motores()

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # Área de códigos expansível
        self.grid_rowconfigure(6, weight=1)  # Área de log expansível

        # --- CABEÇALHO ---
        frame_cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        frame_cabecalho.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="ew")
        frame_cabecalho.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame_cabecalho, text="AVANÇO PRO", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(frame_cabecalho, text=f"Sessão: {operador_logado.title()}", text_color="gray").grid(row=1, column=0, sticky="w")

        # Botão de configurações no canto superior direito
        self.btn_config = ctk.CTkButton(
            frame_cabecalho, text="⚙️ Config", width=90, height=30,
            fg_color="gray30", hover_color="gray40",
            command=self._abrir_configuracoes
        )
        self.btn_config.grid(row=0, column=1, rowspan=2, padx=(10, 0), sticky="e")

        # --- MODO DE OPERAÇÃO ---
        self.frame_modo = ctk.CTkFrame(self)
        self.frame_modo.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.frame_modo.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.frame_modo, text="MODO DE OPERAÇÃO", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        self.modo_var = ctk.IntVar(value=1)

        ctk.CTkRadioButton(
            self.frame_modo,
            text="Distribuição Padrão (IA)",
            variable=self.modo_var, value=1
        ).grid(row=1, column=0, padx=15, pady=5, sticky="w")

        ctk.CTkRadioButton(
            self.frame_modo,
            text="Focar Lojas Zeradas (detectadas automaticamente)",
            variable=self.modo_var, value=2
        ).grid(row=2, column=0, padx=15, pady=(5, 15), sticky="w")

        # --- ENTRADA DE CÓDIGOS ---
        ctk.CTkLabel(self, text="CÓDIGOS DOS PRODUTOS", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=3, column=0, padx=20, pady=(15, 5), sticky="w")

        self.txt_codigos = ctk.CTkTextbox(self, font=("Consolas", 12), height=150)
        self.txt_codigos.grid(row=4, column=0, padx=20, pady=5, sticky="nsew")

        # --- BOTÃO DE INÍCIO ---
        self.btn_iniciar = ctk.CTkButton(
            self, text="▶  EXECUTAR RPA", height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#1f538d", hover_color="#14375e",
            command=self.ao_clicar_iniciar
        )
        self.btn_iniciar.grid(row=5, column=0, padx=20, pady=(15, 5), sticky="ew")

        # --- ÁREA DE LOG EM TEMPO REAL ---
        ctk.CTkLabel(self, text="LOG DE OPERAÇÃO", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").grid(
            row=7, column=0, padx=20, pady=(10, 2), sticky="w")

        self.txt_log = ctk.CTkTextbox(self, font=("Consolas", 10), height=180, state="disabled", text_color="#aaffaa")
        self.txt_log.grid(row=6, column=0, padx=20, pady=(5, 5), sticky="nsew")

        # --- STATUS ---
        self.lbl_status = ctk.CTkLabel(self, text="Pronto para iniciar.", text_color="gray", font=ctk.CTkFont(size=11))
        self.lbl_status.grid(row=8, column=0, padx=20, pady=(0, 15))

    def _log(self, msg):
        """Escreve no painel de log de forma thread-safe."""
        def _escrever():
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", msg + "\n")
            self.txt_log.see("end")  # Auto-scroll
            self.txt_log.configure(state="disabled")
        self.after(0, _escrever)

    def _abrir_configuracoes(self):
        JanelaConfiguracoes(self)

    def preparar_motores(self):
        path_db = os.path.join(BASE_DIR, 'dados', 'DB.txt')
        path_estoque = os.path.join(BASE_DIR, 'dados', 'estoque99.csv')

        cfg = carregar_config()
        modo_conexao = cfg.get("conexao", "pyautogui")
        host = cfg.get("host", "192.168.70.250")
        porta = int(cfg.get("porta", 23) or 23)

        try:
            self.motor = MotorInteligencia(path_db, path_estoque)
            
            if modo_conexao == "telnet":
                self.robo = BotTelnet(self.operador_logado, host=host, port=porta, log_callback=self._log)
            else:
                self.robo = RoboOperador(self.operador_logado, log_callback=self._log)
                
        except Exception as e:
            messagebox.showerror("Erro Fatal", f"Erro ao inicializar sistemas:\n{str(e)}")
            sys.exit()

    def ao_clicar_iniciar(self):
        texto = self.txt_codigos.get("1.0", "end-1c").strip()
        if not texto:
            messagebox.showwarning("Aviso", "Insira pelo menos um código.")
            return

        # Limpa o log anterior
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")

        self.btn_iniciar.configure(state="disabled", text="EM EXECUÇÃO...")
        self.lbl_status.configure(text="Aguardando 5 segundos para início...", text_color="#ffcc00")

        threading.Thread(target=self.processar_automacao, args=(texto,), daemon=True).start()

    def processar_automacao(self, codigos_texto):
        try:
            self.robo.contador_sessao = 0  # Reset para ignorar setinhas no 1º item
            codigos = [int(x.strip()) for x in codigos_texto.split() if x.strip().isdigit()]
            modo = self.modo_var.get()

            modo_nome = "Distribuição Padrão" if modo == 1 else "Focar Lojas Zeradas"
            self._log(f"🚀 Iniciando em modo: {modo_nome}")
            self._log(f"📋 {len(codigos)} código(s) na fila: {codigos}")
            self._log("⏳ Aguardando 5 segundos — mova o cursor para a tela do Avanço...")

            time.sleep(5)

            for i, cod in enumerate(codigos):
                self.after(0, lambda i=i, cod=cod: self.lbl_status.configure(
                    text=f"Processando Item {i+1}/{len(codigos)}: {cod}", text_color="#ffcc00"))

                self._log(f"\n{'='*40}")
                self._log(f"[{i+1}/{len(codigos)}] Item {cod}")

                distribuicao, cd_total, status = self.motor.calcular_distribuicao(cod, modo=modo)

                # Sempre chama o robô para ele digitar o código na tela. 
                # Se não houver distribuição (ex: estoque negativo), ele fará a tratativa de ESC e N.
                if distribuicao is None:
                    distribuicao = {}
                self.robo.executar_item(cod, distribuicao, cd_total, status)

            self.robo.gerar_relatorio_csv()
            self._log("\n✅ PROCESSAMENTO FINALIZADO!")
            self.after(0, lambda: self.lbl_status.configure(text="Finalizado com sucesso!", text_color="#44ff44"))
            messagebox.showinfo("Sucesso", "RPA finalizado com sucesso!\nRelatório salvo na pasta 'relatorios'.")

        except Exception as e:
            self._log(f"\n❌ ERRO CRÍTICO: {str(e)}")
            messagebox.showerror("Erro Crítico", f"Falha na automação:\n{str(e)}")
        finally:
            self.after(0, lambda: self.btn_iniciar.configure(state="normal", text="▶  EXECUTAR RPA"))


def abrir_tela_principal(operador):
    app = AppReposicao(operador)
    app.mainloop()


# ==========================================
# TELA DE LOGIN
# ==========================================
def abrir_tela_login():
    auth = AutenticadorFirebase()

    login = ctk.CTk()
    login.title("Avanço Pro — Login")
    login.geometry("350x450")
    login.eval('tk::PlaceWindow . center')

    ctk.CTkLabel(login, text="ACESSO RESTRITO", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(40, 30))

    entry_email = ctk.CTkEntry(login, placeholder_text="Seu E-mail", width=250, height=40)
    entry_email.insert(0, "leandro@passos.com")
    entry_email.pack(pady=10)

    entry_senha = ctk.CTkEntry(login, placeholder_text="Sua Senha", width=250, height=40, show="*")
    entry_senha.insert(0, "leandro")
    entry_senha.pack(pady=10)

    def executar_login(event=None):
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

    login.bind('<Return>', executar_login)

    btn_login = ctk.CTkButton(
        login, text="ENTRAR", width=250, height=45,
        font=ctk.CTkFont(weight="bold"), command=executar_login
    )
    btn_login.pack(pady=30)

    login.mainloop()
