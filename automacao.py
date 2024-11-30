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
