# codex_one/core/embedding_manager.py

from sentence_transformers import SentenceTransformer
from typing import List, Optional, Union
import numpy as np
from config import SENTENCE_TRANSFORMER_MODEL

_model: Optional[SentenceTransformer] = None

def carregar_modelo_embedding() -> Optional[SentenceTransformer]:
    """
    Carrega o modelo SentenceTransformer especificado em config.py.
    Retorna a instância do modelo ou None se ocorrer um erro.
    """
    global _model
    if _model is None:
        try:
            print(f"Carregando modelo de embedding: {SENTENCE_TRANSFORMER_MODEL}...")
            _model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
            print(f"Modelo de embedding '{SENTENCE_TRANSFORMER_MODEL}' carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar o modelo de embedding '{SENTENCE_TRANSFORMER_MODEL}': {e}")
            _model = None
    return _model

def gerar_embeddings(
    textos: List[str],
    batch_size: int = 32 
) -> Optional[List[List[float]]]:
    """
    Gera embeddings para uma lista de textos usando o modelo carregado.
    """
    modelo = carregar_modelo_embedding()
    if not modelo:
        print("Modelo de embedding não está carregado. Não é possível gerar embeddings.")
        return None
    if not textos:
        print("Nenhum texto fornecido para gerar embeddings.")
        return []

    try:
        print(f"Gerando embeddings para {len(textos)} textos (batch_size={batch_size})...")
        embeddings_np: Union[np.ndarray, List[np.ndarray]] = modelo.encode(
            textos,
            batch_size=batch_size,
            show_progress_bar=False # Desabilitar barra de progresso para logs mais limpos em produção/pipeline
        )
        
        embeddings_list: List[List[float]] = [emb.tolist() for emb in embeddings_np]
        
        print(f"Embeddings gerados com sucesso. Dimensão: {len(embeddings_list[0]) if embeddings_list else 'N/A'}")
        return embeddings_list
    except Exception as e:
        print(f"Erro ao gerar embeddings: {e}")
        return None

def obter_dimensao_embedding() -> Optional[int]:
    """
    Retorna a dimensão dos embeddings gerados pelo modelo carregado.
    """
    modelo = carregar_modelo_embedding()
    if modelo:
        try:
            return modelo.get_sentence_embedding_dimension()
        except Exception as e:
            print(f"Erro ao obter a dimensão do embedding via get_sentence_embedding_dimension: {e}")
            try:
                test_embedding = modelo.encode(["teste_dimensao"])
                return len(test_embedding[0]) if isinstance(test_embedding, list) and test_embedding else None
            except Exception as e2:
                print(f"Erro ao gerar embedding de teste para obter dimensão: {e2}")
                return None
    return None
