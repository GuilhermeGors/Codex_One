# codex_one/nucleo_rag/processador_documentos.py

import fitz # PyMuPDF
import os 
from typing import List, Dict, Tuple, Optional, Any, Callable

from config import CHUNK_SIZE, CHUNK_OVERLAP 

def extrair_texto_e_metadados_pdf(
    caminho_pdf: str,
    page_progress_callback: Optional[Callable[[int, int], None]] = None # callback(pagina_atual, total_paginas)
) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
    """
    Extrai texto de cada página de um arquivo PDF e metadados básicos do documento.
    Chama page_progress_callback após processar cada página.
    """
    try:
        documento = fitz.open(caminho_pdf)
    except Exception as e:
        print(f"Erro ao abrir o PDF '{caminho_pdf}': {e}")
        return None

    paginas_texto = []
    total_paginas = len(documento)
    for num_pagina_idx in range(total_paginas):
        pagina = documento.load_page(num_pagina_idx)
        texto = pagina.get_text("text") 
        paginas_texto.append({
            "numero_pagina": num_pagina_idx + 1, 
            "texto_pagina": texto.strip()
        })
        if page_progress_callback:
            page_progress_callback(num_pagina_idx + 1, total_paginas)


    metadados_doc = {
        "total_paginas": documento.page_count,
        "titulo": documento.metadata.get("title", ""),
        "autor": documento.metadata.get("author", ""),
    }
    
    documento.close()
    print(f"Texto extraído de {metadados_doc['total_paginas']} páginas do PDF: {os.path.basename(caminho_pdf)}")
    return paginas_texto, metadados_doc

