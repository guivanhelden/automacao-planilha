import os
import requests
from bs4 import BeautifulSoup
import time

def fazer_login():
    url = 'http://vhseguro.sixvox.com.br/'
    login = os.environ.get('LOGIN')
    senha = os.environ.get('SENHA')
    session = requests.Session()
    
    try:
        response = session.get(url)
        print(f"Status código inicial: {response.status_code}")
        
        dados_login = {
            'email': login,
            'xenha': senha,
        }
        
        response_login = session.post(url, data=dados_login)
        print(f"Status código login: {response_login.status_code}")
        
        return session
    except Exception as e:
        print(f"Erro durante o login: {str(e)}")
        return None

def navegar_menu(session):
    try:
        # Primeiro, clicar em menu_equipe
        response = session.get('http://vhseguro.sixvox.com.br/Corretor')
        print(f"Status código navegação: {response.status_code}")
        
        # Analisar a estrutura da tabela
        soup = BeautifulSoup(response.text, 'lxml')
        tabela = soup.find('table', {'id': 'gv'})
        
        if tabela:
            print("\nCabeçalho da tabela encontrado:")
            headers = [th.text.strip() for th in tabela.find_all('td', class_='Freezing')]
            print(headers)
        else:
            print("Tabela não encontrada")
            
        return response.text
        
    except Exception as e:
        print(f"Erro durante a navegação: {str(e)}")
        return None

def main():
    print("Iniciando automação...")
    session = fazer_login()
    if session:
        print("Login realizado com sucesso")
        print("\nNavegando para a página do corretor...")
        conteudo = navegar_menu(session)
        if conteudo:
            print("Navegação realizada com sucesso")
    else:
        print("Falha no login")

if __name__ == "__main__":
    main()
