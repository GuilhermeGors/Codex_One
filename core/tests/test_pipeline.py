# codex_one/core/tests/test_pipeline.py

import unittest
from unittest.mock import patch, MagicMock, ANY
import os
import shutil
import sys
import uuid
import time 

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core import pipeline 
from config import DOCUMENTS_DIR, CHROMA_PERSIST_DIR, ensure_directories_exist, TOP_K_RESULTS
from data_access import file_system_manager # CORRIGIDO
from data_access import vector_db as pipeline_vector_db 
from processing import document_parser as pipeline_document_parser


ACTUAL_EMBEDDING_DIM_TEST = 768 
try:
    from core.embedding_manager import obter_dimensao_embedding
    dim_test = obter_dimensao_embedding() 
    if dim_test: ACTUAL_EMBEDDING_DIM_TEST = dim_test
except ImportError: 
    print(f"AVISO (test_pipeline): Módulo core.embedding_manager não encontrado. Usando dimensão {ACTUAL_EMBEDDING_DIM_TEST}.")


class TestPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n[TestPipeline] Configurando classe de teste...")
        ensure_directories_exist()
        print("[TestPipeline] Tentando limpar armazenamento persistente em setUpClass...")
        pipeline_vector_db.delete_persistent_storage() # Limpa ANTES de tudo
        
        if os.path.exists(DOCUMENTS_DIR):
            for item in os.listdir(DOCUMENTS_DIR):
                item_path = os.path.join(DOCUMENTS_DIR, item)
                if os.path.isfile(item_path) and "pipeline_test_doc" in item : 
                    try: os.remove(item_path)
                    except Exception as e: print(f"Erro ao limpar {item_path} em setUpClass: {e}")
        else:
            os.makedirs(DOCUMENTS_DIR)
        
    @classmethod
    def tearDownClass(cls):
        print("\n[TestPipeline] Limpando após todos os testes da classe...")
        pipeline_vector_db.delete_persistent_storage() # Limpa DEPOIS de tudo
        
        if os.path.exists(DOCUMENTS_DIR): 
            for item in os.listdir(DOCUMENTS_DIR):
                item_path = os.path.join(DOCUMENTS_DIR, item)
                if os.path.isfile(item_path) and "pipeline_test_doc" in item:
                    try: os.remove(item_path)
                    except Exception as e: print(f"Erro ao limpar {item_path} em tearDownClass: {e}")

    def setUp(self):
        print(f"\n[TestPipeline] Configurando teste: {self.id()}")
        # Forçar reset e recriação da coleção para cada teste para isolamento
        pipeline_vector_db.reset_db_state_for_tests() # Isto deve apagar a pasta e resetar vars globais
        
        # Forçar a reinicialização da variável db_collection DENTRO do módulo pipeline
        # e garantir que a instância do cliente também seja nova.
        pipeline.db_collection = pipeline_vector_db.initialize_vector_db(force_new_client=True)
        self.db_collection_test_instance = pipeline.db_collection 

        self.assertIsNotNone(self.db_collection_test_instance, "Falha ao reinicializar db_collection em setUp para pipeline.")
        time.sleep(0.2) 
        if self.db_collection_test_instance: 
            self.assertEqual(self.db_collection_test_instance.count(), 0, f"Coleção não está vazia no início. Count: {self.db_collection_test_instance.count()}")

        self.pdf_teste_nome = f"pipeline_test_doc_{uuid.uuid4().hex[:4]}.pdf"
        self.temp_upload_dir_pipeline = "temp_pipeline_uploads_test_temp"
        os.makedirs(self.temp_upload_dir_pipeline, exist_ok=True)
        self.pdf_teste_caminho_temporario_upload = os.path.join(self.temp_upload_dir_pipeline, self.pdf_teste_nome)
        
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "Conteúdo de teste do pipeline para PDF.")
        doc.set_metadata({"title": "Pipeline Test PDF", "author":"Test Author"})
        doc.save(self.pdf_teste_caminho_temporario_upload)
        doc.close()
        
        self.pdf_teste_caminho_salvo_em_docs = file_system_manager.save_uploaded_file(
            self.pdf_teste_caminho_temporario_upload, self.pdf_teste_nome
        )
        self.assertIsNotNone(self.pdf_teste_caminho_salvo_em_docs, "Falha ao salvar PDF de teste para pipeline.")
        self.pdf_teste_nome_salvo = os.path.basename(self.pdf_teste_caminho_salvo_em_docs)


    def tearDown(self):
        print(f"[TestPipeline] Limpando após teste: {self.id()}")
        if hasattr(self, 'pdf_teste_caminho_salvo_em_docs') and self.pdf_teste_caminho_salvo_em_docs and os.path.exists(self.pdf_teste_caminho_salvo_em_docs):
            try: os.remove(self.pdf_teste_caminho_salvo_em_docs)
            except Exception as e: print(f"Erro ao limpar {self.pdf_teste_caminho_salvo_em_docs}: {e}")
        
        if hasattr(self, 'pdf_teste_caminho_temporario_upload') and self.pdf_teste_caminho_temporario_upload and os.path.exists(self.pdf_teste_caminho_temporario_upload):
            try: os.remove(self.pdf_teste_caminho_temporario_upload)
            except Exception as e: print(f"Erro ao limpar {self.pdf_teste_caminho_temporario_upload}: {e}")

        if hasattr(self, 'temp_upload_dir_pipeline') and self.temp_upload_dir_pipeline and os.path.exists(self.temp_upload_dir_pipeline):
            shutil.rmtree(self.temp_upload_dir_pipeline, ignore_errors=True)
        
        # Forçar reset do cliente e coleção globais do vector_db para o próximo teste
        # Isto é crucial para evitar o PermissionError
        pipeline_vector_db._client = None
        pipeline_vector_db._collection = None
        pipeline.db_collection = None # Resetar a instância no módulo pipeline também
        time.sleep(0.1)


    @patch('core.pipeline.embedding_manager.gerar_embeddings') 
    def test_indexar_documento_sucesso(self, mock_gerar_embeddings):
        print(f"\nExecutando test_indexar_documento_sucesso para {self.pdf_teste_nome_salvo}...")
        mock_gerar_embeddings.return_value = [[0.1] * ACTUAL_EMBEDDING_DIM_TEST] 
        callback_progresso_chamadas = []
        def _callback(msg, prog):
            # print(f"  [Callback Indexar Teste] {msg} @ {prog*100:.0f}%")
            callback_progresso_chamadas.append((msg, prog))
        sucesso = pipeline.indexar_documento(
            self.pdf_teste_caminho_salvo_em_docs, 
            self.pdf_teste_nome_salvo, 
            _callback
        )
        self.assertTrue(sucesso, "A indexação deveria ser bem-sucedida.")
        time.sleep(0.1) 
        self.assertTrue(self.db_collection_test_instance.count() > 0, "Deveria haver chunks na coleção após indexação.")
        self.assertTrue(len(callback_progresso_chamadas) > 0, "Callback de progresso deveria ter sido chamado.")
        if callback_progresso_chamadas:
            self.assertAlmostEqual(callback_progresso_chamadas[-1][1], 1.0, places=2, msg="Progresso final não foi 1.0")


    @patch('core.pipeline.llm_handler.gerar_resposta_com_contexto')
    @patch('core.pipeline.embedding_manager.gerar_embeddings')
    def test_pesquisar_e_responder_sucesso(self, mock_gerar_embeddings_pesquisa, mock_gerar_resposta_llm):
        print("\nExecutando test_pesquisar_e_responder_sucesso...")
        # Assegurar que o mock para indexação é diferente do mock para pesquisa
        with patch('core.pipeline.embedding_manager.gerar_embeddings') as mock_index_embeddings:
            mock_index_embeddings.return_value = [[0.2] * ACTUAL_EMBEDDING_DIM_TEST]
            pipeline.indexar_documento(self.pdf_teste_caminho_salvo_em_docs, self.pdf_teste_nome_salvo)
        
        time.sleep(0.1)
        self.assertTrue(self.db_collection_test_instance.count() > 0, "Documento não foi indexado antes da pesquisa.")

        mock_gerar_embeddings_pesquisa.return_value = [[0.21] * ACTUAL_EMBEDDING_DIM_TEST] 
        mock_gerar_resposta_llm.return_value = "Resposta mockada do LLM com base no contexto."
        pergunta = "Qual o conteúdo do PDF?"
        resultado = pipeline.pesquisar_e_responder(pergunta)

        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["resposta"], "Resposta mockada do LLM com base no contexto.")
        self.assertTrue(len(resultado["fontes"]) > 0)
        self.assertIn(self.pdf_teste_nome_salvo, resultado["fontes"][0]["nome_arquivo"])
        mock_gerar_embeddings_pesquisa.assert_called_once_with([pergunta])
        mock_gerar_resposta_llm.assert_called_once()

    def test_pesquisar_sem_documentos_indexados(self):
        print("\nExecutando test_pesquisar_sem_documentos_indexados...")
        time.sleep(0.1) 
        self.assertEqual(self.db_collection_test_instance.count(), 0)
        with patch('core.pipeline.embedding_manager.gerar_embeddings') as mock_gerar_embeddings_pesquisa:
            mock_gerar_embeddings_pesquisa.return_value = [[0.3] * ACTUAL_EMBEDDING_DIM_TEST]
            resultado = pipeline.pesquisar_e_responder("Qualquer pergunta?")
            self.assertIsNotNone(resultado)
            self.assertIn("não encontrei informações relevantes", resultado["resposta"])
            self.assertEqual(len(resultado["fontes"]), 0)

if __name__ == '__main__':
    unittest.main()
