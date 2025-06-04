# codex_one/nucleo_rag/banco_vetorial_chroma.py

import chromadb
import uuid 
from typing import List, Dict, Optional, Any

from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME

_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None

def get_chroma_client() -> Optional[chromadb.PersistentClient]:
    global _client
    if _client is None:
        try:
            print(f"Inicializando ChromaDB client com persistência em: {CHROMA_PERSIST_DIR}")
            _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        except Exception as e:
            print(f"Erro ao inicializar o cliente ChromaDB: {e}")
            _client = None
    return _client

def get_or_create_collection(client: chromadb.PersistentClient, embedding_function: Optional[Any] = None) -> Optional[chromadb.Collection]:
    global _collection
    if _collection is None and client is not None:
        try:
            print(f"Tentando obter ou criar a coleção: {CHROMA_COLLECTION_NAME}")
            _collection = client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
            )
            print(f"Coleção '{CHROMA_COLLECTION_NAME}' obtida/criada com sucesso.")
        except Exception as e:
            print(f"Erro ao obter ou criar a coleção '{CHROMA_COLLECTION_NAME}': {e}")
            _collection = None
    return _collection

def initialize_vector_db(embedding_function_instance: Optional[Any] = None) -> Optional[chromadb.Collection]:
    client = get_chroma_client()
    if client:
        return get_or_create_collection(client, embedding_function=embedding_function_instance)
    return None

def add_chunks_to_collection(
    collection: chromadb.Collection,
    chunk_texts: List[str],
    embeddings: List[List[float]],
    metadatas: List[Dict[str, Any]],
    chunk_ids: List[str]
) -> bool:
    if not collection:
        print("Erro: Coleção ChromaDB não inicializada.")
        return False
    if not (len(chunk_texts) == len(embeddings) == len(metadatas) == len(chunk_ids)):
        print("Erro: Listas de chunks, embeddings, metadados e IDs têm tamanhos diferentes.")
        return False
    if not chunk_texts:
        print("Nenhum chunk para adicionar.")
        return True

    try:
        print(f"Adicionando {len(chunk_texts)} chunks à coleção '{collection.name}'...")
        collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas
        )
        print(f"{len(chunk_texts)} chunks adicionados com sucesso.")
        return True
    except Exception as e:
        print(f"Erro ao adicionar chunks à coleção: {e}")
        return False

def find_similar_chunks(
    collection: chromadb.Collection,
    query_embedding: List[float],
    top_k: int = 3,
    filter_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    if not collection:
        print("Erro: Coleção ChromaDB não inicializada.")
        return []
    try:
        print(f"Buscando {top_k} chunks similares...")
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata,
            include=['metadatas', 'documents', 'distances']
        )
        
        processed_results = []
        if results and results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                chunk_id = results['ids'][0][i]
                document_text = results['documents'][0][i] if results['documents'] else None
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                distance = results['distances'][0][i] if results['distances'] else float('inf')
                
                processed_results.append({
                    "id_chunk": chunk_id,
                    "texto_chunk": document_text,
                    "metadatos": metadata,
                    "distancia": distance
                })
            print(f"Encontrados {len(processed_results)} chunks.")
        else:
            print("Nenhum chunk similar encontrado.")
        return processed_results
        
    except Exception as e:
        print(f"Erro ao buscar chunks similares: {e}")
        return []

def delete_document_chunks(collection: chromadb.Collection, doc_id_value: str) -> bool:
    if not collection:
        print("Erro: Coleção ChromaDB não inicializada.")
        return False
    try:
        print(f"Tentando remover chunks para doc_id_original: {doc_id_value}")
        collection.delete(where={"doc_id_original": doc_id_value})
        print(f"Todos os chunks associados ao doc_id_original '{doc_id_value}' foram solicitados para remoção.")
        return True
    except Exception as e:
        print(f"Erro ao remover chunks para doc_id_original '{doc_id_value}': {e}")
        return False

