# codex_one/processing/tests/test_document_parser.py
import unittest
import os
import fitz 
import ebooklib 
from ebooklib import epub
import sys
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from processing.document_parser import processar_documento_ficheiro
from config import DOCUMENTS_DIR, CHUNK_SIZE, ensure_directories_exist

class TestDocumentParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_directories_exist()
        cls.test_dir = os.path.join(DOCUMENTS_DIR, "parser_tests") # Subpasta para testes
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)
        os.makedirs(cls.test_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def setUp(self):
        # Criar PDF de teste
        self.pdf_path = os.path.join(self.test_dir, "parser_main_test.pdf")
        doc_pdf = fitz.open()
        page_pdf = doc_pdf.new_page()
        page_pdf.insert_text((50, 72), "Conteúdo PDF para parser.")
        doc_pdf.set_metadata({"title": "PDF Parser Main Test", "author": "Tester Main PDF"})
        doc_pdf.save(self.pdf_path)
        doc_pdf.close()

        # Criar ePub de teste com 2 seções de conteúdo na espinha
        self.epub_path = os.path.join(self.test_dir, "parser_main_test.epub")
        book_epub = epub.EpubBook()
        book_epub.set_identifier('id_parser_main_docparser')
        book_epub.set_title('ePub Parser Main Test')
        book_epub.add_author('Tester Main ePub')
        
        c1_epub = epub.EpubHtml(title='Cap 1 Conteúdo', file_name='c1.xhtml')
        c1_epub.content = '<h1>Capítulo ePub Um</h1><p>Conteúdo ePub para parser, seção um.</p>'
        c2_epub = epub.EpubHtml(title='Cap 2 Conteúdo', file_name='c2.xhtml')
        c2_epub.content = '<h2>Capítulo ePub Dois</h2><p>Conteúdo ePub para parser, seção dois.</p>'
        
        book_epub.add_item(c1_epub)
        book_epub.add_item(c2_epub)
        
        # Itens de navegação que não devem ser contados como conteúdo principal pelo epub_processor
        nav_doc = epub.EpubNav(uid='nav_parser', file_name='nav_parser.xhtml')
        book_epub.add_item(nav_doc)
        book_epub.add_item(epub.EpubNcx())

        book_epub.spine = [c1_epub, c2_epub] # Apenas os capítulos de conteúdo na espinha
        book_epub.toc = (epub.Link('c1.xhtml', 'Capítulo 1', 'c1'), epub.Link('c2.xhtml', 'Capítulo 2', 'c2'))
        epub.write_epub(self.epub_path, book_epub, {})


    def test_processar_pdf(self):
        print(f"\n[TestDocumentParser] Testando PDF: {self.pdf_path}")
        chunks = processar_documento_ficheiro(self.pdf_path)
        self.assertIsNotNone(chunks, "Processamento de PDF não deveria retornar None.")
        self.assertTrue(len(chunks) > 0, "Deveria haver chunks para o PDF.")
        if chunks: # Adicionar verificação
            self.assertEqual(chunks[0]['metadados_chunk']['titulo_documento'], "PDF Parser Main Test")
            self.assertIn("Conteúdo PDF para parser.", chunks[0]['texto_chunk'])

    def test_processar_epub(self):
        print(f"\n[TestDocumentParser] Testando ePub: {self.epub_path}")
        chunks = processar_documento_ficheiro(self.epub_path)
        self.assertIsNotNone(chunks, "Processamento de ePub não deveria retornar None.")
        self.assertTrue(len(chunks) > 0, "Deveria haver chunks para o ePub.")
        if chunks: # Adicionar verificação
            self.assertEqual(chunks[0]['metadados_chunk']['titulo_documento'], "ePub Parser Main Test")
            # Verificar se o conteúdo de ambas as seções está presente nos chunks
            texto_completo_chunks = " ".join([c['texto_chunk'] for c in chunks])
            self.assertIn("Conteúdo ePub para parser, seção um.", texto_completo_chunks)
            self.assertIn("Conteúdo ePub para parser, seção dois.", texto_completo_chunks)
            
            # Verificar se os metadados da primeira seção estão corretos
            meta_primeiro_chunk = chunks[0]['metadados_chunk']
            self.assertEqual(meta_primeiro_chunk.get('id_pagina_ou_secao_original'), 1)


    def test_tipo_nao_suportado(self):
        print("\n[TestDocumentParser] Testando tipo não suportado...")
        txt_path = os.path.join(self.test_dir, "parser_test.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("teste de tipo não suportado")
        chunks = processar_documento_ficheiro(txt_path)
        self.assertIsNone(chunks, "Deveria retornar None para tipos não suportados.")
        if os.path.exists(txt_path): os.remove(txt_path)
        
    def test_processar_com_callback(self):
        print(f"\n[TestDocumentParser] Testando PDF com callback: {self.pdf_path}")
        callback_chamadas = []
        def _callback(atual, total):
            print(f"  [Callback Parser Teste] Item {atual}/{total}")
            callback_chamadas.append((atual, total))
        
        processar_documento_ficheiro(self.pdf_path, progress_callback_gui=_callback)
        self.assertTrue(len(callback_chamadas) > 0, "Callback não foi chamado para PDF.")
        if callback_chamadas: # Adicionar verificação
             self.assertEqual(callback_chamadas[-1], (1,1), "Callback final do PDF incorreto (esperado 1 página).")

        print(f"\n[TestDocumentParser] Testando ePub com callback: {self.epub_path}")
        callback_chamadas_epub = []
        def _callback_epub(atual, total):
            print(f"  [Callback Parser Teste ePub] Item {atual}/{total}")
            callback_chamadas_epub.append((atual, total))
        processar_documento_ficheiro(self.epub_path, progress_callback_gui=_callback_epub)
        self.assertTrue(len(callback_chamadas_epub) > 0, "Callback não foi chamado para ePub.")
        if callback_chamadas_epub: # Adicionar verificação
            self.assertEqual(callback_chamadas_epub[-1], (2,2), "Callback final do ePub incorreto (esperado 2 seções).")


if __name__ == '__main__':
    unittest.main()
