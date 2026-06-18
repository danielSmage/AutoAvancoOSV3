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
        self.df_estoque['Media_Num'] = pd.to_numeric(self.df_estoque['Media'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        self.df_estoque['Estoque_Num'] = pd.to_numeric(self.df_estoque['Estoque'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        # Carrega o banco de dados mestre de embalagens (dados.xlsx) se existir
        self.fatores_mestre = {}
        caminho_dados_xlsx = os.path.join(os.path.dirname(self.caminho_estoque99), 'dados.xlsx')
        if os.path.exists(caminho_dados_xlsx):
            try:
                df_mestre = pd.read_excel(caminho_dados_xlsx)
                if 'Produto' in df_mestre.columns and 'Fator' in df_mestre.columns:
                    # Limpa NaNs
                    df_mestre_clean = df_mestre.dropna(subset=['Produto', 'Fator'])
                    self.fatores_mestre = dict(zip(
                        pd.to_numeric(df_mestre_clean['Produto'], errors='coerce').fillna(0).astype(int),
                        pd.to_numeric(df_mestre_clean['Fator'], errors='coerce').fillna(12).astype(float)
                    ))
                    print(f"[OK] Banco Mestre de Embalagens (dados.xlsx) carregado com {len(self.fatores_mestre)} produtos!")
            except Exception as e:
                print(f"[AVISO] Não foi possível ler o Fator do dados.xlsx: {e}")

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

        # --- FATOR DINÂMICO (PRIORIDADE MASTER) ---
        # 1º Tenta do dados.xlsx (Mestre), 2º Tenta do db.csv (Histórico), 3º Fallback Seguro
        fator_produto = self.fatores_mestre.get(codigo_int)
        if not fator_produto or fator_produto <= 0:
            fator_produto = self.fatores_historicos.get(codigo_int, 12)
            
        if fator_produto <= 0:
            fator_produto = 12

        # Proteção contra o bug do NaN e KeyError
        estoque_bruto = df_item_completo.iloc[0].get('Estoque Lojas', 0)
        estoque_str = str(estoque_bruto).replace(',', '.')
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

            ddv_val = pd.to_numeric(str(loja.get('DDV', 0)).replace(',', '.'), errors='coerce')
            ddv_val = float(ddv_val) if pd.notna(ddv_val) else 0.0
            
            estoque_loja = float(loja.get('Estoque_Num', 0))

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
                dias_alvo = 30 if info['perfil'] == 1 else 15
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