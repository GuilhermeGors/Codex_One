# codex_one/nucleo_rag/gerenciador_embeddings.py

from sentence_transformers import SentenceTransformer
from typing import List, Optional, Union
import numpy as np

# Importar configurações do projeto
from config import SENTENCE_TRANSFORMER_MODEL

# Variável global para o modelo, para evitar recarregá-lo a cada chamada
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
            # Você pode especificar o dispositivo (device='cuda' ou device='cpu') se necessário.
            # Por padrão, ele tentará usar a GPU se disponível.
            _model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
            print(f"Modelo de embedding '{SENTENCE_TRANSFORMER_MODEL}' carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar o modelo de embedding '{SENTENCE_TRANSFORMER_MODEL}': {e}")
            _model = None
    return _model

def gerar_embeddings(
    textos: List[str],
    batch_size: int = 32 # Processar em lotes para eficiência com muitos textos
) -> Optional[List[List[float]]]:
    """
    Gera embeddings para uma lista de textos usando o modelo carregado.

    Args:
        textos (List[str]): Uma lista de strings (chunks de texto).
        batch_size (int): O tamanho do lote para processamento de embeddings.

    Returns:
        Optional[List[List[float]]]: Uma lista de embeddings, onde cada embedding é uma
                                     lista de floats. Retorna None se o modelo não
                                     estiver carregado ou ocorrer um erro.
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
        # O método encode retorna um numpy array ou uma lista de numpy arrays.
        # Convertemos para lista de listas de floats para consistência.
        embeddings_np: Union[np.ndarray, List[np.ndarray]] = modelo.encode(
            textos,
            batch_size=batch_size,
            show_progress_bar=True # Mostra uma barra de progresso para listas longas
        )
        
        # Converter para lista de listas de floats padrão
        embeddings_list: List[List[float]] = [emb.tolist() for emb in embeddings_np]
        
        print(f"Embeddings gerados com sucesso. Dimensão do embedding: {len(embeddings_list[0]) if embeddings_list else 'N/A'}")
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
        # A dimensão pode ser obtida de um embedding de teste ou de uma propriedade do modelo
        try:
            return modelo.get_sentence_embedding_dimension()
        except Exception as e:
            print(f"Erro ao obter a dimensão do embedding: {e}")
            # Fallback: gerar um embedding de teste
            try:
                test_embedding = modelo.encode(["teste"])
                return len(test_embedding[0])
            except Exception as e2:
                print(f"Erro ao gerar embedding de teste para obter dimensão: {e2}")
                return None
    return None


# --- Bloco de Teste ---
if __name__ == '__main__':
    print("Testando módulo gerenciador_embeddings.py...")

    # Importar config para garantir que os diretórios existam (se necessário para o modelo)
    from config import ensure_directories_exist
    ensure_directories_exist()

    # Teste de carregar modelo e obter dimensão
    print("\n--- Teste de Carregar Modelo e Obter Dimensão ---")
    dimensao = obter_dimensao_embedding()
    if dimensao:
        print(f"Dimensão do embedding do modelo '{SENTENCE_TRANSFORMER_MODEL}': {dimensao}")
        assert isinstance(dimensao, int) and dimensao > 0
    else:
        print(f"Não foi possível obter a dimensão do embedding para '{SENTENCE_TRANSFORMER_MODEL}'.")

    # Teste de gerar embeddings
    print("\n--- Teste de Gerar Embeddings ---")
    textos_para_teste = [
        "Olá, mundo!",
        "Como vai você hoje?",
        "Inteligência artificial é fascinante.",
        "Python é uma linguagem de programação versátil."
    ]
    embeddings_gerados = gerar_embeddings(textos_para_teste)

    if embeddings_gerados:
        print(f"Número de embeddings gerados: {len(embeddings_gerados)}")
        assert len(embeddings_gerados) == len(textos_para_teste)
        if dimensao: # Se a dimensão foi obtida com sucesso antes
             assert all(len(emb) == dimensao for emb in embeddings_gerados)
        print("Primeiro embedding (primeiros 5 valores):", embeddings_gerados[0][:5] if embeddings_gerados[0] else "N/A")
    else:
        print("Falha ao gerar embeddings para os textos de teste.")

    # Teste com lista vazia
    print("\n--- Teste com Lista Vazia ---")
    embeddings_vazios = gerar_embeddings([])
    if embeddings_vazios is not None: # Deve retornar lista vazia, não None
        print(f"Embeddings para lista vazia: {embeddings_vazios}")
        assert len(embeddings_vazios) == 0
    else:
        print("Falha no teste com lista vazia (retornou None inesperadamente).")
        
    print("\nTestes do gerenciador_embeddings.py concluídos.")

