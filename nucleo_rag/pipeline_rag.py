# codex_one/nucleo_rag/pipeline_rag.py

import os
import uuid
from typing import List, Dict, Optional, Any, Callable # Callable adicionado

from config import TOP_K_RESULTS, CHROMA_COLLECTION_NAME 
from . import processador_documentos
from . import gerenciador_embeddings
from . import banco_vetorial_chroma
from . import manipulador_llm 

db_collection = banco_vetorial_chroma.initialize_vector_db()

def indexar_documento_pdf(
    caminho_arquivo_pdf_completo: str,
    nome_arquivo_original: str,
    gui_progress_callback: Optional[Callable[[str, float], None]] = None # <--- VERIFIQUE ESTE TERCEIRO ARGUMENTO
) -> bool:
    """
    Processa um arquivo PDF, gera embeddings para seus chunks e os armazena no ChromaDB.
    Chama gui_progress_callback para atualizar a GUI sobre o progresso.
    """
    if not db_collection:
        print("Erro: A coleção do ChromaDB não está inicializada. Não é possível indexar.")
        if gui_progress_callback:
            gui_progress_callback("Erro: DB não inicializado.", -1) # -1 para indicar erro
        return False

    print(f"Iniciando indexação para: {nome_arquivo_original} (caminho: {caminho_arquivo_pdf_completo})")
    if gui_progress_callback:
        gui_progress_callback(f"Iniciando indexação de '{nome_arquivo_original}'...", 0.0)

    # --- Estágio 1: Processamento do PDF (0% -> 60% do progresso total) ---
    def _page_proc_callback_adapter(pagina_atual: int, total_paginas: int):
        if gui_progress_callback:
            progresso_pdf = (pagina_atual / total_paginas) * 0.60 # PDF processing é 60% do total
            gui_progress_callback(f"Processando PDF: página {pagina_atual}/{total_paginas}", progresso_pdf)

    chunks_info = processador_documentos.processar_documento_pdf(
        caminho_arquivo_pdf_completo, 
        page_progress_callback=_page_proc_callback_adapter
    )
    
    if not chunks_info:
        print(f"Falha ao processar o documento PDF: {nome_arquivo_original}")
        if gui_progress_callback:
            gui_progress_callback(f"Falha ao processar PDF '{nome_arquivo_original}'.", -1)
        return False
    if gui_progress_callback:
        gui_progress_callback("PDF processado, preparando embeddings...", 0.60)


    textos_dos_chunks = [chunk['texto_chunk'] for chunk in chunks_info]
    metadados_dos_chunks_originais = [chunk['metadados_chunk'] for chunk in chunks_info]

    if not textos_dos_chunks:
        print(f"Nenhum texto extraído para indexação do documento: {nome_arquivo_original}")
        if gui_progress_callback:
            gui_progress_callback(f"Nenhum texto em '{nome_arquivo_original}'.", 1.0) # Concluído, mas nada a fazer
        return True 

    # --- Estágio 2: Geração de Embeddings (60% -> 90% do progresso total) ---
    if gui_progress_callback:
        gui_progress_callback(f"Gerando embeddings para {len(textos_dos_chunks)} chunks...", 0.65)
    
    embeddings = gerenciador_embeddings.gerar_embeddings(textos_dos_chunks) # show_progress_bar=True no console
    
    if not embeddings or len(embeddings) != len(textos_dos_chunks):
        print(f"Falha ao gerar embeddings para os chunks do documento: {nome_arquivo_original}")
        if gui_progress_callback:
            gui_progress_callback(f"Falha nos embeddings de '{nome_arquivo_original}'.", -1)
        return False
    if gui_progress_callback:
        gui_progress_callback("Embeddings gerados, adicionando ao banco...", 0.90)

    # --- Estágio 3: Adição ao Banco de Dados (90% -> 100% do progresso total) ---
    doc_id_original_para_db = f"docid_{nome_arquivo_original}_{uuid.uuid4().hex[:8]}" 
    ids_para_db = []
    metadados_para_db = []

    for i, meta_original in enumerate(metadados_dos_chunks_originais):
        chunk_db_id = f"{doc_id_original_para_db}_chunk_{i}" 
        ids_para_db.append(chunk_db_id)
        
        meta_db_chunk = meta_original.copy()
        meta_db_chunk['doc_id_original'] = doc_id_original_para_db 
        meta_db_chunk['id_chunk_db'] = chunk_db_id 
        metadados_para_db.append(meta_db_chunk)

    sucesso_adicao = banco_vetorial_chroma.add_chunks_to_collection(
        collection=db_collection,
        chunk_texts=textos_dos_chunks,
        embeddings=embeddings,
        metadatas=metadados_para_db,
        chunk_ids=ids_para_db
    )

    if sucesso_adicao:
        print(f"Documento '{nome_arquivo_original}' indexado com sucesso com ID de documento: {doc_id_original_para_db}")
        if gui_progress_callback:
            gui_progress_callback(f"'{nome_arquivo_original}' indexado com sucesso!", 1.0)
    else:
        print(f"Falha ao adicionar chunks do documento '{nome_arquivo_original}' ao ChromaDB.")
        if gui_progress_callback:
            gui_progress_callback(f"Falha ao salvar no DB '{nome_arquivo_original}'.", -1)
    
    return sucesso_adicao

