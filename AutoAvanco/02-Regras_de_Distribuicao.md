# Regras de Distribuição e Cálculo de Estoque

## A Mudança de ML para Matemática Pura
Anteriormente, o sistema utilizava um `RandomForestRegressor`. No entanto, como o histórico de reposições era afetado por faltas de estoque no CD (que forçavam cortes nos envios), a IA aprendia erroneamente a enviar menos. A solução foi migrar para um cálculo determinístico e seguro.

## Fórmula de Distribuição Estrita
A nova regra garante transparência e abastecimento correto:

```text
Necessidade em Caixas = ((MDV * Dias_Alvo) - Estoque_Atual_Loja) / Fator_Mestre
```

### Variáveis
- **MDV (Média Diária de Vendas)**: Venda diária do produto na loja. **Corrigida automaticamente** quando a loja está zerada (Anti-Ruptura P0-001).
- **Dias_Alvo (Giro-Alvo)**: Cobertura desejada.
  - Lojas Grandes: Configurável de 7 a 60 dias (Padrão: 30d).
  - Lojas Pequenas: Configurável de 7 a 60 dias (Padrão: 15d).
- **Estoque_Atual_Loja**: O que a loja já tem do produto.
- **Fator_Mestre**: Quantidade de unidades por caixa. Extraído do `sp10a02.csv` (prioridade), `db.csv` (fallback) ou valor fixo 12 (último recurso com alerta ⚠️).

## Trava de Saldo (Guardrails)
O sistema conta com proteção de saldo no CD (Estoque99). O algoritmo jamais permite a emissão de quantidades superiores ao que consta no estoque físico do Centro de Distribuição, e prioriza a distribuição balanceada quando há escassez.

## Melhorias de Precisão Ativas
### MDV Anti-Ruptura (P0-001)
Lojas com estoque zerado têm MDV artificialmente baixo. O sistema substitui pela **mediana** das lojas com estoque positivo quando o MDV da loja zerada é menor que 50% dessa mediana.

### Validação Cruzada DDV (P0-002)
O DDV do ERP é recalculado internamente como `estoque / MDV`. Se divergir mais de 30%, o valor calculado é preferido.
