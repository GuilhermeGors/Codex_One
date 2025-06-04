# codex_one/core/tests/test_llm_handler.py

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from core import llm_handler 
from config import OLLAMA_MODEL, OLLAMA_BASE_URL, ensure_directories_exist

# Tentar importar a exceção real para usar nos mocks
try:
    from ollama import ResponseError as OllamaActualResponseError
except ImportError:
    # Fallback se ollama não estiver instalado no ambiente de teste
    # Os testes que dependem de levantar esta exceção específica podem precisar ser pulados
    # ou o mock precisará ser mais genérico.
    class OllamaActualResponseError(Exception): # Definir um fallback que herda de Exception
        def __init__(self, error, status_code):
            super().__init__(error)
            self.error = error
            self.status_code = status_code

class TestLLMHandler(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_directories_exist()

    def test_construir_prompt(self):
        print("\nExecutando test_construir_prompt...")
        pergunta = "Qual a capital da França?"
        contexto = "Fonte: geo.txt, Pág 1\nConteúdo: Paris é a capital da França."
        prompt = llm_handler.construir_prompt_para_llm(pergunta, contexto)
        self.assertIn(pergunta, prompt)
        self.assertIn(contexto, prompt)
        self.assertIn("Responda à seguinte PERGUNTA", prompt)
        print("Prompt construído com sucesso.")

    @patch('core.llm_handler.ollama') 
    def test_gerar_resposta_sucesso(self, mock_ollama_lib): # Argumento mock adicionado
        print("\nExecutando test_gerar_resposta_sucesso...")
        mock_ollama_lib.chat.return_value = {
            'message': { 'content': ' Paris é a capital. ' }
        }
        resposta = llm_handler.gerar_resposta_com_contexto("P", "C")
        self.assertEqual(resposta, "Paris é a capital.")
        mock_ollama_lib.chat.assert_called_once()
        print("Geração de resposta (mock) sucesso.")

    @patch('core.llm_handler.ollama')
    def test_gerar_resposta_ollama_response_error_404(self, mock_ollama_lib): # Argumento mock adicionado
        print("\nExecutando test_gerar_resposta_ollama_response_error_404...")
        # Configurar o mock para levantar a exceção importada/definida
        mock_ollama_lib.ResponseError = OllamaActualResponseError # Para o `except ollama.ResponseError` funcionar
        mock_ollama_lib.chat.side_effect = OllamaActualResponseError(
            error="model 'modelo_inexistente' not found", 
            status_code=404
        )
        resposta = llm_handler.gerar_resposta_com_contexto("P", "C")
        self.assertIn("Erro ao comunicar com o modelo (Ollama)", resposta)
        self.assertIn("model 'modelo_inexistente' not found", resposta)
        print("Tratamento de Ollama ResponseError 404 ok.")

    @patch('core.llm_handler.ollama')
    def test_gerar_resposta_connection_error(self, mock_ollama_lib): # Argumento mock adicionado
        print("\nExecutando test_gerar_resposta_connection_error...")
        mock_ollama_lib.chat.side_effect = ConnectionRefusedError("Falha na conexão")
        resposta = llm_handler.gerar_resposta_com_contexto("P", "C")
        self.assertIn("Erro: Não foi possível conectar ao servidor Ollama.", resposta)
        print("Tratamento de ConnectionRefusedError ok.")

    @patch('core.llm_handler.ollama')
    def test_gerar_resposta_outra_excecao_ollama(self, mock_ollama_lib): # Argumento mock adicionado
        print("\nExecutando test_gerar_resposta_outra_excecao_ollama...")
        mock_ollama_lib.ResponseError = OllamaActualResponseError
        mock_ollama_lib.chat.side_effect = OllamaActualResponseError(
            error="outro erro do servidor", 
            status_code=500
        )
        resposta = llm_handler.gerar_resposta_com_contexto("P", "C")
        self.assertIn("Erro ao comunicar com o modelo (Ollama)", resposta)
        self.assertIn("outro erro do servidor", resposta)
        print("Tratamento de Ollama ResponseError 500 ok.")

    @patch('core.llm_handler.ollama')
    def test_gerar_resposta_excecao_inesperada(self, mock_ollama_lib): # Argumento mock adicionado
        print("\nExecutando test_gerar_resposta_excecao_inesperada...")
        mock_ollama_lib.chat.side_effect = Exception("Algo muito inesperado aconteceu")
        resposta = llm_handler.gerar_resposta_com_contexto("P", "C")
        self.assertIn("Erro inesperado ao gerar resposta:", resposta)
        self.assertIn("Algo muito inesperado aconteceu", resposta)
        print("Tratamento de exceção inesperada geral ok.")

if __name__ == '__main__':
    unittest.main()
