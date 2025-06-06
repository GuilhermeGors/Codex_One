Codex One
1. Visão Geral do Projeto
O Codex One é uma aplicação desktop de Inteligência Artificial que cria uma base de conhecimento privada e totalmente local a partir dos seus documentos. O projeto resolve o problema de pesquisar e extrair informações de uma grande coleção de ficheiros (PDFs, ePubs) de forma intuitiva, permitindo que os utilizadores façam perguntas em linguagem natural e recebam respostas precisas, contextuais e com referências diretas às fontes originais.

A solução é baseada na arquitetura RAG (Retrieval-Augmented Generation). Em vez de depender de um LLM genérico com conhecimento vasto e público, o Codex One utiliza um LLM local que tem o seu conhecimento "aumentado" em tempo real com informações recuperadas diretamente dos documentos fornecidos pelo utilizador. Isto garante total privacidade dos dados e respostas altamente relevantes ao corpus documental específico.

Objetivos Principais
Privacidade Total: Operar 100% offline e localmente, sem que os documentos do utilizador saiam da sua máquina.

Busca Semântica Inteligente: Permitir que os utilizadores façam perguntas complexas em linguagem natural, em vez de dependerem de palavras-chave.

Respostas Contextualizadas e com Fontes: Gerar respostas precisas baseadas apenas no conteúdo dos documentos e citar claramente de onde a informação foi retirada (ficheiro e página/seção).

Suporte a Múltiplos Formatos: Iniciar com suporte para PDF e ePub, com uma arquitetura modular para expansão futura.

Interface Intuitiva: Oferecer uma interface gráfica desktop simples e amigável para gerir documentos e interagir com a IA.

2. Arquitetura da Solução de IA
O projeto pertence à área de Processamento de Linguagem Natural (PLN) e implementa um pipeline de Geração Aumentada por Recuperação (RAG).

A arquitetura é composta pelos seguintes módulos principais:

Ingestão de Dados (processing): Utiliza PyMuPDF para PDFs e EbookLib para ePubs para extrair texto bruto e metadados. O document_parser orquestra a chamada ao processador correto com base no tipo de ficheiro.

Processamento e Divisão de Texto (processing): A função dividir_texto_em_chunks no text_splitter.py divide o texto extraído em "chunks" (pedaços) menores e sobrepostos. Isto é crucial para que o modelo de embedding capture o contexto semântico de forma eficaz.

Geração de Embeddings (core): Um modelo da biblioteca Sentence-Transformers é usado para converter cada chunk de texto num vetor numérico de alta dimensão (embedding), que representa o seu significado semântico.

Armazenamento Vetorial (data_access): Os embeddings e os metadados associados (como o nome do ficheiro original, número da página/seção e o texto do chunk) são armazenados e indexados numa base de dados vetorial local usando ChromaDB.

Recuperação e Geração (core):

Quando um utilizador faz uma pergunta, esta é convertida num embedding usando o mesmo modelo.

O ChromaDB é consultado para encontrar os chunks de texto cujos embeddings são mais semanticamente similares ao embedding da pergunta (busca por similaridade de cosseno ou L2).

Estes chunks recuperados são formatados como um contexto e, juntamente com a pergunta original, são inseridos num prompt estruturado.

Este prompt é enviado para um LLM (Large Language Model) servido localmente via Ollama, que gera a resposta final baseada exclusivamente no contexto fornecido.

3. Dados
Fonte dos Dados
Não há um dataset pré-definido. O dataset é a coleção de documentos (.pdf, .epub) fornecida pelo próprio utilizador final. Isto cria uma base de conhecimento privada, tornando o Codex One uma ferramenta de pesquisa pessoal e segura.

Pré-processamento
O pipeline de pré-processamento inclui os seguintes passos:

Extração de Texto: O texto é extraído de cada página (PDF) ou seção de conteúdo (ePub).

Extração de Metadados: Título do documento, autor e número de páginas/seções são extraídos quando disponíveis.

Divisão em Chunks (Chunking): O texto de cada página/seção é dividido em pedaços sobrepostos para garantir que o contexto semântico não seja perdido nas fronteiras dos chunks.

Considerações Éticas e Vieses
Como os dados são fornecidos pelo utilizador, quaisquer vieses, incorreções ou conteúdos sensíveis presentes nos documentos de entrada serão refletidos nas respostas da IA. A aplicação opera localmente, garantindo a privacidade dos documentos do utilizador, que nunca saem da sua máquina. O utilizador é responsável pelo conteúdo que fornece ao sistema.

4. Stack Tecnológico
Linguagem: Python 3.10+

Interface Gráfica: CustomTkinter

IA & PLN: Ollama, Sentence-Transformers

Banco de Dados Vetorial: ChromaDB

Processamento de Ficheiros: PyMuPDF (PDFs), EbookLib & BeautifulSoup4 (ePubs)

Testes: unittest

CLI Visual (Test Runner): Rich

5. Configuração do Ambiente e Dependências
Para executar o projeto, é necessário configurar um ambiente Python e instalar as dependências.

Clone o repositório:

git clone https://URL_DO_SEU_REPOSITORIO/codex-one.git
cd codex-one

Crie e ative um ambiente virtual (recomendado):

# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

Instale as dependências a partir do ficheiro requirements.txt:

# requirements.txt
customtkinter
PyMuPDF
sentence-transformers
ollama
chromadb
ebooklib
beautifulsoup4
rich

Execute o seguinte comando para instalar tudo:

pip install -r requirements.txt

6. Guia de Instalação
Siga estes passos para ter o Codex One a funcionar na sua máquina:

Instale o Python: Certifique-se de que tem o Python 3.10 ou uma versão mais recente instalada.

Instale o Ollama: Faça o download e instale o Ollama de acordo com o seu sistema operativo.

Baixe um Modelo LLM: Após instalar o Ollama, execute o seguinte comando no seu terminal para baixar o modelo recomendado (ou outro da sua preferência listado na biblioteca do Ollama):

ollama pull llama3:8b-instruct-q5_k_m

Certifique-se de que o nome do modelo no seu ficheiro config.py corresponde ao modelo que você baixou.

Clone o Projeto e Instale as Dependências: Siga os passos detalhados na seção "Configuração do Ambiente e Dependências" acima.

Execute a Aplicação: Com o servidor Ollama em execução em segundo plano, inicie a aplicação principal:

python main_app.py

7. Instruções de Uso
Treinamento do Modelo
Este projeto não envolve o treinamento de modelos de IA. Ele utiliza modelos pré-treinados para embeddings (Sentence-Transformers) e para geração de linguagem (Ollama). A "aprendizagem" do sistema ocorre durante a indexação dos seus documentos.

Inferência/Predição (Uso da Aplicação)
Inicie a aplicação com python main_app.py.

Use o botão "Carregar Documento" para selecionar ficheiros .pdf ou .epub. A aplicação irá processar e indexar o ficheiro, mostrando o progresso.

Após a indexação, o ficheiro aparecerá na lista de "Documentos Indexados".

Digite a sua pergunta em linguagem natural na caixa de texto na parte direita e clique em "Enviar" ou pressione Enter.

A resposta gerada pela IA aparecerá na caixa de texto superior, e os trechos dos documentos usados como fonte aparecerão na caixa inferior.

Avaliação do Modelo
A avaliação da qualidade das respostas é, por natureza, qualitativa. Para garantir a integridade e o funcionamento correto de todos os componentes do pipeline, pode executar a suíte de testes unitários:

python run_tests.py

8. Resultados e Métricas
Como o projeto opera com dados fornecidos pelo utilizador, não há um benchmark padrão. As métricas de sucesso são qualitativas:

Métrica

Descrição

Avaliação

Relevância da Resposta

A resposta gerada aborda diretamente a pergunta do utilizador.

Inspeção manual

Factualidade

A resposta está estritamente baseada no contexto fornecido pelos documentos recuperados.

Verificação cruzada

Qualidade da Fonte

As fontes citadas são precisas e contêm a informação usada para gerar a resposta.

Inspeção manual

Tratamento de "Out-of-Scope"

O modelo responde corretamente que não sabe quando a informação não está nos documentos.

Teste com perguntas

9. Roadmap
Temos vários planos para o futuro do Codex One:

[ ] Suporte a Novos Formatos: Adicionar suporte para .docx, .txt, e .md.

[ ] Extração Melhorada: Implementar lógica para extrair texto de tabelas e, futuramente, descrições de imagens (via modelos multimodais).

[ ] Filtragem de Busca: Permitir que o utilizador selecione em quais documentos específicos deseja que a busca seja realizada.

[ ] Cache de Embeddings: Implementar um sistema de cache para evitar re-gerar embeddings para ficheiros já processados.

[ ] Melhorias na UI/UX: Refinar a interface, tornando a visualização das fontes mais interativa (ex: clicar para ver o contexto completo).

[ ] Empacotamento: Criar um executável standalone (via PyInstaller ou similar) para facilitar a distribuição e instalação.

10. Como Contribuir
As contribuições são muito bem-vindas! Se você tem ideias para novas funcionalidades, melhorias, ou encontrou um bug, sinta-se à vontade para contribuir.

Guia Rápido:

Faça um fork deste repositório.

Crie um novo branch para a sua funcionalidade ou correção (git checkout -b feature/minha-feature ou git checkout -b fix/meu-fix).

Implemente as suas alterações. Por favor, adicione testes unitários para novas funcionalidades.

Certifique-se de que todos os testes estão a passar (python run_tests.py).

Abra um Pull Request detalhando as suas alterações.

Para mais detalhes, por favor, consulte o ficheiro CONTRIBUTING.md (a ser criado).

11. Licença
Este projeto está licenciado sob a MIT License. Veja o ficheiro LICENSE.md para mais detalhes.

12. Autoria e Agradecimentos
Autores Principais
Guilherme Oliveira

Agradecimentos
Este projeto não seria possível sem o trabalho incrível das equipas por trás das seguintes tecnologias open-source:

Ollama

ChromaDB

Sentence-Transformers

CustomTkinter

PyMuPDF

EbookLib

13. Recursos Adicionais
Blog: What is Retrieval-Augmented Generation?

Paper Original do RAG (Lewis et al., 2020)

Documentação do ChromaDB

Documentação do Ollama no GitHub
