# codex_one/nucleo_rag/banco_sqlite.py

import sqlite3
import json
import os
import platform # Para ajudar a determinar o nome do arquivo da extensão
from ..config import DATABASE_PATH, SENTENCE_TRANSFORMER_MODEL

EMBEDDING_DIMENSION = 768 # Para all-mpnet-base-v2. Ajuste se usar outro modelo.
                        # Para mxbai-embed-large (Ollama), seria 1024.

def get_vss_extension_path():
    """Determina o caminho para o arquivo da extensão SQLite VSS."""
    system = platform.system()
    # machine = platform.machine() # ex: 'AMD64', 'arm64'

    # Caminho relativo da pasta 'nucleo_rag' para a raiz do projeto 'codex_one'
    # Onde esperamos que o .dll/.so/.dylib esteja.
    base_path_to_extension = ".." # Sobe um nível de 'nucleo_rag' para 'codex_one'

    if system == "Windows":
        # Assumindo que o arquivo DLL (ex: vss0.dll) foi colocado na pasta raiz 'codex_one'
        return os.path.join(base_path_to_extension, "vss0.dll")
    elif system == "Linux":
        # Assumindo que o arquivo SO (ex: vss0.so) foi colocado na pasta raiz 'codex_one'
        return os.path.join(base_path_to_extension, "vss0.so")
    elif system == "Darwin": # macOS
        # Assumindo que o arquivo DYLIB (ex: vss0.dylib) foi colocado na pasta raiz 'codex_one'
        return os.path.join(base_path_to_extension, "vss0.dylib")
    
    # Fallback se o sistema não for reconhecido, tenta carregar 'vss0' diretamente
    # Isso pode funcionar se 'vss0' estiver no PATH do sistema ou no diretório de trabalho atual
    # quando o script é executado a partir da raiz do projeto.
    # No entanto, é mais robusto especificar o caminho.
    print(f"Sistema operacional '{system}' não explicitamente coberto para caminho da extensão VSS. Tentando 'vss0'.")
    return "vss0"


SQLITE_VSS_EXTENSION_PATH = get_vss_extension_path()

def load_vss_extension(conn):
    """
    Tenta carregar a extensão sqlite-vss.
    É crucial que o arquivo da extensão (ex: vss0.dll) esteja acessível.
    """
    conn.enable_load_extension(True)
    try:
        # O caminho é relativo ao diretório de onde o script Python é executado.
        # Se main_app.py (na raiz do projeto) importa e chama funções de banco_sqlite.py,
        # o caminho relativo em SQLITE_VSS_EXTENSION_PATH deve ser a partir da raiz do projeto.
        # Se banco_sqlite.py for executado diretamente (como no if __name__ == '__main__'),
        # o caminho relativo será a partir de nucleo_rag.
        # Para ser mais robusto, podemos construir um caminho absoluto.

        # Construindo um caminho absoluto para a extensão a partir da localização de banco_sqlite.py
        # __file__ é o caminho para banco_sqlite.py
        # os.path.dirname(__file__) é 'codex_one/nucleo_rag'
        # os.path.join(os.path.dirname(__file__), SQLITE_VSS_EXTENSION_PATH)
        # Se SQLITE_VSS_EXTENSION_PATH for "../vss0.dll", isso resultará em
        # 'codex_one/nucleo_rag/../vss0.dll' que simplifica para 'codex_one/vss0.dll'
        
        # Caminho da extensão relativo ao local deste arquivo (banco_sqlite.py)
        # Se vss0.dll está em 'codex_one/', e banco_sqlite.py está em 'codex_one/nucleo_rag/'
        # então o caminho relativo de banco_sqlite.py para vss0.dll é '../vss0.dll'
        
        # Se você colocou o vss0.dll na pasta 'codex_one/':
        actual_extension_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vss0.dll"))
        # Ajuste "vss0.dll" para o nome exato do seu arquivo se for diferente (ex: vss0.so para Linux)
        if platform.system() == "Linux":
            actual_extension_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vss0.so"))
        elif platform.system() == "Darwin":
            actual_extension_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vss0.dylib"))


        print(f"Tentando carregar extensão VSS de: {actual_extension_path}")
        conn.load_extension(actual_extension_path)
        print(f"Extensão SQLite VSS ({actual_extension_path}) carregada com sucesso.")
    except sqlite3.OperationalError as e:
        print(f"Falha ao carregar a extensão SQLite VSS ({actual_extension_path if 'actual_extension_path' in locals() else SQLITE_VSS_EXTENSION_PATH}): {e}")
        print("Verifique se:")
        print(f"1. O arquivo da extensão está em: {actual_extension_path if 'actual_extension_path' in locals() else 'CAMINHO_ESPERADO'}")
        print("2. O nome do arquivo está correto (vss0.dll, vss0.so, vss0.dylib).")
        print("3. A arquitetura da extensão (32/64 bits) corresponde à do seu Python.")
        print("4. Você tem as dependências necessárias (ex: Microsoft VC++ Redistributable no Windows).")
        print("Consulte a documentação do sqlite-vss para instruções de instalação.")
    conn.enable_load_extension(False)


