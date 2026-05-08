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
        self.df_estoque['Estoque_Num'] = pd.to_numeric(self.df_estoque['Estoque'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        # 2. TREINANDO O CLONE COMPORTAMENTAL (Machine Learning)
        self.modelo_ia = None
        if os.path.exists(caminho_db):
            print("🤖 Treinando a Inteligência Artificial com seu histórico (DB.txt)...")
            try:
                df_treino = pd.read_csv(caminho_db, sep='\t')
                if 'Peso' in df_treino.columns:
                    df_treino = df_treino.drop(columns=['Peso'])
                df_treino = df_treino.fillna(0)
                df_treino['Perfil_Loja'] = df_treino['Lj'].apply(lambda x: 1 if x in self.lojas_maiores else 0)
                
                # Variáveis que a IA usa para aprender
                features = ['Estoque CD', 'Fator', 'Estoque Loja', 'MDV', 'Norma', 'Lastro', 'Perfil_Loja']
                X = df_treino[features]
                y = df_treino['Quantidade'] # Sua decisão passada
                
                self.modelo_ia = RandomForestRegressor(n_estimators=100, random_state=42)
                self.modelo_ia.fit(X, y)
                print("✅ IA Treinada com sucesso!")
            except Exception as e:
                print(f"⚠️ Erro ao treinar IA (usando regras matemáticas de fallback): {e}")
        else:
            print("⚠️ Arquivo DB.txt não encontrado. Usando apenas regras matemáticas (Fallback).")

    def calcular_distribuicao(self, codigo, modo=1, lojas_zeradas=None):
        """
        Calcula a distribuição baseada em IA ou Regras.
        modo: 1 = Normal, 2 = Zerados
        """
        # Filtra o item
        df_item = self.df_estoque[self.df_estoque['Codigo_Produto'] == int(codigo)]
        if df_item.empty:
            return None, 0, "Item não encontrado no estoque99"

        df_mix = df_item[df_item['Mix Loja'] == 'S'].sort_values(by='Loja')
        if df_mix.empty:
            return None, 0, "Item não possui lojas ativas no Mix (Mix='S')"

        # --- INTELIGÊNCIA AUTOMÁTICA DE ZERADOS ---
        # Se o modo for 2 (Zerados) e não vierem lojas manuais, 
        # o sistema busca automaticamente quem está com Estoque_Num == 0
        if modo == 2 and not lojas_zeradas:
            lojas_zeradas = df_mix[df_mix['Estoque_Num'] <= 0]['Loja'].tolist()
            print(f"🔍 Modo Zerados Automático: Detectadas {len(lojas_zeradas)} lojas sem estoque.")

        # Proteção contra o bug do NaN no math.floor
        estoque_str = str(df_item.iloc[0]['Estoque Lojas']).replace(',', '.')
        estoque_cd_un = pd.to_numeric(estoque_str, errors='coerce')
        if pd.isna(estoque_cd_un):
            estoque_cd_un = 0 # Previne o erro do math.floor
            
        estoque_cd_cx = math.floor(estoque_cd_un / 24) # Supondo fator 24 (pode ser dinâmico depois)
        
        if estoque_cd_cx <= 0:
            return df_mix, estoque_cd_cx, "Estoque CD Zerado/Negativo"

        distribuicao = {}
        caixas_disp = estoque_cd_cx

        for _, loja in df_mix.iterrows():
            lj = int(loja['Loja'])
            
            if modo == 2:
                if lj not in lojas_zeradas:
                    distribuicao[lj] = {'qtd': 0, 'motivo': 'Ignorado (Não está zerada)'}
                    continue

            if caixas_disp <= 0:
                distribuicao[lj] = {'qtd': 0, 'motivo': 'Falta no CD'}
                continue

            perfil_loja = 1 if lj in self.lojas_maiores else 0
            
            # --- O CÉREBRO EM AÇÃO ---
            if self.modelo_ia is not None:
                # Se a IA foi treinada, ela faz a previsão baseada no seu histórico
                cenario = pd.DataFrame({
                    'Estoque CD': [estoque_cd_un],
                    'Fator': [24],
                    'Estoque Loja': [loja['Estoque_Num']],
                    'MDV': [loja['Media_Num']],
                    'Norma': [45],
                    'Lastro': [9],
                    'Perfil_Loja': [perfil_loja]
                })
                previsao = self.modelo_ia.predict(cenario)[0]
                sugestao = math.ceil(previsao)
                motivo = "Previsão Machine Learning"
            else:
                # Regra Matemática (Se a IA falhar ou não tiver DB.txt)
                necessidade = (loja['Media_Num'] * 30) - loja['Estoque_Num']
                sugestao = math.ceil(necessidade / 24) if necessidade > 0 else 0
                motivo = "Giro 30d N3ormal"

            # Trava de Segurança Final (Regras Inquebráveis)
            if sugestao > 0:
                if perfil_loja == 1: # Loja Maior
                    # Regra do Pallet (10% de margem para completar)
                    if sugestao >= (45 * 0.90):
                        sugestao = 45
                        motivo += " -> Ajustado p/ Pallet Fechado (Margem 10%)"
                    elif sugestao > 9:
                        # Regra do Lastro (Se faltar 3% ou menos para o próximo múltiplo de 9, arredonda p/ cima)
                        proximo_lastro = math.ceil(sugestao / 9) * 9
                        if (proximo_lastro - sugestao) <= (9 * 0.03):
                            sugestao = proximo_lastro
                            motivo += " -> Arredondado p/ Cima (Margem 3%)"
                        else:
                            sugestao = round(sugestao / 9) * 9 # Arredondamento normal
                            motivo += " -> Ajustado p/ Lastro"
                else: # Loja Menor
                    if sugestao > 22:
                        sugestao = 22
                        motivo += " -> Limitado Meio Pallet"
                
                if sugestao > caixas_disp:
                    sugestao = caixas_disp
                    motivo += " -> Raspou o fundo do CD"

            distribuicao[lj] = {'qtd': sugestao, 'motivo': motivo}
            caixas_disp -= sugestao

        return distribuicao, estoque_cd_cx, "Sucesso"