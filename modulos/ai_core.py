import pandas as pd
import math
import os
from sklearn.ensemble import RandomForestRegressor

class MotorInteligencia:
    def __init__(self, caminho_db, caminho_estoque99):
        print("[IA] Inicializando Motor de IA...")
        self.lojas_maiores = [1, 3, 4, 5, 6, 7, 8, 9, 11, 14, 15, 16, 17, 20, 22]
        # Lojas reais do ERP (1 a 29, exceto 26, 28 e 29 que não são para digitar - bug ERP)
        self.lojas_validas = [i for i in range(1, 30) if i not in [26, 28, 29]]
        
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
        
        caminho_datasimul = os.path.join(os.path.dirname(caminho_db), 'datasimul.csv')
        if os.path.exists(caminho_datasimul):
            print("[IA] Lendo datasimul.csv para treinamento do Machine Learning...")
            try:
                df_treino = pd.read_csv(caminho_datasimul, sep=';', encoding='latin1', low_memory=False)
                
                # Limpa e converte as colunas numéricas importantes
                # Col 6: Quantidade (Target), Col 7: Estoque, Col 9: Fator
                for col in ['Quantidade', 'Estoque', 'Fator']:
                    if col in df_treino.columns:
                        df_treino[col] = pd.to_numeric(
                            df_treino[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
                            errors='coerce'
                        ).fillna(0)
                        
                # Adiciona Perfil da Loja
                if 'Lj' in df_treino.columns:
                    df_treino['Lj'] = pd.to_numeric(df_treino['Lj'], errors='coerce').fillna(0)
                    df_treino['Perfil_Loja'] = df_treino['Lj'].apply(lambda x: 1 if x in self.lojas_maiores else 0)
                else:
                    df_treino['Perfil_Loja'] = 0

                # Variáveis que a IA usa para aprender
                features = ['Estoque', 'Fator', 'Perfil_Loja']
                X = df_treino[features]
                y = df_treino['Quantidade']

                self.modelo_ia = RandomForestRegressor(n_estimators=100, random_state=42)
                self.modelo_ia.fit(X, y)
                print(f"[OK] Machine Learning Treinado com {len(df_treino)} registros do datasimul.csv!")
            except Exception as e:
                print(f"[AVISO] Erro ao treinar IA com datasimul.csv: {e}")
        else:
            print("[AVISO] Arquivo datasimul.csv não encontrado. Sem base histórica de digitação.")

    def calcular_distribuicao(self, codigo, modo=1, lojas_zeradas=None):
        """
        Calcula a distribuição em DUAS ONDAS:
        1. Prioridade absoluta para lojas zeradas.
        2. Distribuição inteligente baseada em IA e Giro.

        Modo 1 = Distribuição Padrão
        Modo 2 = Focar lojas zeradas (detectadas automaticamente via estoque99)
        """
        codigo_int = int(codigo)
        df_raw = self.df_estoque[self.df_estoque['Codigo_Produto'] == codigo_int]
        # Filtra apenas lojas reais (exclui registros auxiliares como 70, 72, 73)
        df_item_completo = df_raw[df_raw['Loja'].astype(int).isin(self.lojas_validas)].sort_values(by='Loja')

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
            return None, estoque_cd_cx, "Estoque CD Zerado/Negativo"

        # --- MODO ZERADOS: detecta lojas zeradas automaticamente ---
        if modo == 2:
            df_zeradas = df_item_completo[
                (df_item_completo['Estoque_Num'] <= 0) & (df_item_completo['Mix Loja'] == 'S')
            ]
            lojas_zeradas = df_zeradas['Loja'].astype(int).tolist()
            if not lojas_zeradas:
                print(f"[INFO] Item {codigo_int}: Nenhuma loja zerada encontrada. Usando distribuição padrão.")
                modo = 1  # Cai para padrão se não há lojas zeradas

        # Descobre até qual loja este produto específico vai (evita "passar da digitação" na tela)
        max_loja_produto = int(df_item_completo['Loja'].astype(int).max()) if not df_item_completo.empty else 0
        lojas_validas_produto = [lj for lj in self.lojas_validas if lj <= max_loja_produto]
        
        distribuicao = {lj: {'qtd': 0, 'motivo': 'Não listado'} for lj in lojas_validas_produto}
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

            ddv_val = pd.to_numeric(str(loja.get('DDV', 0)).replace(',', '.'), errors='coerce')
            ddv_val = float(ddv_val) if pd.notna(ddv_val) else 0.0

            lojas_processar.append({
                'loja': lj,
                'tem_mix': (loja['Mix Loja'] == 'S'),
                'estoque': loja['Estoque_Num'],
                'mdv': mdv_final,
                'perfil': 1 if lj in self.lojas_maiores else 0,
                'ddv': ddv_val
            })
            distribuicao[lj]['motivo'] = 'Pendente'

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

            if info['estoque'] <= 0:
                distribuicao[lj] = {'qtd': 1, 'motivo': 'Prioridade: Anti-Zera'}
                caixas_disp -= 1

        # ==========================================
        # ONDA 2: DISTRIBUIÇÃO POR MDV
        # Cobertura alvo: 30 dias (lojas maiores) / 15 dias (lojas menores)
        # Racionamento por DDV crescente quando CD é insuficiente
        # ==========================================
        COBERTURA_GRANDE = 30
        COBERTURA_PEQUENA = 15

        if caixas_disp > 0:
            # Passo 1: calcula necessidade de cada loja
            necessidades = []
            for info in lojas_processar:
                lj = info['loja']
                if not info['tem_mix']:
                    continue
                if modo == 2 and lojas_zeradas and lj not in lojas_zeradas:
                    continue

                cobertura = COBERTURA_GRANDE if info['perfil'] == 1 else COBERTURA_PEQUENA
                mdv = info['mdv']

                if mdv <= 0:
                    # Sem MDV e com estoque → não envia (se zerado já foi tratado na Onda 1)
                    continue

                necessidade_un = (mdv * cobertura) - info['estoque']
                necessidade_cx = math.ceil(necessidade_un / fator_produto) if necessidade_un > 0 else 0

                # --- HÍBRIDO (Matemática + IA) ---
                # Faz uma média entre a matemática ideal (DDV) e o padrão de digitação humana (datasimul)
                if self.modelo_ia is not None:
                    try:
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            df_pred = pd.DataFrame([[info['estoque'], fator_produto, info['perfil']]], columns=['Estoque', 'Fator', 'Perfil_Loja'])
                            pred_ia = self.modelo_ia.predict(df_pred)[0]
                            # Ponderação: 50% Matemática Ideal + 50% Histórico Humano
                            necessidade_hibrida = math.ceil((necessidade_cx + max(0, pred_ia)) / 2.0)
                            necessidade_cx = necessidade_hibrida
                    except Exception:
                        pass # Fallback silencioso para matemática pura em caso de erro

                ja_tem = distribuicao[lj]['qtd']  # alocado na Onda 1
                extra_cx = max(0, necessidade_cx - ja_tem)

                if extra_cx > 0:
                    necessidades.append({
                        'loja': lj,
                        'extra_cx': extra_cx,
                        'ddv': info['ddv'],
                        'cobertura': cobertura
                    })

            # Passo 2: racionamento — ordena por DDV crescente (ruptura iminente primeiro)
            necessidades.sort(key=lambda x: x['ddv'])

            for n in necessidades:
                lj = n['loja']
                if caixas_disp <= 0:
                    if distribuicao[lj]['motivo'] == 'Pendente':
                        distribuicao[lj]['motivo'] = "CD Insuficiente"
                    continue
                enviar = min(n['extra_cx'], caixas_disp)
                motivo_onda2 = f"Giro MDV ({n['cobertura']}d)"
                distribuicao[lj]['qtd'] += enviar
                distribuicao[lj]['motivo'] = (
                    "Urgência + Giro MDV"
                    if distribuicao[lj]['motivo'] != 'Pendente'
                    else motivo_onda2
                )
                caixas_disp -= enviar

        # --- VALIDAÇÃO FINAL DE SEGURANÇA ---
        for lj in distribuicao:
            distribuicao[lj]['qtd'] = max(0, int(distribuicao[lj]['qtd']))
            if distribuicao[lj]['qtd'] <= 0:
                if not any(lp['loja'] == lj and lp['tem_mix'] for lp in lojas_processar):
                    distribuicao[lj]['motivo'] = "Sem Mix"
                else:
                    distribuicao[lj]['motivo'] = "Estoque OK / CD Esgotado"

        return distribuicao, estoque_cd_cx, "Sucesso"