def get_db_connection():
    """Estabelece conexão com o banco de dados SQLite e carrega a extensão VSS."""
    try:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        load_vss_extension(conn) # Carrega a extensão aqui
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados SQLite: {e}")
        return None

def create_tables(conn):
    """Cria as tabelas necessárias no banco de dados se não existirem."""
    if not conn:
        return

    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documentos (
                id_documento INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_arquivo TEXT NOT NULL UNIQUE,
                caminho_arquivo TEXT NOT NULL,
                autor TEXT,
                titulo TEXT,
                data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                numero_chunks INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id_chunk INTEGER PRIMARY KEY AUTOINCREMENT,
                id_documento_fk INTEGER NOT NULL,
                texto_chunk TEXT NOT NULL,
                numero_pagina INTEGER,
                embedding_json TEXT, 
                FOREIGN KEY (id_documento_fk) REFERENCES documentos (id_documento) ON DELETE CASCADE
            )
        """)
        cursor.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vss_chunks USING vss0(
                chunk_embedding({EMBEDDING_DIMENSION})
            )
        """)
        conn.commit()
        print("Tabelas verificadas/criadas com sucesso.")
    except sqlite3.Error as e:
        print(f"Erro ao criar tabelas: {e}")
        if "no such module: vss0" in str(e).lower():
            print("ERRO: O módulo vss0 não foi encontrado. Isso significa que a extensão SQLite VSS não foi carregada corretamente.")
            print("Verifique as mensagens da função 'load_vss_extension' para mais detalhes.")
    finally:
        cursor.close()

# ... (o restante do arquivo banco_sqlite.py permanece o mesmo) ...
def add_document(conn, nome_arquivo, caminho_arquivo, autor=None, titulo=None):
    """Adiciona um novo documento à tabela 'documentos'."""
    if not conn:
        return None
    sql = """
        INSERT INTO documentos (nome_arquivo, caminho_arquivo, autor, titulo)
        VALUES (?, ?, ?, ?)
    """
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (nome_arquivo, caminho_arquivo, autor, titulo))
        conn.commit()
        doc_id = cursor.lastrowid
        print(f"Documento '{nome_arquivo}' adicionado com ID: {doc_id}")
        return doc_id
    except sqlite3.IntegrityError:
        print(f"Documento '{nome_arquivo}' já existe no banco de dados.")
        cursor.execute("SELECT id_documento FROM documentos WHERE nome_arquivo = ?", (nome_arquivo,))
        result = cursor.fetchone()
        return result['id_documento'] if result else None
    except sqlite3.Error as e:
        print(f"Erro ao adicionar documento '{nome_arquivo}': {e}")
        return None
    finally:
        cursor.close()

def get_document_id(conn, caminho_arquivo):
    """Recupera o ID de um documento pelo seu caminho."""
    if not conn: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id_documento FROM documentos WHERE caminho_arquivo = ?", (caminho_arquivo,))
        result = cursor.fetchone()
        return result['id_documento'] if result else None
    except sqlite3.Error as e:
        print(f"Erro ao buscar ID do documento '{caminho_arquivo}': {e}")
        return None
    finally:
        cursor.close()

def delete_document(conn, doc_id):
    """Remove um documento e seus chunks associados do banco de dados."""
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id_chunk FROM chunks WHERE id_documento_fk = ?", (doc_id,))
        chunk_ids_to_delete = [row['id_chunk'] for row in cursor.fetchall()]

        if chunk_ids_to_delete:
            placeholders = ','.join('?' for _ in chunk_ids_to_delete)
            cursor.execute(f"DELETE FROM vss_chunks WHERE rowid IN ({placeholders})", chunk_ids_to_delete)
            print(f"Embeddings de {len(chunk_ids_to_delete)} chunks removidos da vss_chunks para doc_id {doc_id}.")

        cursor.execute("DELETE FROM documentos WHERE id_documento = ?", (doc_id,))
        conn.commit()
        print(f"Documento com ID {doc_id} e seus chunks associados foram removidos.")
        return True
    except sqlite3.Error as e:
        print(f"Erro ao deletar documento com ID {doc_id}: {e}")
        conn.rollback() 
        return False
    finally:
        cursor.close()

