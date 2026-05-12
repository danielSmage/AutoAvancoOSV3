# 🚀 Avanço Pro System V2
<!-- Última sincronização: 2026-05-12 11:35 -->


**Avanço Pro System** é um orquestrador inteligente de RPA (Robotic Process Automation) integrado com Machine Learning, projetado para automatizar a reposição de estoque com precisão cirúrgica.

## ✨ Funcionalidades

-   **🔐 Autenticação Centralizada**: Integração com Firebase Auth para controle de acesso remoto.
-   **🧠 Motor de Inteligência Artificial**: Utiliza `RandomForestRegressor` para aprender com o histórico de reposição (`DB.txt`) e prever a demanda ideal.
-   **🤖 Automação RPA Robusta**: Execução via `PyAutoGUI` (Visual) ou `Telnet` (Direto ao Servidor), com tratamento de exceções.
-   **📊 Relatórios Dinâmicos**: Geração automática de logs de execução em CSV para auditoria e controle.
-   **🎯 Modos de Operação**:
    -   *Modo Padrão*: Distribuição balanceada baseada em giro e estoque.
    -   *Modo Zerados*: Foco total em urgências para lojas com ruptura de estoque.
    -   *Modo Telnet*: Conexão direta com o servidor Avanço ERP para máxima precisão.

## 🛠️ Tecnologias Utilizadas

-   **Linguagem**: Python 3.13+
-   **Interface**: Tkinter
-   **Data Science**: Pandas, Scikit-Learn
-   **Automação**: PyAutoGUI
-   **Backend**: Firebase (Firestore & Identity Toolkit)

## 🚀 Como Executar

1.  **Clone o repositório**:
    ```bash
    git clone https://github.com/seu-usuario/avanco-pro-system.git
    cd avanco-pro-system
    ```

2.  **Instale as dependências**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure os dados**:
    -   Coloque o arquivo de estoque em `dados/estoque99.csv`.
    -   Coloque o histórico de reposição em `dados/DB.txt`.
    -   (Opcional) Se estiver em uma rede corporativa, configure o Proxy no arquivo `.env`.

4.  **Inicie a aplicação**:
    ```bash
    python app_main.py
    ```

## 📂 Estrutura do Projeto

```text
├── app_main.py          # Ponto de entrada da aplicação
├── modulos/             # Módulos principais
│   ├── ai_core.py       # Lógica de Machine Learning
│   ├── interface.py     # Interface gráfica (Tkinter)
│   ├── rpa_bot.py       # Automação de interface (PyAutoGUI)
│   └── seguranca.py     # Integração com Firebase
├── dados/               # Dados de entrada (CSV/TXT) - Ignorado no Git
├── relatorios/          # Relatórios gerados (CSV) - Ignorado no Git
└── requirements.txt     # Dependências do projeto
```

## ⚖️ Licença

Este projeto é de uso restrito e confidencial. Todos os direitos reservados.

---
Desenvolvido com ❤️ por [Seu Nome/Empresa]
