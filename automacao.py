import os

def main():
    # Testa se conseguimos acessar os secrets
    login = os.environ.get('LOGIN')
    senha = os.environ.get('SENHA')
    
    print("Iniciando automação...")
    print(f"Login configurado: {'Sim' if login else 'Não'}")
    print(f"Senha configurada: {'Sim' if senha else 'Não'}")

if __name__ == "__main__":
    main()