def add_chunk(conn, doc_id, texto_chunk, embedding, numero_pagina=None):
    """Adiciona um chunk de texto e seu embedding ao banco de dados."""
    if not conn: return None
    
    embedding_json = json.dumps(embedding) 

    cursor = conn.cursor()
    try:
        sql_chunks = """
            INSERT INTO chunks (id_documento_fk, texto_chunk, numero_pagina, embedding_json)
            VALUES (?, ?, ?, ?)
        """
        cursor.execute(sql_chunks, (doc_id, texto_chunk, numero_pagina, embedding_json))
        chunk_id = cursor.lastrowid 
        
        cursor.execute("INSERT INTO vss_chunks (rowid, chunk_embedding) VALUES (?, ?)", (chunk_id, embedding))
        conn.commit()
        
        cursor.execute("UPDATE documentos SET numero_chunks = numero_chunks + 1 WHERE id_documento = ?", (doc_id,))
        conn.commit()

        print(f"Chunk adicionado com ID {chunk_id} para o documento ID {doc_id}.")
        return chunk_id
    except sqlite3.Error as e:
        print(f"Erro ao adicionar chunk para o documento ID {doc_id}: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()

def find_similar_chunks(conn, query_embedding, top_k=3):
    """Encontra os chunks mais similares ao embedding da consulta."""
    if not conn: return []
    
    cursor = conn.cursor()
    try:
        sql = f"""
            SELECT
                c.id_chunk,
                c.id_documento_fk,
                c.texto_chunk,
                c.numero_pagina,
                d.nome_arquivo,
                d.autor,
                d.titulo,
                v.distance
            FROM vss_chunks v
            JOIN chunks c ON v.rowid = c.id_chunk
            JOIN documentos d ON c.id_documento_fk = d.id_documento
            WHERE vss_search(v.chunk_embedding, ?)
            ORDER BY v.distance
            LIMIT ?
        """
        cursor.execute(sql, (query_embedding, top_k))
        
        results = cursor.fetchall()
        return results
    except sqlite3.Error as e:
        print(f"Erro ao buscar chunks similares: {e}")
        return []
    finally:
        cursor.close()

def get_all_documents(conn):
    """Recupera todos os documentos da tabela 'documentos'."""
    if not conn: return []
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id_documento, nome_arquivo, autor, titulo, data_upload, numero_chunks FROM documentos ORDER BY nome_arquivo")
        documents = cursor.fetchall()
        return [dict(doc) for doc in documents] 
    except sqlite3.Error as e:
        print(f"Erro ao buscar todos os documentos: {e}")
        return []
    finally:
        cursor.close()

def get_document_path(conn, doc_id):
    """Recupera o caminho de um arquivo de documento pelo seu ID."""
    if not conn: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT caminho_arquivo FROM documentos WHERE id_documento = ?", (doc_id,))
        result = cursor.fetchone()
        return result['caminho_arquivo'] if result else None
    except sqlite3.Error as e:
        print(f"Erro ao buscar caminho do documento ID {doc_id}: {e}")
        return None
    finally:
        cursor.close()

def get_document_details(conn, doc_id):
    """Recupera detalhes de um documento pelo seu ID."""
    if not conn: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM documentos WHERE id_documento = ?", (doc_id,))
        result = cursor.fetchone()
        return dict(result) if result else None
    except sqlite3.Error as e:
        print(f"Erro ao buscar detalhes do documento ID {doc_id}: {e}")
        return None
    finally:
        cursor.close()


if __name__ == '__main__':
    print("Testando módulo banco_sqlite.py...")
    from ..config import ensure_directories_exist
    ensure_directories_exist()

    conn = get_db_connection()
    if conn:
        create_tables(conn)
        
        doc_id1 = add_document(conn, "teste1.pdf", "/caminho/para/teste1.pdf", "Autor Teste", "Título Teste")
        doc_id2 = add_document(conn, "teste2.pdf", "/caminho/para/teste2.pdf", "Outro Autor", "Outro Título")
        
        if doc_id1:
            print(f"Documento 1 ID: {doc_id1}")
            dummy_embedding1 = [0.1] * EMBEDDING_DIMENSION 
            dummy_embedding2 = [0.2] * EMBEDDING_DIMENSION
            add_chunk(conn, doc_id1, "Este é o primeiro chunk do documento 1.", dummy_embedding1, 1)
            add_chunk(conn, doc_id1, "Este é o segundo chunk do documento 1.", dummy_embedding2, 2)

        if doc_id2:
            print(f"Documento 2 ID: {doc_id2}")
            dummy_embedding3 = [0.3] * EMBEDDING_DIMENSION
            add_chunk(conn, doc_id2, "Chunk único do documento 2.", dummy_embedding3, 1)

        print("\nTodos os documentos:")
        all_docs = get_all_documents(conn)
        for doc in all_docs:
            print(f"- ID: {doc['id_documento']}, Nome: {doc['nome_arquivo']}, Chunks: {doc['numero_chunks']}")

        if doc_id1: 
            query_emb = [0.11] * EMBEDDING_DIMENSION 
            print("\nBuscando chunks similares a um embedding de exemplo:")
            similar_chunks = find_similar_chunks(conn, query_emb, top_k=2)
            if similar_chunks:
                for chunk_info in similar_chunks:
                    print(f"  - Chunk ID: {chunk_info['id_chunk']}, Doc: {chunk_info['nome_arquivo']}, Texto: '{chunk_info['texto_chunk'][:30]}...', Dist: {chunk_info['distance']:.4f}")
            else:
                print("  Nenhum chunk similar encontrado ou erro na busca.")
        
        if doc_id1:
            details = get_document_details(conn, doc_id1)
            print(f"\nDetalhes do Documento ID {doc_id1}: {details}")

        conn.close()
    else:
        print("Não foi possível conectar ao banco de dados.")
