# codex_one/core/pipeline.py

import os
import uuid
from typing import List, Dict, Optional, Any, Callable 

# Importar dos novos locais
from config import TOP_K_RESULTS, CHROMA_COLLECTION_NAME 
from processing import document_parser # Alterado de ..processing para processing (se executado da raiz)
from core import embedding_manager    # Alterado de . para core
from data_access import vector_db     # Alterado de ..data_acces para data_access
from core import llm_handler          # Alterado de . para core

# Inicializar a base de dados vetorial ao carregar o módulo
# Esta inicialização pode ser movida para a app principal se preferir mais controle.
db_collection = vector_db.initialize_vector_db()

def indexar_documento( # Renomeado de indexar_documento_pdf para ser mais genérico
    caminho_arquivo_completo: str, 
    nome_arquivo_original: str,
    gui_progress_callback: Optional[Callable[[str, float], None]] = None 
) -> bool:
    """
    Processa um arquivo (PDF ou ePub), gera embeddings e armazena no ChromaDB.
    """
    if not db_collection:
        print("Erro [Pipeline]: A coleção do ChromaDB não está inicializada.")
        if gui_progress_callback:
            gui_progress_callback("Erro: DB não inicializado.", -1)
        return False

    print(f"[Pipeline] Iniciando indexação para: {nome_arquivo_original} (caminho: {caminho_arquivo_completo})")
    if gui_progress_callback:
        gui_progress_callback(f"Iniciando indexação de '{nome_arquivo_original}'...", 0.0)

    # --- Estágio 1: Processamento do Documento (0% -> 60%) ---
    def _parser_progress_adapter(item_atual: int, total_itens: int):
        if gui_progress_callback and total_itens > 0:
            progresso_parser = (item_atual / total_itens) * 0.60 
            gui_progress_callback(f"Processando doc: item {item_atual}/{total_itens}", progresso_parser)

    # Usar a função renomeada de document_parser
    chunks_info_list = document_parser.processar_documento_ficheiro(
        caminho_arquivo_completo, 
        progress_callback_gui=_parser_progress_adapter # Passando o callback para o parser
    )
    
    if chunks_info_list is None: # Falha no processamento
        print(f"[Pipeline] Falha ao processar o documento: {nome_arquivo_original}")
        if gui_progress_callback:
            gui_progress_callback(f"Falha ao processar '{nome_arquivo_original}'.", -1)
        return False
    
    if not chunks_info_list: # Nenhum chunk extraído
        print(f"[Pipeline] Nenhum texto extraído para indexação do documento: {nome_arquivo_original}")
        if gui_progress_callback:
            gui_progress_callback(f"Nenhum texto em '{nome_arquivo_original}'.", 1.0)
        return True 

    if gui_progress_callback:
        gui_progress_callback("Documento processado, preparando embeddings...", 0.60)

    textos_dos_chunks = [chunk_data['texto_chunk'] for chunk_data in chunks_info_list]
    metadados_originais_dos_chunks = [chunk_data['metadados_chunk'] for chunk_data in chunks_info_list]

    # --- Estágio 2: Geração de Embeddings (60% -> 90%) ---
    if gui_progress_callback:
        gui_progress_callback(f"Gerando embeddings para {len(textos_dos_chunks)} chunks...", 0.65)
    
    embeddings = embedding_manager.gerar_embeddings(textos_dos_chunks)
    
    if not embeddings or len(embeddings) != len(textos_dos_chunks):
        print(f"[Pipeline] Falha ao gerar embeddings para '{nome_arquivo_original}'.")
        if gui_progress_callback:
            gui_progress_callback(f"Falha nos embeddings de '{nome_arquivo_original}'.", -1)
        return False
    if gui_progress_callback:
        gui_progress_callback("Embeddings gerados, adicionando ao banco...", 0.90)

    # --- Estágio 3: Adição ao Banco de Dados (90% -> 100%) ---
    # Usar o nome_arquivo_original para criar um ID de documento mais estável para deleção.
    # O UUID garante unicidade se o mesmo nome de arquivo for indexado múltiplas vezes (embora a UI deva prevenir isso).
    doc_id_db = f"docid_{nome_arquivo_original}_{uuid.uuid4().hex[:6]}" 
    
    ids_para_db = []
    metadados_para_db = []

    for i, meta_chunk_original in enumerate(metadados_originais_dos_chunks):
        chunk_db_id = f"{doc_id_db}_chunk_{i}" 
        ids_para_db.append(chunk_db_id)
        
        meta_db_final = meta_chunk_original.copy()
        meta_db_final['doc_id_original_db'] = doc_id_db # ID do documento no DB
        # 'nome_arquivo_original' já deve estar em meta_chunk_original
        metadados_para_db.append(meta_db_final)

    sucesso_adicao = vector_db.add_chunks_to_collection(
        collection=db_collection,
        chunk_texts=textos_dos_chunks,
        embeddings=embeddings,
        metadatas=metadados_para_db,
        chunk_ids=ids_para_db
    )

    if sucesso_adicao:
        print(f"[Pipeline] Documento '{nome_arquivo_original}' indexado com ID: {doc_id_db}")
        if gui_progress_callback:
            gui_progress_callback(f"'{nome_arquivo_original}' indexado!", 1.0)
    else:
        print(f"[Pipeline] Falha ao adicionar chunks de '{nome_arquivo_original}' ao DB.")
        if gui_progress_callback:
            gui_progress_callback(f"Falha ao salvar no DB '{nome_arquivo_original}'.", -1)
    
    return sucesso_adicao


