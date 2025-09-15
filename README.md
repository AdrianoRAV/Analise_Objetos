📦 Análise de Objetos por Setup
Uma aplicação Streamlit para análise e visualização de objetos processados em diferentes setups de operação logística.

📋 Descrição
Este projeto conecta-se a um banco de dados MySQL para analisar objetos processados em diferentes turnos (setups) de operação, fornecendo visualizações interativas através de gráficos e tabelas.

✨ Funcionalidades
Conexão com Banco MySQL: Acesso a dados de objetos e setups

Filtros Interativos:

Seleção de data específica

Filtro por direções/rotas

Seleção de setup individual ou visão consolidada

Visualizações Gráficas:

Gráficos de barras para quantidades de objetos

Gráficos de percentual de entregas

Visualização empilhada para todos os setups

Tabelas Detalhadas: Expansão para visualizar objetos específicos por setup

🛠️ Tecnologias Utilizadas
Python 3.x

Streamlit

Pandas

NumPy

MySQL Connector

Plotly Express

Datetime

📦 Como Baixar e Instalar
Baixe o código:

bash
git clone <url-do-repositorio>
cd <nome-do-repositorio>
Instale as dependências:

bash
pip install streamlit pandas numpy mysql-connector-python plotly
Execute a aplicação:

bash
streamlit run app.py
⚙️ Configuração
Certifique-se de que o banco de dados MySQL está acessível com as seguintes credenciais (modificáveis no código):

Host: IP

Usuário: root

Senha: 123

Banco de dados: sci

🚀 Uso
Após executar a aplicação, acesse http://localhost:8501 no seu navegador.

📊 Estrutura do Banco de Dados
A aplicação espera as seguintes tabelas:

tb_dados_stes - Contém informações dos objetos

tbl_entrega_matutina ou tbl_entrada_matutina - Contém informações dos setups

📈 Funcionalidades Principais
Seleção de Data: Analise dados de qualquer data específica

Filtro por Direções: Foque em rotas específicas

Análise por Setup:

Setup 1: 20h do dia anterior até às 6h

Setup 2: 6h até às 8h40

Setup 3: 8h40 até às 10h

Setup 4: 10h até às 14h

Visão Consolidada: Visualize todos os setups em gráficos empilhados

![Tela Layout](image.png)


📝 Licença
Este projeto é de uso interno.
