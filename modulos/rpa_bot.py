import pyautogui
import time
import pandas as pd
from datetime import datetime

pyautogui.FAILSAFE = True

class RoboOperador:
    def __init__(self, operador_nome):
        self.relatorio = []
        self.operador = operador_nome

    def executar_item(self, codigo, distribuicao, cd_total, status_ia):
        print(f"\n🤖 Operando Item {codigo}...")
        
        pyautogui.write(str(codigo))
        pyautogui.press('enter')
        time.sleep(1.5)

        if status_ia == "Estoque CD Zerado/Negativo" or cd_total <= 0:
            print("⚠️ Sem estoque no CD. Apertando ESC e N...")
            pyautogui.press('esc')
            time.sleep(0.5)
            pyautogui.press('n')
            time.sleep(1)
            
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
            time.sleep(0.1)
            
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
        time.sleep(2)

    def gerar_relatorio_csv(self):
        if not self.relatorio:
            return
        df_rel = pd.DataFrame(self.relatorio)
        nome_arquivo = f"relatorios/Envios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_rel.to_csv(nome_arquivo, index=False, sep=';')
        print(f"\n📊 Relatório gerado com sucesso: {nome_arquivo}")