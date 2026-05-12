import os
import sys
import time

# Tenta importar o pywinauto. Se não tiver, instala na hora.
try:
    from pywinauto import Desktop
except ImportError:
    print(" Instalando biblioteca pywinauto (necessária para o teste)...")
    os.system(f"{sys.executable} -m pip install pywinauto")
    from pywinauto import Desktop

def iniciar_teste():
    print("=" * 50)
    print(" TESTE DE LEITURA DE TELA (RAIO-X)")
    print("=" * 50)
    print("\nInstruções:")
    print("1. Você tem 5 segundos.")
    print("2. Clique na janela do ERP, exatamente onde aparece a grade de lojas.")
    print("3. Deixe a janela do ERP ativa na tela.")
    
    for i in range(5, 0, -1):
        print(f"⏳ Lendo a tela em {i} segundos...")
        time.sleep(1)
        
    print("\n🔍 Analisando a tela ativa agora...")
    
    try:
        # Pega a janela que está ativa no momento (focada) - usando o motor antigo win32
        janela_ativa = Desktop(backend="win32").windows(visible_only=True)[0]
        titulo = janela_ativa.window_text()
        print(f"\n[OK] Janela encontrada: {titulo}")
        
        print("\nExtraindo todos os textos internos da janela...")
        # Monta a árvore de elementos da janela
        arvore = janela_ativa.dump_tree(depth=5, filename="resultado_tela.txt")
        
        print("\n" + "="*50)
        print("✅ TESTE FINALIZADO!")
        print("Um arquivo chamado 'resultado_tela.txt' foi criado na mesma pasta.")
        print("Abra o arquivo e veja se você consegue encontrar os nomes das lojas ou os números de estoque nele.")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Erro ao tentar ler a janela: {e}")

if __name__ == "__main__":
    iniciar_teste()
    input("\nPressione ENTER para sair...")
