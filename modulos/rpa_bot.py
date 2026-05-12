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
        timeout = 10
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

        if self.contador_sessao > 0:
            pyautogui.press(['up', 'up'])
            time.sleep(0.5)

        # Limpa o campo (segurança extra)
        pyautogui.press('backspace', presses=8)

        pyautogui.write(str(codigo), interval=0.05)
        pyautogui.press('enter')
        time.sleep(4.0)  # Tempo MANTIDO e AUMENTADO para 4 segundos para garantir que o ERP carregou

        if status_ia == "Estoque CD Zerado/Negativo" or cd_total <= 0:
            self._log(f"[AVISO] Item {codigo}: Sem estoque no CD. Cancelando operação...")
            pyautogui.press('esc')
            time.sleep(1.5)  # Aumentado para o usuário ver
            pyautogui.press('n')
            time.sleep(2.0)  # Aumentado para não atropelar

            self.relatorio.append({
                'DataHora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Operador': self.operador,
                'Codigo': codigo, 'Loja': 'TODAS', 'Qtd_Enviada': 0, 'Motivo': 'Estoque CD Zerado'
            })
            return

        for loja_id, dados in distribuicao.items():
            qtd = int(dados['qtd'])

            # Trava anti-negativo no nível de hardware
            if qtd > 0:
                pyautogui.write(str(qtd), interval=0.1) # Digitação mais devagar
                self._log(f"   Loja {loja_id}: {qtd} cx → {dados['motivo']}")
            else:
                self._log(f"   Loja {loja_id}: 0 cx → {dados.get('motivo', 'Ignorada')}")

            time.sleep(0.1)
            pyautogui.press(['enter', 'enter'])
            time.sleep(0.6) # Dobro do tempo antigo (0.25 -> 0.6)

            self.relatorio.append({
                'DataHora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Operador': self.operador,
                'Codigo': codigo, 'Loja': loja_id,
                'Qtd_Enviada': max(0, qtd), 'Motivo': dados['motivo']
            })

        time.sleep(1.0)
        pyautogui.press(['enter', 'enter'])
        time.sleep(1.5)

        # Confirmação final de gravação
        pyautogui.write('s')
        self._log(f"[OK] Item {codigo} salv com sucesso!")
        self.contador_sessao += 1

        # --- RETROALIMENTAÇÃO DO DB.TXT ---
        self._registrar_no_db(codigo, distribuicao, cd_total, fator)

        time.sleep(4)  # Pausa para o banco de dados do ERP processar

    def _registrar_no_db(self, codigo, distribuicao, cd_total, fator):
        """
        Salva cada distribuição no DB.txt para treinar a IA na próxima sessão.
        Formato compatível com o que o ai_core.py já lê.
        """
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            caminho_db = os.path.join(base_dir, 'dados', 'DB.txt')
            data_hoje = datetime.now().strftime("%d/%m/%Y")

            linhas = []
            for loja_id, dados in distribuicao.items():
                qtd = int(dados.get('qtd', 0))
                if qtd > 0:
                    linha = {
                        'Lj': loja_id,
                        'Data': data_hoje,
                        'Item': codigo,
                        'Quantidade': qtd,
                        'Estoque CD': cd_total * fator,  # Volta para unidades
                        'Fator': fator,
                        'Estoque Loja': 0,  # Não temos esse dado no momento da operação
                        'MDV': 0,           # Idem
                        'Norma': 45,
                        'Lastro': 9
                    }
                    linhas.append(linha)

            if linhas:
                df_novo = pd.DataFrame(linhas)
                # Adiciona ao arquivo existente (ou cria se não existir)
                if os.path.exists(caminho_db):
                    df_novo.to_csv(caminho_db, mode='a', sep='\t', index=False, header=False)
                else:
                    df_novo.to_csv(caminho_db, mode='w', sep='\t', index=False, header=True)
                self._log(f"[DB] DB.txt atualizado com {len(linhas)} linha(s) do item {codigo}.")
        except Exception as e:
            self._log(f"[AVISO] Erro ao salvar no DB.txt: {e}")

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
