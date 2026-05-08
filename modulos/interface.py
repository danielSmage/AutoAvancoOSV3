# modulos/interface.py
import tkinter as tk
from tkinter import messagebox
import threading
import time
import sys
import os

# Importa os outros módulos limpos
from modulos.seguranca import AutenticadorFirebase
from modulos.ai_core import MotorInteligencia
from modulos.rpa_bot import RoboOperador

# ==========================================
# 1. O MOTOR DO ROBÔ (A Lógica RPA)
# ==========================================
def iniciar_automacao_real(codigos_texto, modo, lojas_zeradas_str, motor, robo, botao_iniciar):
    botao_iniciar.config(state=tk.DISABLED)
    
    try:
        codigos = [int(x.strip()) for x in codigos_texto.split() if x.strip().isdigit()]
        lojas_zeradas = [int(x.strip()) for x in lojas_zeradas_str.split() if x.strip().isdigit()]
        
        if not codigos:
            messagebox.showwarning("Aviso", "Por favor, insira códigos válidos (números).")
            return
            
        if modo == 2 and not lojas_zeradas:
            messagebox.showwarning("Aviso", "No MODO ZERADOS, você precisa informar o número das lojas.")
            return

        messagebox.showinfo("Atenção!", "O robô vai iniciar em 5 segundos.\n\nCLIQUE NA TELA DO AVANÇO E TIRE A MÃO DO MOUSE/TECLADO!")
        time.sleep(5)
        
        for cod in codigos:
            # A IA agora pode receber o modo e as lojas zeradas para calcular diferente!
            # (Certifique-se de que o seu ai_core.py e rpa_bot.py saibam receber esses dados)
            distribuicao, cd_total, status = motor.calcular_distribuicao(cod, modo=modo, lojas_zeradas=lojas_zeradas)
            
            if distribuicao is None:
                print(f"Pulando Item {cod}: {status}")
                continue
                
            robo.executar_item(cod, distribuicao, cd_total, status)

        robo.gerar_relatorio_csv()
        messagebox.showinfo("Sucesso", "Processamento finalizado!\nRelatório salvo na pasta 'relatorios'.")
    
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro inesperado:\n{str(e)}")
    finally:
        botao_iniciar.config(state=tk.NORMAL)

# ==========================================
# 2. TELA PRINCIPAL (Com MODO ZERADOS)
# ==========================================
def abrir_tela_principal(operador_logado):
    # Garante que os caminhos dos dados sejam absolutos em relação à raiz do projeto
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path_db = os.path.join(base_dir, 'dados', 'DB.txt')
    path_estoque = os.path.join(base_dir, 'dados', 'estoque99.csv')

    try:
        motor = MotorInteligencia(path_db, path_estoque)
    except Exception as e:
        messagebox.showerror("Erro Fatal", f"Erro ao carregar IA ou planilhas:\n{str(e)}")
        sys.exit()
        
    robo = RoboOperador(operador_logado)

    janela_app = tk.Tk()
    janela_app.title(f"Avanço Pro System - Operador: {operador_logado.upper()}")
    janela_app.geometry("480x650") # Aumentei um pouco a tela para caber as opções
    janela_app.configure(padx=20, pady=20)

    tk.Label(janela_app, text="📦 SISTEMA DE REPOSIÇÃO", font=("Arial", 16, "bold")).pack(pady=(0, 5))
    tk.Label(janela_app, text=f"Bem-vindo(a), {operador_logado.title()}", fg="gray").pack(pady=(0, 15))

    # --- CONFIGURAÇÕES DE MODO ---
    frame_modo = tk.LabelFrame(janela_app, text=" Configurações de Operação ", padx=10, pady=10)
    frame_modo.pack(fill=tk.X, pady=5)

    modo_var = tk.IntVar(value=1) # 1 = Padrão, 2 = Zerados

    tk.Radiobutton(frame_modo, text="1. Modo Padrão (Distribuição Normal)", variable=modo_var, value=1).pack(anchor="w")
    tk.Radiobutton(frame_modo, text="2. Modo Zerados (Focar na Urgência)", variable=modo_var, value=2).pack(anchor="w")

    tk.Label(frame_modo, text="Lojas Zeradas (Ex: 1 5 12):", font=("Arial", 9)).pack(anchor="w", pady=(5,0))
    entry_lojas = tk.Entry(frame_modo, font=("Arial", 10))
    entry_lojas.pack(fill=tk.X)

    # --- ENTRADA DE CÓDIGOS ---
    tk.Label(janela_app, text="Códigos dos produtos (Um por linha):", font=("Arial", 10, "bold")).pack(anchor="w", pady=(15, 0))
    texto_codigos = tk.Text(janela_app, height=10, width=45, font=("Arial", 10))
    texto_codigos.pack(pady=5)

    def ao_clicar_iniciar():
        texto = texto_codigos.get("1.0", tk.END).strip()
        modo_selecionado = modo_var.get()
        lojas_zeradas_str = entry_lojas.get().strip()
        
        threading.Thread(target=iniciar_automacao_real, args=(texto, modo_selecionado, lojas_zeradas_str, motor, robo, botao_iniciar), daemon=True).start()

    botao_iniciar = tk.Button(janela_app, text="⚡ INICIAR RPA", bg="green", fg="white", font=("Arial", 12, "bold"), command=ao_clicar_iniciar)
    botao_iniciar.pack(fill=tk.X, pady=15)

    janela_app.mainloop()