# ... (o resto do arquivo pipeline_rag.py, incluindo pesquisar_e_responder e o bloco de teste, permanece o mesmo) ...
# Apenas o bloco de teste precisará de um callback dummy se quisermos testar a nova assinatura.

def pesquisar_e_responder(pergunta_usuario: str) -> Optional[Dict[str, Any]]:
    if not db_collection:
        print("Erro: A coleção do ChromaDB não está inicializada. Não é possível pesquisar.")
        return None
    if not pergunta_usuario.strip():
        print("Pergunta do usuário está vazia.")
        return {"resposta": "Por favor, faça uma pergunta.", "fontes": []}

    print(f"\nProcessando pergunta: '{pergunta_usuario}'")

    embedding_pergunta = gerenciador_embeddings.gerar_embeddings([pergunta_usuario])
    if not embedding_pergunta or not embedding_pergunta[0]:
        print("Falha ao gerar embedding para a pergunta.")
        return None

    chunks_similares = banco_vetorial_chroma.find_similar_chunks(
        collection=db_collection,
        query_embedding=embedding_pergunta[0],
        top_k=TOP_K_RESULTS 
    )

    if not chunks_similares:
        print("Nenhum chunk similar encontrado para a pergunta.")
        return {"resposta": "Desculpe, não encontrei informações relevantes nos documentos para responder à sua pergunta.", "fontes": []}

    print(f"Encontrados {len(chunks_similares)} chunks relevantes:")
    for i, chunk_info in enumerate(chunks_similares):
        print(f"  Chunk {i+1} (ID: {chunk_info['id_chunk']}, Dist: {chunk_info['distancia']:.4f}):")
        print(f"    Fonte: {chunk_info['metadatos'].get('nome_arquivo_original', 'N/A')}, "
              f"Pág: {chunk_info['metadatos'].get('numero_pagina', 'N/A')}")
        print(f"    Texto: '{chunk_info['texto_chunk'][:100]}...'")

    contexto_para_llm = "\n\n---\n\n".join(
        [f"Fonte: {ch['metadatos'].get('nome_arquivo_original', 'N/A')}, "
         f"Página: {ch['metadatos'].get('numero_pagina', 'N/A')}\n"
         f"Conteúdo: {ch['texto_chunk']}" 
         for ch in chunks_similares]
    )
    
    print("\nEnviando para o LLM...")
    resposta_llm = manipulador_llm.gerar_resposta_com_contexto(pergunta_usuario, contexto_para_llm)

    if resposta_llm is None: 
        resposta_llm = "Ocorreu um erro crítico ao tentar gerar a resposta com o modelo de linguagem."

    fontes_formatadas = []
    for ch_info in chunks_similares:
        meta = ch_info['metadatos']
        fontes_formatadas.append({
            "nome_arquivo": meta.get('nome_arquivo_original', 'N/A'),
            "pagina": meta.get('numero_pagina', 'N/A'),
            "titulo_documento": meta.get('titulo_documento', 'N/A'),
            "autor_documento": meta.get('autor_documento', 'N/A'),
            "texto_chunk_relevante": ch_info['texto_chunk'][:200] + "..." 
        })

    return {
        "resposta": resposta_llm,
        "fontes": fontes_formatadas,
        "contexto_bruto_enviado_llm": contexto_para_llm 
    }


