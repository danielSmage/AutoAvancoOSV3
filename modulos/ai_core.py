import pandas as pd
import math
import os

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
        self.media_historica_item = {}
        
        # Como o usuário consolidou tudo no db.csv, lemos diretamente dele
        if os.path.exists(caminho_db):
            print(f"[IA] Lendo {os.path.basename(caminho_db)} para treinamento do Machine Learning...")
            try:
                # O arquivo do usuário é separado por ;
                # Usa tratamento flexível para ignorar linhas corrompidas (como campos vazando ponto-e-vírgula)
                try:
                    df_treino = pd.read_csv(caminho_db, sep=';', encoding='latin1', low_memory=False, on_bad_lines='skip')
                except TypeError:
                    # Fallback para versões mais antigas do pandas
                    df_treino = pd.read_csv(caminho_db, sep=';', encoding='latin1', low_memory=False, error_bad_lines=False)
                
                
                # Garante os nomes corretos
                if 'Quantidade Digitada' in df_treino.columns:
                    df_treino['Quantidade'] = df_treino['Quantidade Digitada']
                
                # Limpa e converte as colunas numéricas importantes do histórico
                for col in ['Quantidade', 'Estoque', 'Fator']:
                    if col in df_treino.columns:
                        df_treino[col] = pd.to_numeric(
                            df_treino[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
                            errors='coerce'
                        ).fillna(0)
                        
                # OTIMIZAÇÃO CRÍTICA: O db.csv original do usuário não tem a curva de vendas (MDV) nem o DDV.
                # Isso deixava a IA "burra". Vamos fundir o histórico com o estoque99 atual para injetar o MDV e o DDV!
                try:
                    df_estoque_slim = self.df_estoque[['Loja', 'Codigo_Produto', 'Media_Num', 'DDV']].copy()
                    df_estoque_slim['Loja'] = pd.to_numeric(df_estoque_slim['Loja'], errors='coerce').fillna(0)
                    df_estoque_slim['Codigo_Produto'] = pd.to_numeric(df_estoque_slim['Codigo_Produto'], errors='coerce').fillna(0)
                    
                    df_treino['Lj'] = pd.to_numeric(df_treino['Lj'], errors='coerce').fillna(0)
                    df_treino['Item'] = pd.to_numeric(df_treino['Item'], errors='coerce').fillna(0)
                    
                    # Merge do histórico com a curva de vendas atual (Media_Num) e DDV
                    df_treino = pd.merge(
                        df_treino, df_estoque_slim, 
                        left_on=['Lj', 'Item'], right_on=['Loja', 'Codigo_Produto'], 
                        how='left'
                    )
                    df_treino['Media_Num'] = df_treino['Media_Num'].fillna(0)
                    df_treino['DDV'] = pd.to_numeric(df_treino['DDV'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                except Exception as merge_err:
                    print(f"[AVISO IA] Falha ao fundir MDV/DDV no histórico: {merge_err}")
                    df_treino['Media_Num'] = 0
                    df_treino['DDV'] = 0

                # IA DESATIVADA: O db.csv contém dados ruidosos (envios limitados por escassez)
                # que fazem a IA aprender a enviar menos do que o necessário.
                # Solução: usar apenas matemática pura (MDV * dias - estoque) para distribuir.
                # O db.csv continua sendo usado APENAS para extrair os fatores históricos.
                print(f"[IA] db.csv lido com {len(df_treino)} registros. (ML desativado — modo matemática pura)")
                    
                # Salva os fatores reais dos produtos para corrigir a divisão matemática
                df_fatores = df_treino[['Item', 'Fator']].drop_duplicates(subset=['Item'], keep='last')
                self.fatores_historicos = dict(zip(df_fatores['Item'].astype(int), df_fatores['Fator'].astype(float)))
                    
            except Exception as e:
                print(f"[ERRO CRÍTICO IA] Falha severa no treinamento: {e}")
        else:
            print("[AVISO] Arquivo db.csv não encontrado. IA rodará baseada em matemática pura.")
            self.fatores_historicos = {}


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
            
        print("Colunas do dataframe:", self.df_estoque.columns.tolist())
        self.df_estoque['Media_Num'] = pd.to_numeric(self.df_estoque['Media'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
        self.df_estoque['Estoque_Num'] = pd.to_numeric(self.df_estoque['Estoque'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

        # Carrega o cadastro mestre de produtos (sp10a02.csv) — substitui o antigo dados.xlsx
        # Contém: Fator, Norma (cxs/pallet), Lastro, Camada, Peso, Departamento, Categoria
        self.fatores_mestre = {}
        self.normas_mestre = {}    # Norma = qtd caixas por pallet
        self.dados_mestre = {}     # Dados completos do cadastro por produto
        caminho_sp10 = os.path.join(os.path.dirname(self.caminho_estoque99), 'sp10a02.csv')
        if os.path.exists(caminho_sp10):
            try:
                df_mestre = pd.read_csv(
                    caminho_sp10, sep=';', encoding='latin1', low_memory=False,
                    usecols=['Produto', 'Desc', 'Fator', 'Norma', 'Lastro', 'Camada',
                             'Peso', 'Departamento', 'Categoria']
                )
                # Converte campos numéricos (formato brasileiro: 0012,0000)
                for col in ['Fator', 'Norma', 'Peso']:
                    df_mestre[col] = pd.to_numeric(
                        df_mestre[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
                        errors='coerce'
                    ).fillna(0)
                for col in ['Lastro', 'Camada']:
                    df_mestre[col] = pd.to_numeric(df_mestre[col], errors='coerce').fillna(0)
                df_mestre['Produto'] = pd.to_numeric(df_mestre['Produto'], errors='coerce')

                # FILTRA: só guarda produtos com fator > 0 (63% dos registros tem fator=0)
                df_valido = df_mestre.dropna(subset=['Produto'])
                df_com_fator = df_valido[df_valido['Fator'] > 0]

                self.fatores_mestre = dict(zip(
                    df_com_fator['Produto'].astype(int),
                    df_com_fator['Fator'].astype(float)
                ))
                # Norma (cxs por pallet) — útil para calcular pallets fechados
                df_com_norma = df_valido[df_valido['Norma'] > 0]
                self.normas_mestre = dict(zip(
                    df_com_norma['Produto'].astype(int),
                    df_com_norma['Norma'].astype(float)
                ))
                # Dados completos para consulta rápida
                for _, row in df_com_fator.iterrows():
                    cod = int(row['Produto'])
                    self.dados_mestre[cod] = {
                        'desc': str(row.get('Desc', '')).strip(),
                        'fator': float(row['Fator']),
                        'norma': float(row['Norma']),
                        'lastro': int(row['Lastro']),
                        'camada': int(row['Camada']),
                        'peso': float(row['Peso']),
                        'depto': str(row.get('Departamento', '')).strip(),
                        'categoria': str(row.get('Categoria', '')).strip(),
                    }
                total_lidos = len(df_mestre)
                total_validos = len(self.fatores_mestre)
                print(f"[OK] sp10a02.csv: {total_validos} produtos com fator válido (de {total_lidos} total)")
                print(f"[OK] {len(self.normas_mestre)} produtos com Norma (cxs/pallet) carregada")
            except Exception as e:
                print(f"[AVISO] Não foi possível ler sp10a02.csv: {e}")

        # Carrega a planilha de modelo de lojas zeradas
        self.lojas_zeradas_planilha = {}
        caminho_zeradas = os.path.join(os.path.dirname(self.caminho_estoque99), 'modelo_lojas_zeradas.xlsx')
        if os.path.exists(caminho_zeradas):
            try:
                df_zeradas = pd.read_excel(caminho_zeradas)
                if 'COD' in df_zeradas.columns and 'SUGESTAO LJ ZERADA' in df_zeradas.columns:
                    df_zeradas['COD'] = df_zeradas['COD'].ffill()
                    for cod, group in df_zeradas.groupby('COD'):
                        lojas = group['SUGESTAO LJ ZERADA'].dropna().astype(int).tolist()
                        self.lojas_zeradas_planilha[int(cod)] = lojas
                print(f"[OK] Planilha de lojas zeradas carregada com {len(self.lojas_zeradas_planilha)} produtos!")
            except Exception as e:
                print(f"[AVISO] Não foi possível ler modelo_lojas_zeradas.xlsx: {e}")

    def calcular_distribuicao(self, codigo, modo=1, lojas_zeradas=None, dias_grande=None, dias_pequena=None):
        """
        Calcula a distribuição em DUAS ONDAS:
        1. Prioridade absoluta para lojas zeradas.
        2. Distribuição inteligente baseada em Giro.

        Modo 1 = Distribuição Padrão
        Modo 2 = Focar lojas zeradas (detectadas automaticamente via estoque99)
        
        dias_grande / dias_pequena: override manual do giro-alvo (para promoções).
                                    Se None, usa os padrões 30/15.
        """
        # Define os dias-alvo (manual ou padrão)
        alvo_grande = dias_grande if dias_grande is not None else 30
        alvo_pequena = dias_pequena if dias_pequena is not None else 15
        codigo_int = int(codigo)
        df_raw = self.df_estoque[self.df_estoque['Codigo_Produto'] == codigo_int]
        # Filtra apenas lojas válidas E que possuem MIX (o ERP não exibe lojas sem Mix)
        df_item_completo = df_raw[
            (pd.to_numeric(df_raw['Loja'], errors='coerce').isin(self.lojas_validas)) & 
            (df_raw['Mix Loja'] == 'S')
        ].sort_values(by='Loja')

        if df_item_completo.empty:
            return None, 0, "Item não encontrado ou sem lojas com Mix no estoque99"

        # --- FATOR DINÂMICO (PRIORIDADE MASTER) ---
        # 1º Tenta do sp10a02.csv (Mestre), 2º Tenta do db.csv (Histórico), 3º Fallback Seguro
        fator_produto = self.fatores_mestre.get(codigo_int)
        fator_fonte = 'SP10'
        if not fator_produto or fator_produto <= 0:
            fator_produto = self.fatores_historicos.get(codigo_int, 0)
            fator_fonte = 'DB.CSV'
            
        if not fator_produto or fator_produto <= 0:
            fator_produto = 12
            fator_fonte = 'FALLBACK'
            print(f"  ⚠️ Item {codigo_int}: fator fallback (12). Verificar cadastro mestre.")

        # Proteção contra o bug do NaN e KeyError
        estoque_bruto = df_item_completo.iloc[0].get('Estoque Lojas', 0)
        estoque_str = str(estoque_bruto).replace('.', '').replace(',', '.')
        estoque_cd_un = pd.to_numeric(estoque_str, errors='coerce')
        if pd.isna(estoque_cd_un):
            estoque_cd_un = 0

        # Trava de Segurança Absoluta: 
        # Se o estoque físico do CD for menor que 1 (ex: 0.70), já bloqueia direto.
        if estoque_cd_un < 1:
            return None, 0, "Estoque CD Menor que 1", fator_produto

        estoque_cd_cx = math.floor(estoque_cd_un / fator_produto)
        if estoque_cd_cx <= 0:
            return None, estoque_cd_cx, "Estoque CD Zerado/Negativo", fator_produto

        # ... (restante da lógica mantém inalterada)
        
        # Pega EXATAMENTE as lojas que existem no estoque99 para este produto
        lojas_validas_produto = sorted(df_item_completo['Loja'].astype(int).unique().tolist())
        
        distribuicao = {lj: {'qtd': 0, 'motivo': 'Não listado', 'mdv': 0, 'ddv': 0, 'estoque': 0} for lj in lojas_validas_produto}
        caixas_disp = estoque_cd_cx

        # --- FILTRO DE SAZONALIDADE ---
        media_hist = self.media_historica_item.get(codigo_int, 0)

        # Prepara os dados de todas as lojas de forma otimizada (sem iterrows)
        lojas_dict = df_item_completo.to_dict('records')
        lojas_processar = []
        
        for loja in lojas_dict:
            lj = int(loja['Loja'])
            mdv_final = float(loja.get('Media_Num', 0))
            
            # Trava de sazonalidade extrema (teto de 3x a média histórica)
            if media_hist > 0 and mdv_final > (media_hist * 3):
                mdv_final = media_hist

            ddv_val = pd.to_numeric(str(loja.get('DDV', 0)).replace('.', '').replace(',', '.'), errors='coerce')
            ddv_val = float(ddv_val) if pd.notna(ddv_val) else 0.0
            
            estoque_loja = float(loja.get('Estoque_Num', 0))

            # --- P0-002: VALIDAÇÃO CRUZADA DO DDV ---
            # Recalcula DDV internamente e prefere o calculado se divergir >30% do ERP
            if mdv_final > 0:
                ddv_calculado = estoque_loja / mdv_final
                if ddv_val > 0 and abs(ddv_calculado - ddv_val) > (ddv_calculado * 0.3):
                    ddv_val = round(ddv_calculado, 1)
            
            lojas_processar.append({
                'loja': lj,
                'tem_mix': (str(loja.get('Mix Loja', '')).upper() == 'S'),
                'estoque': estoque_loja,
                'mdv': mdv_final,
                'perfil': 1 if lj in self.lojas_maiores else 0,
                'ddv': ddv_val
            })
            distribuicao[lj]['motivo'] = 'Pendente'
            distribuicao[lj]['mdv'] = mdv_final
            distribuicao[lj]['ddv'] = ddv_val
            distribuicao[lj]['estoque'] = estoque_loja

        # --- P0-001: CORREÇÃO MDV ANTI-RUPTURA (ciclo vicioso) ---
        # Quando loja está zerada, o MDV cai artificialmente. Substituímos pela mediana
        # das lojas que TÊM estoque para não subdistribuir.
        lojas_com_estoque_e_venda = [l for l in lojas_processar if l['estoque'] > 0 and l['mdv'] > 0]
        if lojas_com_estoque_e_venda:
            mdvs_positivos = sorted([l['mdv'] for l in lojas_com_estoque_e_venda])
            mediana_mdv = mdvs_positivos[len(mdvs_positivos) // 2]
            for info in lojas_processar:
                if info['estoque'] <= 0 and info['mdv'] < (mediana_mdv * 0.5):
                    info['mdv'] = mediana_mdv
                    distribuicao[info['loja']]['mdv'] = mediana_mdv

        # ==========================================
        # 0. PRÉ-CÁLCULO DE NECESSIDADE GLOBAL (TRAVA DE SALDO / STOCK CONFIDENCE)
        # ==========================================
        total_necessidade_matematica = 0
        for info in lojas_processar:
            if not info['tem_mix']:
                continue
                
            # Tratamento especial para o Modo Zerados
            if modo == 2:
                # Se o produto consta na planilha modelo_lojas_zeradas, prioriza estritamente aquelas lojas
                if hasattr(self, 'lojas_zeradas_planilha') and codigo_int in self.lojas_zeradas_planilha:
                    if info['loja'] not in self.lojas_zeradas_planilha[codigo_int]:
                        continue
                else:
                    # Fallback para detecção automática: apenas lojas com estoque <= 0
                    if info['estoque'] > 0:
                        continue
            else:
                # Modo Padrão
                if info['mdv'] <= 0 and info['estoque'] > 0:
                    continue

            if info['mdv'] > 0:
                dias_alvo = alvo_grande if info['perfil'] == 1 else alvo_pequena
                nec_alvo_un = (info['mdv'] * dias_alvo) - info['estoque']
                cx_alvo_regra = math.ceil(nec_alvo_un / fator_produto) if nec_alvo_un > 0 else 0
            else:
                cx_alvo_regra = 1 if info['estoque'] <= 0 else 0
                
            info['cx_alvo_regra'] = cx_alvo_regra
            total_necessidade_matematica += cx_alvo_regra

        # Escassez Real
        tem_escassez = (caixas_disp < total_necessidade_matematica)

        # ==========================================
        # DEFINIÇÃO DOS LIMITES E CÁLCULO FINAL
        # ==========================================
        necessidades = []
        for info in lojas_processar:
            lj = info['loja']
            if 'cx_alvo_regra' not in info:
                continue
                
            cx_alvo_regra = info['cx_alvo_regra']
            cx_alvo = cx_alvo_regra
            mdv = info['mdv']
            estoque = info['estoque']
            ddv = info['ddv']

            # cx_alvo segue a regra matemática pura (MDV * dias - estoque) / fator
            # ML desativado: db.csv ruidoso fazia a IA cortar quantidades indevidamente

            # 3. Mínimo de Segurança (Onda 1)
            cx_min = 0
            if estoque <= 0:
                nec_urgente = (mdv * 10) - estoque if mdv > 0 else 0
                cx_min = max(1, math.ceil(nec_urgente / fator_produto))
            elif ddv <= 7 and mdv > 0:
                nec_urgente = (mdv * 10) - estoque
                cx_min = max(0, math.ceil(nec_urgente / fator_produto))

            cx_min = min(cx_min, cx_alvo)

            if cx_alvo > 0 or cx_min > 0:
                necessidades.append({
                    'loja': lj,
                    'cx_min': cx_min,
                    'cx_alvo': cx_alvo,
                    'ddv': ddv,
                    'estoque': estoque
                })

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
                        distribuicao[lj]['motivo'] = "Alvo IA (db.csv)"
                    caixas_disp -= enviar

        # --- VALIDAÇÃO FINAL DE SEGURANÇA ---
        for lj in distribuicao:
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

        return distribuicao, estoque_cd_cx, "Sucesso", fator_produto

    def encontrar_pallets(self, dias_alvo_max=35, estoque_cd_minimo_cx=20, max_resultados=50):
        """
        Varre o estoque99 procurando produtos onde:
        - O CD tem estoque alto (>= estoque_cd_minimo_cx caixas)
        - As lojas precisam de caixas suficientes para justificar envio (~1 pallet)
        
        Retorna lista de dicts: [{codigo, descricao, estoque_cd_cx, fator, necessidade_total_cx,
                                  lojas_precisando, cx_por_loja_media}]
        """
        resultados = []
        
        # Agrupa por produto para iterar uma vez
        produtos = self.df_estoque.groupby('Codigo_Produto')
        
        for codigo_int, df_produto in produtos:
            try:
                codigo_int = int(codigo_int)
            except (ValueError, TypeError):
                continue
            
            # Filtra lojas válidas com Mix
            df_valido = df_produto[
                (pd.to_numeric(df_produto['Loja'], errors='coerce').isin(self.lojas_validas)) &
                (df_produto['Mix Loja'] == 'S')
            ]
            
            if df_valido.empty:
                continue
            
            # Pega o estoque do CD
            estoque_bruto = df_valido.iloc[0].get('Estoque Lojas', 0)
            estoque_str = str(estoque_bruto).replace('.', '').replace(',', '.')
            estoque_cd_un = pd.to_numeric(estoque_str, errors='coerce')
            if pd.isna(estoque_cd_un) or estoque_cd_un < 1:
                continue
            
            # Fator do produto
            fator = self.fatores_mestre.get(codigo_int)
            if not fator or fator <= 0:
                fator = self.fatores_historicos.get(codigo_int, 12)
            if fator <= 0:
                fator = 12
            
            estoque_cd_cx = math.floor(estoque_cd_un / fator)
            if estoque_cd_cx < estoque_cd_minimo_cx:
                continue
            
            # Calcula necessidade total das lojas para atingir dias_alvo_max
            total_nec_cx = 0
            lojas_precisando = 0
            
            for _, loja in df_valido.iterrows():
                lj = int(loja['Loja'])
                if lj in self.lojas_bugadas_erp:
                    continue
                
                mdv = float(loja.get('Media_Num', 0))
                estoque_loja = pd.to_numeric(
                    str(loja.get('Estoque', 0)).replace('.', '').replace(',', '.'), errors='coerce'
                )
                if pd.isna(estoque_loja):
                    estoque_loja = 0
                
                if mdv <= 0:
                    continue
                
                # Dias de estoque atuais da loja
                ddv_loja = estoque_loja / mdv if mdv > 0 else 999
                
                if ddv_loja < dias_alvo_max:
                    # Loja precisa de reposição
                    nec_un = (mdv * dias_alvo_max) - estoque_loja
                    nec_cx = math.ceil(nec_un / fator) if nec_un > 0 else 0
                    if nec_cx > 0:
                        total_nec_cx += nec_cx
                        lojas_precisando += 1
            
            if total_nec_cx <= 0 or lojas_precisando == 0:
                continue
            
            # Só mostra se cabe pelo menos 80% da necessidade no CD
            cobertura = min(estoque_cd_cx, total_nec_cx)
            if cobertura < total_nec_cx * 0.8:
                continue
            
            descricao = str(df_valido.iloc[0].get('Descrição', df_valido.iloc[0].get('Descricao', '')))
            
            resultados.append({
                'codigo': codigo_int,
                'descricao': descricao[:40],
                'estoque_cd_cx': estoque_cd_cx,
                'fator': int(fator),
                'necessidade_total_cx': total_nec_cx,
                'lojas_precisando': lojas_precisando,
                'cx_por_loja_media': round(total_nec_cx / lojas_precisando, 1),
                'cobertura_pct': round((cobertura / total_nec_cx) * 100, 0)
            })
        
        # Ordena por maior necessidade (melhores candidatos a pallet)
        resultados.sort(key=lambda x: x['necessidade_total_cx'], reverse=True)
        
        return resultados[:max_resultados]