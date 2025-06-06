# codex_one/processing/epub_processor.py

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import os
from typing import List, Dict, Tuple, Optional, Any, Callable

def extrair_conteudo_epub(
    caminho_arquivo: str,
    page_progress_callback: Optional[Callable[[int, int], None]] = None
) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
    try:
        livro = epub.read_epub(caminho_arquivo)
    except Exception as e:
        print(f"Erro ao abrir o ePub '{caminho_arquivo}': {e}")
        return None

    conteudo_por_secao = []
    
    spine_items_meta = livro.spine
    
    items_de_conteudo_processaveis = []
    for item_id, _ in spine_items_meta:
        item = livro.get_item_with_id(item_id)
        if item and item.get_type() == ebooklib.ITEM_DOCUMENT and item.get_name() != 'nav.xhtml': # Excluir nav.xhtml
            items_de_conteudo_processaveis.append(item)
    
    if not items_de_conteudo_processaveis:
        items_de_conteudo_processaveis = [
            item for item in livro.get_items() 
            if item.get_type() == ebooklib.ITEM_DOCUMENT and item.get_name() != 'nav.xhtml'
        ]

    total_secoes_reais = len(items_de_conteudo_processaveis)
    
    for i, item in enumerate(items_de_conteudo_processaveis):
        try:
            html_content = item.get_content()
            try:
                decoded_content = html_content.decode('utf-8')
            except UnicodeDecodeError:
                decoded_content = html_content.decode('utf-8', errors='ignore')

            soup = BeautifulSoup(decoded_content, 'html.parser')
            
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
            
            texto_secao = soup.get_text(separator='\n', strip=True)
            
            titulo_secao_item = ""
            item_href = item.get_name()
            for toc_item in livro.toc:
                if isinstance(toc_item, epub.Link) and toc_item.href.split('#')[0] == item_href:
                    titulo_secao_item = toc_item.title
                    break
                elif isinstance(toc_item, tuple): # Para TOCs aninhadas
                    for sub_toc_item in toc_item[1]:
                         if isinstance(sub_toc_item, epub.Link) and sub_toc_item.href.split('#')[0] == item_href:
                            titulo_secao_item = sub_toc_item.title
                            break
                    if titulo_secao_item: break
            
            if not titulo_secao_item and soup.title and soup.title.string:
                titulo_secao_item = soup.title.string.strip()
            elif not titulo_secao_item and soup.h1 and soup.h1.string:
                titulo_secao_item = soup.h1.string.strip()
            
            if not titulo_secao_item: # Fallback final
                base_name, _ = os.path.splitext(item.get_name() if item.get_name() else f"secao_desconhecida_{i+1}")
                titulo_secao_item = base_name.replace('_', ' ').replace('-', ' ').title()


            conteudo_por_secao.append({
                "numero_pagina_ou_secao": i + 1,
                "titulo_secao": titulo_secao_item,
                "texto_conteudo": texto_secao
            })
            if page_progress_callback:
                page_progress_callback(i + 1, total_secoes_reais)
        except AttributeError as ae: # Capturar AttributeError específico
            item_name_for_log = "Item Desconhecido (erro ao obter nome/id)"
            if item and hasattr(item, 'get_name') and item.get_name(): item_name_for_log = item.get_name()
            elif item and hasattr(item, 'id'): item_name_for_log = f"item_id_{item.id}"
            print(f"AttributeError ao processar item '{item_name_for_log}' no ePub '{os.path.basename(caminho_arquivo)}': {ae}")
            continue
        except Exception as e_item:
            item_name_for_log = "Item Desconhecido (erro ao obter nome/id)"
            if item and hasattr(item, 'get_name') and item.get_name(): item_name_for_log = item.get_name()
            elif item and hasattr(item, 'id'): item_name_for_log = f"item_id_{item.id}"
            print(f"Erro geral ao processar item '{item_name_for_log}' no ePub '{os.path.basename(caminho_arquivo)}': {e_item}")
            continue

    titulo_doc = "Título Desconhecido"
    dc_title_list = livro.get_metadata('DC', 'title')
    if dc_title_list and dc_title_list[0]:
        titulo_doc = dc_title_list[0][0] if isinstance(dc_title_list[0], tuple) else dc_title_list[0]

    autor_doc = "Autor Desconhecido"
    dc_creator_list = livro.get_metadata('DC', 'creator')
    if dc_creator_list and dc_creator_list[0]:
        autor_doc = dc_creator_list[0][0] if isinstance(dc_creator_list[0], tuple) else dc_creator_list[0]
        
    metadados_comuns = {
        "titulo_documento": titulo_doc,
        "autor_documento": autor_doc,
        "total_paginas_ou_secoes": total_secoes_reais 
    }
    
    print(f"Texto extraído de {metadados_comuns['total_paginas_ou_secoes']} seções do ePub: {os.path.basename(caminho_arquivo)}")
    return conteudo_por_secao, metadados_comuns
