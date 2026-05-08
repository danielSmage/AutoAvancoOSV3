import pandas as pd
import math
import os
from sklearn.ensemble import RandomForestRegressor

class MotorInteligencia:
    def __init__(self, caminho_db, caminho_estoque99):
        print("🧠 Inicializando Motor de IA...")
        self.lojas_maiores = [1, 3, 4, 5, 6, 7, 8, 9, 11, 14, 15, 16, 17, 20, 22]
        
        # 1. LENDO O ESTOQUE99 (Blindado contra bugs de caracteres)
        print("📂 Lendo o estoque atual...")
        try:
            self.df_estoque = pd.read_csv(caminho_estoque99, sep=';', encoding='latin1', low_memory=False)
        except Exception:
            # Se latin1 falhar, tenta utf-8
            self.df_estoque = pd.read_csv(caminho_estoque99, sep=';', encoding='utf-8', low_memory=False)
            
        # Padroniza o nome da coluna de código para evitar o bug do "CÃ³digo"
        colunas_codigo = [col for col in self.df_estoque.columns if 'digo' in col]
        if colunas_codigo:
            self.df_estoque.rename(columns={colunas_codigo[0]: 'Codigo_Produto'}, inplace=True)
            
        self.df_estoque['Media_Num'] = pd.to_numeric(self.df_estoque['Media'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        self.df_estoque['Estoque_Num'] = pd.to_numeric(self.df_estoque['Estoque'].astype(str).str.replace(',', '.'), errors='coerce').fill        # 2. TREINANDO O CLONE COMPORTAMENTAL E CALCULANDO MÉDIA HISTÓRICA
        self.modelo_ia = None
        self.media_historica_item = {} # Dicionário {codigo: media_mdv}
        
        if os.path.exists(caminho_db):
            print("🤖 Analisando histórico (DB.txt) para cálculo de sazonalidade...")
            try:
                df_treino = pd.read_csv(caminho_db, sep='\t')
                
                # Calcula a média do MDV histórico por item
                if 'Item' in df_treino.columns and 'MDV' in df_treino.columns:
                    self.media_historica_item = df_treino.groupby('Item')['MDV'].mean().to_dict()

                if 'Peso' in df_treino.columns:
                    df_treino = df_treino.drop(columns=['Peso'])
                df_treino = df_treino.fillna(0)
                df_treino['Perfil_Loja'] = df_treino['Lj'].apply(lambda x: 1 if x in self.lojas_maiores else 0)
                
                # Variáveis que a IA usa para aprender
                features = ['Estoque CD', 'Fator', 'Estoque Loja', 'MDV', 'Norma', 'Lastro', 'Perfil_Loja']
                X = df_treino[features]
                y = df_treino['Quantidade']
                
                self.modelo_ia = RandomForestRegressor(n_estimators=100, random_state=42)
                self.modelo_ia.fit(X, y)
                print(f"✅ IA Treinada e {len(self.media_historica_item)} itens com histórico mapeado!")
            except Exception as e:
                print(f"⚠️ Erro ao treinar IA: {e}")
        else:
            print("⚠️ Arquivo DB.txt não encontrado. Sem base histórica.")

    def calcular_distribuicao(self, codigo, modo=1, lojas_zeradas=None):
        """
        Calcula a distribuição em DUAS ONDAS:
        1. Prioridade absoluta para lojas zeradas (exceto 28/29).
        2. Distribuição normal do restante baseada em IA e Giro.
        Sazonalidade: Se o giro atual for 3x maior que o histórico, usa o histórico.
        """
        codigo_int = int(codigo)
        df_item_completo = self.df_estoque[self.df_estoque['Codigo_Produto'] == codigo_int].sort_values(by='Loja')
        
        if df_item_completo.empty:
            return None, 0, "Item não encontrado no estoque99"

        # Proteção contra o bug do NaN no math.floor
        estoque_str = str(df_item_completo.iloc[0]['Estoque Lojas']).replace(',', '.')
        estoque_cd_un = pd.to_numeric(estoque_str, errors='coerce')
        if pd.isna(estoque_cd_un):
            estoque_cd_un = 0 
            
        estoque_cd_cx = math.floor(estoque_cd_un / 24) 
        if estoque_cd_cx <= 0:
            return df_item_completo, estoque_cd_cx, "Estoque CD Zerado/Negativo"

        distribuicao = {}
        caixas_disp = estoque_cd_cx
        
        # --- FILTRO DE SAZONALIDADE (Histórico vs Atual) ---
        media_hist = self.media_historica_item.get(codigo_int, 0)

        # Prepara os dados de todas as lojas
        lojas_processar = []
        for _, loja in df_item_completo.iterrows():
            lj = int(loja['Loja'])
            mdv_final = loja['Media_Num']
            
            # Se o MDV atual for ridiculamente desproporcional (>3x o histórico)
            if media_hist > 0 and mdv_final > (media_hist * 3):
                print(f"⚠️ Sazonalidade Detectada (Item {codigo_int}, Loja {lj}): {mdv_final} -> Usando Histórico {media_hist}")
                mdv_final = media_hist

            lojas_processar.append({
                'loja': lj,
                'tem_mix': (loja['Mix Loja'] == 'S'),
                'estoque': loja['Estoque_Num'],
                'mdv': mdv_final,
                'perfil': 1 if lj in self.lojas_maiores else 0
            })
            distribuicao[lj] = {'qtd': 0, 'motivo': 'Pendente'}

        # ==========================================
        # ONDA 1: PRIORIDADE ABSOLUTA (Anti-Ruptura)
        # ==========================================
        for info in lojas_processar:
            lj = info['loja']
            if not info['tem_mix'] or caixas_disp <= 0:
                continue
            
            # Se está zerada e NÃO é 28/29 -> Garante 1 caixa imediatamente
            if info['estoque'] <= 0 and lj not in [28, 29]:
                distribuicao[lj] = {'qtd': 1, 'motivo': 'Prioridade: Ruptura Zero'}
                caixas_disp -= 1

        # ==========================================
        # ONDA 2: DISTRIBUIÇÃO INTELIGENTE (Restante)
        # ==========================================
        if caixas_disp > 0:
            for info in lojas_processar:
                lj = info['loja']
                if not info['tem_mix'] or caixas_disp <= 0:
                    continue
                
                # Calcula a sugestão baseada em IA ou Giro
                if self.modelo_ia is not None:
                    cenario = pd.DataFrame({
                        'Estoque CD': [estoque_cd_un], 'Fator': [24],
                        'Estoque Loja': [info['estoque']], 'MDV': [info['mdv']],
                        'Norma': [45], 'Lastro': [9], 'Perfil_Loja': [info['perfil']]
                    })
                    previsao = self.modelo_ia.predict(cenario)[0]
                    sugestao = math.ceil(previsao)
                    motivo_base = "Decisão IA"
                else:
                    necessidade = (info['mdv'] * 30) - info['estoque']
                    sugestao = math.ceil(necessidade / 24) if necessidade > 0 else 0
                    motivo_base = "Cálculo Giro"

                # Desconta o que já foi enviado na Onda 1
                sugestao_extra = max(0, sugestao - distribuicao[lj]['qtd'])
                
                if sugestao_extra > 0:
                    # Trava de Segurança Final (Lastro/Pallet)
                    if info['perfil'] == 1: # Loja Maior
                        if (distribuicao[lj]['qtd'] + sugestao_extra) >= (45 * 0.90):
                            sugestao_extra = 45 - distribuicao[lj]['qtd']
                        elif (distribuicao[lj]['qtd'] + sugestao_extra) > 9:
                            total = round((distribuicao[lj]['qtd'] + sugestao_extra) / 9) * 9
                            sugestao_extra = total - distribuicao[lj]['qtd']
                    else: # Loja Menor
                        if (distribuicao[lj]['qtd'] + sugestao_extra) > 22:
                            sugestao_extra = 22 - distribuicao[lj]['qtd']

                    if sugestao_extra > caixas_disp:
                        sugestao_extra = caixas_disp
                    
                    distribuicao[lj]['qtd'] += sugestao_extra
                    distribuicao[lj]['motivo'] = motivo_base if distribuicao[lj]['motivo'] == 'Pendente' else "Urgência + Inteligência"
                    caixas_disp -= sugestao_extra

        # Limpa motivos de quem ficou com zero
        for lj in distribuicao:
            if distribuicao[lj]['qtd'] <= 0:
                if not any(lp['loja'] == lj and lp['tem_mix'] for lp in lojas_processar):
                    distribuicao[lj]['motivo'] = "Sem Mix"
                else:
                    distribuicao[lj]['motivo'] = "Estoque OK ou CD Esgotado"

        return distribuicao, estoque_cd_cx, "Sucesso"
= sugestao

        return distribuicao, estoque_cd_cx, "Sucesso"