import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
from supabase import create_client, Client
import logging

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
        print("Iniciando processo de login...")
        driver.get("http://vhseguro.sixvox.com.br/")
        
        # Espera o campo de email estar disponível
        email = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="email"]'))
        )
        email.send_keys(os.environ.get('LOGIN'))
        
        # Preenche a senha
        password = driver.find_element(By.XPATH, '//*[@id="xenha"]')
        password.send_keys(os.environ.get('SENHA'))
        
        # Clica no botão de login
        login_button = driver.find_element(By.XPATH, '//*[@id="enviar"]')
        login_button.click()
        print("Login realizado com sucesso!")
        return True
    except Exception as e:
        print(f"Erro durante o login: {str(e)}")
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

def extrair_dados_tabela(driver):
    try:
        print("Iniciando extração dos dados...")
        
        # Script JavaScript para extrair dados da tabela
        script_extracao = """
            const rows = Array.from(document.querySelectorAll('tr')).filter(row => 
                !row.classList.contains('Freezing') && row.cells.length > 0
            );
            return rows.map(row => {
                const cells = Array.from(row.cells);
                return cells.map(cell => cell.innerText.trim());
            });
        """
        
        raw_data = driver.execute_script(script_extracao)
        dados = []
        
        for row in raw_data:
            if len(row) >= 28:
                registro = {
                    'data_extracao': datetime.now().strftime('%Y-%m-%d'),
                    'administradora': row[1],
                    'corretor': row[2],
                    'data_cadastro': row[3],
                    'data_venda': row[4],
                    'modalidade': row[5],
                    'operadora': row[6],
                    'tipo': row[7],
                    'titular': row[8],
                    'valor': row[9].replace('R$', '').replace('.', '').replace(',', '.').strip(),
                    'status': row[17],
                    'vigencia': row[19]
                }
                dados.append(registro)
                
        print(f"Extração concluída! {len(dados)} registros encontrados.")
        return dados
    except Exception as e:
        print(f"Erro ao extrair dados da tabela: {str(e)}")
        return []

def salvar_no_supabase(dados):
    try:
        print("Iniciando salvamento no Supabase...")
        supabase = create_client(
            os.environ.get('SUPABASE_URL'),
            os.environ.get('SUPABASE_KEY')
        )
        
        # Limpa a tabela existente
        supabase.table('vendas').delete().neq('id', 0).execute()
        
        # Insere os novos dados
        result = supabase.table('vendas').insert(dados).execute()
        
        print(f"Dados salvos com sucesso! {len(dados)} registros inseridos.")
        return True
    except Exception as e:
        print(f"Erro ao salvar no Supabase: {str(e)}")
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
                dados = extrair_dados_tabela(driver)
                if dados:
                    if salvar_no_supabase(dados):
                        print("Processo completado com sucesso!")
                    else:
                        print("Falha ao salvar dados no Supabase")
                else:
                    print("Nenhum dado foi extraído")
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
