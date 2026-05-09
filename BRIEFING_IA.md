# 🧠 BRIEFING COMPLETO — AVANÇO PRO SYSTEM V2
> **Para a IA:** Leia este arquivo inteiro antes de qualquer coisa. Ele contém todo o contexto do projeto.
> **Para o Daniel:** Quando abrir esse projeto na máquina certa, mostre esse arquivo para a IA e diga "leia o BRIEFING_IA.md e me ajude a continuar".

---

## 📌 O QUE É ESSE PROJETO

**Avanço Pro System V2** é um agente de automação (RPA + IA) que trabalha sozinho para fazer a reposição de estoque das lojas da empresa. O fluxo é:

1. Daniel cola os códigos dos produtos que quer repor
2. Aperta PLAY
3. O programa consulta o `estoque99.csv`, calcula quanto mandar pra cada loja (IA + regras), e opera o ERP Avanço automaticamente via teclado
4. Gera um relatório CSV no final

**Caminho do projeto na máquina de desenvolvimento:**
```
E:\ProgramasPy\Avanco_Pro_System V2_EXE\
```

**Caminho do projeto de testes / raiz antiga (referência histórica):**
```
E:\ProgramasPy\Avanco_Pro_System\AutoAvancoOSV3\
```

---

## 🗂️ ESTRUTURA DE ARQUIVOS

```
Avanco_Pro_System V2_EXE/
├── app_main.py              ← Ponto de entrada: chama abrir_tela_login()
├── requirements.txt         ← requests, pyautogui, pandas, scikit-learn, python-dotenv, customtkinter
├── BRIEFING_IA.md           ← ESTE ARQUIVO
├── README.md                ← Documentação geral (desatualizada, ignorar)
├── .env                     ← Chaves Firebase REAIS (git-ignored)
├── .env.example             ← Template sem as chaves
├── .gitignore               ← Ignora dados/, relatorios/, dist/, build/
│
├── modulos/
│   ├── __init__.py
│   ├── ai_core.py           ← Motor de IA (RandomForest + regras)
│   ├── interface.py         ← GUI CustomTkinter (tela login + tela principal)
│   ├── rpa_bot.py           ← Robô pyautogui + base abstrata para Telnet futuro
│   └── seguranca.py         ← Autenticação Firebase
│
├── dados/                   ← GIT-IGNORED — precisa estar na máquina
│   ├── estoque99.csv        ← 80 MB | 304.799 linhas | sep=; | encoding=latin1
│   ├── DB.txt               ← 356 KB | 7.589 linhas | sep=\t | histórico de treino da IA
│   └── config.json          ← Criado pelo botão ⚙️ Config (host, porta, tipo de conexão)
│
└── relatorios/              ← GIT-IGNORED — CSVs gerados a cada execução
```

---

## 🧩 DETALHAMENTO DE CADA MÓDULO

### `modulos/ai_core.py` — Cérebro
**Classe:** `MotorInteligencia(caminho_db, caminho_estoque99)`

**O que faz:**
- Lê o `estoque99.csv` inteiro na memória (encoding latin1, sep=`;`)
- Normaliza a coluna de código (detecta por `'digo'` no nome → renomeia para `Codigo_Produto`)
- Calcula `Fator_Num` dinamicamente por produto (detecta coluna com `'plicac'` ou `'ator'` no nome — fallback 24)
- Treina um `RandomForestRegressor` com o `DB.txt` se ele existir
- Features do ML: `Estoque CD, Fator, Estoque Loja, MDV, Norma, Lastro, Perfil_Loja, Giro_Historico`

**Método principal:** `calcular_distribuicao(codigo, modo=1)`
- `modo=1` → Distribuição Padrão (IA + giro)
- `modo=2` → Modo Zerados: detecta automaticamente lojas com `Estoque_Num <= 0` e `Mix Loja == 'S'`
- Se não houver lojas zeradas no modo 2, cai para modo 1 automaticamente

**Distribuição em 2 ondas:**
- **Onda 1 — Anti-Ruptura:** lojas com estoque zero recebem 1 cx de prioridade absoluta
- **Onda 2 — IA/Giro:** distribui o restante baseado em ML ou cálculo de necessidade (Mdv×30 - Estoque) / fator

**Lojas maiores** (recebem mais, até 45 cx, meio pallet, pallet fechado):
`1, 3, 4, 5, 6, 7, 8, 9, 11, 14, 15, 16, 17, 20, 22`

**Lojas menores** (limite de 22 cx):
`2, 10, 12, 13, 18, 19, 21, 23, 24, 25, 27`

**Proteção sazonal:** se MDV atual > 3× a média histórica do item, usa a média histórica (evita picos falsos)

---

### `modulos/rpa_bot.py` — Robô
**Classe base abstrata:** `BaseOperador` (ABC)
- Preparada para futura implementação de `TelnetOperador` — quando o IP do servidor for descoberto

