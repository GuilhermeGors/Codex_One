# codex_one/processing/tests/test_text_splitter.py

import unittest
# Ajustar importação para refletir a nova estrutura de pastas e a execução a partir da raiz
from processing.text_splitter import dividir_texto_em_chunks
# Para aceder a config.py da raiz do projeto
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) # Adiciona a raiz do projeto ao sys.path
from config import CHUNK_SIZE, CHUNK_OVERLAP # Agora pode importar de config

class TestTextSplitter(unittest.TestCase):

    def test_divisao_basica(self):
        texto_teste = "Este é um texto de exemplo muito longo que precisa ser dividido em vários pedaços menores para processamento. A ideia é que cada pedaço, ou chunk, mantenha algum contexto do anterior e do próximo através da sobreposição. Isso ajuda os modelos de linguagem a entenderem melhor a informação contida nos documentos. A modularização desta função é importante."
        metadados_base = {"documento_id": "doc123", "fonte": "teste.txt"}
        
        chunks = dividir_texto_em_chunks(texto_teste, chunk_size=50, chunk_overlap=10, metadados_base_chunk=metadados_base)
        self.assertTrue(len(chunks) > 1)
        self.assertEqual(chunks[0]["metadados_chunk"]["documento_id"], "doc123")
        self.assertIn("texto_chunk", chunks[0])
        # Verificar sobreposição (aproximada)
        if len(chunks) > 1:
            overlap_calculado = len(chunks[0]["texto_chunk"]) + len(chunks[1]["texto_chunk"]) - len(chunks[0]["texto_chunk"] + chunks[1]["texto_chunk"][10:])
            # A lógica de sobreposição exata pode ser complexa de testar sem replicar a lógica interna,
            # mas podemos verificar se o segundo chunk começa com parte do final do primeiro.
            # Este é um teste simples, a lógica de sobreposição no código original é mais direta.
            # O importante é que os chunks são gerados.
            self.assertTrue(chunks[1]["texto_chunk"].startswith(chunks[0]["texto_chunk"][50-10:]))


    def test_sem_overlap(self):
        texto_teste = "Texto sem sobreposição para teste."
        chunks = dividir_texto_em_chunks(texto_teste, chunk_size=10, chunk_overlap=0)
        self.assertTrue(len(chunks) >= 3) # "Texto sem ", "sobreposi", "ção para ", "teste."
        if len(chunks) > 1:
            self.assertNotEqual(chunks[0]["texto_chunk"][-1], chunks[1]["texto_chunk"][0]) # Não deve haver sobreposição

    def test_texto_curto(self):
        texto_curto = "Texto curto."
        chunks = dividir_texto_em_chunks(texto_curto, chunk_size=50, chunk_overlap=10)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["texto_chunk"], texto_curto)

    def test_texto_vazio(self):
        chunks = dividir_texto_em_chunks("", chunk_size=50, chunk_overlap=10)
        self.assertEqual(len(chunks), 0)

    def test_chunk_size_maior_que_texto(self):
        texto = "abc"
        chunks = dividir_texto_em_chunks(texto, chunk_size=10, chunk_overlap=2)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]['texto_chunk'], "abc")

    def test_overlap_igual_chunk_size(self):
        # Deve evitar loop infinito e processar corretamente
        texto = "abcdefghijklmno"
        chunks = dividir_texto_em_chunks(texto, chunk_size=5, chunk_overlap=5)
        # Espera-se que ele avance de alguma forma, ou processe o texto em um chunk se a lógica de avanço for mínima
        self.assertTrue(len(chunks) > 0)
        # A lógica exata de quantos chunks seriam gerados aqui depende da implementação do avanço mínimo.
        # O principal é que não entre em loop.
        # Ex: "abcde", "fghij", "klmno" (se avanço for de chunk_size - overlap + 1, e overlap == chunk_size, avança 1)
        # Se o código atual avança 1:
        # "abcde"
        # "bcdef"
        # "cdefg"
        # ...
        # O código foi ajustado para avançar em 1 se overlap >= chunk_size
        self.assertEqual(chunks[0]['texto_chunk'], "abcde")
        if len(chunks) > 1:
             self.assertEqual(chunks[1]['texto_chunk'], "bcdef")


if __name__ == '__main__':
    unittest.main()
