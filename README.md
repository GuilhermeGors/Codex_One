# Codex_One
Uma aplicação IA que lê livros

codex_one/
├── main_app.py
├── config.py
├── requirements.txt
├── .gitignore
|
├── core/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── llm_handler.py
│   ├── embedding_manager.py
│   └── tests/
│       ├── __init__.py
│       ├── test_pipeline.py
│       ├── test_llm_handler.py
│       └── test_embedding_manager.py
|
├── data_access/
│   ├── __init__.py
│   ├── vector_db.py
│   ├── file_system_manager.py
│   └── tests/
│       ├── __init__.py
│       ├── test_vector_db.py
│       └── test_file_system_manager.py
|
├── processing/
│   ├── __init__.py
│   ├── document_parser.py  # Lógica principal de parsing
│   ├── pdf_processor.py    # Funções específicas para PDF
│   ├── epub_processor.py   # Funções específicas para ePub
│   ├── text_splitter.py    # Anteriormente: text_utils.py (focado em chunking)
│   └── tests/
│       ├── __init__.py
│       ├── test_document_parser.py
│       ├── test_pdf_processor.py
│       ├── test_epub_processor.py
│       └── test_text_splitter.py
|
└── (futuramente: ui/, assets/, etc.)

