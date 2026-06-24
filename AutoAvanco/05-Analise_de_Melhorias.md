# Análise de Melhorias para Precisão na Distribuição

> **Data da Análise:** 24/06/2026  
> **Escopo:** Revisão completa de `ai_core.py`, `interface.py`, `rpa_bot.py` e `seguranca.py`  
> **Objetivo:** Identificar fraquezas na lógica atual e propor implementações que aumentem a assertividade da distribuição

---

## 🔴 Problemas Críticos Encontrados

### 1. Sazonalidade é Praticamente Inexistente
**Arquivo:** `ai_core.py` — linhas 203-216  
**Problema:** O sistema possui um "filtro de sazonalidade" que apenas trava MDVs maiores que 3x a média histórica. Porém, `self.media_historica_item` nunca é populado de fato (é um dicionário vazio `{}`). Isso significa que **a sazonalidade está 100% ignorada** — o sistema não sabe distinguir Natal de Janeiro, Black Friday de Março.  
**Impacto:** Em datas sazonais, o sistema subdistribui (não preparou estoque) ou sobredistribui (continua enviando o ritmo de pico após o fim da promoção).

### 2. MDV Estático (Foto vs. Filme)
**Arquivo:** `ai_core.py` — leitura do `estoque99.csv`  
**Problema:** O MDV (Média Diária de Vendas) usado vem exclusivamente do `estoque99.csv`, que é uma **fotografia** pontual. Se o produto está em ruptura na loja, o MDV caiu artificialmente (não vende porque não tem). Quando o sistema lê esse MDV baixo, calcula que a loja precisa de menos — criando um **ciclo vicioso de subabastecimento**.  
**Impacto:** Lojas em ruptura recebem cada vez menos, pois o MDV "confirma" que vendem pouco.

### 3. DDV Calculado Apenas pelo ERP, Sem Validação
**Arquivo:** `ai_core.py` — linhas 218-219  
**Problema:** O DDV (Dias de Venda em estoque) vem direto do CSV como texto, é parseado e usado diretamente. Não há validação cruzada (`estoque / mdv`). Se o ERP reportar DDV errado, a priorização de urgência erra.  
**Impacto:** Uma loja pode ser tratada como urgente quando tem estoque ou ignorada quando está em ruptura real.

### 4. Distribuição Não Considera Velocidade de Giro Relativa
**Problema:** Todas as lojas grandes recebem o mesmo `dias_alvo` e todas as pequenas recebem o mesmo. Não há diferenciação intra-grupo. Uma loja grande que vende 50 un/dia de um produto e outra que vende 5 un/dia recebem o mesmo alvo de cobertura.  
**Impacto:** A loja de alto giro pode zerar antes da próxima reposição, enquanto a de baixo giro fica sobreestocada.

### 5. Fator Fallback Fixo (12)
**Arquivo:** `ai_core.py` — linhas 173-177  
**Problema:** Quando o fator não é encontrado nem no `dados.xlsx` nem no `db.csv`, o sistema assume `12`. Esse "chute" pode estar muito errado para produtos com fator real de 1 (unitário) ou 48 (caixa grande), causando envio de 4x a mais ou 4x a menos.  
**Impacto:** Erros silenciosos de magnitude alta em produtos sem cadastro mestre correto.

### 6. Ausência de Feedback Loop Real
**Arquivo:** `rpa_bot.py` — método `_registrar_no_db`  
**Problema:** O sistema grava no `db.csv` o que distribuiu, mas nunca lê de volta para avaliar se a distribuição foi boa. Não há métrica de acerto. Não sabemos se o envio de ontem resultou em ruptura (pouco) ou sobreestoque (muito).  
**Impacto:** Sem essa medição, é impossível calibrar o sistema. Estamos operando "às cegas" — confiando que a fórmula está correta sem validação.

---

## 🟡 Pontos de Atenção (Médio Risco)

### 7. Autenticação Bypassada
**Arquivo:** `interface.py` — linhas 533-545  
O login do Firebase está comentado (`# BYPASS DE AUTENTICAÇÃO PARA TESTES`). Qualquer pessoa pode acessar o sistema.

### 8. Importação Desnecessária do Telnet
**Arquivo:** `interface.py` — linha 13  
O `from modulos.bot_telnet import BotTelnet` ainda está importado, e o `preparar_motores()` ainda aceita o modo "telnet" (linha 391). Código morto que pode causar confusão.

### 9. Sem Tratamento de Concorrência no `estoque99.csv`
Se o arquivo for atualizado enquanto o RPA está rodando, a releitura do `recarregar_estoque()` pode pegar um CSV parcialmente escrito.

---

## 🟢 O Que Já Funciona Bem

- ✅ A fórmula base `(MDV * dias_alvo) - estoque_loja) / fator` é sólida e transparente.
- ✅ O sistema de Duas Ondas (Mínimo de Segurança → Alvo) é inteligente e prioriza urgências.
- ✅ A Trava de Saldo impede envio além do estoque físico do CD.
- ✅ O filtro `Fator > 0` no `dados.xlsx` evita divisões por zero.
- ✅ O mecanismo de STOP é robusto e verifica a flag em múltiplos pontos.
- ✅ Relatórios CSV de auditoria são gerados automaticamente.
