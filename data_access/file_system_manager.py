# codex_one/data_access/file_system_manager.py

import os
import shutil
from typing import List, Optional
from config import DOCUMENTS_DIR 

def ensure_documents_directory_exists():
    """Garante que o diretório de documentos do usuário exista."""
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)

def save_uploaded_file(uploaded_file_path: str, original_filename: str) -> Optional[str]:
    """
    Salva um arquivo carregado no diretório de documentos da aplicação.
    Evita sobrescrever arquivos com o mesmo nome, adicionando um sufixo numérico se necessário.
    """
    ensure_documents_directory_exists()
    
    if not original_filename:
        print("Erro: Nome do arquivo original não pode ser vazio.")
        return None

    filename, file_extension = os.path.splitext(original_filename)
    current_filename_to_save = original_filename 
    destination_path = os.path.join(DOCUMENTS_DIR, current_filename_to_save)
    
    counter = 1
    while os.path.exists(destination_path):
        current_filename_to_save = f"{filename}_{counter}{file_extension}"
        destination_path = os.path.join(DOCUMENTS_DIR, current_filename_to_save)
        counter += 1
        if counter > 100: 
            print(f"Erro: Muitas colisões de nome para {original_filename}. Abortando.")
            return None
            
    try:
        shutil.copy(uploaded_file_path, destination_path)
        print(f"Arquivo '{original_filename}' salvo como '{current_filename_to_save}' em {DOCUMENTS_DIR}")
        return destination_path 
    except IOError as e:
        print(f"Erro ao salvar o arquivo '{original_filename}': {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao salvar o arquivo '{original_filename}': {e}")
        return None

def get_document_path(filename: str) -> Optional[str]:
    """Retorna o caminho completo para um arquivo no diretório de documentos."""
    path = os.path.join(DOCUMENTS_DIR, filename)
    if os.path.exists(path):
        return path
    return None

def list_saved_documents() -> List[str]:
    """Lista todos os arquivos salvos no diretório de documentos."""
    ensure_documents_directory_exists()
    try:
        return [f for f in os.listdir(DOCUMENTS_DIR) if os.path.isfile(os.path.join(DOCUMENTS_DIR, f))]
    except OSError as e:
        print(f"Erro ao listar documentos: {e}")
        return []

def delete_saved_file(filename: str) -> bool:
    """Remove um arquivo do diretório de documentos."""
    path_to_delete = os.path.join(DOCUMENTS_DIR, filename)
    if os.path.exists(path_to_delete):
        try:
            os.remove(path_to_delete)
            print(f"Arquivo '{filename}' removido de {DOCUMENTS_DIR}")
            return True
        except OSError as e:
            print(f"Erro ao remover o arquivo '{filename}': {e}")
            return False
    else:
        print(f"Arquivo '{filename}' não encontrado para remoção.")
        return False