def pesquisar_e_responder(pergunta_usuario: str) -> Optional[Dict[str, Any]]:
    if not db_collection:
        print("Erro [Pipeline]: A coleção do ChromaDB não está inicializada.")
        return None
    if not pergunta_usuario.strip():
        print("[Pipeline] Pergunta do usuário está vazia.")
        return {"resposta": "Por favor, faça uma pergunta.", "fontes": []}

    print(f"\n[Pipeline] Processando pergunta: '{pergunta_usuario}'")

    embedding_pergunta = embedding_manager.gerar_embeddings([pergunta_usuario])
    if not embedding_pergunta or not embedding_pergunta[0]:
        print("[Pipeline] Falha ao gerar embedding para a pergunta.")
        return None

    chunks_similares = vector_db.find_similar_chunks(
        collection=db_collection,
        query_embedding=embedding_pergunta[0],
        top_k=TOP_K_RESULTS 
    )

    if not chunks_similares:
        print("[Pipeline] Nenhum chunk similar encontrado.")
        return {"resposta": "Desculpe, não encontrei informações relevantes nos documentos para responder à sua pergunta.", "fontes": []}

    print(f"[Pipeline] Encontrados {len(chunks_similares)} chunks relevantes.")
    # Log dos chunks pode ser removido ou reduzido para produção
    # for i, chunk_info in enumerate(chunks_similares):
    #     print(f"  Chunk {i+1} (ID: {chunk_info['id_chunk']}, Dist: {chunk_info['distancia']:.4f}):")
    #     print(f"    Fonte: {chunk_info['metadatos'].get('nome_arquivo_original', 'N/A')}")

    contexto_para_llm = "\n\n---\n\n".join(
        [f"Fonte: {ch['metadatos'].get('nome_arquivo_original', 'N/A')}, "
         f"Seção/Página: {ch['metadatos'].get('id_pagina_ou_secao_original', 'N/A')} "
         f"(Título Seção/Página: {ch['metadatos'].get('titulo_pagina_ou_secao_original', 'N/A')})\n"
         f"Conteúdo: {ch['texto_chunk']}" 
         for ch in chunks_similares]
    )
    
    resposta_llm = llm_handler.gerar_resposta_com_contexto(pergunta_usuario, contexto_para_llm)

    if resposta_llm is None: 
        resposta_llm = "Ocorreu um erro crítico ao tentar gerar a resposta com o LLM."

    fontes_formatadas = []
    for ch_info in chunks_similares:
        meta = ch_info['metadatos']
        fontes_formatadas.append({
            "nome_arquivo": meta.get('nome_arquivo_original', 'N/A'),
            "pagina_ou_secao": meta.get('id_pagina_ou_secao_original', 'N/A'),
            "titulo_secao": meta.get('titulo_pagina_ou_secao_original', 'N/A'),
            "titulo_documento": meta.get('titulo_documento', 'N/A'),
            "autor_documento": meta.get('autor_documento', 'N/A'),
            "texto_chunk_relevante": ch_info['texto_chunk'][:250] + "..." 
        })

    return {
        "resposta": resposta_llm,
        "fontes": fontes_formatadas,
        "contexto_bruto_enviado_llm": contexto_para_llm # Para depuração
    }
