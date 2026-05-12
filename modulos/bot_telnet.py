# modulos/bot_telnet.py
import socket
import time
import re
from datetime import datetime
import csv
import os

# Padrões VT100
KEY_UP    = b"\x1b[A"
KEY_DOWN  = b"\x1b[B"
KEY_RIGHT = b"\x1b[C"
KEY_LEFT  = b"\x1b[D"
KEY_ENTER = b"\r"
KEY_TAB   = b"\t"
KEY_ESC   = b"\x1b"
KEY_F3    = b"\x1bOR"

# Protocolo Telnet
IAC = bytes([255])
DONT, DO, WONT, WILL = bytes([254]), bytes([253]), bytes([252]), bytes([251])
SB, SE = bytes([250]), bytes([240])

OPT_ECHO, OPT_SGA, OPT_TERMTYPE, OPT_NAWS = 1, 3, 24, 31

class BotTelnet:
    def __init__(self, operador, host="192.168.70.250", port=23, log_callback=None):
        self.operador = operador
        self.host = host
        self.port = port
        self.log_callback = log_callback
        self.sock = None
        self.conectado = False
        self.relatorio = []
        
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(msg)

    def processar_telnet(self, data: bytes):
        limpo = bytearray()
        respostas = bytearray()
        i = 0
        while i < len(data):
            if data[i] == 0xFF and i + 1 < len(data):
                cmd = data[i+1]
                if cmd == 0xFF:
                    limpo.append(0xFF)
                    i += 2
                    continue
                if cmd in (253, 254, 251, 252) and i + 2 < len(data):
                    opt = data[i+2]
                    if cmd == 253:
                        if opt in (OPT_TERMTYPE, OPT_NAWS, OPT_SGA):
                            respostas += IAC + WILL + bytes([opt])
                            if opt == OPT_NAWS:
                                respostas += IAC + SB + bytes([OPT_NAWS, 0, 80, 0, 24]) + IAC + SE
                        else:
                            respostas += IAC + WONT + bytes([opt])
                    elif cmd == 251:
                        if opt in (OPT_ECHO, OPT_SGA):
                            respostas += IAC + DO + bytes([opt])
                        else:
                            respostas += IAC + DONT + bytes([opt])
                    i += 3
                    continue
                if cmd == 250:
                    j = i + 2
                    while j + 1 < len(data):
                        if data[j] == 0xFF and data[j+1] == 0xF0:
                            break
                        j += 1
                    subneg = data[i+2:j]
                    if len(subneg) >= 2 and subneg[0] == OPT_TERMTYPE and subneg[1] == 1:
                        respostas += IAC + SB + bytes([OPT_TERMTYPE, 0]) + b"ANSI" + IAC + SE
                    i = j + 2
                    continue
                i += 2
            else:
                limpo.append(data[i])
                i += 1
        return bytes(limpo), bytes(respostas)

    def limpar_ansi(self, texto: str) -> str:
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', texto)

    def ler_tela(self, espera=1.0):
        time.sleep(espera)
        self.sock.setblocking(False)
        data = bytearray()
        deadline = time.time() + 0.5
        while time.time() < deadline:
            try:
                chunk = self.sock.recv(4096)
                if chunk:
                    data.extend(chunk)
                    deadline = time.time() + 0.2
                else:
                    break
            except BlockingIOError:
                time.sleep(0.01)
        self.sock.setblocking(True)
        raw = bytes(data)
        limpo, respostas = self.processar_telnet(raw)
        if respostas:
            self.sock.sendall(respostas)
        try:
            return limpo.decode('utf-8', errors='ignore')
        except:
            return limpo.decode('latin1', errors='ignore')

    def esperar_prompt(self, texto_esperado, timeout=10):
        acumulado = bytearray()
        inicio = time.time()
        self.sock.setblocking(False)
        while time.time() - inicio < timeout:
            try:
                chunk = self.sock.recv(4096)
                if chunk:
                    limpo, respostas = self.processar_telnet(chunk)
                    if respostas:
                        self.sock.setblocking(True)
                        self.sock.sendall(respostas)
                        self.sock.setblocking(False)
                    acumulado.extend(limpo)
                    texto = acumulado.decode('latin1', errors='ignore')
                    if texto_esperado in texto:
                        self.sock.setblocking(True)
                        return texto
            except BlockingIOError:
                time.sleep(0.05)
        self.sock.setblocking(True)
        return acumulado.decode('latin1', errors='ignore')

    def drenar_buffer(self, pausa=0.5):
        self.sock.setblocking(False)
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk: break
                _, resp = self.processar_telnet(chunk)
                if resp:
                    self.sock.setblocking(True)
                    self.sock.sendall(resp)
                    self.sock.setblocking(False)
        except BlockingIOError:
            pass
        finally:
            self.sock.setblocking(True)
        time.sleep(pausa)

    def conectar_e_navegar(self):
        self._log("📡 Conectando ao servidor Telnet...")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.conectado = True

        self._log("🔑 Login Linux...")
        self.esperar_prompt("login:", 5)
        self.sock.sendall(b"danielos\r\n")
        self.esperar_prompt("Password:", 5)
        self.sock.sendall(b"sl123456\r\n")

        self._log("🏢 Selecionando Lojas Super Luna (1)...")
        self.ler_tela(3.0)
        self.sock.sendall(b"1\r")

        self._log("🔐 Login ERP Avanço...")
        self.ler_tela(2.0)
        self.sock.sendall(b"986\r")
        self.ler_tela(1.0)
        self.sock.sendall(b"12344\r")

        self._log("⏳ Limpando erros de permissão...")
        tela = self.limpar_ansi(self.esperar_prompt("ENTER", 8))
        if "ROTINA NAO AUTORIZADA" in tela:
            self.drenar_buffer(0.3)
            self.sock.sendall(b"\r")
            self.esperar_prompt("F3:", 5)
            self.drenar_buffer(1.0)

        self._log("⬇️  Acessando Adm. Materiais...")
        self.sock.sendall(KEY_DOWN)
        time.sleep(0.5)
        self.sock.sendall(KEY_ENTER)
        
        self.esperar_prompt("Filial", 5)
        self.sock.sendall(b"70\r")

        self._log("🛤️  Navegando nos menus P > U > I > S...")
        self.esperar_prompt("ADMINISTRACAO", 5)
        for tecla in [b"P", b"U", b"I", b"\r", b"S"]:
            self.sock.sendall(tecla)
            self.ler_tela(1.0)

        self._log("📄 Aguardando tela PED990...")
        self.esperar_prompt("PED", 5)
        
        self._log("✅ Tela pronta para digitação!")

    def executar_item(self, codigo, distribuicao, cd_total, status_ia, fator=24):
        self._log(f"\n[TELNET] Operando Item {codigo}...")
        
        if not self.conectado:
            try:
                self.conectar_e_navegar()
            except Exception as e:
                self._log(f"❌ Erro de conexão Telnet: {e}")
                return

        # Para posicionar no código, damos 3 Enters
        for _ in range(3):
            self.sock.sendall(b"\r")
            self.ler_tela(0.3)

        self.sock.sendall(str(codigo).encode('ascii') + b"\r")
        tela_limpa = self.limpar_ansi(self.ler_tela(2.0))

        if "Item nao cadastrado" in tela_limpa:
            self._log(f"⚠️ Item {codigo} não cadastrado. Abortando.")
            self.sock.sendall(KEY_ESC)
            self.ler_tela(0.5)
            return

        if status_ia == "Estoque CD Zerado/Negativo" or cd_total <= 0:
            self._log(f"⚠️ Item {codigo}: Estoque crítico. Cancelando (ESC+N).")
            self.sock.sendall(KEY_ESC)
            self.ler_tela(0.5)
            self.sock.sendall(b"N")
            self.ler_tela(0.5)
            self.relatorio.append({
                'DataHora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Operador': self.operador,
                'Codigo': codigo, 'Loja': 'TODAS', 'Qtd_Enviada': 0, 'Motivo': 'Estoque CD Zerado'
            })
            return

        # Distribuição Padrão
        for loja_id, dados in distribuicao.items():
            qtd = int(dados['qtd'])
            
            if qtd > 0:
                self.sock.sendall(str(qtd).encode('ascii'))
                self._log(f"   Loja {loja_id}: {qtd} cx → {dados['motivo']}")
            else:
                self._log(f"   Loja {loja_id}: 0 cx → {dados.get('motivo', 'Ignorada')}")

            # Confirma campo
            self.sock.sendall(b"\r\r")
            eco = self.limpar_ansi(self.ler_tela(0.3))
            
            # Checa se ERP travou com mensagem (ex: Excede Máximo)
            if any(a in eco.upper() for a in ["TECLE", "ENTER", "EXCEDE", "MAXIMO"]):
                self.sock.sendall(b"\r")
                self.ler_tela(0.2)

            self.relatorio.append({
                'DataHora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Operador': self.operador,
                'Codigo': codigo, 'Loja': loja_id,
                'Qtd_Enviada': max(0, qtd), 'Motivo': dados['motivo']
            })

        self.sock.sendall(b"S\r")
        self.ler_tela(1.0)
        self._log(f"[OK] Item {codigo} salvo no ERP!")

    def gerar_relatorio_csv(self):
        if not self.relatorio:
            return
        os.makedirs(os.path.join(self.BASE_DIR, 'relatorios'), exist_ok=True)
        filename = os.path.join(self.BASE_DIR, 'relatorios', f"Relatorio_Telnet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        try:
            with open(filename, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['DataHora', 'Operador', 'Codigo', 'Loja', 'Qtd_Enviada', 'Motivo'])
                writer.writeheader()
                writer.writerows(self.relatorio)
            self._log(f"📄 Relatório salvo: {filename}")
        except Exception as e:
            self._log(f"❌ Erro ao salvar relatório: {str(e)}")

    def fechar_conexao(self):
        if self.sock:
            self.sock.close()
            self.conectado = False
