# codex_one/nucleo_rag/manipulador_llm.py

import ollama
from typing import Optional, List, Dict, Any

# Importar configurações do projeto
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

# Configurar o cliente Ollama globalmente ou numa função de inicialização
# Para simplicidade, vamos configurar o host aqui se for diferente do padrão.
# A biblioteca ollama por padrão tenta conectar a http://localhost:11434
# Se OLLAMA_BASE_URL for diferente, você pode precisar configurar o cliente:
# ollama.Client(host=OLLAMA_BASE_URL)
# No entanto, a biblioteca 'ollama' geralmente usa variáveis de ambiente como OLLAMA_HOST
# ou o padrão. Se o seu OLLAMA_BASE_URL é apenas o host e porta padrão,
# não é necessária configuração explícita do cliente aqui.

def construir_prompt_para_llm(pergunta_usuario: str, contexto_chunks: str) -> str:
    """
    Constrói o prompt formatado para enviar ao LLM.

    Args:
        pergunta_usuario (str): A pergunta original do usuário.
        contexto_chunks (str): Uma string contendo os chunks de texto relevantes,
                               cada um idealmente prefixado com sua fonte.

    Returns:
        str: O prompt formatado.
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

    Args:
        pergunta_usuario (str): A pergunta original do usuário.
        contexto_chunks (str): O contexto formatado a partir dos chunks relevantes.

    Returns:
        Optional[str]: A resposta gerada pelo LLM, ou None se ocorrer um erro.
    """
    prompt_completo = construir_prompt_para_llm(pergunta_usuario, contexto_chunks)
    
    print(f"\n[MANIPULADOR LLM] Enviando prompt para Ollama (modelo: {OLLAMA_MODEL})...")
    # print(f"[MANIPULADOR LLM] Prompt (primeiros 500 chars):\n{prompt_completo[:500]}...") # Para depuração

    try:
        # Certifique-se de que o servidor Ollama está rodando e o modelo está disponível.
        # Se OLLAMA_BASE_URL for diferente do padrão, configure o cliente ollama.
        # Ex: client = ollama.Client(host=OLLAMA_BASE_URL)
        #     response = client.chat(...) ou client.generate(...)
        
        # Usando a interface padrão da biblioteca que deve respeitar OLLAMA_HOST se configurado
        # ou o padrão localhost:11434.
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    'role': 'user',
                    'content': prompt_completo,
                }
            ],
            # options={ # Opcional: para controlar temperatura, etc.
            #     'temperature': 0.7 
            # }
        )
        
        resposta_texto = response['message']['content']
        print(f"[MANIPULADOR LLM] Resposta recebida do Ollama.")
        # print(f"[MANIPULADOR LLM] Resposta completa: {resposta_texto}") # Para depuração
        return resposta_texto.strip()
        
    except ollama.ResponseError as e:
        print(f"[MANIPULADOR LLM] Erro de resposta do Ollama: {e.status_code}")
        print(f"[MANIPULADOR LLM] Detalhes do erro: {e.error}")
        if e.status_code == 404:
             print(f"  Possível causa: O modelo '{OLLAMA_MODEL}' não foi encontrado ou não está disponível no servidor Ollama.")
             print(f"  Verifique se o modelo foi baixado com 'ollama pull {OLLAMA_MODEL}' ou se o nome está correto.")
        return f"Erro ao comunicar com o modelo de linguagem (Ollama): {e.error} (status: {e.status_code})"
    except ConnectionRefusedError:
        print(f"[MANIPULADOR LLM] Erro: Não foi possível conectar ao servidor Ollama em {OLLAMA_BASE_URL}.")
        print("  Verifique se o servidor Ollama está em execução.")
        return "Erro: Não foi possível conectar ao servidor Ollama. Verifique se ele está em execução."
    except Exception as e:
        print(f"[MANIPULADOR LLM] Erro inesperado ao gerar resposta com Ollama: {e}")
        return f"Erro inesperado ao tentar gerar a resposta: {e}"

