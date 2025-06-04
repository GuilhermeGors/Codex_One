# codex_one/run_tests.py

import unittest
import sys
import os
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.progress import Progress # Para uma futura barra de progresso se quisermos

console = Console()

def run_all_tests():
    """
    Descobre e executa todos os testes no projeto Codex One com saída formatada por Rich.
    """
    console.rule("[bold cyan]Iniciando Execução de Testes do Codex One[/bold cyan]")

    project_root = os.path.abspath(os.path.dirname(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        console.log(f"Adicionado ao sys.path: [italic blue]{project_root}[/italic blue]")

    # CORRIGIDO: Nome da pasta 'data_access'
    test_dirs_relative_to_root = [
        'core/tests',
        'data_access/tests', 
        'processing/tests'
    ]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    total_tests_found = 0

    for test_dir_relative in test_dirs_relative_to_root:
        test_dir_absolute = os.path.join(project_root, test_dir_relative)
        if os.path.isdir(test_dir_absolute):
            console.print(f"\nDescobrindo testes em: [italic]{test_dir_absolute}[/italic]")
            # Passar top_level_dir=project_root para ajudar na descoberta de módulos
            dir_suite = loader.discover(start_dir=test_dir_absolute, pattern='test_*.py', top_level_dir=project_root)
            
            num_tests_in_dir = dir_suite.countTestCases()
            if num_tests_in_dir > 0:
                console.print(f"  [green]Encontrados {num_tests_in_dir} testes em '{test_dir_relative}'.[/green]")
                suite.addTest(dir_suite)
                total_tests_found += num_tests_in_dir
            else:
                console.print(f"  [yellow]Nenhum teste encontrado em '{test_dir_relative}' com o padrão 'test_*.py'.[/yellow]")
        else:
            console.print(f"  [red]AVISO: Diretório de testes não encontrado: {test_dir_absolute}[/red]")

    if total_tests_found == 0:
        console.print("\n[bold red]Nenhum teste foi encontrado no projeto.[/bold red]")
        return False

    console.print(f"\nTotal de casos de teste a serem executados: [bold]{total_tests_found}[/bold]")
    console.rule()

    # Usar um TextTestRunner padrão, mas vamos formatar a saída depois
    # Para uma integração mais profunda com Rich, seria necessário um TestRunner customizado.
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2) # verbosity=2 para detalhes
    result = runner.run(suite)

    console.rule("[bold cyan]Resumo da Execução dos Testes[/bold cyan]")
    
    table = Table(title="Detalhes dos Resultados")
    table.add_column("Métrica", style="dim", width=30)
    table.add_column("Valor", justify="right")

    total_run = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    successes = total_run - failures - errors - skipped

    table.add_row("Total de Testes Executados", str(total_run))
    table.add_row("Sucessos", Text(str(successes), style="green"))
    table.add_row("Falhas", Text(str(failures), style="red" if failures > 0 else "white"))
    table.add_row("Erros", Text(str(errors), style="bold red" if errors > 0 else "white"))
    table.add_row("Pulados (Skipped)", Text(str(skipped), style="yellow" if skipped > 0 else "white"))
    
    console.print(table)

    if total_run > 0:
        success_percentage = (successes / total_run) * 100
        style_percentage = "green" if success_percentage == 100 else ("yellow" if success_percentage >= 70 else "red")
        console.print(f"\nPercentagem de Sucesso: [bold {style_percentage}]{success_percentage:.2f}%[/bold {style_percentage}]")
    else:
        console.print("\nNenhum teste foi executado para calcular a percentagem.")

    console.rule()

    if result.wasSuccessful():
        console.print("[bold green]TODOS OS TESTES PASSARAM! ✅[/bold green]")
        return True
    else:
        console.print("[bold red]ALGUNS TESTES FALHARAM OU TIVERAM ERROS. ❌[/bold red]")
        # Imprimir detalhes de falhas e erros de forma mais legível
        if result.failures:
            console.print("\n[bold yellow]Detalhes das Falhas:[/bold yellow]")
            for test, traceback_text in result.failures:
                console.print(f"[dim]{test.id()}[/dim]")
                console.print(Text(traceback_text, style="red"))
                console.print("-" * 20)
        if result.errors:
            console.print("\n[bold magenta]Detalhes dos Erros:[/bold magenta]")
            for test, traceback_text in result.errors:
                console.print(f"[dim]{test.id()}[/dim]")
                console.print(Text(traceback_text, style="magenta"))
                console.print("-" * 20)
        return False

if __name__ == '__main__':
    run_all_tests()
