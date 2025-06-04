# codex_one/nucleo_rag/gerenciador_arquivos.py

import os
import shutil
from typing import List, Optional

from config import DOCUMENTS_DIR # Importa o diretório configurado para os documentos

def ensure_documents_directory_exists():
    """Garante que o diretório de documentos do usuário exista."""
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)

def save_uploaded_file(uploaded_file_path: str, original_filename: str) -> Optional[str]:
    """
    Salva um arquivo carregado no diretório de documentos da aplicação.
    Evita sobrescrever arquivos com o mesmo nome, adicionando um sufixo numérico se necessário.

    Args:
        uploaded_file_path (str): O caminho temporário do arquivo carregado.
        original_filename (str): O nome original do arquivo.

    Returns:
        Optional[str]: O caminho completo para o arquivo salvo, ou None se ocorrer um erro.
    """
    ensure_documents_directory_exists()
    
    if not original_filename:
        print("Erro: Nome do arquivo original não pode ser vazio.")
        return None

    filename, file_extension = os.path.splitext(original_filename)
    destination_path = os.path.join(DOCUMENTS_DIR, original_filename)
    
    # Lida com colisões de nome de arquivo
    counter = 1
    while os.path.exists(destination_path):
        new_filename = f"{filename}_{counter}{file_extension}"
        destination_path = os.path.join(DOCUMENTS_DIR, new_filename)
        counter += 1
        if counter > 100: # Limite para evitar loop infinito em caso de erro estranho
            print(f"Erro: Muitas colisões de nome para {original_filename}. Abortando.")
            return None
            
    try:
        shutil.copy(uploaded_file_path, destination_path)
        print(f"Arquivo '{original_filename}' salvo como '{os.path.basename(destination_path)}' em {DOCUMENTS_DIR}")
        return destination_path
    except IOError as e:
        print(f"Erro ao salvar o arquivo '{original_filename}': {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao salvar o arquivo '{original_filename}': {e}")
        return None

def get_document_path(filename: str) -> Optional[str]:
    """
    Retorna o caminho completo para um arquivo no diretório de documentos.

    Args:
        filename (str): O nome do arquivo (pode ser o nome original ou o nome salvo com sufixo).

    Returns:
        Optional[str]: O caminho completo se o arquivo existir, caso contrário None.
    """
    path = os.path.join(DOCUMENTS_DIR, filename)
    if os.path.exists(path):
        return path
    return None

def list_saved_documents() -> List[str]:
    """
    Lista todos os arquivos salvos no diretório de documentos.

    Returns:
        List[str]: Uma lista com os nomes dos arquivos.
    """
    ensure_documents_directory_exists()
    try:
        return [f for f in os.listdir(DOCUMENTS_DIR) if os.path.isfile(os.path.join(DOCUMENTS_DIR, f))]
    except OSError as e:
        print(f"Erro ao listar documentos: {e}")
        return []

def delete_saved_file(filename: str) -> bool:
    """
    Remove um arquivo do diretório de documentos.

    Args:
        filename (str): O nome do arquivo a ser removido.

    Returns:
        bool: True se o arquivo foi removido com sucesso, False caso contrário.
    """
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

# --- Bloco de Teste ---
if __name__ == '__main__':
    print("Testando módulo gerenciador_arquivos.py...")

    # Garante que os diretórios de configuração existam (incluindo DOCUMENTS_DIR)
    from config import ensure_directories_exist as ensure_all_project_dirs_exist
    ensure_all_project_dirs_exist() # Chama a função do config.py para criar todos os diretórios necessários

    # Criar um arquivo de teste temporário para simular um upload
    temp_dir = "temp_test_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    test_file_content1 = "Este é um arquivo de teste PDF 1."
    temp_file_path1 = os.path.join(temp_dir, "meu_documento.pdf")
    with open(temp_file_path1, "w", encoding="utf-8") as f:
        f.write(test_file_content1)

    test_file_content2 = "Este é um arquivo de teste PDF 2, com o mesmo nome."
    temp_file_path2 = os.path.join(temp_dir, "outro_documento.txt") # Nome diferente para teste
    with open(temp_file_path2, "w", encoding="utf-8") as f:
        f.write(test_file_content2)

    # Teste de salvar arquivo
    print("\n--- Teste de Salvar Arquivo ---")
    saved_path1 = save_uploaded_file(temp_file_path1, "meu_documento.pdf")
    if saved_path1:
        print(f"Arquivo 1 salvo em: {saved_path1}")
        assert os.path.exists(saved_path1)
    
    saved_path2 = save_uploaded_file(temp_file_path2, "outro_documento.txt")
    if saved_path2:
        print(f"Arquivo 2 salvo em: {saved_path2}")
        assert os.path.exists(saved_path2)

    # Teste de salvar arquivo com nome duplicado
    print("\n--- Teste de Salvar Arquivo com Nome Duplicado ---")
    temp_file_path_dup = os.path.join(temp_dir, "meu_documento_duplicado.pdf")
    with open(temp_file_path_dup, "w", encoding="utf-8") as f:
        f.write("Conteúdo do duplicado.")
    
    saved_path_dup = save_uploaded_file(temp_file_path_dup, "meu_documento.pdf") # Tenta salvar com o mesmo nome original
    if saved_path_dup:
        print(f"Arquivo duplicado salvo como: {os.path.basename(saved_path_dup)}")
        assert os.path.exists(saved_path_dup)
        assert os.path.basename(saved_path_dup) != "meu_documento.pdf" # Deve ter sido renomeado

    # Teste de listar arquivos
    print("\n--- Teste de Listar Arquivos ---")
    saved_files = list_saved_documents()
    print(f"Arquivos salvos: {saved_files}")
    assert len(saved_files) >= 2 # Pelo menos os dois primeiros devem estar lá

    # Teste de obter caminho
    print("\n--- Teste de Obter Caminho ---")
    if saved_path1:
        retrieved_path = get_document_path(os.path.basename(saved_path1))
        print(f"Caminho recuperado para '{os.path.basename(saved_path1)}': {retrieved_path}")
        assert retrieved_path == saved_path1

    # Teste de deletar arquivo
    print("\n--- Teste de Deletar Arquivo ---")
    if saved_path2:
        filename_to_delete = os.path.basename(saved_path2)
        success_delete = delete_saved_file(filename_to_delete)
        print(f"Tentativa de deletar '{filename_to_delete}': {'Sucesso' if success_delete else 'Falha'}")
        assert success_delete
        assert not os.path.exists(saved_path2)
        
        # Tentar deletar novamente (deve falhar)
        success_delete_again = delete_saved_file(filename_to_delete)
        print(f"Tentativa de deletar '{filename_to_delete}' novamente: {'Sucesso' if success_delete_again else 'Falha'}")
        assert not success_delete_again

    # Limpar arquivos de teste e diretório temporário
    print("\nLimpando arquivos de teste...")
    if saved_path1 and os.path.exists(saved_path1):
        os.remove(saved_path1)
    if saved_path_dup and os.path.exists(saved_path_dup):
        os.remove(saved_path_dup)
    # Os arquivos dentro de temp_dir
    os.remove(temp_file_path1)
    os.remove(temp_file_path2)
    os.remove(temp_file_path_dup)
    os.rmdir(temp_dir)
    
    # Opcional: Limpar o diretório DOCUMENTS_DIR se quiser um estado completamente limpo após o teste
    # for f in list_saved_documents():
    #     delete_saved_file(f)
    print("Testes do gerenciador_arquivos.py concluídos.")

