# codex_one/main_app.py

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import os
import threading
import uuid # <--- CORREÇÃO 1: Adicionado import uuid
from typing import List, Dict, Optional, Any, Callable 

from nucleo_rag import gerenciador_arquivos
from nucleo_rag import banco_vetorial_chroma 
from nucleo_rag import pipeline_rag # Certifique-se que indexar_documento_pdf aqui aceita 3 args
from config import ensure_directories_exist, DOCUMENTS_DIR, OLLAMA_MODEL

ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue") 

class CodexOneApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Codex One - IA de Documentos (Modelo: {OLLAMA_MODEL})")
        self.geometry("1100x700") 
        self.minsize(800, 600)

        ensure_directories_exist() 
        self.db_collection = banco_vetorial_chroma.initialize_vector_db()
        if not self.db_collection:
            messagebox.showerror("Erro Crítico", 
                                 "Não foi possível inicializar a base de dados vetorial (ChromaDB).\n"
                                 "Verifique os logs e a configuração do ChromaDB.")
            self.after(100, self.destroy) 
            return

        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=3) 
        self.grid_rowconfigure(0, weight=1)

        self.frame_esquerda = ctk.CTkFrame(self, width=350)
        self.frame_esquerda.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.frame_esquerda.grid_rowconfigure(1, weight=1) 
        self.frame_esquerda.grid_rowconfigure(3, weight=0) 

        self.frame_direita = ctk.CTkFrame(self)
        self.frame_direita.grid(row=0, column=1, padx=(0,10), pady=10, sticky="nsew")
        self.frame_direita.grid_rowconfigure(1, weight=1) 
        self.frame_direita.grid_columnconfigure(0, weight=1)

        # --- Widgets no Frame da Esquerda ---
        self.label_documentos = ctk.CTkLabel(self.frame_esquerda, text="Documentos Indexados", font=ctk.CTkFont(size=16, weight="bold"))
        self.label_documentos.grid(row=0, column=0, columnspan=3, padx=10, pady=(10,5), sticky="ew")
        
        self.tree_documentos = ttk.Treeview(self.frame_esquerda, columns=("nome", "chunks"), show="headings", height=10)
        self.tree_documentos.heading("nome", text="Nome do Arquivo")
        self.tree_documentos.heading("chunks", text="Chunks")
        self.tree_documentos.column("nome", width=200, anchor="w")
        self.tree_documentos.column("chunks", width=50, anchor="center")
        self.tree_documentos.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        
        self.scrollbar_tree = ctk.CTkScrollbar(self.frame_esquerda, command=self.tree_documentos.yview)
        self.scrollbar_tree.grid(row=1, column=2, padx=(0,10), pady=5, sticky="ns")
        self.tree_documentos.configure(yscrollcommand=self.scrollbar_tree.set)

        self.botao_carregar_pdf = ctk.CTkButton(self.frame_esquerda, text="Carregar PDF", command=self.iniciar_carregamento_pdf)
        self.botao_carregar_pdf.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.botao_remover_pdf = ctk.CTkButton(self.frame_esquerda, text="Remover Selecionado", command=self.remover_documento_selecionado, fg_color="tomato")
        self.botao_remover_pdf.grid(row=2, column=1, columnspan=2, padx=10, pady=10, sticky="ew")
        
        self.progress_bar_indexacao = ctk.CTkProgressBar(self.frame_esquerda, orientation="horizontal", mode="determinate")
        self.progress_bar_indexacao.set(0) 
        self.progress_bar_indexacao.grid(row=3, column=0, columnspan=3, padx=10, pady=(5,0), sticky="ew")
        
        self.status_bar_esquerda = ctk.CTkLabel(self.frame_esquerda, text="Pronto.", anchor="w")
        self.status_bar_esquerda.grid(row=4, column=0, columnspan=3, padx=10, pady=(0,10), sticky="ew")

        # --- Widgets no Frame da Direita ---
        self.label_chat = ctk.CTkLabel(self.frame_direita, text="Faça sua Pergunta ao Codex One", font=ctk.CTkFont(size=16, weight="bold"))
        self.label_chat.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")

        self.textbox_resposta = ctk.CTkTextbox(self.frame_direita, wrap="word", state="disabled", height=200)
        self.textbox_resposta.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        self.label_fontes = ctk.CTkLabel(self.frame_direita, text="Fontes Relevantes:", font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        self.label_fontes.grid(row=2, column=0, padx=10, pady=(10,0), sticky="ew")
        
        self.textbox_fontes = ctk.CTkTextbox(self.frame_direita, wrap="word", state="disabled", height=100)
        self.textbox_fontes.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")

        self.frame_entrada_pergunta = ctk.CTkFrame(self.frame_direita, fg_color="transparent")
        self.frame_entrada_pergunta.grid(row=4, column=0, padx=10, pady=(5,10), sticky="ew")
        self.frame_entrada_pergunta.grid_columnconfigure(0, weight=1)

        self.entry_pergunta = ctk.CTkEntry(self.frame_entrada_pergunta, placeholder_text="Digite sua pergunta aqui...")
        self.entry_pergunta.grid(row=0, column=0, padx=(0,10), pady=0, sticky="ew")
        self.entry_pergunta.bind("<Return>", self.enviar_pergunta_evento)

        self.botao_enviar = ctk.CTkButton(self.frame_entrada_pergunta, text="Enviar", width=100, command=self.enviar_pergunta_em_thread)
        self.botao_enviar.grid(row=0, column=1, pady=0, sticky="e")
        
        self.atualizar_lista_documentos()

    def _safe_update_gui(self, func: Callable, *args, **kwargs): # <--- CORREÇÃO 3: Adicionado **kwargs
        """Chama uma função de atualização da GUI de forma segura a partir de uma thread."""
        try:
            if self.winfo_exists(): 
                # Usar lambda para passar corretamente args e kwargs para a função agendada
                self.after(0, lambda func=func, args=args, kwargs=kwargs: func(*args, **kwargs))
        except Exception as e:
            print(f"Erro ao agendar atualização da GUI: {e}")


    def gui_atualizar_progresso_indexacao(self, mensagem: str, progresso: float):
        if progresso < 0: 
            self.status_bar_esquerda.configure(text=f"Erro: {mensagem}", text_color="tomato")
            self.progress_bar_indexacao.set(0)
            self.botao_carregar_pdf.configure(state="normal") 
        elif progresso >= 1.0:
            self.status_bar_esquerda.configure(text=mensagem, text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"])
            self.progress_bar_indexacao.set(1.0)
            self.after(2000, lambda: self.progress_bar_indexacao.set(0)) 
            self.botao_carregar_pdf.configure(state="normal")
        else:
            self.status_bar_esquerda.configure(text=f"{mensagem} ({progresso*100:.0f}%)", text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"])
            self.progress_bar_indexacao.set(progresso)

    def _tarefa_indexacao_pdf(self, caminho_fisico_pdf: str, nome_original_pdf: str):
        # Certifique-se que pipeline_rag.indexar_documento_pdf aceita 3 argumentos
        # incluindo o callback de progresso.
        sucesso_indexacao = pipeline_rag.indexar_documento_pdf(
            caminho_fisico_pdf, 
            nome_original_pdf,
            lambda msg, prog: self._safe_update_gui(self.gui_atualizar_progresso_indexacao, msg, prog)
        )
        
        if sucesso_indexacao:
            self._safe_update_gui(messagebox.showinfo, "Sucesso", f"Documento '{nome_original_pdf}' carregado e indexado com sucesso!")
            self._safe_update_gui(self.atualizar_lista_documentos)
        else:
            self._safe_update_gui(messagebox.showerror, "Erro de Indexação", f"Falha ao indexar o documento '{nome_original_pdf}'. Verifique os logs do console.")
        
        # Correção 3 aplicada aqui também para o configure
        self._safe_update_gui(self.botao_carregar_pdf.configure, state="normal")
        if sucesso_indexacao:
             self._safe_update_gui(self.status_bar_esquerda.configure, text="Pronto.")


    def iniciar_carregamento_pdf(self):
        self.status_bar_esquerda.configure(text="Selecionando arquivo PDF...")
        filepath = filedialog.askopenfilename(
            title="Selecionar Arquivo PDF",
            filetypes=(("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*"))
        )
        if not filepath:
            self.status_bar_esquerda.configure(text="Nenhum arquivo selecionado.")
            return

        original_filename = os.path.basename(filepath)
        
        self.status_bar_esquerda.configure(text=f"Preparando '{original_filename}'...")
        self.update_idletasks()
        caminho_salvo = gerenciador_arquivos.save_uploaded_file(filepath, original_filename)
        
        if not caminho_salvo:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar o arquivo '{original_filename}'.")
            self.status_bar_esquerda.configure(text="Erro ao salvar arquivo.")
            return
        
        nome_arquivo_salvo_no_sistema = os.path.basename(caminho_salvo)

        self.botao_carregar_pdf.configure(state="disabled")
        self.progress_bar_indexacao.set(0) 
        self.status_bar_esquerda.configure(text=f"Iniciando indexação de '{nome_arquivo_salvo_no_sistema}'...")

        thread_indexacao = threading.Thread(
            target=self._tarefa_indexacao_pdf, 
            args=(caminho_salvo, nome_arquivo_salvo_no_sistema), 
            daemon=True 
        )
        thread_indexacao.start()

    def _get_sort_key_for_documents(self, doc_info: Optional[Dict[str, Any]]) -> str:
        if not isinstance(doc_info, dict):
            return "" 
        
        nome_arquivo = doc_info.get('nome_arquivo')
        return str(nome_arquivo) if nome_arquivo is not None else ""

    def atualizar_lista_documentos(self):
        for i in self.tree_documentos.get_children():
            self.tree_documentos.delete(i)
        
        if not self.db_collection:
            self.status_bar_esquerda.configure(text="DB não inicializado para listar.")
            return
            
        try:
            documentos_info = banco_vetorial_chroma.get_all_document_infos(self.db_collection)
            
            if documentos_info:
                for doc_info in sorted(documentos_info, key=self._get_sort_key_for_documents):
                    nome_exibicao = doc_info.get('nome_arquivo', 'Nome Desconhecido')
                    num_chunks = doc_info.get('numero_chunks', 0)
                    doc_id_original = str(doc_info.get('doc_id_original', uuid.uuid4())) # <--- CORREÇÃO 1: uuid.uuid4() usado aqui
                    self.tree_documentos.insert("", "end", iid=doc_id_original, values=(nome_exibicao, num_chunks))
            self.status_bar_esquerda.configure(text=f"{len(documentos_info) if documentos_info else 0} documentos carregados.")
        except Exception as e:
            self.status_bar_esquerda.configure(text="Erro ao listar documentos.")
            print(f"Erro ao atualizar lista de documentos: {e}") 

    def remover_documento_selecionado(self):
        selecionado = self.tree_documentos.selection() 
        if not selecionado:
            messagebox.showwarning("Nenhum Documento", "Por favor, selecione um documento da lista para remover.")
            return

        doc_id_original_para_remover = selecionado[0] 
        try:
            item_values = self.tree_documentos.item(doc_id_original_para_remover, "values")
            if not item_values: 
                messagebox.showerror("Erro", "Não foi possível obter informações do documento selecionado.")
                return
            nome_arquivo_para_mensagem = item_values[0]
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível obter nome do documento selecionado: {e}")
            return

        confirmar = messagebox.askyesno("Confirmar Remoção", 
                                        f"Tem certeza que deseja remover o documento '{nome_arquivo_para_mensagem}' e todos os seus dados indexados?")
        if not confirmar:
            return

        self.status_bar_esquerda.configure(text=f"Removendo '{nome_arquivo_para_mensagem}'...")
        self.update_idletasks()

        sucesso_db = banco_vetorial_chroma.delete_document_chunks(self.db_collection, doc_id_original_para_remover)
        sucesso_fs = gerenciador_arquivos.delete_saved_file(nome_arquivo_para_mensagem)

        if sucesso_db and sucesso_fs:
            messagebox.showinfo("Sucesso", f"Documento '{nome_arquivo_para_mensagem}' removido com sucesso.")
            self.status_bar_esquerda.configure(text=f"'{nome_arquivo_para_mensagem}' removido.")
        elif sucesso_db and not sucesso_fs:
            messagebox.showwarning("Remoção Parcial", f"Dados indexados de '{nome_arquivo_para_mensagem}' removidos, mas o arquivo físico não foi encontrado ou não pôde ser deletado.")
            self.status_bar_esquerda.configure(text=f"Dados de '{nome_arquivo_para_mensagem}' removidos; arquivo físico não.")
        else: 
            messagebox.showerror("Erro ao Remover", f"Falha ao remover os dados indexados do documento '{nome_arquivo_para_mensagem}'. O arquivo físico pode ou não ter sido removido.")
            self.status_bar_esquerda.configure(text=f"Erro ao remover dados de '{nome_arquivo_para_mensagem}'.")
            
        self.atualizar_lista_documentos()

    def exibir_resposta_e_fontes(self, resposta_llm: str, fontes: List[Dict[str, Any]]):
        self.textbox_resposta.configure(state="normal")
        self.textbox_resposta.delete("1.0", "end")
        self.textbox_resposta.insert("1.0", resposta_llm)
        self.textbox_resposta.configure(state="disabled")

        self.textbox_fontes.configure(state="normal")
        self.textbox_fontes.delete("1.0", "end")
        if fontes:
            texto_fontes = ""
            for i, fonte_info in enumerate(fontes):
                texto_fontes += f"Fonte {i+1}:\n"
                texto_fontes += f"  Arquivo: {fonte_info.get('nome_arquivo', 'N/A')}\n"
                texto_fontes += f"  Página: {fonte_info.get('pagina', 'N/A')}\n"
                if fonte_info.get('titulo_documento'):
                    texto_fontes += f"  Título Doc: {fonte_info.get('titulo_documento')}\n"
                if fonte_info.get('autor_documento'):
                    texto_fontes += f"  Autor Doc: {fonte_info.get('autor_documento')}\n"
                texto_fontes += f"  Trecho Relevante: {fonte_info.get('texto_chunk_relevante', '')}\n\n"
            self.textbox_fontes.insert("1.0", texto_fontes)
        else:
            self.textbox_fontes.insert("1.0", "Nenhuma fonte específica encontrada para esta resposta.")
        self.textbox_fontes.configure(state="disabled")

    def _tarefa_pesquisa_resposta(self, pergunta: str):
        try:
            resultado = pipeline_rag.pesquisar_e_responder(pergunta)
            if resultado:
                self._safe_update_gui(self.exibir_resposta_e_fontes, 
                                      resultado.get("resposta", "Erro ao obter resposta."), 
                                      resultado.get("fontes", []))
            else:
                self._safe_update_gui(self.exibir_resposta_e_fontes, "Ocorreu um erro ao processar sua pergunta.", [])
                self._safe_update_gui(messagebox.showerror, "Erro na Pesquisa", "Não foi possível obter uma resposta do pipeline RAG.")
        except Exception as e:
            print(f"Erro na thread de pesquisa: {e}")
            self._safe_update_gui(self.exibir_resposta_e_fontes, f"Erro crítico ao processar sua pergunta: {e}", [])
            self._safe_update_gui(messagebox.showerror, "Erro Crítico", f"Um erro inesperado ocorreu: {e}")
        finally:
            # Correção 3 aplicada aqui também
            self._safe_update_gui(self.botao_enviar.configure, state="normal")
            self._safe_update_gui(self.entry_pergunta.configure, state="normal")

    def enviar_pergunta_em_thread(self):
        pergunta = self.entry_pergunta.get().strip()
        if not pergunta:
            messagebox.showwarning("Pergunta Vazia", "Por favor, digite uma pergunta.")
            return

        self.textbox_resposta.configure(state="normal")
        self.textbox_resposta.delete("1.0", "end")
        self.textbox_resposta.insert("1.0", "Processando sua pergunta...\nPor favor, aguarde.")
        self.textbox_resposta.configure(state="disabled")
        self.textbox_fontes.configure(state="normal")
        self.textbox_fontes.delete("1.0", "end")
        self.textbox_fontes.insert("1.0", "Buscando informações...")
        self.textbox_fontes.configure(state="disabled")
        
        self.botao_enviar.configure(state="disabled")
        self.entry_pergunta.configure(state="disabled") 
        self.update_idletasks() 

        thread_pesquisa = threading.Thread(
            target=self._tarefa_pesquisa_resposta,
            args=(pergunta,),
            daemon=True
        )
        thread_pesquisa.start()

    def enviar_pergunta_evento(self, event=None): 
        if self.botao_enviar.cget("state") == "normal": 
            self.enviar_pergunta_em_thread()

if __name__ == "__main__":
    app = CodexOneApp()
    app.mainloop()