# --- Bloco de Teste ---
if __name__ == '__main__':
    print("Testando módulo pipeline_rag.py...")

    from config import ensure_directories_exist, DOCUMENTS_DIR
    from nucleo_rag import gerenciador_arquivos 
    import fitz 

    ensure_directories_exist()
    gerenciador_arquivos.ensure_documents_directory_exists()

    pdf_teste_nome_pipeline = "documento_pipeline_teste.pdf"
    pdf_teste_caminho_pipeline = os.path.join(DOCUMENTS_DIR, pdf_teste_nome_pipeline)

    # Callback de teste para o pipeline
    def meu_callback_progresso_pipeline(mensagem: str, progresso: float):
        if progresso >= 0:
            print(f"  [Pipeline Callback Teste] {mensagem} - Progresso: {progresso*100:.2f}%")
        else:
            print(f"  [Pipeline Callback Teste] ERRO: {mensagem}")


    if not os.path.exists(pdf_teste_caminho_pipeline):
        try:
            doc_teste = fitz.open()
            # ... (criação do PDF de teste como antes) ...
            pagina_teste1 = doc_teste.new_page()
            pagina_teste1.insert_text((50, 72), "O pipeline RAG combina recuperação de informação com geração de texto.", fontsize=11)
            pagina_teste1.insert_text((50, 92), "Primeiro, documentos são indexados. Depois, partes relevantes são usadas como contexto para um LLM.", fontsize=11)
            
            pagina_teste2 = doc_teste.new_page()
            pagina_teste2.insert_text((50, 72), "Este sistema é útil para responder perguntas baseadas em um corpus específico.", fontsize=11)
            pagina_teste2.insert_text((50, 92), "O ChromaDB armazena os vetores e o Ollama pode servir o LLM.", fontsize=11)
            
            doc_teste.set_metadata({"title": "Teste de Pipeline RAG", "author": "Pipeline Tester"})
            doc_teste.save(pdf_teste_caminho_pipeline)
            doc_teste.close()
            print(f"PDF de teste '{pdf_teste_nome_pipeline}' criado para o pipeline.")
        except Exception as e:
            print(f"Erro ao criar PDF de teste para pipeline: {e}")
            pdf_teste_caminho_pipeline = None
    else:
        print(f"Usando PDF de teste existente: {pdf_teste_nome_pipeline}")

    print("\n--- Teste de Indexação do Documento com Callback ---")
    if pdf_teste_caminho_pipeline and db_collection:
        print(f"Verificando e limpando chunks antigos de '{pdf_teste_nome_pipeline}' antes de reindexar...")
        ids_para_deletar = []
        resultados_get = db_collection.get(where={"nome_arquivo_original": pdf_teste_nome_pipeline}, include=[])
        if resultados_get and resultados_get['ids']:
            ids_para_deletar = resultados_get['ids']
            if ids_para_deletar:
                db_collection.delete(ids=ids_para_deletar)
                print(f"Deletados {len(ids_para_deletar)} chunks antigos de '{pdf_teste_nome_pipeline}'.")

        # Passar o callback de teste para indexar_documento_pdf
        sucesso_index = indexar_documento_pdf(
            pdf_teste_caminho_pipeline, 
            pdf_teste_nome_pipeline,
            meu_callback_progresso_pipeline # Passando o callback
        )
        print(f"Resultado da indexação para '{pdf_teste_nome_pipeline}': {'Sucesso' if sucesso_index else 'Falha'}")
        assert sucesso_index
    # ... (restante do bloco de teste como antes) ...
    elif not db_collection:
        print("Coleção ChromaDB não inicializada, pulando teste de indexação.")
    else:
        print("PDF de teste para pipeline não disponível, pulando teste de indexação.")

    print("\n--- Teste de Pesquisa e Resposta ---")
    if db_collection: 
        pergunta_teste = "Como funciona o pipeline RAG?"
        resultado_pesquisa = pesquisar_e_responder(pergunta_teste)

        if resultado_pesquisa:
            print(f"\nResposta do Pipeline para '{pergunta_teste}':")
            print(f"  LLM: {resultado_pesquisa['resposta']}")
            print(f"  Fontes ({len(resultado_pesquisa['fontes'])}):")
            for i, fonte in enumerate(resultado_pesquisa['fontes']):
                print(f"    Fonte {i+1}: {fonte['nome_arquivo']} (Pág: {fonte['pagina']}) - Trecho: '{fonte['texto_chunk_relevante'][:50]}...'")
            
            resposta_llm_texto = resultado_pesquisa['resposta'].lower()
            is_known_error_message = "erro" in resposta_llm_texto or \
                                     "não encontrei informação" in resposta_llm_texto or \
                                     "não foi possível conectar" in resposta_llm_texto or \
                                     "not found" in resposta_llm_texto or \
                                     "ocorreu um erro crítico" in resposta_llm_texto
            
            is_meaningful_response = len(resposta_llm_texto.strip()) > 0 and not is_known_error_message

            assert is_meaningful_response or is_known_error_message, \
                f"Resposta inesperada do LLM: {resultado_pesquisa['resposta']}"

            if is_meaningful_response:
                 assert len(resultado_pesquisa['fontes']) > 0, "Resposta significativa do LLM, mas sem fontes."
        else:
            print(f"Nenhum resultado da pesquisa para '{pergunta_teste}'.")
            assert False, "Pesquisar_e_responder retornou None"
    else:
        print("Coleção ChromaDB não inicializada, pulando teste de pesquisa.")
    
    print("\nTestes do pipeline_rag.py concluídos.")
