# codex_one/core/llm_handler.py

import ollama
from typing import Optional, List, Dict, Any
from config import OLLAMA_BASE_URL, OLLAMA_MODEL 

def construir_prompt_para_llm(pergunta_usuario: str, contexto_chunks: str) -> str:
    """
    Constrói o prompt formatado para enviar ao LLM.
    """
    prompt = f"""Você é um assistente de IA especializado em responder perguntas com base em documentos fornecidos.
Responda à seguinte PERGUNTA do usuário utilizando APENAS o CONTEXTO fornecido.
Se a resposta não estiver no contexto, diga "Com base nos documentos fornecidos, não encontrei informação para responder a esta pergunta."
Tente ser conciso e direto ao ponto.
Se possível, mencione o nome do arquivo e o número da página da fonte de onde a informação foi retirada.

CONTEXTO:
{contexto_chunks}

PERGUNTA:
{pergunta_usuario}

RESPOSTA:
"""
    return prompt

def gerar_resposta_com_contexto(pergunta_usuario: str, contexto_chunks: str) -> Optional[str]:
    """
    Envia a pergunta e o contexto para o Ollama e retorna a resposta do LLM.
    """
    prompt_completo = construir_prompt_para_llm(pergunta_usuario, contexto_chunks)
    
    print(f"\n[LLM HANDLER] Enviando prompt para Ollama (modelo: {OLLAMA_MODEL})...")

    try:

        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': prompt_completo,
                }
            ]
        )
        
        resposta_texto = response['message']['content']
        print(f"[LLM HANDLER] Resposta recebida do Ollama.")
        return resposta_texto.strip()
        
    except ollama.ResponseError as e:
        print(f"[LLM HANDLER] Erro de resposta do Ollama: {e.status_code}")
        print(f"[LLM HANDLER] Detalhes do erro: {e.error}")
        if e.status_code == 404:
             print(f"  Causa provável: Modelo '{OLLAMA_MODEL}' não encontrado ou indisponível no Ollama.")
             print(f"  Verifique com 'ollama pull {OLLAMA_MODEL}'.")
        return f"Erro ao comunicar com o modelo (Ollama): {e.error} (status: {e.status_code})"
    except ConnectionRefusedError:
        print(f"[LLM HANDLER] Erro: Conexão recusada ao servidor Ollama em {OLLAMA_BASE_URL}.")
        print("  Verifique se o servidor Ollama está em execução.")
        return "Erro: Não foi possível conectar ao servidor Ollama."
    except Exception as e:
        print(f"[LLM HANDLER] Erro inesperado ao gerar resposta com Ollama: {e}")
        return f"Erro inesperado ao gerar resposta: {e}"
