# Changelog — Alterações do Sistema

> Registro cronológico de todas as mudanças significativas feitas no AutoAvançoOSV3.

---

## 2026-06-24 — Migração sp10a02 + Melhorias de Precisão

### 🔄 Migração de Dados Mestre
- **REMOVIDO:** Dependência do `dados.xlsx` (antigo cadastro mestre).
- **ADICIONADO:** Leitura do `sp10a02.csv` como nova fonte de dados mestre.
- O `sp10a02.csv` é um CSV separado por `;` com encoding `latin1`, atualizado diariamente.
- Contém **40.593 produtos**, dos quais **15.088** possuem fator válido (> 0).
- Dados extraídos: `Produto`, `Desc`, `Fator`, `Norma`, `Lastro`, `Camada`, `Peso`, `Departamento`, `Categoria`.
- **Vantagem:** Carregamento ~10x mais rápido que `.xlsx` e dados mais ricos (Norma, Lastro, Camada).

### 🧮 Novos Dicionários no Motor de Inteligência
| Dicionário | Conteúdo | Qtd Registros |
|------------|----------|---------------|
| `fatores_mestre` | Código → Fator (un/caixa) | 15.088 |
| `normas_mestre` | Código → Norma (cxs/pallet) | 14.196 |
| `dados_mestre` | Código → dict completo (desc, fator, norma, lastro, camada, peso, depto, categoria) | 15.088 |

### 🛡️ P0-001: MDV Anti-Ruptura (IMPLEMENTADO)
- Quando uma loja está com estoque zerado, o MDV cai artificialmente (não vende porque não tem).
- **Nova regra:** Se o MDV da loja zerada for menor que 50% da mediana das lojas com estoque, substitui pela mediana.
- **Resultado:** Quebra o ciclo vicioso de subabastecimento.
- **Local:** `ai_core.py` → `calcular_distribuicao()`, após montagem de `lojas_processar`.

### 🛡️ P0-002: Validação Cruzada do DDV (IMPLEMENTADO)
- O DDV informado pelo ERP nem sempre é confiável.
- **Nova regra:** Recalcula `DDV = estoque_loja / MDV` internamente. Se divergir mais de 30% do valor do ERP, usa o calculado.
- **Local:** `ai_core.py` → dentro do loop de montagem de `lojas_processar`.

### ⚠️ Alerta de Fator Fallback (IMPLEMENTADO)
- Quando o sistema não encontra o fator no `sp10a02.csv` nem no `db.csv` e usa o fallback (12), agora imprime: `⚠️ Item XXXXX: fator fallback (12). Verificar cadastro mestre.`
- Rastreia a fonte do fator: `SP10`, `DB.CSV` ou `FALLBACK`.

### 🖥️ Interface — Limpeza do Telnet
- Removida importação morta: `from modulos.bot_telnet import BotTelnet`.
- Removido branch `if modo_conexao == "telnet"` do `preparar_motores()`.
- Dropdown de configuração agora só mostra `pyautogui`.

### 🖥️ Interface — Log Enriquecido
- Durante execução do RPA, o log agora exibe por item:
  - Descrição do produto (do sp10a02)
  - Fator e Norma (cxs/pallet)
  - Departamento e Categoria
  - Estoque do CD em caixas e status do cálculo

---

## Notas Técnicas
- Todos os dados (`sp10a02.csv` e `estoque99.csv`) são recarregados dinamicamente a cada execução via `recarregar_estoque()`.
- O `sp10a02.csv` possui números no formato brasileiro (`0012,0000`) — tratamento via `str.replace('.','').replace(',','.')`.
- **63% dos produtos no sp10a02 têm fator = 0** — filtrados rigorosamente para evitar divisão por zero.
