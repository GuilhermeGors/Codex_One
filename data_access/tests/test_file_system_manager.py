# codex_one/data_access/tests/test_file_system_manager.py

import unittest
import os
import shutil
import sys

# Adicionar a raiz do projeto ao sys.path para permitir importações de 'config' e 'data_access'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from data_access import file_system_manager # Importa o módulo a ser testado
from config import DOCUMENTS_DIR, ensure_directories_exist as ensure_all_project_dirs_exist

class TestFileSystemManager(unittest.TestCase):

    def setUp(self):
        """Configura o ambiente de teste antes de cada teste."""
        # Garante que o diretório de documentos principal exista (criado por config)
        ensure_all_project_dirs_exist()
        # Diretório de teste específico para uploads temporários, não o DOCUMENTS_DIR principal
        self.temp_upload_dir = "temp_test_uploads_fs_manager"
        os.makedirs(self.temp_upload_dir, exist_ok=True)
        
        # Limpar o DOCUMENTS_DIR real para garantir que os testes sejam isolados
        # CUIDADO: Isto apagará ficheiros em DOCUMENTS_DIR. Use um DOCUMENTS_DIR de teste se preferir.
        # Por agora, vamos assumir que DOCUMENTS_DIR pode ser limpo para testes.
        if os.path.exists(DOCUMENTS_DIR):
            for item in os.listdir(DOCUMENTS_DIR):
                item_path = os.path.join(DOCUMENTS_DIR, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
        else:
            os.makedirs(DOCUMENTS_DIR)


        # Criar alguns ficheiros temporários para simular uploads
        self.test_file1_content = "Conteúdo do ficheiro de teste 1."
        self.temp_file1_path = os.path.join(self.temp_upload_dir, "doc_fs_test1.pdf")
        with open(self.temp_file1_path, "w", encoding="utf-8") as f:
            f.write(self.test_file1_content)

        self.test_file2_content = "Conteúdo do ficheiro de teste 2."
        self.temp_file2_path = os.path.join(self.temp_upload_dir, "doc_fs_test2.txt")
        with open(self.temp_file2_path, "w", encoding="utf-8") as f:
            f.write(self.test_file2_content)

    def tearDown(self):
        """Limpa o ambiente de teste após cada teste."""
        if os.path.exists(self.temp_upload_dir):
            shutil.rmtree(self.temp_upload_dir)
        
        # Limpar novamente o DOCUMENTS_DIR após os testes
        if os.path.exists(DOCUMENTS_DIR):
            for item in os.listdir(DOCUMENTS_DIR):
                item_path = os.path.join(DOCUMENTS_DIR, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)

    def test_save_uploaded_file_novo(self):
        original_name = "novo_documento.pdf"
        saved_path = file_system_manager.save_uploaded_file(self.temp_file1_path, original_name)
        self.assertIsNotNone(saved_path)
        self.assertTrue(os.path.exists(saved_path))
        self.assertEqual(os.path.basename(saved_path), original_name)
        # Verificar conteúdo (opcional, mas bom)
        with open(saved_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, self.test_file1_content)

    def test_save_uploaded_file_duplicado(self):
        original_name = "documento_repetido.pdf"
        # Salvar pela primeira vez
        saved_path1 = file_system_manager.save_uploaded_file(self.temp_file1_path, original_name)
        self.assertIsNotNone(saved_path1)
        self.assertEqual(os.path.basename(saved_path1), original_name)

        # Salvar pela segunda vez com o mesmo nome original
        saved_path2 = file_system_manager.save_uploaded_file(self.temp_file2_path, original_name)
        self.assertIsNotNone(saved_path2)
        self.assertTrue(os.path.exists(saved_path2))
        self.assertNotEqual(os.path.basename(saved_path2), original_name) # Deve ter sido renomeado
        self.assertTrue(os.path.basename(saved_path2).startswith("documento_repetido_1"))

    def test_save_uploaded_file_sem_nome(self):
        saved_path = file_system_manager.save_uploaded_file(self.temp_file1_path, "")
        self.assertIsNone(saved_path)

    def test_list_saved_documents(self):
        file_system_manager.save_uploaded_file(self.temp_file1_path, "doc1.pdf")
        file_system_manager.save_uploaded_file(self.temp_file2_path, "doc2.txt")
        
        docs = file_system_manager.list_saved_documents()
        self.assertIn("doc1.pdf", docs)
        self.assertIn("doc2.txt", docs)
        self.assertEqual(len(docs), 2)

    def test_get_document_path(self):
        saved_path = file_system_manager.save_uploaded_file(self.temp_file1_path, "doc_caminho.pdf")
        retrieved_path = file_system_manager.get_document_path("doc_caminho.pdf")
        self.assertEqual(saved_path, retrieved_path)
        
        non_existent_path = file_system_manager.get_document_path("nao_existe.pdf")
        self.assertIsNone(non_existent_path)

    def test_delete_saved_file(self):
        file_system_manager.save_uploaded_file(self.temp_file1_path, "para_deletar.pdf")
        self.assertTrue(file_system_manager.delete_saved_file("para_deletar.pdf"))
        self.assertFalse(os.path.exists(os.path.join(DOCUMENTS_DIR, "para_deletar.pdf")))
        
        # Tentar deletar ficheiro inexistente
        self.assertFalse(file_system_manager.delete_saved_file("nao_existe_para_deletar.pdf"))

if __name__ == '__main__':
    unittest.main()
