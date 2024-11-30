import os
import requests
from bs4 import BeautifulSoup

def fazer_login():
    # URL do sistema
    url = 'http://vhseguro.sixvox.com.br/'
    
    # Pegar credenciais dos secrets
    login = os.environ.get('LOGIN')
    senha = os.environ.get('SENHA')
    
    # Criar uma sessão para manter os cookies
    session = requests.Session()
    
    try:
        # Primeiro acesso para pegar possível token ou cookie
        response = session.get(url)
        print(f"Status código inicial: {response.status_code}")
        
        # Dados do formulário
        dados_login = {
            'email': login,
            'xenha': senha,  # campo senha no formulário
        }
        
        # Fazer o POST do login
        response_login = session.post(url, data=dados_login)
        print(f"Status código login: {response_login.status_code}")
        
        # Verificar se logou com sucesso (vamos imprimir o texto para análise)
        print("Conteúdo da resposta:")
        print(response_login.text[:500])  # Primeiros 500 caracteres
        
        return session
        
    except Exception as e:
        print(f"Erro durante o login: {str(e)}")
        return None

def main():
    print("Iniciando automação...")
    session = fazer_login()
    if session:
        print("Login realizado com sucesso")
    else:
        print("Falha no login")

if __name__ == "__main__":
    main()
