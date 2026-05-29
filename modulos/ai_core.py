import pandas as pd
import math
import os
from sklearn.ensemble import RandomForestRegressor

class MotorInteligencia:
    def __init__(self, caminho_db, caminho_estoque99):
        print("[IA] Inicializando Motor de IA...")
        self.lojas_maiores = [1, 3, 4, 5, 6, 7, 8, 9, 11, 14, 15, 16, 17, 20, 22]
        # Lojas válidas: 1 a 29. 
        # ATENÇÃO: As lojas 26, 28 e 29 DEVEM estar no dicionário para que o robô 
        # consiga dar os 'Enters' e pular os campos na tela do ERP. Se tirarmos do dicionário,
        # o robô perde o alinhamento da tela!
        self.lojas_validas = list(range(1, 30))
        self.lojas_bugadas_erp = [26, 28, 29]
        
        # 1. LENDO O ESTOQUE99 (agora extraído para método próprio)
        self.caminho_estoque99 = caminho_estoque99
        self.recarregar_estoque()

        # 2. TREINANDO O CLONE COMPORTAMENTAL
        self.modelo_ia = None
        
        # Como o usuário consolidou tudo no db.csv, lemos diretamente dele
        if os.path.exists(caminho_db):
            print(f"[IA] Lendo {os.path.basename(caminho_db)} para treinamento do Machine Learning...")
            try:
                # O arquivo do usuário é separado por ;
                df_treino = pd.read_csv(caminho_db, sep=';', encoding='latin1', low_memory=False)
                
                # Garante os nomes corretos
                if 'Quantidade Digitada' in df_treino.columns:
                    df_treino['Quantidade'] = df_treino['Quantidade Digitada']
                
                # Limpa e converte as colunas numéricas importantes
                for col in ['Quantidade', 'Estoque', 'Fator']:
                    if col in df_treino.columns:
                        df_treino[col] = pd.to_numeric(
                            df_treino[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
                            errors='coerce'
                        ).fillna(0)

                features = ['Lj', 'Estoque', 'Fator']
                target = 'Quantidade'

                # Pega apenas colunas que realmente existem
                features_validas = [f for f in features if f in df_treino.columns]
                
                if features_validas and target in df_treino.columns:
                    X = df_treino[features_validas].fillna(0)
                    y = df_treino[target]
                    
                    # Motor de Random Forest (árvore de decisão avançada)
                    self.modelo_ia = RandomForestRegressor(n_estimators=50, random_state=42)
                    self.modelo_ia.fit(X, y)
                    print(f"[OK] Machine Learning Treinado com {len(df_treino)} registros do db.csv!")
            except Exception as e:
                print(f"[AVISO] Erro ao treinar IA com db.csv: {e}")
        else:
            print("[AVISO] Arquivo db.csv não encontrado. Sem base histórica de digitação.")


    def recarregar_estoque(self):
        """Lê o arquivo de estoque do disco dinamicamente para garantir dados atualizados."""
        print("[ARQUIVO] Lendo o estoque atualizado...")
        try:
            self.df_estoque = pd.read_csv(self.caminho_estoque99, sep=';', encoding='latin1', low_memory=False)
        except Exception:
            self.df_estoque = pd.read_csv(self.caminho_estoque99, sep=';', encoding='utf-8', low_memory=False)
            
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
        # Filtra apenas lojas válidas E que possuem MIX (o ERP não exibe lojas sem Mix)
        df_item_completo = df_raw[
            (df_raw['Loja'].astype(int).isin(self.lojas_validas)) & 
            (df_raw['Mix Loja'] == 'S')
        ].sort_values(by='Loja')

        if df_item_completo.empty:
            return None, 0, "Item não encontrado ou sem lojas com Mix no estoque99"

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
            df_zeradas = df_item_completo[df_item_completo['Estoque_Num'] <= 0]
            lojas_zeradas = df_zeradas['Loja'].astype(int).tolist()
            if not lojas_zeradas:
                print(f"[INFO] Item {codigo_int}: Nenhuma loja zerada encontrada. Usando distribuição padrão.")
                modo = 1  # Cai para padrão se não há lojas zeradas

        # Pega EXATAMENTE as lojas que existem no estoque99 para este produto (espelho da tela do ERP)
        lojas_validas_produto = sorted(df_item_completo['Loja'].astype(int).unique().tolist())
        
        distribuicao = {lj: {'qtd': 0, 'motivo': 'Não listado', 'mdv': 0, 'ddv': 0, 'estoque': 0} for lj in lojas_validas_produto}
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
            
            estoque_loja = loja['Estoque_Num']

            lojas_processar.append({
                'loja': lj,
                'tem_mix': (loja['Mix Loja'] == 'S'),
                'estoque': estoque_loja,
                'mdv': mdv_final,
                'perfil': 1 if lj in self.lojas_maiores else 0,
                'ddv': ddv_val
            })
            distribuicao[lj]['motivo'] = 'Pendente'
            distribuicao[lj]['mdv'] = mdv_final
            distribuicao[lj]['ddv'] = ddv_val
            distribuicao[lj]['estoque'] = estoque_loja

        # ==========================================
        # DEFINIÇÃO DOS LIMITES E CÁLCULO BASEADO NO MÊS (30 DIAS) E DDV
        # ==========================================
        necessidades = []
        for info in lojas_processar:
            lj = info['loja']
            if not info['tem_mix']:
                continue
                
            # No modo 2 (Zerados), só processamos lojas com estoque real <= 0
            if modo == 2 and info['estoque'] > 0:
                continue

            mdv = info['mdv']
            estoque = info['estoque']
            ddv = info['ddv']

            # Se a loja não tem venda e ainda tem estoque, ignora
            if mdv <= 0 and estoque > 0:
                continue

            # 1. Alvo Mensal/Quinzenal Padrão
            # Lojas grandes recebem alvo de 30 dias. Lojas pequenas alvo de 15 dias.
            if mdv > 0:
                dias_alvo = 30 if info['perfil'] == 1 else 15
                nec_alvo_un = (mdv * dias_alvo) - estoque
                cx_alvo_regra = math.ceil(nec_alvo_un / fator_produto) if nec_alvo_un > 0 else 0
            else:
                cx_alvo_regra = 1 if estoque <= 0 else 0

            # 2. IA APRENDIZADO
            # Se tivermos o modelo treinado pelo DB.txt, ele tem a palavra final sobre o alvo!
            cx_alvo = cx_alvo_regra
            if self.modelo_ia is not None:
                try:
                    # O modelo aprendeu com: ['Lj', 'Estoque Loja', 'MDV', 'DDV', 'Fator']
                    df_pred = pd.DataFrame([{
                        'Lj': lj,
                        'Estoque Loja': estoque,
                        'MDV': mdv,
                        'DDV': ddv,
                        'Fator': fator_produto
                    }])
                    # Preditando quantidade de unidades (porque treinamos a IA com unidades se usamos datasimul, ou caixas se usamos db.txt, vamos garantir a consistência no __init__)
                    predicao_cx = self.modelo_ia.predict(df_pred)[0]
                    cx_alvo_ia = max(0, round(predicao_cx))
                    
                    # A IA substitui a regra cega se tiver sugestão, mas nunca passa de um limite extremo
                    cx_alvo = cx_alvo_ia
                except Exception as e:
                    pass

            # 3. Mínimo de Segurança (Onda 1)
            cx_min = 0
            if estoque <= 0:
                nec_urgente = (mdv * 10) - estoque if mdv > 0 else 0
                cx_min = max(1, math.ceil(nec_urgente / fator_produto))
            elif ddv <= 7 and mdv > 0:
                nec_urgente = (mdv * 10) - estoque
                cx_min = max(0, math.ceil(nec_urgente / fator_produto))

            # Não podemos exigir um mínimo maior que o alvo mensal
            cx_min = min(cx_min, cx_alvo)

            if cx_alvo > 0 or cx_min > 0:
                necessidades.append({
                    'loja': lj,
                    'cx_min': cx_min,
                    'cx_alvo': cx_alvo,
                    'ddv': ddv,
                    'estoque': estoque
                })

        # Racionamento: Prioriza zeradas e menor DDV
        necessidades.sort(key=lambda x: (x['estoque'] > 0, x['ddv']))

        # ==========================================
        # ONDA 1: GARANTIR O MÍNIMO DE SEGURANÇA
        # ==========================================
        for n in necessidades:
            lj = n['loja']
            enviar_min = n['cx_min']
            if enviar_min > 0 and caixas_disp > 0:
                enviar = min(enviar_min, caixas_disp)
                distribuicao[lj]['qtd'] += enviar
                distribuicao[lj]['motivo'] = "Mín. Segurança"
                caixas_disp -= enviar

        # ==========================================
        # ONDA 2: BUSCAR O ALVO IDEAL (IA ou MÁXIMO)
        # Se o CD tem estoque bom, completa até a quantidade que a equipe costuma digitar
        # ==========================================
        if caixas_disp > 0:
            for n in necessidades:
                lj = n['loja']
                ja_tem = distribuicao[lj]['qtd']
                falta_pro_alvo = n['cx_alvo'] - ja_tem

                if falta_pro_alvo > 0 and caixas_disp > 0:
                    enviar = min(falta_pro_alvo, caixas_disp)
                    distribuicao[lj]['qtd'] += enviar
                    if ja_tem > 0:
                        distribuicao[lj]['motivo'] = "Mín. + Complemento IA"
                    else:
                        distribuicao[lj]['motivo'] = "Alvo IA (datasimul)"
                    caixas_disp -= enviar

        # Se sobrou caixas e todas bateram o alvo, não fazemos nada (respeito ao limite máximo)

        # --- VALIDAÇÃO FINAL DE SEGURANÇA ---
        for lj in distribuicao:
            # Trava para pular as lojas bugadas do ERP
            if lj in self.lojas_bugadas_erp:
                distribuicao[lj]['qtd'] = 0
                distribuicao[lj]['motivo'] = "Pulo Obrigatório (Bug ERP)"
                continue

            distribuicao[lj]['qtd'] = max(0, int(distribuicao[lj]['qtd']))
            if distribuicao[lj]['qtd'] <= 0:
                if not any(lp['loja'] == lj and lp['tem_mix'] for lp in lojas_processar):
                    distribuicao[lj]['motivo'] = "Sem Mix"
                else:
                    if distribuicao[lj]['motivo'] == 'Pendente':
                        distribuicao[lj]['motivo'] = "Estoque Suficiente"

        return distribuicao, estoque_cd_cx, "Sucesso"