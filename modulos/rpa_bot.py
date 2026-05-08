import pyautogui
import time
import pandas as pd
import os
from datetime import datetime

pyautogui.FAILSAFE = True

class RoboOperador:
    def __init__(self, operador_nome):
        self.relatorio = []
        self.operador = operador_nome
        self.contador_sessao = 0 # Controla quantos itens foram feitos nesta rodada

    def enxergar_sistema_pronto(self):
        """
        Visão Computacional Básica: 
        Tira um print da região do cursor para ver se o sistema carregou.
        Como não temos imagens padrão, usamos uma verificação de estabilidade.
        """
        print("👁️ Jarvis está observando a tela...")
        # Tira dois prints rápidos para ver se a tela parou de "piscar" (carregou)
        p1 = pyautogui.screenshot(region=(0,0, 300, 300)) 
        time.sleep(0.5)
        p2 = pyautogui.screenshot(region=(0,0, 300, 300))
        
        if p1 == p2:
            return True
        return False

    def executar_item(self, codigo, distribuicao, cd_total, status_ia):
        print(f"\n🤖 Operando Item {codigo}...")
        
        # Garante que o sistema está pronto antes de começar
        self.enxergar_sistema_pronto()

        # Só dá as setinhas se NÃO for o primeiro item da lista
        if self.contador_sessao > 0:
            pyautogui.press(['up', 'up'])
            time.sleep(0.5)

        # Blindagem: Limpa o campo antes de digitar (Segurança Extra)
        pyautogui.press('backspace', presses=10)
        
        pyautogui.write(str(codigo))
        pyautogui.press('enter')
        time.sleep(2.5) # Tempo para o Avanço carregar os dados do item

        if status_ia == "Estoque CD Zerado/Negativo" or cd_total <= 0:
            print("⚠️ Sem estoque no CD. Apertando ESC e N...")
            pyautogui.press('esc')
            time.sleep(1.0)
            pyautogui.press('n')
            time.sleep(1.5)
            
            self.relatorio.append({
                'DataHora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Operador': self.operador,
                'Codigo': codigo, 'Loja': 'TODAS', 'Qtd_Enviada': 0, 'Motivo': 'Estoque CD Zerado'
            })
            return

        for loja_id, dados in distribuicao.items():
            qtd = dados['qtd']
            
            # TRAVA ANTI-NEGATIVO ABSOLUTA
            if qtd > 0:
                # Digita apenas números positivos
                pyautogui.write(str(int(qtd)))
            
            pyautogui.press(['enter', 'enter'])
            time.sleep(0.3) # Cadência estável
            
            self.relatorio.append({
                'DataHora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Operador': self.operador,
                'Codigo': codigo, 'Loja': loja_id, 'Qtd_Enviada': max(0, qtd), 'Motivo': dados['motivo']
            })

        time.sleep(0.5)
        pyautogui.press(['enter', 'enter'])
        time.sleep(0.8)
        
        # Confirmação final
        pyautogui.write('s')
        print(f"✅ Item {codigo} salvo!")
        self.contador_sessao += 1 
        time.sleep(5) # Espera o sistema gravar antes do próximo

    def gerar_relatorio_csv(self):
        if not self.relatorio:
            return
        os.makedirs("relatorios", exist_ok=True)
        df_rel = pd.DataFrame(self.relatorio)
        nome_arquivo = f"relatorios/Envios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_rel.to_csv(nome_arquivo, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📊 Relatório gerado: {nome_arquivo}")