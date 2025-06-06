# 🎯 Codex One

![Status](https://img.shields.io/badge/status-beta-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

## 🧠 1. Visão Geral do Projeto

O **Codex One** é uma aplicação desktop de Inteligência Artificial que cria uma base de conhecimento **privada e totalmente local** a partir dos seus documentos. Destina-se a pesquisar e extrair informações de diversas fontes (PDFs, ePubs) por meio de **perguntas em linguagem natural**, retornando respostas **precisas, com contexto e referências claras** às fontes originais.

A solução é baseada na arquitetura **RAG (Retrieval‑Augmented Generation)**: as respostas são geradas por um LLM local, enriquecido com informações recuperadas diretamente dos seus documentos — garantindo **privacidade total** e **relevância personalizada**.

---

## 🎯 2. Objetivos Principais

- **Privacidade Total**: 100 % offline — seus documentos **nunca saem da máquina**  
- **Busca Semântica Inteligente**: perguntas complexas sem depender exclusivamente de palavras‑chave  
- **Respostas Contextualizadas e Citadas**: citação clara de arquivo + página/seção  
- **Suporte Multiformato**: PDFs e ePubs agora; fácil extensão futura  
- **Interface Amigável**: desktop com UI simples via CustomTkinter

---

## 🧩 3. Arquitetura da Solução de IA

1. **Ingestão de Dados**  
   - PDFs: via PyMuPDF  
   - ePubs: via EbookLib + BeautifulSoup4  
   - `document_parser` seleciona o processador adequado  

2. **Divisão de Texto (Chunking)**  
   - O `text_splitter.dividir_texto_em_chunks(...)` cria pedaços sobrepostos para preservar o contexto  

3. **Geração de Embeddings**  
   - Sentence‑Transformers converte chunks em vetores semânticos  

4. **Armazenamento Vetorial**  
   - ChromaDB armazena embeddings + metadados (arquivo, página, chunk)  

5. **Recuperação + Geração**  
   - Pergunta → embedding → busca no ChromaDB → retrieval de chunks  
   - Prompt montado com contexto + pergunta → enviado ao LLM local (Ollama) → resposta final

---

## 📂 4. Dados

- **Origem**: apenas os documentos que o utilizador fornece (.pdf, .epub)  
- **Pré‑processamento**:
  - Extração de texto e metadados (título, autor, páginas)  
  - Chunking com sobreposição para preservar contexto  
- **Ética & Vieses**:
  - O conteúdo reflete o que é fornecido — privacidade garantida, mas qualidade depende da entrada

---

## 🛠️ 5. Stack Tecnológico

| Componente              | Ferramenta                                |
|------------------------|-------------------------------------------|
| Linguagem              | Python 3.10+                              |
| Interface Gráfica      | CustomTkinter                             |
| IA &                   | Ollama (llama3:8b-instruct-q5_k_m)        |
| PLN                    | Sentence‑Transformers                     |
| Banco Vetorial         | ChromaDB                                  |
| Extração de Ficheiros  | PyMuPDF, EbookLib, BeautifulSoup4         |
| Testes                 | unittest                                  |
| CLI (test runner)      | Rich                                      |

---

## ⚙️ 6. Configuração e Dependências

```bash
git clone https://URL_DO_SEU_REPOSITORIO/codex-one.git
cd codex-one

# Crie e ative o ambiente virtual:
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Instale as dependências:
pip install -r requirements.txt