def get_all_document_infos(collection: chromadb.Collection) -> List[Dict[str, Any]]:
    """Recupera informações agregadas sobre todos os documentos únicos na coleção."""
    if not collection:
        print("Erro: Coleção ChromaDB não inicializada.")
        return []
    try:
        print("Recuperando informações de todos os documentos...")
        num_items = collection.count()
        if num_items == 0:
            return []
            
        # Para coleções muito grandes, buscar tudo pode ser pesado.
        # Considere paginação ou uma forma mais eficiente se necessário no futuro.
        all_items = collection.get(include=['metadatas'], limit=num_items if num_items > 0 else 1) 
        
        document_infos = {} 
        if all_items and all_items['metadatas']:
            for meta in all_items['metadatas']:
                doc_id = meta.get('doc_id_original')
                # CORREÇÃO AQUI: Usar 'nome_arquivo_original' para obter o nome
                nome_arquivo = meta.get('nome_arquivo_original') 
                
                if not doc_id and nome_arquivo: 
                    doc_id = nome_arquivo # Fallback se doc_id_original não estiver lá, usando o nome do arquivo
                
                if doc_id and doc_id not in document_infos:
                    document_infos[doc_id] = {
                        "doc_id_original": doc_id,
                        # Guardar como 'nome_arquivo' para consistência com o que a GUI espera
                        "nome_arquivo": nome_arquivo, 
                        "autor": meta.get("autor_documento"), # Usar as chaves corretas dos metadados dos chunks
                        "titulo": meta.get("titulo_documento"),# Usar as chaves corretas
                        "data_upload": meta.get("data_upload"), 
                        "numero_chunks": 0 
                    }
                if doc_id: 
                    document_infos[doc_id]["numero_chunks"] += 1
        
        print(f"Encontradas informações para {len(document_infos)} documentos únicos.")
        return list(document_infos.values())
        
    except Exception as e:
        print(f"Erro ao recuperar informações de todos os documentos: {e}")
        return []

def get_document_chunk_count(collection: chromadb.Collection, doc_id_value: str) -> int:
    if not collection:
        return 0
    try:
        results = collection.get(where={"doc_id_original": doc_id_value}, include=[]) 
        return len(results['ids']) if results and results['ids'] else 0
    except Exception as e:
        print(f"Erro ao contar chunks para doc_id_original '{doc_id_value}': {e}")
        return 0

