import pyautogui
import time
import pandas as pd
import os
from datetime import datetime
from abc import ABC, abstractmethod

pyautogui.FAILSAFE = True

# ==========================================
# BASE ABSTRATA — Prepara plug-in Telnet futuro
# ==========================================
class BaseOperador(ABC):
    """Interface comum para qualquer operador (pyautogui ou Telnet futuro)."""

    @abstractmethod
    def executar_item(self, codigo, distribuicao, cd_total, status_ia, fator=24):
        pass

    @abstractmethod
    def gerar_relatorio_csv(self):
        pass


# ==========================================
# OPERADOR PYAUTOGUI — Atual (tela gráfica)
# ==========================================
class RoboOperador(BaseOperador):
    def __init__(self, operador_nome, log_callback=None):
        self.relatorio = []
        self.operador = operador_nome
        self.contador_sessao = 0
        self.log_callback = log_callback  # Função da interface para exibir mensagens

    def _log(self, msg):
        """Envia mensagem para a interface ou para o terminal."""
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(msg)

    def enxergar_sistema_pronto(self):
        """
        Visão Computacional: verifica estabilidade da tela com timeout de 10s.
        """
        self._log("[VISAO] Aguardando estabilidade da tela...")
        timeout = 20  # ERP pode levar até 20s para carregar produtos com muitas lojas
        start_time = time.time()

        while time.time() - start_time < timeout:
            p1 = pyautogui.screenshot(region=(0, 0, 400, 400))
            time.sleep(0.4)
            p2 = pyautogui.screenshot(region=(0, 0, 400, 400))

            if p1 == p2:
                self._log("[OK] Tela estabilizada. Iniciando operação.")
                return True
            time.sleep(0.2)

        self._log("[AVISO] Timeout de estabilidade — prosseguindo mesmo assim.")
        return False

    def executar_item(self, codigo, distribuicao, cd_total, status_ia, fator=24):
        self._log(f"\n[ROBO] Operando Item {codigo}...")

        self.enxergar_sistema_pronto()

        # Limpa o campo de código (segurança)
        pyautogui.press('backspace', presses=8)

        # 1. Digita o código do produto
        codigo_str = str(codigo)
        pyautogui.write(codigo_str, interval=0.05)
        
        if len(codigo_str) == 6:
            self._log("[RPA] Código de 6 caracteres (auto-submit). Aguardando carregar...")
            time.sleep(1.5)
        else:
            self._log("[RPA] Código menor que 6 caracteres. Enviando Enter...")
            pyautogui.press('enter')
            time.sleep(1.5)

        if status_ia == "Estoque CD Zerado/Negativo" or cd_total <= 0:
            self._log(f"[AVISO] Item {codigo}: Sem estoque no CD. Cancelando operação...")
            pyautogui.press('esc')
            time.sleep(0.5)
            self._log("[RPA] Seta para cima para pular o item zerado.")
            pyautogui.press('up')
            
            self.relatorio.append({
                'DataHora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Operador': self.operador,
                'Codigo': codigo, 'Loja': 'TODAS', 'Qtd_Enviada': 0, 'Motivo': 'Estoque CD Zerado'
            })
            return

        # 2. Digita Loja e Quantidade
        for loja_id, dados in distribuicao.items():
            qtd = int(dados.get('qtd', 0))

            if qtd > 0:
                self._log(f"   Loja {loja_id}: {qtd} cx → {dados.get('motivo', '')}")
                
                # a. Digita a loja
                loja_str = str(loja_id)
                pyautogui.write(loja_str, interval=0.01)
                
                # Se for loja de 1 dígito (ex: 1 a 9), precisa de Enter
                if len(loja_str) < 2:
                    pyautogui.press('enter')
                
                time.sleep(0.1)
                
                # Responde à pergunta "prossegue para alterar?"
                pyautogui.write('a')
                time.sleep(0.05)
                
                # b. Digita a quantidade, um enter e cinco letras 's'
                pyautogui.write(str(qtd), interval=0.01)
                pyautogui.press('enter')
                time.sleep(0.1)
                pyautogui.write('sssss', interval=0.01)
                time.sleep(0.1)

                self.relatorio.append({
                    'DataHora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'Operador': self.operador,
                    'Codigo': codigo, 'Loja': loja_id,
                    'Qtd_Enviada': max(0, qtd), 'Motivo': dados.get('motivo', '')
                })

        # 3. Finaliza o código com seta para cima
        time.sleep(0.3)
        self._log(f"[OK] Item {codigo} finalizado. Seta para Cima para o próximo...")
        pyautogui.press('up')
        time.sleep(0.3)

        self.contador_sessao += 1

        # --- RETROALIMENTAÇÃO DO DB.TXT ---
        self._registrar_no_db(codigo, distribuicao, cd_total, fator)

    def _registrar_no_db(self, codigo, distribuicao, cd_total, fator):
        """
        Salva cada distribuição no db.csv para treinar a IA continuamente.
        Inclui contexto adicional (MDV, DDV, Alvo original) para evitar data leakage
        e permitir que o modelo diferencie decisões ideais de decisões limitadas por escassez.
        """
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            caminho_db = os.path.join(base_dir, 'dados', 'db.csv')
            data_hoje = datetime.now().strftime("%d/%m/%Y")

            linhas = []
            for loja_id, dados in distribuicao.items():
                qtd = int(dados.get('qtd', 0))
                if qtd > 0:
                    cx_alvo = dados.get('cx_alvo', qtd)
                    linha = {
                        'Lj': loja_id,
                        'Data': data_hoje,
                        'Item': codigo,
                        'Descricao': '',
                        'Quantidade Digitada': qtd,
                        'Estoque': dados.get('estoque', 0),
                        'UN': '',
                        'Fator': fator,
                        'Peso': '',
                        'Comp': '',
                        'N.Comp': '',
                        'MDV_Momento': dados.get('mdv', 0),
                        'DDV_Momento': dados.get('ddv', 0),
                        'Qtd_Alvo_Original': cx_alvo,
                        'Foi_Limitado': 1 if qtd < cx_alvo else 0,
                    }
                    linhas.append(linha)

            if linhas:
                df_novo = pd.DataFrame(linhas)
                
                # Deduplicação: não grava se o mesmo item+loja+data já existe no db.csv
                if os.path.exists(caminho_db):
                    try:
                        df_existente = pd.read_csv(caminho_db, sep=';', encoding='latin1',
                                                   low_memory=False, on_bad_lines='skip',
                                                   usecols=['Lj', 'Data', 'Item'])
                        chaves_existentes = set(
                            zip(df_existente['Lj'].astype(str),
                                df_existente['Data'].astype(str),
                                df_existente['Item'].astype(str))
                        )
                        df_novo['_chave'] = list(zip(
                            df_novo['Lj'].astype(str),
                            df_novo['Data'].astype(str),
                            df_novo['Item'].astype(str)
                        ))
                        df_novo = df_novo[~df_novo['_chave'].isin(chaves_existentes)]
                        df_novo = df_novo.drop(columns=['_chave'])
                    except Exception:
                        pass  # Se falhar a leitura, grava sem dedup
                
                if not df_novo.empty:
                    if os.path.exists(caminho_db):
                        df_novo.to_csv(caminho_db, mode='a', sep=';', index=False, header=False, encoding='latin1')
                    else:
                        df_novo.to_csv(caminho_db, mode='w', sep=';', index=False, header=True, encoding='latin1')
                    self._log(f"[DB] db.csv atualizado com {len(df_novo)} linha(s) do item {codigo}.")
                else:
                    self._log(f"[DB] Item {codigo} já registrado hoje — pulando dedup.")
        except Exception as e:
            self._log(f"[AVISO] Erro ao salvar no db.csv: {e}")

    def gerar_relatorio_csv(self):
        if not self.relatorio:
            return
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pasta_rel = os.path.join(base_dir, 'relatorios')
        os.makedirs(pasta_rel, exist_ok=True)
        df_rel = pd.DataFrame(self.relatorio)
        nome_arquivo = os.path.join(pasta_rel, f"Envios_Inteligentes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df_rel.to_csv(nome_arquivo, index=False, sep=';', encoding='utf-8-sig')
        self._log(f"\n[RELATORIO] Relatório gerado: {nome_arquivo}")
