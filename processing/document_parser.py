# codex_one/processing/document_parser.py

import os
from typing import List, Dict, Optional, Any, Callable

# Importar processadores específicos e utilitários de texto
from .pdf_processor import extrair_conteudo_pdf
from .epub_processor import extrair_conteudo_epub
from .text_splitter import dividir_texto_em_chunks

def _determinar_tipo_arquivo(caminho_arquivo: str) -> Optional[str]:
    """Determina o tipo do arquivo pela extensão."""
    _, ext = os.path.splitext(caminho_arquivo)
    return ext.lower().strip('.')

def processar_documento_ficheiro(
    caminho_arquivo: str,
    progress_callback_gui: Optional[Callable[[int, int], None]] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Processa um arquivo (PDF ou ePub): extrai conteúdo, metadados e divide em chunks.
    Retorna uma lista de chunks, cada um sendo um dicionário com 'texto_chunk' e 'metadados_chunk'.
    """
    nome_base_arquivo = os.path.basename(caminho_arquivo)
    tipo_arquivo = _determinar_tipo_arquivo(caminho_arquivo)

    print(f"Iniciando processamento do documento: {nome_base_arquivo} (Tipo: {tipo_arquivo})")

    extrator_func = None
    if tipo_arquivo == 'pdf':
        extrator_func = extrair_conteudo_pdf
    elif tipo_arquivo == 'epub':
        extrator_func = extrair_conteudo_epub
    else:
        print(f"Tipo de arquivo não suportado: {tipo_arquivo} para {nome_base_arquivo}")
        return None

    resultado_extracao = extrator_func(caminho_arquivo, page_progress_callback=progress_callback_gui)
    
    if not resultado_extracao:
        print(f"Falha na extração de conteúdo para {nome_base_arquivo}.")
        return None
    
    conteudos_extraidos, metadados_doc_comuns = resultado_extracao
    todos_os_chunks_finais = []

    print(f"  Título: {metadados_doc_comuns.get('titulo_documento', 'N/A')}, Autor: {metadados_doc_comuns.get('autor_documento', 'N/A')}")

    for item_conteudo in conteudos_extraidos:
        texto_item = item_conteudo["texto_conteudo"]
        # 'numero_pagina_ou_secao' e 'titulo_secao' vêm de cada processador específico
        id_item_no_doc = item_conteudo["numero_pagina_ou_secao"] 
        titulo_item_no_doc = item_conteudo["titulo_secao"]

        if not texto_item.strip():
            continue # Pula páginas/seções vazias

        # Metadados base que serão passados para a função de chunking
        # e depois enriquecidos por ela.
        metadados_base_para_chunking = {
            "nome_arquivo_original": nome_base_arquivo,
            "caminho_completo_original": caminho_arquivo, # Pode ser útil para referências futuras
            "id_pagina_ou_secao_original": id_item_no_doc,
            "titulo_pagina_ou_secao_original": titulo_item_no_doc,
            # Metadados do documento inteiro
            "titulo_documento": metadados_doc_comuns.get("titulo_documento", ""),
            "autor_documento": metadados_doc_comuns.get("autor_documento", "")
            # Outros metadados do documento podem ser adicionados aqui se necessário
        }
        
        chunks_gerados_do_item = dividir_texto_em_chunks(
            texto_item,
            metadados_base_chunk=metadados_base_para_chunking
        )
        todos_os_chunks_finais.extend(chunks_gerados_do_item)
    
    if not todos_os_chunks_finais:
        print(f"Nenhum chunk de texto pôde ser gerado do documento: {nome_base_arquivo}")
        return []

    print(f"Total de {len(todos_os_chunks_finais)} chunks gerados para o documento: {nome_base_arquivo}")
    return todos_os_chunks_finais