# --- Bloco de Teste (sem alterações significativas, mas a limpeza inicial é importante) ---
if __name__ == '__main__':
    print("Testando módulo banco_vetorial_chroma.py...")
    
    from config import ensure_directories_exist, SENTENCE_TRANSFORMER_MODEL
    ensure_directories_exist()

    ACTUAL_EMBEDDING_DIM = 768 
    try:
        from nucleo_rag.gerenciador_embeddings import obter_dimensao_embedding
        dim_from_model = obter_dimensao_embedding()
        if dim_from_model:
            ACTUAL_EMBEDDING_DIM = dim_from_model
        else:
            print(f"AVISO: Não foi possível obter a dimensão do modelo {SENTENCE_TRANSFORMER_MODEL}. Usando {ACTUAL_EMBEDDING_DIM} como padrão para teste.")
    except ImportError:
        print(f"AVISO: Módulo gerenciador_embeddings não encontrado. Usando {ACTUAL_EMBEDDING_DIM} como padrão para teste.")

    collection = initialize_vector_db()

    if collection:
        print(f"Nome da coleção: {collection.name}")
        print(f"ID da coleção: {collection.id}")
        
        print(f"Contagem inicial de itens na coleção: {collection.count()}")
        if collection.count() > 0:
            print("Limpando todos os itens da coleção para garantir um teste limpo...")
            current_items_ids = collection.get(include=[])['ids'] 
            if current_items_ids:
                collection.delete(ids=current_items_ids)
            print(f"Contagem após limpeza: {collection.count()}")
        
        chunk_id1 = f"doc1_banco_test_{uuid.uuid4().hex[:4]}"
        chunk_id2 = f"doc1_banco_test_{uuid.uuid4().hex[:4]}"
        chunk_id3 = f"doc2_banco_test_{uuid.uuid4().hex[:4]}"

        texts = [
            "Este é o primeiro chunk do documento de teste 1 sobre IA no banco.",
            "O segundo chunk do banco discute aprendizado de máquina no contexto do documento 1.",
            "Este é um chunk de um documento diferente, o documento 2 do banco, sobre Python."
        ]
        embeddings_data = [
            [0.1] * ACTUAL_EMBEDDING_DIM,
            [0.4] * ACTUAL_EMBEDDING_DIM,
            [0.7] * ACTUAL_EMBEDDING_DIM
        ]
        # Metadados como seriam salvos pelo processador_documentos e pipeline_rag
        metadatas_data = [
            {"doc_id_original": "doc_banco_teste_1", "nome_arquivo_original": "banco_teste1.pdf", "numero_pagina": 1, "autor_documento": "Autor Banco", "titulo_documento": "Título Banco 1"},
            {"doc_id_original": "doc_banco_teste_1", "nome_arquivo_original": "banco_teste1.pdf", "numero_pagina": 2, "autor_documento": "Autor Banco", "titulo_documento": "Título Banco 1"},
            {"doc_id_original": "doc_banco_teste_2", "nome_arquivo_original": "banco_teste2.py", "numero_pagina": 1, "autor_documento": "Autor Banco Py", "titulo_documento": "Título Banco 2"}
        ]
        chunk_ids_data = [chunk_id1, chunk_id2, chunk_id3]
        
        print("\n--- Teste de Adição ---")
        success_add = add_chunks_to_collection(collection, texts, embeddings_data, metadatas_data, chunk_ids_data)
        if success_add:
            print(f"Contagem após adição: {collection.count()}")
            assert collection.count() == 3, f"Esperado 3 chunks, mas obteve {collection.count()}"
        else:
            print("Falha ao adicionar chunks.")
            assert False, "Falha na adição de chunks no teste do banco_vetorial_chroma"

        print("\n--- Teste de Busca por Similaridade ---")
        query_emb = [0.15] * ACTUAL_EMBEDDING_DIM 
        similar = find_similar_chunks(collection, query_emb, top_k=2)
        if similar:
            for item in similar:
                print(f"  ID: {item['id_chunk']}, Dist: {item['distancia']:.4f}, "
                      f"Doc: {item['metadatos'].get('nome_arquivo_original')}, Pag: {item['metadatos'].get('numero_pagina')}, " # Ajustado para nome_arquivo_original
                      f"Texto: '{item['texto_chunk'][:40]}...'")
            assert len(similar) > 0, "Busca por similaridade não retornou resultados."
        else:
            print("  Nenhum chunk similar encontrado.")

        print("\n--- Teste de Listagem de Documentos ---")
        doc_infos = get_all_document_infos(collection)
        if doc_infos:
            for info in doc_infos:
                print(f"  Doc ID: {info.get('doc_id_original')}, Nome: {info.get('nome_arquivo')}, Chunks: {info.get('numero_chunks')}")
            assert any(d['doc_id_original'] == "doc_banco_teste_1" and d['nome_arquivo'] == "banco_teste1.pdf" for d in doc_infos), "doc_banco_teste_1 não encontrado ou nome incorreto."
            assert any(d['doc_id_original'] == "doc_banco_teste_2" and d['nome_arquivo'] == "banco_teste2.py" for d in doc_infos), "doc_banco_teste_2 não encontrado ou nome incorreto."
        else:
            print("  Nenhuma informação de documento encontrada.")
            assert collection.count() == 0, "Infos de documentos vazias, mas coleção não está vazia."
            
        print("\n--- Teste de Contagem de Chunks por Documento ---")
        count_doc1 = get_document_chunk_count(collection, "doc_banco_teste_1")
        print(f"  Chunks para 'doc_banco_teste_1': {count_doc1}")
        assert count_doc1 == 2, f"Esperado 2 chunks para doc_banco_teste_1, obteve {count_doc1}"
        
        count_doc2 = get_document_chunk_count(collection, "doc_banco_teste_2")
        print(f"  Chunks para 'doc_banco_teste_2': {count_doc2}")
        assert count_doc2 == 1, f"Esperado 1 chunk para doc_banco_teste_2, obteve {count_doc2}"

        print("\n--- Teste de Exclusão de Documento ---")
        if get_document_chunk_count(collection, "doc_banco_teste_1") > 0:
            success_delete = delete_document_chunks(collection, "doc_banco_teste_1")
            if success_delete:
                print(f"Contagem após exclusão de 'doc_banco_teste_1': {collection.count()}")
                assert get_document_chunk_count(collection, "doc_banco_teste_1") == 0, "Chunks de doc_banco_teste_1 não foram totalmente deletados."
                assert collection.count() == 1, f"Esperado 1 chunk restante, obteve {collection.count()}"
            else:
                print("Falha ao excluir chunks de 'doc_banco_teste_1'.")
                assert False, "Falha na exclusão de chunks de doc_banco_teste_1"
        else:
            print("Documento 'doc_banco_teste_1' não encontrado para exclusão ou já excluído.")

        if get_document_chunk_count(collection, "doc_banco_teste_2") > 0:
             delete_document_chunks(collection, "doc_banco_teste_2")
             print(f"Limpando doc_banco_teste_2. Contagem final: {collection.count()}")
             assert collection.count() == 0, "Coleção não foi totalmente limpa no final do teste."

    else:
        print("Não foi possível inicializar a coleção ChromaDB.")
        assert False, "Falha ao inicializar coleção ChromaDB no teste"

    print("\nTestes do banco_vetorial_chroma.py concluídos.")
