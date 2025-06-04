# codex_one/processing/text_splitter.py

from typing import List, Dict, Optional, Any
from config import CHUNK_SIZE, CHUNK_OVERLAP 

def dividir_texto_em_chunks(
    texto_completo: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    metadados_base_chunk: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Divide um texto longo em chunks menores com alguma sobreposição.
    Associa metadados base a cada chunk gerado.
    """
    if not texto_completo:
        return []

    chunks_com_meta = []
    inicio = 0
    id_sequencial_chunk = 0 

    while inicio < len(texto_completo):
        fim = min(inicio + chunk_size, len(texto_completo))
        texto_do_chunk = texto_completo[inicio:fim]

        meta_chunk_atual = metadados_base_chunk.copy() if metadados_base_chunk else {}
        meta_chunk_atual['id_sequencial_no_texto_origem'] = id_sequencial_chunk
        
        chunks_com_meta.append({
            "texto_chunk": texto_do_chunk,
            "metadados_chunk": meta_chunk_atual
        })

        id_sequencial_chunk += 1
        proximo_inicio = inicio + chunk_size - chunk_overlap

        if proximo_inicio <= inicio and chunk_size > 0 : 
             if chunk_overlap >= chunk_size and fim < len(texto_completo): 
                proximo_inicio = inicio + 1 
             elif fim == len(texto_completo): 
                 break
        
        inicio = proximo_inicio
        if inicio >= len(texto_completo):
            break
            
    return chunks_com_meta