**Classe atual:** `RoboOperador(operador_nome, log_callback=None)`
- `log_callback`: função da interface que recebe mensagens → exibe no painel de log em tempo real
- Usa `pyautogui` para operar a tela do SecureNetTerm (Telnet gráfico)

**Método `executar_item(codigo, distribuicao, cd_total, status_ia, fator=24)`:**
1. Chama `enxergar_sistema_pronto()` → compara 2 screenshots, aguarda estabilidade (timeout 10s)
2. A partir do 2º item: pressiona `UP UP` para voltar ao campo de código
3. Limpa com 8 backspaces, digita código, Enter, aguarda 2,8s (ERP carrega)
4. Se CD zerado: ESC → N → pula
5. Para cada loja: digita qtd (se > 0), pressiona Enter Enter (cadência 0,25s)
6. Confirma com `s` no final
7. Chama `_registrar_no_db()` → retroalimenta o DB.txt com a operação real
8. Aguarda 4s para o banco do ERP processar

**Método `_registrar_no_db()`:**
- Appenda linhas no `dados/DB.txt` no mesmo formato tab-separado que o ai_core lê
- Isso faz a IA aprender com cada operação real feita

**Método `gerar_relatorio_csv()`:**
- Salva em `relatorios/Envios_Inteligentes_YYYYMMDD_HHMMSS.csv`
- Colunas: `DataHora, Operador, Codigo, Loja, Qtd_Enviada, Motivo`
- Encoding: utf-8-sig (compatível com Excel)

---

### `modulos/interface.py` — Interface
**Framework:** CustomTkinter (dark mode, blue theme)

**Tela de Login (standalone):**
- `abrir_tela_login()` → janela 350×450
- Firebase email+password
- Enter no campo de senha dispara o login
- Verifica `ativo` no Firestore antes de liberar

**Tela Principal (`AppReposicao`):** 500×780
- Cabeçalho com botão ⚙️ Config (canto superior direito)
- Seletor de modo (RadioButton): Padrão / Zerados
- Textbox para colar os códigos (um por linha ou separados por espaço)
- Botão EXECUTAR RPA (verde escuro, travado durante execução)
- **Painel de log verde** em tempo real (CTkTextbox read-only com auto-scroll)
- Label de status na base

**Thread de automação:**
- Roda em daemon thread para não travar a GUI
- Após 5 segundos aguarda → Daniel move o cursor para a tela do Avanço
- Logs chegam via `self.after(0, ...)` — thread-safe

**Janela de Configurações (`JanelaConfiguracoes`):**
- Abre como CTkToplevel modal
- Campos: Host/IP, Porta, Tipo de conexão (pyautogui / Telnet em breve)
- Salva em `dados/config.json`

---

### `modulos/seguranca.py` — Firebase
**Classe:** `AutenticadorFirebase`
- Credenciais via `.env` (python-dotenv)
- `API_KEY` e `PROJECT_ID` do Firebase
- Kill-switch remoto: `Firestore > sistema/config > status_ativo (bool)`
- Login: `identitytoolkit.googleapis.com/v1/accounts:signInWithPassword`
- Verificação de usuário: `Firestore > usuarios/{uid} > ativo (bool)`
- Suporte a proxy corporativo via `HTTP_PROXY` / `HTTPS_PROXY` no `.env`

---

## 📊 ESTRUTURA DO ESTOQUE99.CSV
**35 colunas**, principais:
| Coluna | Uso |
|---|---|
| `Código` | ID do produto → renomeado para `Codigo_Produto` |
| `Loja` | Número da loja |
| `Estoque` | Estoque atual na loja (unidades) |
| `Media` | MDV — Média Diária de Vendas |
| `Estoque Lojas` | Estoque no CD (unidades) |
| `Mix Loja` | `S` = produto está no mix da loja (elegível para receber) |
| `DDV` | Dias de Vendas |
| `Aplicacao` | Pode conter o fator de caixa do produto |

---

## 📋 ESTRUTURA DO DB.TXT (treino da IA)
**Separador:** tab (`\t`) | Colunas:
```
Lj | Data | Item | Quantidade | Estoque CD | Fator | Estoque Loja | MDV | Norma | Lastro
```
- 7.589 linhas de histórico real de distribuição
- A IA usa isso para aprender o comportamento do Daniel
- **Cada execução real do robô acrescenta novas linhas automaticamente**

---

## 🖥️ O ERP AVANÇO (tela do SecureNetTerm)

É um sistema Telnet legado. A tela de distribuição tem:
```
Item......: [CÓDIGO] [DESCRIÇÃO] CX [FATOR],00 UN
Lj  Quant  Estoque  Reserva  Transito  U lt30  Ult15  Mdv35  Vendas
01  [___]  31       2        0         89      45     3,25   Abr/26 25
02  [___]  44       0        0         7       5      0,34   Mar/26 12
...
```
**Rodapé:** `Usuario: 986 | Lastro: 9 | Norma: 45 | 24 CX | Min/Max: X,XX / Y,YY`
**Confirmação final:** `Confirma Distribuição? (S/N)` → digitar `s`