def dividir_texto_em_chunks(
    texto_completo: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    metadados_origem: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Divide um texto longo em chunks menores com alguma sobreposição.
    """
    if not texto_completo:
        return []

    chunks_com_meta = []
    inicio = 0
    id_chunk_doc = 0

    while inicio < len(texto_completo):
        fim = min(inicio + chunk_size, len(texto_completo))
        texto_chunk = texto_completo[inicio:fim]
        
        meta_chunk = {"id_chunk_no_documento": id_chunk_doc} 
        if metadados_origem:
            meta_chunk.update(metadados_origem) 

        chunks_com_meta.append({
            "texto_chunk": texto_chunk,
            "metadados_chunk": meta_chunk 
        })
        
        id_chunk_doc += 1
        inicio += (chunk_size - chunk_overlap)
        if inicio >= len(texto_completo) and fim == len(texto_completo): 
            break
        if inicio + chunk_overlap >= len(texto_completo) and fim < len(texto_completo): 
            fim = len(texto_completo)
            texto_chunk = texto_completo[inicio:fim]
            if chunks_com_meta and chunks_com_meta[-1]["metadados_chunk"]["id_chunk_no_documento"] == id_chunk_doc -1:
                 chunks_com_meta[-1]["texto_chunk"] = texto_chunk 
            else: 
                meta_chunk_final = {"id_chunk_no_documento": id_chunk_doc}
                if metadados_origem:
                    meta_chunk_final.update(metadados_origem)
                chunks_com_meta.append({
                    "texto_chunk": texto_chunk,
                    "metadados_chunk": meta_chunk_final
                })
            break
    return chunks_com_meta

def processar_documento_pdf(
    caminho_pdf: str,
    page_progress_callback: Optional[Callable[[int, int], None]] = None # Passar o callback
) -> Optional[List[Dict[str, Any]]]:
    """
    Processa um arquivo PDF: extrai texto, metadados e divide o texto em chunks.
    """
    # Passar o page_progress_callback para extrair_texto_e_metadados_pdf
    resultado_extracao = extrair_texto_e_metadados_pdf(caminho_pdf, page_progress_callback)
    if not resultado_extracao:
        return None
    
    paginas_texto, metadados_doc = resultado_extracao
    todos_os_chunks = []

    print(f"Processando documento: {os.path.basename(caminho_pdf)}")
    print(f"  Título: {metadados_doc.get('titulo', 'N/A')}, Autor: {metadados_doc.get('autor', 'N/A')}")

    # O progresso de chunking por página é mais difícil de granularizar para um callback simples,
    # o callback principal de progresso de página já foi chamado em extrair_texto_e_metadados_pdf.
    # O chunking em si é geralmente rápido por página.
    for pagina_info in paginas_texto:
        texto_da_pagina = pagina_info["texto_pagina"]
        num_pagina = pagina_info["numero_pagina"]

        if not texto_da_pagina.strip(): 
            continue

        metadados_para_chunks_pagina = {
            "nome_arquivo_original": os.path.basename(caminho_pdf), 
            "caminho_completo_original": caminho_pdf, 
            "numero_pagina": num_pagina,
            "titulo_documento": metadados_doc.get("titulo", ""),
            "autor_documento": metadados_doc.get("autor", "")
        }
        
        chunks_da_pagina = dividir_texto_em_chunks(
            texto_da_pagina,
            metadados_origem=metadados_para_chunks_pagina
        )
        todos_os_chunks.extend(chunks_da_pagina)
        # Não chamamos mais o callback aqui, pois ele é chamado por página em extrair_texto_e_metadados_pdf
        # print(f"  Página {num_pagina}: extraídos {len(chunks_da_pagina)} chunks.")


    if not todos_os_chunks:
        print(f"Nenhum chunk de texto pôde ser extraído do documento: {os.path.basename(caminho_pdf)}")
        return [] 

    print(f"Total de {len(todos_os_chunks)} chunks gerados para o documento: {os.path.basename(caminho_pdf)}")
    return todos_os_chunks


# --- Bloco de Teste ---
if __name__ == '__main__':
    print("Testando módulo processador_documentos.py...")

    from config import ensure_directories_exist, DOCUMENTS_DIR
    from nucleo_rag import gerenciador_arquivos 

    ensure_directories_exist() 
    gerenciador_arquivos.ensure_documents_directory_exists() 

    pdf_teste_nome = "documento_teste_proc.pdf"
    pdf_teste_caminho_completo = os.path.join(DOCUMENTS_DIR, pdf_teste_nome)

    # Callback de teste para progresso de página
    def meu_callback_progresso_pagina(pagina_atual, total_paginas):
        percentual = (pagina_atual / total_paginas) * 100
        print(f"  [Callback Teste] Processando página: {pagina_atual}/{total_paginas} ({percentual:.2f}%)")

    try:
        doc_teste = fitz.open() 
        pagina_teste1 = doc_teste.new_page()
        pagina_teste1.insert_text((50, 72), "Este é o conteúdo da primeira página do PDF de teste. Ele discute IA.", fontsize=12)
        pagina_teste1.insert_text((50, 92), "A inteligência artificial é um campo vasto e interessante.", fontsize=12)
        
        pagina_teste2 = doc_teste.new_page()
        pagina_teste2.insert_text((50, 72), "A segunda página foca em Python.", fontsize=12)
        pagina_teste2.insert_text((50, 92), "Python é uma linguagem popular para desenvolvimento de IA.", fontsize=12)
        
        doc_teste.set_metadata({"title": "PDF de Teste para Processamento", "author": "Testador Mestre"})
        doc_teste.save(pdf_teste_caminho_completo)
        doc_teste.close()
        print(f"PDF de teste '{pdf_teste_nome}' criado em: {pdf_teste_caminho_completo}")

        print("\n--- Teste de Processamento de Documento PDF com Callback ---")
        # Passar o callback de teste
        chunks_processados = processar_documento_pdf(pdf_teste_caminho_completo, meu_callback_progresso_pagina)

        if chunks_processados:
            print(f"\nTotal de chunks processados do PDF de teste: {len(chunks_processados)}")
            # ... (restante do bloco de teste como antes) ...
        else:
            print("Nenhum chunk foi processado do PDF de teste.")

    except Exception as e:
        print(f"Erro durante o teste do processador_documentos: {e}")
    finally:
        if os.path.exists(pdf_teste_caminho_completo):
            try:
                os.remove(pdf_teste_caminho_completo)
                print(f"PDF de teste '{pdf_teste_nome}' removido.")
            except OSError as e:
                print(f"Erro ao remover PDF de teste: {e}")
    
    print("\nTestes do processador_documentos.py concluídos.")
