# Codex_One
Uma aplicação IA que lê livros

seu_projeto_rag/
├── main_app.py                     # Ponto de entrada da aplicação, lógica principal da GUI (CustomTkinter)
|
├── interface_usuario/              # Módulos/arquivos relacionados à GUI
│   ├── janela_principal.py         # Layout principal, interações
│   └── widgets_documentos.py     # Widgets para listar, adicionar, remover arquivos
|
├── nucleo_rag/                     # Lógica principal do RAG e gerenciamento de dados
│   ├── processador_documentos.py   # Carregar, parsear PDFs, extrair texto, dividir em chunks
│   ├── gerenciador_embeddings.py   # Gerar embeddings
│   ├── banco_sqlite.py             # Interação com SQLite (tabelas de metadados e vetores)
│   ├── manipulador_llm.py          # Comunicação com o Ollama
│   ├── pipeline_rag.py             # Orquestra o fluxo de consulta e geração
│   └── gerenciador_arquivos.py     # Lógica para upload, salvar, listar e deletar arquivos físicos
|
├── dados/                            # Onde os dados da aplicação são armazenados
│   ├── documentos_usuario/           # Pasta para armazenar os PDFs carregados
│   └── rag_database.db               # Arquivo do banco de dados SQLite
|
├── config.py                       # Configurações (ex: URL do Ollama, nome do modelo, caminho da DB)
└── requirements.txt                # Dependências Python (customtkinter, PyMuPDF, sentence-transformers, ollama, etc.)