**Ciclo do robô:**
```
[código] → Enter → (carrega) → [qtd loja01] → Enter Enter → [qtd loja02] → Enter Enter → ... → s → [código próximo] → ...
```

**Regras de negócio que o robô segue:**
- Se `Estoque < Mdv35 × 7 dias` → prioridade alta (vai romper em 1 semana)
- Se `Estoque > Mdv35 × 30 dias` → não enviar (loja com excesso)
- Lojas maiores: pallet fechado (45 cx) ou meio pallet (22 cx) ou lastro (9 cx)
- Lojas menores: máximo 22 cx, normalmente o necessário para cobrir até o próximo pedido
- Norma: 45 cx | Lastro: 9 cx | Fator típico: 24 unidades/cx

---

## 🔌 SITUAÇÃO DO TELNET HEADLESS

**Estado atual:** NÃO implementado — o robô ainda usa `pyautogui` na tela gráfica do SecureNetTerm.

**O que falta para implementar:**
1. Descobrir o IP do servidor Avanço (ver nas propriedades da conexão no SecureNetTerm)
2. Testar conexão: `telnetlib` Python ou `socket` direto na porta 23
3. Criar `TelnetOperador(BaseOperador)` em `rpa_bot.py` — a `BaseOperador` já existe
4. Implementar o handshake: login Linux → autenticação ERP (usuário `986`) → navegar até tela de distribuição
5. Substituir o `pyautogui` por envio de strings via socket

**A arquitetura já está preparada** — só falta o IP e testar se a conexão direta é aceita pelo servidor.

---

## 🔐 FIREBASE (credenciais — só no .env, nunca no git)
- **Project ID:** `avancoprosystem`
- **API Key:** está no `.env` (não comitar)
- **Firestore collections:**
  - `sistema/config` → campo `status_ativo` (bool) — kill-switch
  - `usuarios/{uid}` → campo `ativo` (bool) — controle por usuário

---

## 🚨 PROBLEMAS CONHECIDOS / PONTOS DE ATENÇÃO

| Problema | Status | Observação |
|---|---|---|
| Enter duplo nem sempre funciona igual | ⚠️ Em observação | O ERP às vezes pede confirmação extra. Código já usa `['enter','enter']` como padrão |
| Número de lojas por produto é variável | ✅ Tratado | ai_core filtra por `Mix Loja == 'S'` |
| Fator de caixa varia por produto | ✅ Tratado | ai_core lê fator dinâmico do estoque99 |
| Modo Zerados pedia input manual | ✅ Corrigido | Detecção automática via estoque99 |
| DB.txt não era alimentado | ✅ Corrigido | rpa_bot._registrar_no_db() faz isso agora |
| Log só no terminal | ✅ Corrigido | Painel verde na interface em tempo real |
| customtkinter faltava no requirements | ✅ Corrigido | Adicionado |
| Telnet headless | 🔜 Futuro | Arquitetura preparada, falta o IP |
| Campo de lojas zeradas manual | ✅ Removido | Programa detecta sozinho |

---

## ✅ CHECKLIST PARA TESTAR NA MÁQUINA REAL

```
[ ] 1. pip install -r requirements.txt
[ ] 2. Garantir que dados/estoque99.csv está na pasta dados/
[ ] 3. Garantir que dados/DB.txt está na pasta dados/ (ou criar vazio com header)
[ ] 4. Criar/verificar .env com FIREBASE_API_KEY e FIREBASE_PROJECT_ID
[ ] 5. Abrir o SecureNetTerm e conectar no Avanço com o usuário 986
[ ] 6. Navegar até a tela de distribuição (deixar cursor no campo "Item")
[ ] 7. Rodar: python app_main.py
[ ] 8. Logar com email/senha Firebase
[ ] 9. Colar 1 código de teste → EXECUTAR RPA
[ ] 10. Observar o log e verificar se o robô operou corretamente
[ ] 11. Verificar relatorios/ para o CSV gerado
[ ] 12. Verificar se DB.txt ganhou novas linhas
```

---

## 💬 CONTEXTO PESSOAL DO PROJETO

- **Desenvolvedor:** Daniel (usuário 986 no ERP)
- **Empresa:** Trabalha com reposição de estoque (Supply Chain)
- **26 lojas no total** (nem sempre o mesmo produto tem mix em todas)
- O estoque99.csv é **dinâmico** — atualizado frequentemente na empresa
- A ideia é: Daniel escolhe os códigos manualmente, cola no programa, e colhe o relatório no fim
- O projeto evoluiu de uma tentativa com Telnet direto → para pyautogui → e está caminhando de volta para Telnet headless
- Histórico de conversas e brainstorming está em `E:\ADT\KitInfo\Documentos\`

---

## 📁 COMO RETOMAR COM A IA

Quando for retomar, diga para a IA:

> *"Leia o arquivo BRIEFING_IA.md que está em E:\ProgramasPy\Avanco_Pro_System V2_EXE\ e me ajude a continuar o projeto."*

A IA terá tudo que precisa para continuar de onde paramos.
