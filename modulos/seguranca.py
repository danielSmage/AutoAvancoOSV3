import requests
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (Caminho absoluto para evitar erros)
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_path, '.env')
load_dotenv(env_path)

class AutenticadorFirebase:
    def __init__(self):
        # As chaves agora são carregadas do ambiente para maior segurança
        self.API_KEY = os.getenv("FIREBASE_API_KEY", "").strip()
        self.PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "").strip()
        
        # Log de segurança para conferência (mostra apenas o início e fim da chave)
        if self.API_KEY:
            print(f"[KEY] Chave carregada: {self.API_KEY[:5]}...{self.API_KEY[-5:]}")
        else:
            print("[ERRO] FIREBASE_API_KEY não encontrada no arquivo .env!")

        # Configuração de Proxy
        self.proxies = {
            "http": os.getenv("HTTP_PROXY"),
            "https": os.getenv("HTTPS_PROXY")
        }
        # Remove se estiver vazio (None)
        self.proxies = {k: v for k, v in self.proxies.items() if v}

        self.token_atual = None
        self.uid_atual = None

    def verificar_status_sistema(self):
        url = f"https://firestore.googleapis.com/v1/projects/{self.PROJECT_ID}/databases/(default)/documents/sistema/config"
        try:
            resposta = requests.get(url, proxies=self.proxies, timeout=10)
            if resposta.status_code == 200:
                dados = resposta.json()
                return dados['fields']['status_ativo']['booleanValue']
            
            print(f"[AVISO] Erro no Firebase: Status {resposta.status_code}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"[ERRO] Erro de Conexão: {e}")
            # Se falhar a conexão, avisamos que pode ser o Proxy/Internet
            return False

    def login_usuario(self, email, senha):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.API_KEY}"
        payload = {"email": email, "password": senha, "returnSecureToken": True}
        try:
            resposta = requests.post(url, json=payload, proxies=self.proxies, timeout=10)
            dados = resposta.json()
            if "error" in dados:
                return False, f"Falha no login: {dados['error']['message']}"
            
            self.token_atual = dados["idToken"]
            self.uid_atual = dados["localId"]
            return True, "Sucesso"
        except requests.exceptions.RequestException as e:
            return False, f"Erro de conexão (Verifique o Proxy): {str(e)}"

    def verificar_usuario_ativo(self):
        if not self.uid_atual or not self.token_atual:
            return False, "Usuário não autenticado."
            
        url = f"https://firestore.googleapis.com/v1/projects/{self.PROJECT_ID}/databases/(default)/documents/usuarios/{self.uid_atual}"
        headers = {"Authorization": f"Bearer {self.token_atual}"}
        
        try:
            resposta = requests.get(url, headers=headers, proxies=self.proxies, timeout=10)
            if resposta.status_code == 200:
                dados = resposta.json()
                if 'fields' in dados and 'ativo' in dados['fields']:
                    usuario_ativo = dados['fields']['ativo']['booleanValue']
                    if usuario_ativo:
                        return True, "Acesso Liberado"
                    else:
                        return False, "Sua conta foi desativada pelo administrador."
                else:
                    return False, "Cadastro incompleto no banco."
            else:
                return False, "Acesso negado."
        except requests.exceptions.RequestException as e:
            return False, f"Erro de conexão (Proxy): {str(e)}"