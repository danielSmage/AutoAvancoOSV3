# Mapa de Módulos (Cérebro do Código)

Este documento atua como o registro de todos os módulos vitais do `AutoAvançoOSV3` e suas responsabilidades.

## 1. `app_main.py`
**Responsabilidade:** Entrypoint (Ponto de entrada). Inicia os fluxos do orquestrador e abre a tela de login.

## 2. `modulos/interface.py`
**Responsabilidade:** Front-end da aplicação em Tkinter (ou CustomTkinter).
- Contém o sistema de abas (TabView).
- Hospeda os controles de sliders para o "Giro-Alvo" (7 a 60 dias).
- Renderiza a aba da ferramenta "Encontrar Pallets".
- Fornece os botões de execução e o botão de emergência STOP.

## 3. `modulos/ai_core.py`
**Responsabilidade:** Cérebro da lógica de distribuição.
- Anteriormente abrigava o `RandomForestRegressor`.
- Hoje executa a extração de fatores do `dados.xlsx` com pandas (filtrando `Fator > 0`).
- Aplica a equação determinística de distribuição baseada em MDV, Fator e Estoque_Loja.

## 4. `modulos/rpa_bot.py`
**Responsabilidade:** Automação visual no Windows. **Este é o sistema primário e em uso.**
- Simula cliques e digitação via PyAutoGUI para operar o ERP.
- Implementa o mecanismo iterativo e a trava de segurança `_stop_requested`.

## 5. `modulos/bot_telnet.py`
**Responsabilidade:** Conexão socket de baixo nível ao servidor ERP.
- **Status:** ❌ **INATIVO / FRACASSO**. A tentativa de navegação via rede bypassando o visual falhou. O código existe por razões de histórico, mas não é mais utilizado na esteira de produção. Toda operação agora passa pelo `rpa_bot.py`.

## 6. `modulos/seguranca.py`
**Responsabilidade:** Segurança e restrição de acesso.
- Comunicação com a API do Firebase.
- Validação de credenciais de login.

---
**Status Atual do Repositório:** Estável. Todas as remoções de dependência falha do ML foram aplicadas em produção e comitadas na branch `main`.
