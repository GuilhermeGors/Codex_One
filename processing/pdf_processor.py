# codex_one/processing/pdf_processor.py

import fitz
import os
from typing import List, Dict, Tuple, Optional, Any, Callable

def extrair_conteudo_pdf(
    caminho_arquivo: str,
    page_progress_callback: Optional[Callable[[int, int], None]] = None
) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
    """
    Extrai texto de cada página de um arquivo PDF e metadados básicos do documento.
    Chama page_progress_callback após processar cada página.

    Retorna:
        Uma tupla contendo:
        - Lista de dicionários de conteúdo por página:
          {'numero_pagina_ou_secao': int, 'titulo_secao': str, 'texto_conteudo': str}
        - Dicionário de metadados comuns do documento:
          {'titulo_documento': str, 'autor_documento': str, 'total_paginas_ou_secoes': int}
    """
    try:
        documento = fitz.open(caminho_arquivo)
    except Exception as e:
        print(f"Erro ao abrir o PDF '{caminho_arquivo}': {e}")
        return None

    conteudo_por_pagina = []
    total_paginas = len(documento)
    for num_pagina_idx in range(total_paginas):
        pagina = documento.load_page(num_pagina_idx)
        texto = pagina.get_text("text")
        conteudo_por_pagina.append({
            "numero_pagina_ou_secao": num_pagina_idx + 1,
            "titulo_secao": f"Página {num_pagina_idx + 1}",
            "texto_conteudo": texto.strip()
        })
        if page_progress_callback:
            page_progress_callback(num_pagina_idx + 1, total_paginas)
    
    meta_pdf_bruto = {
        "title": documento.metadata.get("title", ""),
        "author": documento.metadata.get("author", ""),
        "total_paginas_ou_secoes": documento.page_count
    }
    documento.close()
    
    # Normalizar metadados
    metadados_comuns = {
        "titulo_documento": meta_pdf_bruto.get("title", "Título Desconhecido"),
        "autor_documento": meta_pdf_bruto.get("author", "Autor Desconhecido"),
        "total_paginas_ou_secoes": meta_pdf_bruto.get("total_paginas_ou_secoes", 0)
    }
    
    print(f"Texto extraído de {metadados_comuns['total_paginas_ou_secoes']} páginas do PDF: {os.path.basename(caminho_arquivo)}")
    return conteudo_por_pagina, metadados_comuns
