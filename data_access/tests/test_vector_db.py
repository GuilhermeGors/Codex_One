# codex_one/data_access/tests/test_vector_db.py

import unittest
import os
import shutil
import uuid
import sys
import time 

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from data_access import vector_db
from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, ensure_directories_exist

ACTUAL_EMBEDDING_DIM = 768 
try:
    from core.embedding_manager import obter_dimensao_embedding 
    dim_from_model = obter_dimensao_embedding()
    if dim_from_model:
        ACTUAL_EMBEDDING_DIM = dim_from_model
except ImportError:
    print(f"AVISO (test_vector_db): Módulo core.embedding_manager não encontrado. Usando dimensão {ACTUAL_EMBEDDING_DIM}.")


class TestVectorDB(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n[TestVectorDB] Configurando classe de teste...")
        ensure_directories_exist() 
        vector_db.delete_persistent_storage()

    @classmethod
    def tearDownClass(cls):
        print("\n[TestVectorDB] Limpando após todos os testes da classe...")
        vector_db.delete_persistent_storage()

    def setUp(self):
        print(f"\n[TestVectorDB] Configurando teste: {self.id()}")
        # Forçar um estado completamente limpo para cada teste
        vector_db.reset_db_state_for_tests()
        
        self.collection = vector_db.initialize_vector_db(force_new_client=True) 
        self.assertIsNotNone(self.collection, "A coleção ChromaDB não pôde ser inicializada no setUp.")
        time.sleep(0.1) 
        self.assertEqual(self.collection.count(), 0, f"A coleção não está vazia no início do teste. Contagem: {self.collection.count()}")

    def tearDown(self):
        print(f"[TestVectorDB] Limpando após teste: {self.id()}")
        vector_db._client = None 
        vector_db._collection = None

    def test_01_initialize_and_add_chunks(self):
        self.assertIsNotNone(self.collection)
        chunk_id1 = f"test_doc1_chunk1_{uuid.uuid4().hex[:4]}"
        texts = ["Texto do chunk 1 para teste de DB."]
        embeddings = [[0.1] * ACTUAL_EMBEDDING_DIM]
        metadatas = [{"doc_id_original_db": "test_doc1", "nome_arquivo_original": "teste_db.pdf", "numero_pagina": 1}]
        
        success = vector_db.add_chunks_to_collection(self.collection, texts, embeddings, metadatas, [chunk_id1])
        self.assertTrue(success, "Falha ao adicionar chunks à coleção.")
        time.sleep(0.1)
        self.assertEqual(self.collection.count(), 1, "Contagem incorreta de chunks após adição.")

        retrieved = self.collection.get(ids=[chunk_id1], include=["metadatas", "documents"])
        self.assertEqual(len(retrieved['ids'][0]), 1, "Chunk não encontrado após adição.")
        self.assertEqual(retrieved['documents'][0], texts[0])
        self.assertEqual(retrieved['metadatas'][0]["doc_id_original_db"], "test_doc1")

    def test_02_find_similar_chunks(self):
        self.assertIsNotNone(self.collection)
        base_id = "sim_doc_"
        chunk_ids = [f"{base_id}{i}_{uuid.uuid4().hex[:4]}" for i in range(3)]
        texts = [f"Conteúdo similar {i}" for i in range(3)]
        embeddings = [[0.1 + i*0.01] * ACTUAL_EMBEDDING_DIM for i in range(3)]
        metadatas = [{"doc_id_original_db": f"{base_id}doc", "nome_arquivo_original": "similar.pdf", "numero_pagina": i+1} for i in range(3)]
        vector_db.add_chunks_to_collection(self.collection, texts, embeddings, metadatas, chunk_ids)
        time.sleep(0.1) # Delay
        self.assertEqual(self.collection.count(), 3)

        query_embedding = [0.105] * ACTUAL_EMBEDDING_DIM 
        similar_chunks = vector_db.find_similar_chunks(self.collection, query_embedding, top_k=2)
        
        self.assertIsNotNone(similar_chunks)
        self.assertEqual(len(similar_chunks), 2)
        if similar_chunks:
            self.assertEqual(similar_chunks[0]["id_chunk"], chunk_ids[0])

    def test_03_delete_document_chunks(self):
        self.assertIsNotNone(self.collection)
        doc_id_to_delete = "doc_para_deletar_db"
        
        chunk_ids_del = [f"{doc_id_to_delete}_chunk{i}_{uuid.uuid4().hex[:4]}" for i in range(2)]
        texts_del = [f"Chunk {i} de {doc_id_to_delete}" for i in range(2)]
        embed_del = [[0.5 + i*0.01] * ACTUAL_EMBEDDING_DIM for i in range(2)]
        meta_del = [{"doc_id_original_db": doc_id_to_delete, "nome_arquivo_original": "deletar.pdf"}] * 2
        vector_db.add_chunks_to_collection(self.collection, texts_del, embed_del, meta_del, chunk_ids_del)
        
        other_doc_id = "doc_para_manter_db"
        other_chunk_id = f"{other_doc_id}_chunk0_{uuid.uuid4().hex[:4]}"
        vector_db.add_chunks_to_collection(
            self.collection, ["Manter este chunk"], [[0.9] * ACTUAL_EMBEDDING_DIM], 
            [{"doc_id_original_db": other_doc_id, "nome_arquivo_original": "manter.pdf"}], [other_chunk_id]
        )
        time.sleep(0.1)
        self.assertEqual(self.collection.count(), 3)

        success_delete = vector_db.delete_document_chunks(self.collection, doc_id_to_delete)
        self.assertTrue(success_delete)
        time.sleep(0.1) # Delay
        self.assertEqual(self.collection.count(), 1)
        
        remaining = self.collection.get(ids=[other_chunk_id])
        self.assertEqual(len(remaining['ids'][0]), 1)

    def test_04_get_all_document_infos(self):
        self.assertIsNotNone(self.collection)
        vector_db.add_chunks_to_collection(self.collection, 
            ["d1c1", "d1c2"], [[0.1]*ACTUAL_EMBEDDING_DIM, [0.2]*ACTUAL_EMBEDDING_DIM],
            [{"doc_id_original_db": "doc_info_1", "nome_arquivo_original": "info1.pdf", "autor_documento": "Autor1"}]*2,
            [f"d1c1_{uuid.uuid4().hex[:4]}", f"d1c2_{uuid.uuid4().hex[:4]}"]
        )
        vector_db.add_chunks_to_collection(self.collection, ["d2c1"], [[0.3]*ACTUAL_EMBEDDING_DIM],
            [{"doc_id_original_db": "doc_info_2", "nome_arquivo_original": "info2.epub", "autor_documento": "Autor2"}],
            [f"d2c1_{uuid.uuid4().hex[:4]}"]
        )
        time.sleep(0.1)
        doc_infos = vector_db.get_all_document_infos(self.collection)
        self.assertEqual(len(doc_infos), 2)

    def test_05_get_document_chunk_count(self):
        self.assertIsNotNone(self.collection)
        doc_id = "doc_contagem_db"
        vector_db.add_chunks_to_collection(self.collection, ["c1", "c2"], [[0.1]*ACTUAL_EMBEDDING_DIM]*2,
            [{"doc_id_original_db": doc_id, "nome_arquivo_original": "contagem.pdf"}]*2,
            [f"{doc_id}_c{i}_{uuid.uuid4().hex[:4]}" for i in range(2)]
        )
        time.sleep(0.1) # Delay
        self.assertEqual(vector_db.get_document_chunk_count(self.collection, doc_id), 2)
        self.assertEqual(vector_db.get_document_chunk_count(self.collection, "id_nao_existe_db"), 0)

    def test_06_collection_vazia_operacoes(self):
        self.assertIsNotNone(self.collection)
        time.sleep(0.1) # Delay
        self.assertEqual(self.collection.count(), 0)
        self.assertEqual(len(vector_db.get_all_document_infos(self.collection)), 0)
        self.assertEqual(len(vector_db.find_similar_chunks(self.collection, [0.1]*ACTUAL_EMBEDDING_DIM)), 0)
        self.assertTrue(vector_db.delete_document_chunks(self.collection, "doc_inexistente_db"))
        self.assertEqual(vector_db.get_document_chunk_count(self.collection, "doc_inexistente_db"), 0)


if __name__ == '__main__':
    unittest.main()