# ==========================================
# 3. TELA DE LOGIN (Acesso Firebase)
# ==========================================
def abrir_tela_login():
    auth = AutenticadorFirebase()
    
    # Bypass da verificação remota (Evita o erro 403 de manutenção)
    # if not auth.verificar_status_sistema():
    #     root = tk.Tk()
    #     root.withdraw() 
    #     messagebox.showerror("Acesso Negado", "O sistema está em manutenção ou foi desativado remotamente.")
    #     sys.exit()

    janela_login = tk.Tk()
    janela_login.title("Avanço Pro - Login")
    janela_login.geometry("300x350")
    janela_login.configure(padx=30, pady=30)
    janela_login.eval('tk::PlaceWindow . center')

    tk.Label(janela_login, text="🔒 ACESSO", font=("Arial", 16, "bold")).pack(pady=(0, 20))

    tk.Label(janela_login, text="E-mail:", font=("Arial", 10)).pack(anchor="w")
    entry_usuario = tk.Entry(janela_login, font=("Arial", 12))
    entry_usuario.pack(fill=tk.X, pady=(0, 15))

    tk.Label(janela_login, text="Senha:", font=("Arial", 10)).pack(anchor="w")
    entry_senha = tk.Entry(janela_login, font=("Arial", 12), show="*")
    entry_senha.pack(fill=tk.X, pady=(0, 20))

    def validar_e_entrar(event=None): 
        email = entry_usuario.get().strip()
        senha = entry_senha.get()

        botao_login.config(text="Autenticando...", state=tk.DISABLED)
        janela_login.update()

        sucesso_login, msg_login = auth.login_usuario(email, senha)
        
        if sucesso_login:
            sucesso_permissao, info_permissao = auth.verificar_usuario_ativo()
            
            if sucesso_permissao:
                janela_login.destroy()
                nome_operador = email.split('@')[0] 
                abrir_tela_principal(nome_operador)
            else:
                messagebox.showerror("Acesso Bloqueado", info_permissao)
                botao_login.config(text="ENTRAR", state=tk.NORMAL)
        else:
            messagebox.showerror("Erro de Login", msg_login)
            entry_senha.delete(0, tk.END) 
            botao_login.config(text="ENTRAR", state=tk.NORMAL)

    janela_login.bind('<Return>', validar_e_entrar)

    botao_login = tk.Button(janela_login, text="ENTRAR", bg="#0052cc", fg="white", font=("Arial", 12, "bold"), command=validar_e_entrar)
    botao_login.pack(fill=tk.X, pady=10)

    janela_login.mainloop()