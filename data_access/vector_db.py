# codex_one/data_access/vector_db.py

import chromadb
import uuid 
from typing import List, Dict, Optional, Any
import os
import shutil 
import time 

from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME

_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None

def _robust_rmtree(path, max_retries=3, delay=0.5):
    """Tenta remover um diretório de forma robusta, com retries."""
    for i in range(max_retries):
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
                # print(f"[Vector DB] Diretório '{path}' removido com sucesso.") # Silenciado para main_app
            return True
        except PermissionError as e:
            print(f"[Vector DB] PermissionError ao remover '{path}' (tentativa {i+1}/{max_retries}): {e}")
            if i < max_retries - 1:
                time.sleep(delay)
            else:
                print(f"[Vector DB] Falha final ao remover '{path}' após {max_retries} tentativas.")
                return False
        except Exception as e: 
            # print(f"[Vector DB] Exceção ao remover '{path}': {e}") # Silenciado
            return False 
    return True 

def delete_persistent_storage():
    """Força a remoção da pasta de persistência do ChromaDB."""
    # print(f"[Vector DB] Tentando remover o diretório de persistência: {CHROMA_PERSIST_DIR}") # Silenciado
    return _robust_rmtree(CHROMA_PERSIST_DIR)

def reset_db_state_for_tests():
    """Reseta o estado do DB para testes: apaga armazenamento e reseta vars globais."""
    global _client, _collection
    print("[Vector DB] Resetando estado do DB para testes...")
    _client = None
    _collection = None
    delete_persistent_storage()
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)


def get_chroma_client(force_new: bool = False) -> Optional[chromadb.ClientAPI]:
    global _client, _collection 
    if _client is None or force_new:
        if force_new and _client is not None:
            print("[Vector DB] Forçando nova instância do cliente ChromaDB (resetando _client e _collection).")
            _client = None
            _collection = None # Resetar _collection se _client for forçado a ser novo

        try:
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            print(f"[Vector DB] Inicializando ChromaDB client com persistência em: {CHROMA_PERSIST_DIR}")
            _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        except Exception as e:
            print(f"[Vector DB] Erro crítico ao inicializar o cliente ChromaDB: {e}")
            _client = None
    return _client

def get_or_create_collection(client: chromadb.ClientAPI) -> Optional[chromadb.Collection]:
    global _collection
    # A verificação _collection.client != client foi REMOVIDA.
    # Se _collection é None (seja por ser a primeira vez, ou porque _client foi resetado),
    # então tentamos obter ou criar a coleção.
    if _collection is None and client is not None:
        try:
            print(f"[Vector DB] Tentando obter ou criar a coleção: {CHROMA_COLLECTION_NAME}")
            # O get_or_create_collection é idempotente e seguro.
            _collection = client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                # metadata={"hnsw:space": "cosine"} # Opcional
            )
            print(f"[Vector DB] Coleção '{CHROMA_COLLECTION_NAME}' obtida/criada com sucesso.")
        except Exception as e_get_create:
            print(f"[Vector DB] Erro ao obter ou criar a coleção '{CHROMA_COLLECTION_NAME}': {e_get_create}")
            _collection = None
            
    # Se _collection já existe e o cliente é o mesmo (ou não foi forçado a ser novo),
    # esta função retornará a _collection global existente.
    return _collection

def initialize_vector_db(force_new_client: bool = False) -> Optional[chromadb.Collection]:
    """Função principal para inicializar e retornar a coleção."""
    client = get_chroma_client(force_new=force_new_client)
    if client:
        # Se um novo cliente foi forçado, _collection já terá sido resetado para None em get_chroma_client.
        # Assim, get_or_create_collection irá obter/criar a coleção com o novo cliente.
        return get_or_create_collection(client)
    return None

def delete_all_collections(client: chromadb.ClientAPI):
    if not client:
        # print("[Vector DB] Cliente ChromaDB não inicializado para delete_all_collections.") # Silenciado
        return
    try:
        # print("[Vector DB] Tentando deletar todas as coleções via cliente...") # Silenciado
        collections = client.list_collections()
        for coll_obj in collections:
            # print(f"[Vector DB] Deletando coleção: {coll_obj.name}") # Silenciado
            client.delete_collection(name=coll_obj.name)
        global _collection 
        _collection = None 
        # print("[Vector DB] Todas as coleções foram deletadas via cliente.") # Silenciado
    except Exception as e:
        print(f"[Vector DB] Erro ao deletar todas as coleções via cliente: {e}")

