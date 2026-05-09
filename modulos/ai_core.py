import pandas as pd
import math
import os
from sklearn.ensemble import RandomForestRegressor

class MotorInteligencia:
    def __init__(self, caminho_db, caminho_estoque99):
        print("[IA] Inicializando Motor de IA...")
        self.lojas_maiores = [1, 3, 4, 5, 6, 7, 8, 9, 11, 14, 15, 16, 17, 20, 22]
        
        # 1. LENDO O ESTOQUE99
        print("[ARQUIVO] Lendo o estoque atual...")
        try:
            self.df_estoque = pd.read_csv(caminho_estoque99, sep=';', encoding='latin1', low_memory=False)
        except Exception:
            self.df_estoque = pd.read_csv(caminho_estoque99, sep=';', encoding='utf-8', low_memory=False)
            
        # Padroniza o nome da coluna de código
        colunas_codigo = [col for col in self.df_estoque.columns if 'digo' in col]
        if colunas_codigo:
            self.df_estoque.rename(columns={colunas_codigo[0]: 'Codigo_Produto'}, inplace=True)
            
        self.df_estoque['Media_Num'] = pd.to_numeric(self.df_estoque['Media'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        self.df_estoque['Estoque_Num'] = pd.to_numeric(self.df_estoque['Estoque'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        # Normaliza coluna de fator/aplicação para uso dinâmico
        colunas_fator = [col for col in self.df_estoque.columns if 'plicac' in col or 'ator' in col.lower()]
        self.coluna_fator = colunas_fator[0] if colunas_fator else None
        if self.coluna_fator:
            self.df_estoque['Fator_Num'] = pd.to_numeric(
                self.df_estoque[self.coluna_fator].astype(str).str.replace(',', '.'), errors='coerce'
            ).fillna(24)
        else:
            self.df_estoque['Fator_Num'] = 24

        # 2. TREINANDO O CLONE COMPORTAMENTAL E CALCULANDO MÉDIA HISTÓRICA
        self.modelo_ia = None
        self.media_historica_item = {} # Dicionário {codigo: media_mdv}
        
        if os.path.exists(caminho_db):
            print("[IA] Analisando histórico (DB.txt) para cálculo de sazonalidade...")
            try:
                df_treino = pd.read_csv(caminho_db, sep='\t')
                
                # Calcula a média do MDV histórico por item
                if 'Item' in df_treino.columns and 'MDV' in df_treino.columns:
                    self.media_historica_item = df_treino.groupby('Item')['MDV'].mean().to_dict()

                # Mapeia o giro histórico para cada linha do treino para a IA aprender com ele
                if 'Item' in df_treino.columns:
                    df_treino['Giro_Historico'] = df_treino['Item'].map(self.media_historica_item).fillna(0)
                else:
                    df_treino['Giro_Historico'] = 0

                if 'Peso' in df_treino.columns:
                    df_treino = df_treino.drop(columns=['Peso'])
                df_treino = df_treino.fillna(0)
                df_treino['Perfil_Loja'] = df_treino['Lj'].apply(lambda x: 1 if x in self.lojas_maiores else 0)
                
                # Variáveis que a IA usa para aprender
                features = ['Estoque CD', 'Fator', 'Estoque Loja', 'MDV', 'Norma', 'Lastro', 'Perfil_Loja', 'Giro_Historico']
                X = df_treino[features]
                y = df_treino['Quantidade']
                
                self.modelo_ia = RandomForestRegressor(n_estimators=100, random_state=42)
                self.modelo_ia.fit(X, y)
                print(f"[OK] Machine Learning Treinado: {len(self.media_historica_item)} itens com memória inteligente!")
            except Exception as e:
                print(f"[AVISO] Erro ao treinar IA: {e}")
        else:
            print("[AVISO] Arquivo DB.txt não encontrado. Sem base histórica.")

    def calcular_distribuicao(self, codigo, modo=1, lojas_zeradas=None):
        """
        Calcula a distribuição em DUAS ONDAS:
        1. Prioridade absoluta para lojas zeradas.
        2. Distribuição inteligente baseada em IA e Giro.

        Modo 1 = Distribuição Padrão
        Modo 2 = Focar lojas zeradas (detectadas automaticamente via estoque99)
        """
        codigo_int = int(codigo)
        df_item_completo = self.df_estoque[self.df_estoque['Codigo_Produto'] == codigo_int].sort_values(by='Loja')

        if df_item_completo.empty:
            return None, 0, "Item não encontrado no estoque99"

        # --- FATOR DINÂMICO ---
        # Tenta pegar o fator real do produto no estoque99
        fator_produto = 24  # fallback seguro
        if 'Fator_Num' in df_item_completo.columns:
            fator_val = df_item_completo.iloc[0]['Fator_Num']
            if pd.notna(fator_val) and fator_val > 0:
                fator_produto = int(fator_val)

        # Proteção contra o bug do NaN
        estoque_str = str(df_item_completo.iloc[0]['Estoque Lojas']).replace(',', '.')
        estoque_cd_un = pd.to_numeric(estoque_str, errors='coerce')
        if pd.isna(estoque_cd_un):
            estoque_cd_un = 0

        estoque_cd_cx = math.floor(estoque_cd_un / fator_produto)
        if estoque_cd_cx <= 0:
            return df_item_completo, estoque_cd_cx, "Estoque CD Zerado/Negativo"

        # --- MODO ZERADOS: detecta lojas zeradas automaticamente ---
        if modo == 2:
            df_zeradas = df_item_completo[
                (df_item_completo['Estoque_Num'] <= 0) & (df_item_completo['Mix Loja'] == 'S')
            ]
            lojas_zeradas = df_zeradas['Loja'].astype(int).tolist()
            if not lojas_zeradas:
                print(f"[INFO] Item {codigo_int}: Nenhuma loja zerada encontrada. Usando distribuição padrão.")
                modo = 1  # Cai para padrão se não há lojas zeradas

        distribuicao = {}
        caixas_disp = estoque_cd_cx

        # --- FILTRO DE SAZONALIDADE ---
        media_hist = self.media_historica_item.get(codigo_int, 0)

        # Prepara os dados de todas as lojas
        lojas_processar = []
        for _, loja in df_item_completo.iterrows():
            lj = int(loja['Loja'])
            mdv_final = loja['Media_Num']
            
            if media_hist > 0 and mdv_final > (media_hist * 3):
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

            # Modo Zerados: trabalha APENAS nas lojas zeradas detectadas
            if modo == 2 and lojas_zeradas and lj not in lojas_zeradas:
                distribuicao[lj] = {'qtd': 0, 'motivo': 'Ignorado (Modo Zerados)'}
                continue

            if info['estoque'] <= 0 and lj not in [28, 29]:
                distribuicao[lj] = {'qtd': 1, 'motivo': 'Prioridade: Anti-Zera'}
                caixas_disp -= 1

        # ==========================================
        # ONDA 2: DISTRIBUIÇÃO INTELIGENTE (IA/Giro)
        # ==========================================
        if caixas_disp > 0:
            for info in lojas_processar:
                lj = info['loja']
                if not info['tem_mix'] or caixas_disp <= 0:
                    continue

                # Modo Zerados: pula lojas que já foram marcadas como ignoradas
                if modo == 2 and lojas_zeradas and lj not in lojas_zeradas:
                    continue
                
                if self.modelo_ia is not None:
                    cenario = pd.DataFrame({
                        'Estoque CD': [estoque_cd_un], 'Fator': [fator_produto],
                        'Estoque Loja': [info['estoque']], 'MDV': [info['mdv']],
                        'Norma': [45], 'Lastro': [9], 'Perfil_Loja': [info['perfil']],
                        'Giro_Historico': [media_hist]
                    })
                    previsao = self.modelo_ia.predict(cenario)[0]
                    sugestao = math.ceil(previsao)
                    motivo_base = "Inteligência Claude/RF"
                else:
                    necessidade = (info['mdv'] * 30) - info['estoque']
                    sugestao = math.ceil(necessidade / fator_produto) if necessidade > 0 else 0
                    motivo_base = "Cálculo Giro (Fallback)"

                sugestao_extra = max(0, sugestao - distribuicao[lj]['qtd'])
                
                if sugestao_extra > 0:
                    limite_loja = 45 if info['perfil'] == 1 else 22
                    if (distribuicao[lj]['qtd'] + sugestao_extra) > limite_loja:
                        sugestao_extra = limite_loja - distribuicao[lj]['qtd']

                    if sugestao_extra > caixas_disp:
                        sugestao_extra = caixas_disp
                    
                    valor_final_onda = max(0, int(sugestao_extra))
                    distribuicao[lj]['qtd'] += valor_final_onda
                    distribuicao[lj]['motivo'] = motivo_base if distribuicao[lj]['motivo'] == 'Pendente' else "Urgência + IA"
                    caixas_disp -= valor_final_onda

        # --- VALIDAÇÃO FINAL DE SEGURANÇA ---
        for lj in distribuicao:
            distribuicao[lj]['qtd'] = max(0, int(distribuicao[lj]['qtd']))
            if distribuicao[lj]['qtd'] <= 0:
                if not any(lp['loja'] == lj and lp['tem_mix'] for lp in lojas_processar):
                    distribuicao[lj]['motivo'] = "Sem Mix"
                else:
                    distribuicao[lj]['motivo'] = "Estoque OK / CD Esgotado"

        return distribuicao, estoque_cd_cx, "Sucesso"