# --- Bloco de Teste ---
if __name__ == '__main__':
    print("Testando módulo manipulador_llm.py...")
    
    # Importar config para garantir que os diretórios existam (se necessário para o modelo)
    # e para obter OLLAMA_MODEL
    from config import ensure_directories_exist, OLLAMA_MODEL
    ensure_directories_exist()

    # Verificar se o modelo Ollama está acessível (uma forma simples)
    try:
        print(f"\nVerificando modelos disponíveis no Ollama (host: {ollama.Client()._client.host})...")
        models_disponiveis = ollama.list()
        model_names = [m['name'] for m in models_disponiveis['models']]
        print(f"Modelos encontrados: {model_names}")
        if OLLAMA_MODEL not in model_names:
            print(f"AVISO: O modelo '{OLLAMA_MODEL}' configurado em config.py não parece estar na lista de modelos disponíveis do Ollama.")
            print(f"Certifique-se de que o modelo foi baixado com 'ollama pull {OLLAMA_MODEL}'.")
            print("O teste de geração de resposta pode falhar se o modelo não estiver disponível.")
        else:
            print(f"Modelo '{OLLAMA_MODEL}' encontrado na lista de modelos do Ollama.")

    except Exception as e:
        print(f"Não foi possível listar os modelos do Ollama. Erro: {e}")
        print("Certifique-se de que o servidor Ollama está em execução e acessível.")
        print("O teste de geração de resposta provavelmente falhará.")


    print("\n--- Teste de Geração de Resposta com Contexto ---")
    pergunta_teste = "Qual é o principal benefício do pipeline RAG?"
    contexto_teste = """Fonte: Documento Alfa, Página 1
Conteúdo: O pipeline RAG (Retrieval Augmented Generation) melhora significativamente a relevância e a factualidade das respostas de modelos de linguagem grandes. Ele faz isso ao fornecer contexto relevante de uma base de conhecimento externa.

---

Fonte: Documento Beta, Página 5
Conteúdo: Um dos principais benefícios do RAG é a capacidade de mitigar alucinações em LLMs, pois as respostas são ancoradas em informações recuperadas.
"""

    resposta = gerar_resposta_com_contexto(pergunta_teste, contexto_teste)

    if resposta:
        print(f"\nPergunta: {pergunta_teste}")
        print(f"Contexto Fornecido (resumo):\n{contexto_teste[:150]}...")
        print(f"Resposta do LLM ({OLLAMA_MODEL}):\n{resposta}")
        
        # Uma asserção simples para verificar se a resposta não é None ou uma mensagem de erro genérica
        # (se a conexão com Ollama falhar, a resposta conterá "Erro")
        assert resposta is not None
        if "Erro" not in resposta and "não encontrei informação" not in resposta:
             assert len(resposta) > 10 # Espera-se uma resposta minimamente elaborada
    else:
        print("Falha ao gerar resposta (retornou None).")

    print("\n--- Teste com Contexto Insuficiente ---")
    pergunta_insuficiente = "Qual a cor do céu em Marte?"
    contexto_irrelevante = """Fonte: Manual de Culinária, Página 10
Conteúdo: Para fazer um bolo de chocolate, você precisará de farinha, açúcar e cacau.
"""
    resposta_insuficiente = gerar_resposta_com_contexto(pergunta_insuficiente, contexto_irrelevante)
    if resposta_insuficiente:
        print(f"\nPergunta: {pergunta_insuficiente}")
        print(f"Contexto Fornecido (resumo):\n{contexto_irrelevante[:150]}...")
        print(f"Resposta do LLM ({OLLAMA_MODEL}):\n{resposta_insuficiente}")
        assert "não encontrei informação" in resposta_insuficiente or "Erro" in resposta_insuficiente
        
    print("\nTestes do manipulador_llm.py concluídos.")

