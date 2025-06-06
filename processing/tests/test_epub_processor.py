# codex_one/processing/tests/test_epub_processor.py
import unittest
import os
import ebooklib
from ebooklib import epub
import sys
import shutil 

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from processing.epub_processor import extrair_conteudo_epub
from config import DOCUMENTS_DIR, ensure_directories_exist

class TestEpubProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_directories_exist() 
        cls.test_dir = os.path.join(DOCUMENTS_DIR, "epub_processor_tests_temp_v2") 
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)
        os.makedirs(cls.test_dir, exist_ok=True)


    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def setUp(self):
        self.epub_path = os.path.join(self.test_dir, "test_epub_proc.epub")
        
        book = epub.EpubBook()
        book.set_identifier('id_epub_proc_test_v2')
        book.set_title('Livro Teste ePub Processor V2')
        book.set_language('pt-br')
        book.add_author('Testador ePub V2')

        c1 = epub.EpubHtml(title='Capítulo 1 HTML Title', file_name='chap_01.xhtml', lang='pt-br')
        c1.content = u'<h1>Título Visível Cap 1</h1><p>Este é o conteúdo do primeiro capítulo.</p>'
        
        c2 = epub.EpubHtml(title='Capítulo 2 HTML Title', file_name='chap_02.xhtml', lang='pt-br')
        c2.content = u'<h2>Título Visível Cap 2</h2><p>Conteúdo do segundo capítulo.</p>'
        
        book.add_item(c1)
        book.add_item(c2)
        
        # Definir a TOC (Table of Contents) - estes são os links que aparecerão no índice
        book.toc = (
            epub.Link('chap_01.xhtml', 'Link para Capítulo 1', 'uid_c1_link'),
            epub.Link('chap_02.xhtml', 'Link para Capítulo 2', 'uid_c2_link')
        )
        
        # Adicionar itens de navegação padrão (NCX e Nav HTML)
        # O EpubNav é o documento XHTML que contém a navegação (geralmente o toc.xhtml)
        # O NCX é para leitores mais antigos.
        nav_xhtml = epub.EpubNav(uid='nav', file_name='nav.xhtml', title='Navegação')
        # A biblioteca ebooklib pode gerar o conteúdo do nav_xhtml a partir do book.toc
        # ou pode construí-lo manualmente se precisar de mais controle.
        # Para este teste, a simples adição do item é suficiente para que ele exista.
        # O processador de ePub deve ignorá-lo como conteúdo principal se não estiver na espinha de conteúdo.
        book.add_item(nav_xhtml)
        book.add_item(epub.EpubNcx())
        book.spine = [c1, c2]
        
        try:
            epub.write_epub(self.epub_path, book, {"epub3_pages": False, "epub2_guide": False}) # Opções para simplificar
            print(f"[TestEpubProcessor] ePub de teste criado: {self.epub_path}")
        except Exception as e:
            print(f"[TestEpubProcessor] Erro ao criar ePub de teste: {e}")
            self.fail(f"Falha ao criar ePub de teste: {e}")


    def test_extracao_epub_sucesso(self):
        print(f"\n[TestEpubProcessor] Testando extração de: {self.epub_path}")
        if not os.path.exists(self.epub_path):
            self.fail(f"Ficheiro ePub de teste não encontrado em {self.epub_path}")

        resultado = extrair_conteudo_epub(self.epub_path)
        self.assertIsNotNone(resultado, "A extração do ePub não deveria retornar None.")
        
        conteudo, meta = resultado
        self.assertIsNotNone(conteudo, "Conteúdo extraído não deveria ser None.")
        self.assertIsNotNone(meta, "Metadados extraídos não deveriam ser None.")
        
        self.assertEqual(len(conteudo), 2, f"Esperado 2 seções de conteúdo, obtido {len(conteudo)}")
        
        if len(conteudo) == 2:
            self.assertIn("Conteúdo do primeiro capítulo", conteudo[0]['texto_conteudo'])
            self.assertTrue(
                "Título Visível Cap 1" in conteudo[0]['titulo_secao'] or \
                "Capítulo 1 HTML Title" in conteudo[0]['titulo_secao'] or \
                "Chap 01" in conteudo[0]['titulo_secao']
            )

            self.assertIn("Conteúdo do segundo capítulo", conteudo[1]['texto_conteudo'])
            self.assertTrue(
                "Título Visível Cap 2" in conteudo[1]['titulo_secao'] or \
                "Capítulo 2 HTML Title" in conteudo[1]['titulo_secao'] or \
                "Chap 02" in conteudo[1]['titulo_secao']
            )

        self.assertEqual(meta.get("titulo_documento"), "Livro Teste ePub Processor V2")
        self.assertEqual(meta.get("autor_documento"), "Testador ePub V2")
        self.assertEqual(meta.get("total_paginas_ou_secoes"), 2) # Deve ser 2 se o filtro funcionar

    def test_extracao_epub_callback(self):
        print(f"\n[TestEpubProcessor] Testando callback de extração de: {self.epub_path}")
        if not os.path.exists(self.epub_path):
            self.fail(f"Ficheiro ePub de teste não encontrado em {self.epub_path}")

        callback_chamadas = []
        def _callback(atual, total):
            print(f"  [Callback ePub Teste] Seção {atual}/{total}")
            callback_chamadas.append((atual, total))
        
        extrair_conteudo_epub(self.epub_path, page_progress_callback=_callback)
        self.assertEqual(len(callback_chamadas), 2, "Callback não foi chamado o número esperado de vezes para seções de conteúdo.")
        if len(callback_chamadas) == 2:
            self.assertEqual(callback_chamadas[0], (1, 2))
            self.assertEqual(callback_chamadas[1], (2, 2))

    def test_epub_nao_existente(self):
        print("\n[TestEpubProcessor] Testando ePub não existente...")
        resultado = extrair_conteudo_epub("caminho/super/inexistente.epub")
        self.assertIsNone(resultado)

if __name__ == '__main__':
    unittest.main()
