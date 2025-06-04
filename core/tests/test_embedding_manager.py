# codex_one/core/tests/test_embedding_manager.py

import unittest
import sys
import os

# Adicionar a raiz do projeto ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core import embedding_manager # Importa o módulo a ser testado
from config import SENTENCE_TRANSFORMER_MODEL # Para referência no teste

class TestEmbeddingManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Carrega o modelo uma vez para todos os testes desta classe."""
        print("Configurando TestEmbeddingManager: Carregando modelo de embedding...")
        cls.model = embedding_manager.carregar_modelo_embedding()
        if not cls.model:
            raise unittest.SkipTest(f"Não foi possível carregar o modelo de embedding {SENTENCE_TRANSFORMER_MODEL}. Pulando testes.")

    def test_01_carregar_modelo_e_obter_dimensao(self):
        print("\nExecutando test_01_carregar_modelo_e_obter_dimensao...")
        dimensao = embedding_manager.obter_dimensao_embedding()
        self.assertIsNotNone(dimensao, "A dimensão do embedding não deveria ser None.")
        self.assertIsInstance(dimensao, int, "A dimensão do embedding deveria ser um inteiro.")
        self.assertTrue(dimensao > 0, "A dimensão do embedding deveria ser maior que zero.")
        print(f"Dimensão obtida: {dimensao}")

    def test_02_gerar_embeddings_sucesso(self):
        print("\nExecutando test_02_gerar_embeddings_sucesso...")
        textos_para_teste = [
            "Olá, mundo!",
            "Como vai você hoje?",
            "Inteligência artificial é fascinante."
        ]
        embeddings_gerados = embedding_manager.gerar_embeddings(textos_para_teste)
        self.assertIsNotNone(embeddings_gerados, "A geração de embeddings não deveria retornar None.")
        self.assertEqual(len(embeddings_gerados), len(textos_para_teste), "Número incorreto de embeddings gerados.")
        
        dimensao_esperada = embedding_manager.obter_dimensao_embedding()
        if dimensao_esperada: # Só verifica a dimensão se conseguimos obtê-la
            for emb in embeddings_gerados:
                self.assertIsInstance(emb, list, "Cada embedding deveria ser uma lista.")
                self.assertEqual(len(emb), dimensao_esperada, f"Dimensão incorreta do embedding. Esperado {dimensao_esperada}, obtido {len(emb)}.")
        print(f"Gerados {len(embeddings_gerados)} embeddings.")

    def test_03_gerar_embeddings_lista_vazia(self):
        print("\nExecutando test_03_gerar_embeddings_lista_vazia...")
        embeddings_vazios = embedding_manager.gerar_embeddings([])
        self.assertIsNotNone(embeddings_vazios, "Geração para lista vazia não deveria ser None.")
        self.assertEqual(len(embeddings_vazios), 0, "Deveria retornar uma lista vazia para entrada vazia.")
        print("Teste com lista vazia passou.")

    def test_04_modelo_ja_carregado(self):
        print("\nExecutando test_04_modelo_ja_carregado...")
        # A primeira chamada em setUpClass já carregou o modelo.
        # Esta chamada deve usar o modelo em cache.
        model_instance1 = embedding_manager.carregar_modelo_embedding()
        model_instance2 = embedding_manager.carregar_modelo_embedding()
        self.assertIs(model_instance1, model_instance2, "Deveria retornar a mesma instância do modelo em cache.")
        self.assertIsNotNone(model_instance1, "Modelo não deveria ser None após carregamento.")
        print("Teste de modelo em cache passou.")

if __name__ == '__main__':
    unittest.main()
