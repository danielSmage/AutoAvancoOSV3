# Automação RPA e Ferramentas Auxiliares

## Controle do Robô (RPA)
O módulo `rpa_bot.py` orquestra a automação utilizando bibliotecas como `PyAutoGUI`.

### Sistema de Segurança e Parada
Foi implementada uma função crítica para a segurança operacional: o **Botão STOP (⏹ PARAR)**.
- **Como funciona:** O operador pode acionar o botão a qualquer momento na interface.
- **Onde atua:** O sistema checa o flag `_stop_requested` antes de processar um novo produto e durante as esperas estratégicas (ex: sleep inicial de 5s).
- **Vantagem:** Evita que o robô perca o controle do mouse/teclado, permitindo interrupções seguras.

## Ferramenta: "Encontrar Pallets"
Adicionada recentemente à interface, essa ferramenta é vital para a eficiência logística do CD.

**Objetivo:** Varrer o arquivo `estoque99.csv` buscando produtos que:
1. Possuam um alto volume no Centro de Distribuição.
2. Estejam em ruptura ou baixo estoque em várias lojas simultaneamente.
3. A necessidade combinada das lojas justifique o envio de **pallets fechados** (envio direto e massivo).

O operador pode copiar os códigos encontrados e enviá-los diretamente para a fila de execução do RPA.
