# Arquitetura do Sistema: AutoAvançoOSV3

## Visão Geral
O **AutoAvançoOSV3** (Avanço Pro System) é um orquestrador de RPA desenhado para automatizar a reposição de estoque em lojas de forma inteligente, precisa e segura. Ele conecta-se aos dados da empresa e interage com o sistema ERP.

## Componentes Principais
1. **app_main.py**: Ponto de entrada do sistema que carrega a tela de login.
2. **Interface (Tkinter)** (`modulos/interface.py`): Interface gráfica que permite interação do usuário, com abas para configuração, execução, "Encontrar Pallets" e controles de Giro-Alvo.
3. **Core de Inteligência (Matemática)** (`modulos/ai_core.py`): Antigamente utilizava Machine Learning (RandomForest), mas foi atualizado para **Distribuição Matemática Pura** devido a ruídos nos dados históricos.
4. **Bot RPA (PyAutoGUI)** (`modulos/rpa_bot.py`): **(SISTEMA ATUAL)** Responsável pela automação visual. Digita e navega no ERP simulando o usuário humano. Possui mecanismo de parada de emergência (STOP).
5. ~~**Bot Telnet** (`modulos/bot_telnet.py`)~~: **(DEPRECATED / FRACASSO)** Antiga tentativa de conexão direta e rápida ao servidor via socket. Foi um fracasso e o módulo encontra-se abandonado, utilizando-se exclusivamente a automação visual (RPA) para as rotinas.
6. **Segurança** (`modulos/seguranca.py`): Integração com Firebase Auth.

## Repositórios de Dados
- `dados/estoque99.csv`: Estoque atualizado do CD e lojas (atualizado diariamente).
- `dados/sp10a02.csv`: **Cadastro mestre de produtos** — Fator, Norma, Lastro, Camada, Peso, Departamento, Categoria (atualizado diariamente). Substituiu o antigo `dados.xlsx`.
- `dados/db.csv`: Histórico de reposição (alimentado automaticamente pelo RPA). Usado apenas para extração de fatores como fallback.
