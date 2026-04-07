import tkinter as tk
from tkinter import messagebox
import threading
import time
import sys

# Importando os nossos módulos
import seguranca # Lembre-se que deixamos ele na mesma pasta raiz!
from modulos.ai_core import MotorInteligencia
from modulos.rpa_bot import RoboOperador

# ==========================================
# 1. O MOTOR DO ROBÔ (A Lógica RPA)
# ==========================================
def iniciar_automacao_real(codigos_texto, motor, robo, botao_iniciar):
    botao_iniciar.config(state=tk.DISABLED)
    
    try:
        codigos = [int(x.strip()) for x in codigos_texto.split() if x.strip().isdigit()]
        
        if not codigos:
            messagebox.showwarning("Aviso", "Por favor, insira códigos válidos (números).")
            return

        messagebox.showinfo("Atenção!", "O robô vai iniciar em 5 segundos.\n\nCLIQUE NA TELA DO AVANÇO E TIRE A MÃO DO MOUSE/TECLADO!")
        time.sleep(5)
        
        for cod in codigos:
            distribuicao, cd_total, status = motor.calcular_distribuicao(cod)
            
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
# 2. TELA PRINCIPAL (Painel de Controle)
# ==========================================
def abrir_tela_principal(operador_logado):
    try:
        motor = MotorInteligencia('dados/DB.txt', 'dados/estoque99.csv')
    except Exception as e:
        messagebox.showerror("Erro Fatal", f"Erro ao carregar IA ou planilhas:\n{str(e)}")
        sys.exit()
        
    robo = RoboOperador(operador_logado)

    janela_app = tk.Tk()
    janela_app.title(f"Avanço Pro System - Operador: {operador_logado.upper()}")
    janela_app.geometry("450x550")
    janela_app.configure(padx=20, pady=20)

    tk.Label(janela_app, text="📦 SISTEMA DE REPOSIÇÃO", font=("Arial", 16, "bold")).pack(pady=(0, 5))
    tk.Label(janela_app, text=f"Bem-vindo(a), {operador_logado.title()}", fg="gray").pack(pady=(0, 20))

    tk.Label(janela_app, text="Cole os códigos dos produtos abaixo:", font=("Arial", 10, "bold")).pack(anchor="w")

    texto_codigos = tk.Text(janela_app, height=15, width=45, font=("Arial", 10))
    texto_codigos.pack(pady=10)

    def ao_clicar_iniciar():
        texto = texto_codigos.get("1.0", tk.END).strip()
        threading.Thread(target=iniciar_automacao_real, args=(texto, motor, robo, botao_iniciar), daemon=True).start()

    botao_iniciar = tk.Button(janela_app, text="⚡ INICIAR RPA", bg="green", fg="white", font=("Arial", 12, "bold"), command=ao_clicar_iniciar)
    botao_iniciar.pack(fill=tk.X, pady=10)

    janela_app.mainloop()

# ==========================================
# 3. TELA DE LOGIN (Integração com Firebase)
# ==========================================
def abrir_tela_login():
    # 1. Inicia o motor do Firebase
    auth = seguranca.AutenticadorFirebase()
    
    # 2. VERIFICAÇÃO GLOBAL (Kill Switch no Firestore)
    # Se você mudar para 'false' lá no painel do Google, ele nem abre a tela gráfica.
    if not auth.verificar_status_sistema():
        # Usamos uma janela temporária só pra exibir o erro, já que a principal não abriu ainda
        root = tk.Tk()
        root.withdraw() 
        messagebox.showerror("Acesso Negado", "O sistema está em manutenção ou foi desativado remotamente.")
        sys.exit()

    # Se o sistema tá online, desenha a tela de Login
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

        botao_login.config(text="Conectando ao servidor...", state=tk.DISABLED)
        janela_login.update()

        # 3. Faz o login no Firebase Auth
        sucesso_login, msg_login = auth.login_usuario(email, senha)
        
        if sucesso_login:
            # 4. Verifica se o usuário tem a flag ativo = true no Firestore
            sucesso_permissao, info_permissao = auth.verificar_usuario_ativo()
            
            if sucesso_permissao:
                janela_login.destroy()
                # Pega só o nome antes do @ para ficar bonito na tela (ex: joao@empresa.com -> joao)
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

# ==========================================
# INÍCIO DO PROGRAMA
# ==========================================
if __name__ == "__main__":
    abrir_tela_login()