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

        codigo_str = str(codigo)
        pyautogui.write(codigo_str, interval=0.05)
        
        if len(codigo_str) == 6:
            self._log("[RPA] Código de 6 dígitos detectado (auto-submit). Aguardando 1s...")
            time.sleep(1.0)
        else:
            self._log("[RPA] Código menor que 6 dígitos. Enviando Enter e aguardando 4s...")
            pyautogui.press('enter')
            time.sleep(4.0)

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

        for index, (loja_id, dados) in enumerate(distribuicao.items(), start=1):
            qtd = int(dados['qtd'])

            # Trava anti-negativo no nível de hardware
            if qtd > 0:
                pyautogui.write(str(qtd), interval=0.1) # Digitação mais devagar
                self._log(f"   Loja {loja_id}: {qtd} cx → {dados['motivo']}")
            else:
                self._log(f"   Loja {loja_id}: 0 cx → {dados.get('motivo', 'Ignorada')}")

            time.sleep(0.1)
            # 1º Enter (Sempre envia a quantidade digitada)
            pyautogui.press('enter')
            time.sleep(0.4) # Aguarda a tela reagir (mudar de linha ou piscar o aviso)
            
            # =========================================================
            # CHECAGEM VISUAL DO AVISO VERMELHO (SUGESTAO ABC)
            # =========================================================
            # Use o arquivo 'calibrar_aviso.py' para descobrir as coordenadas X e Y do seu ERP
            AVISO_X = 500  # COLOQUE AQUI O X DO CALIBRADOR
            AVISO_Y = 500  # COLOQUE AQUI O Y DO CALIBRADOR
            
            try:
                # Tira print de um pequeno retângulo (40x20) em volta da coordenada para tolerar pequenas tremidas da tela
                bbox = pyautogui.screenshot(region=(AVISO_X - 20, AVISO_Y - 10, 40, 20))
                achou_vermelho = False
                for px in bbox.getdata():
                    # Checa se o pixel é dominantemente vermelho (R alto, G e B baixos)
                    if px[0] > 170 and px[1] < 70 and px[2] < 70:
                        achou_vermelho = True
                        break
                
                if achou_vermelho:
                    self._log(f"   [!] Aviso vermelho detectado na Loja {loja_id}. Dando 2º Enter (Bypass)...")
                    pyautogui.press('enter')
                    time.sleep(0.3)
            except Exception as e:
                pass # Se der erro na leitura (ex: tela minimizada), segue a vida
            
            # Pulo de grade exato: como a lista reflete a tela, a 13ª iteração é a 13ª linha (fim da página)
            if index % 13 == 0:
                self._log(f"   [!] Fim da página detectado (Loja {loja_id}). Aguardando ERP carregar próxima tela...")
                time.sleep(1.0) # Dá tempo para o ERP começar a piscar
                self.enxergar_sistema_pronto() # O robô só volta a digitar quando a tela 2 estabilizar 100%
            else:
                time.sleep(0.6) # Ritmo normal (a grade troca sozinha)


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