# --- Funções CRUD (sem alterações no corpo, apenas logging pode ser ajustado) ---
def add_chunks_to_collection(
    collection: chromadb.Collection,
    chunk_texts: List[str],
    embeddings: List[List[float]],
    metadatas: List[Dict[str, Any]],
    chunk_ids: List[str]
) -> bool:
    if not collection: print("Erro: Coleção ChromaDB não inicializada."); return False
    if not (len(chunk_texts) == len(embeddings) == len(metadatas) == len(chunk_ids)):
        print("Erro: Listas de chunks, embeddings, metadados e IDs têm tamanhos diferentes."); return False
    if not chunk_texts: return True
    try:
        collection.add(ids=chunk_ids, embeddings=embeddings, documents=chunk_texts, metadatas=metadatas)
        return True
    except Exception as e: print(f"Erro ao adicionar chunks à coleção: {e}"); return False

def find_similar_chunks(
    collection: chromadb.Collection, query_embedding: List[float], top_k: int = 3,
    filter_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    if not collection: print("Erro: Coleção ChromaDB não inicializada."); return []
    try:
        count = collection.count()
        if count == 0: return []
        actual_top_k = min(top_k, count) if count > 0 else 0
        if actual_top_k == 0 : return []

        results = collection.query(
            query_embeddings=[query_embedding], n_results=actual_top_k,
            where=filter_metadata, include=['metadatas', 'documents', 'distances']
        )
        processed = []
        if results and results.get('ids') and results['ids'] and results['ids'][0] is not None:
            for i in range(len(results['ids'][0])):
                processed.append({
                    "id_chunk": results['ids'][0][i],
                    "texto_chunk": results['documents'][0][i] if results.get('documents') and results['documents'][0] else None,
                    "metadatos": results['metadatas'][0][i] if results.get('metadatas') and results['metadatas'][0] else {},
                    "distancia": results['distances'][0][i] if results.get('distances') and results['distances'][0] else float('inf')
                })
        return processed
    except Exception as e: print(f"Erro em find_similar_chunks: {e}"); return []

def delete_document_chunks(collection: chromadb.Collection, doc_id_original_db_value: str) -> bool:
    if not collection: print("Erro: Coleção ChromaDB não inicializada."); return False
    try:
        key_to_delete_by = "doc_id_original_db"
        items_to_delete = collection.get(where={key_to_delete_by: doc_id_original_db_value}, include=[])
        if not items_to_delete or not items_to_delete.get('ids') or not items_to_delete['ids'][0]:
            return True
        collection.delete(where={key_to_delete_by: doc_id_original_db_value})
        return True
    except Exception as e: print(f"Erro em delete_document_chunks: {e}"); return False

def get_all_document_infos(collection: chromadb.Collection) -> List[Dict[str, Any]]:
    if not collection: print("Erro: Coleção ChromaDB não inicializada."); return []
    try:
        num_items = collection.count()
        if num_items == 0: return []
        all_items = collection.get(include=['metadatas'], limit=num_items)
        doc_infos = {}
        if all_items and all_items.get('metadatas'):
            for meta_list_item in all_items['metadatas']: # Iterar sobre a lista de metadados
                if meta_list_item is None: continue # Pular se um metadado for None
                # meta_list_item é um dicionário de metadados para um chunk
                doc_id_key = meta_list_item.get('doc_id_original_db') 
                nome_arquivo = meta_list_item.get('nome_arquivo_original')
                if not doc_id_key and nome_arquivo: doc_id_key = nome_arquivo
                if doc_id_key:
                    if doc_id_key not in doc_infos:
                        doc_infos[doc_id_key] = {
                            "doc_id_original": doc_id_key, "nome_arquivo": nome_arquivo,
                            "autor": meta_list_item.get("autor_documento"), 
                            "titulo": meta_list_item.get("titulo_documento"),
                            "data_upload": meta_list_item.get("data_upload"), # Se você adicionar este metadado
                            "numero_chunks": 0
                        }
                    doc_infos[doc_id_key]["numero_chunks"] += 1
        return list(doc_infos.values())
    except Exception as e: print(f"Erro em get_all_document_infos: {e}"); return []

def get_document_chunk_count(collection: chromadb.Collection, doc_id_original_db_value: str) -> int:
    if not collection: return 0
    try:
        results = collection.get(where={"doc_id_original_db": doc_id_original_db_value}, include=[])
        return len(results['ids'][0]) if results and results.get('ids') and results['ids'] and results['ids'][0] is not None else 0
    except Exception as e: print(f"Erro em get_document_chunk_count: {e}"); return 0
