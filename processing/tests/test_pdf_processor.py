# codex_one/processing/tests/test_pdf_processor.py
import unittest
import os
import fitz
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from processing.pdf_processor import extrair_conteudo_pdf
from config import DOCUMENTS_DIR

class TestPdfProcessor(unittest.TestCase):
    def setUp(self):
        self.test_dir = DOCUMENTS_DIR
        os.makedirs(self.test_dir, exist_ok=True)
        self.pdf_path = os.path.join(self.test_dir, "test_pdf_proc.pdf")

        # Criar um PDF de teste
        doc = fitz.open()
        page1 = doc.new_page()
        page1.insert_text((50, 72), "Conteúdo da página 1 do PDF.")
        page2 = doc.new_page()
        page2.insert_text((50, 72), "Conteúdo da página 2 do PDF.")
        doc.set_metadata({"title": "PDF Teste", "author": "Testador PDF"})
        doc.save(self.pdf_path)
        doc.close()

    def tearDown(self):
        if os.path.exists(self.pdf_path):
            os.remove(self.pdf_path)

    def test_extracao_pdf_sucesso(self):
        conteudo, meta = extrair_conteudo_pdf(self.pdf_path)
        self.assertIsNotNone(conteudo)
        self.assertIsNotNone(meta)
        self.assertEqual(len(conteudo), 2) # 2 páginas
        self.assertEqual(conteudo[0]["texto_conteudo"], "Conteúdo da página 1 do PDF.")
        self.assertEqual(meta["titulo_documento"], "PDF Teste")
        self.assertEqual(meta["autor_documento"], "Testador PDF")
        self.assertEqual(meta["total_paginas_ou_secoes"], 2)

    def test_extracao_pdf_callback(self):
        callback_chamadas = []
        def _callback(atual, total):
            callback_chamadas.append((atual, total))
        
        extrair_conteudo_pdf(self.pdf_path, page_progress_callback=_callback)
        self.assertEqual(len(callback_chamadas), 2)
        self.assertEqual(callback_chamadas[0], (1, 2))
        self.assertEqual(callback_chamadas[1], (2, 2))

    def test_pdf_nao_existente(self):
        resultado = extrair_conteudo_pdf("caminho/inexistente.pdf")
        self.assertIsNone(resultado)

if __name__ == '__main__':
    unittest.main()
