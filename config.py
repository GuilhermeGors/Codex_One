# codex_one/config.py

import os

# --- Configurações do Ollama ---
OLLAMA_BASE_URL = "http://localhost:11434"  # URL base do servidor Ollama
OLLAMA_MODEL = "llama3:8b-instruct-q5_k_m"  # Modelo LLM a ser usado (ex: "llama3:8b", "mistral:7b")
OLLAMA_EMBED_MODEL = "mxbai-embed-large" # Modelo de embedding do Ollama (ou use sentence-transformers)
# Se for usar sentence-transformers para embeddings localmente:
SENTENCE_TRANSFORMER_MODEL = "sentence-transformers/all-mpnet-base-v2" # Modelo multilíngue robusto

# --- Configurações do Banco de Dados ---
# O DATABASE_PATH original para SQLite não será mais usado diretamente para vetores.
# Mantemos DATABASE_DIR para organização geral dos dados.
DATABASE_DIR = os.path.join(os.path.dirname(__file__), "dados")

# --- Configurações do ChromaDB ---
CHROMA_PERSIST_DIR = os.path.join(DATABASE_DIR, "chroma_db")
CHROMA_COLLECTION_NAME = "codex_documentos" # Nome da coleção no ChromaDB

# --- Configurações de Documentos ---
DOCUMENTS_DIR = os.path.join(DATABASE_DIR, "documentos_usuario")

# --- Configurações do RAG ---
CHUNK_SIZE = 1000  # Tamanho dos chunks de texto
CHUNK_OVERLAP = 100  # Sobreposição entre chunks
TOP_K_RESULTS = 3  # Número de chunks mais relevantes a serem recuperados

# --- Criação dos diretórios se não existirem ---
def ensure_directories_exist():
    """Garante que os diretórios de dados e documentos existam."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True) # Garante que o diretório do ChromaDB exista

if __name__ == "__main__":
    ensure_directories_exist()
    print(f"Diretório de Dados: {DATABASE_DIR}")
    print(f"Diretório de Persistência do ChromaDB: {CHROMA_PERSIST_DIR}")
    print(f"Diretório de Documentos: {DOCUMENTS_DIR}")
    print("Diretórios verificados/criados.")

