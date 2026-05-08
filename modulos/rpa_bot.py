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

    def executar_item(self, codigo, distribuicao, cd_total, status_ia):
        print(f"\n🤖 Operando Item {codigo}...")
        
        # Só dá as setinhas se NÃO for o primeiro item da lista
        if self.contador_sessao > 0:
            pyautogui.press(['up', 'up'])
            time.sleep(0.5)

        pyautogui.write(str(codigo))
        # Removido o ENTER extra: o sistema já cai na Loja 1 sozinho.
        time.sleep(2.0) # Espera um pouco mais para o sistema carregar o item

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
            if qtd > 0:
                pyautogui.write(str(qtd))
            
            pyautogui.press(['enter', 'enter'])
            time.sleep(0.4) # Cadência mais lenta entre lojas (era 0.1)
            
            self.relatorio.append({
                'DataHora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Operador': self.operador,
                'Codigo': codigo, 'Loja': loja_id, 'Qtd_Enviada': qtd, 'Motivo': dados['motivo']
            })

        time.sleep(0.5)
        pyautogui.press(['enter', 'enter'])
        time.sleep(0.5)
        pyautogui.write('s')
        print(f"✅ Item {codigo} salvo!")
        self.contador_sessao += 1 
        time.sleep(5) # Aguarda o processamento do sistema antes do próximo item

    def gerar_relatorio_csv(self):
        if not self.relatorio:
            return
            
        # Garante que a pasta relatorios existe para não dar erro de salvamento
        os.makedirs("relatorios", exist_ok=True)
            
        df_rel = pd.DataFrame(self.relatorio)
        nome_arquivo = f"relatorios/Envios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Usa utf-8-sig para compatibilidade com acentos no Excel
        df_rel.to_csv(nome_arquivo, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📊 Relatório gerado com sucesso: {nome_arquivo}")