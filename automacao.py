import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time

def configurar_chrome():
    print("Configurando o Chrome...")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("Chrome configurado com sucesso!")
        return driver
    except Exception as e:
        print(f"Erro detalhado ao configurar Chrome: {str(e)}")
        raise

def fazer_login(driver):
    try:
        print("Acessando página de login...")
        driver.get('http://vhseguro.sixvox.com.br/')
        print(f"Título da página: {driver.title}")
        
        # Pegar credenciais dos secrets
        login = os.environ.get('LOGIN')
        senha = os.environ.get('SENHA')
        print("Credenciais obtidas dos secrets")
        
        print("Aguardando campo de email ficar disponível...")
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="email"]'))
        )
        print("Campo de email encontrado!")
        email_field.send_keys(login)
        print("Email preenchido")
        
        print("Localizando campo de senha...")
        senha_field = driver.find_element(By.XPATH, '//*[@id="xenha"]')
        senha_field.send_keys(senha)
        print("Senha preenchida")
        
        print("Localizando botão de login...")
        login_button = driver.find_element(By.XPATH, '//*[@id="enviar"]')
        print("Clicando no botão de login...")
        login_button.click()
        
        # Aguardar um momento para verificar se o login foi bem sucedido
        time.sleep(2)
        print(f"URL após login: {driver.current_url}")
        print(f"Título após login: {driver.title}")
        
        # Tentar encontrar algum elemento que só existe após o login
        try:
            menu = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="menu_relatorios"]'))
            )
            print("Menu encontrado - Login confirmado!")
        except:
            print("Menu não encontrado - Possível falha no login")
        
        return True
        
    except Exception as e:
        print(f"Erro durante o login: {str(e)}")
        print(f"URL atual: {driver.current_url}")
        return False

def navegar_menus(driver):
    try:
        print("Iniciando navegação pelos menus...")
        
        # Clicar em menu_relatorios
        print("Procurando menu_relatorios...")
        menu_relatorios = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="menu_relatorios"]'))
        )
        menu_relatorios.click()
        print("Clicou em menu_relatorios")
        
        # Clicar em chi_operacional
        print("Procurando chi_operacional...")
        chi_operacional = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="chi_operacional"]'))
        )
        chi_operacional.click()
        print("Clicou em chi_operacional")
        
        # Clicar em sub_operacional
        print("Procurando sub_operacional...")
        sub_operacional = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="sub_operacional"]/a[14]'))
        )
        sub_operacional.click()
        print("Clicou em sub_operacional")
        
        # Clicar no botão de relatório
        print("Procurando botão de relatório...")
        botao_relatorio = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='image' and @src='/images/relatorio.png']"))
        )
        botao_relatorio.click()
        print("Clicou no botão de relatório")
        
        time.sleep(2)  # Aguardar carregamento da tabela
        print("Navegação concluída!")
        return True
        
    except Exception as e:
        print(f"Erro durante a navegação: {str(e)}")
        print(f"URL atual: {driver.current_url}")
        return False

def main():
    print("Iniciando automação...")
    try:
        driver = configurar_chrome()
        print("Driver criado com sucesso")
    except Exception as e:
        print(f"Erro ao criar driver: {str(e)}")
        return
    
    try:
        if fazer_login(driver):
            print("Login realizado com sucesso")
            if navegar_menus(driver):
                print("Navegação realizada com sucesso")
                # Aqui vamos adicionar a extração dos dados
            else:
                print("Falha na navegação")
        else:
            print("Falha no login")
    
    except Exception as e:
        print(f"Erro na execução principal: {str(e)}")
    
    finally:
        print("Encerrando o driver...")
        driver.quit()
        print("Driver encerrado")

if __name__ == "__main__":
    main()
