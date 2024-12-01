from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from datetime import datetime
from supabase import create_client
import logging

def configurar_chrome():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Execução sem interface gráfica
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

class SixvoxScraper:
    def __init__(self):
        self.driver = None
        self.supabase = create_client(
            os.environ.get('SUPABASE_URL'),
            os.environ.get('SUPABASE_KEY')
        )
        
        # Configuração do logging
        logging.basicConfig(
            filename=f'scraping_vendas{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def login(self):
        try:
            self.driver = configurar_chrome()
            self.driver.get("http://vhseguro.sixvox.com.br/")
            
            email = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="email"]'))
            )
            email.send_keys(os.environ.get('LOGIN'))
            
            password = self.driver.find_element(By.XPATH, '//*[@id="xenha"]')
            password.send_keys(os.environ.get('SENHA'))
            
            login_button = self.driver.find_element(By.XPATH, '//*[@id="enviar"]')
            login_button.click()
            logging.info("Login realizado com sucesso!")
            return True
        except Exception as e:
            logging.error(f"Erro no login: {str(e)}")
            return False

    def navegar_menus(self):
        try:
            print("Iniciando navegação pelos menus...")
            actions = [
                ('//*[@id="menu_equipe"]', "Menu Equipe"),
                ('//*[@id="chi_manual"]', "Manual"),
                ('//*[@id="sub_manual"]', "Sub Manual"),
                ("//a[@class='botao_menu' and @href='/Corretor']", "Botão Corretor")
            ]
            
            for xpath, description in actions:
                print(f"Procurando {description}...")
                elemento = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                elemento.click()
                print(f"Clicou em {description}")
                time.sleep(1)
            
            return True
        except Exception as e:
            print(f"Erro durante a navegação: {str(e)}")
            return False

    def extrair_dados_tabela(self):
        try:
            print("Iniciando extração dos dados...")
            
            # Aguarda a tabela carregar
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'gv'))
            )
            
            # Extrai os dados usando BeautifulSoup
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            tabela = soup.find('table', {'id': 'gv'})
            
            if not tabela:
                print("Tabela não encontrada")
                return []
            
            # Extrai cabeçalhos
            headers = []
            for th in tabela.find_all('td', class_='Freezing'):
                headers.append(th.text.strip())
            
            # Extrai dados
            dados = []
            for tr in tabela.find_all('tr')[1:]:  # Pula o cabeçalho
                row = {}
                cells = tr.find_all('td')
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        row[headers[i]] = cell.text.strip()
                if row:
                    dados.append(row)
            
            print(f"Extraídos {len(dados)} registros")
            return dados
            
        except Exception as e:
            print(f"Erro ao extrair dados da tabela: {str(e)}")
            return []

    def salvar_csv(self, dados):
        try:
            if not dados:
                print("Sem dados para salvar")
                return False
            
            df = pd.DataFrame(dados)
            filename = f'dados_corretores_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            df.to_csv(filename, index=False)
            print(f"Dados salvos em {filename}")
            return True
            
        except Exception as e:
            print(f"Erro ao salvar CSV: {str(e)}")
            return False
    
    def executar_scraping(self):
        try:
            print("Iniciando processo de scraping...")
            self.configurar_chrome()
            
            if self.fazer_login():
                if self.navegar_menus():
                    dados = self.extrair_dados_tabela()
                    if dados:
                        self.salvar_csv(dados)
                    else:
                        print("Nenhum dado extraído")
                else:
                    print("Falha na navegação")
            else:
                print("Falha no login")
                
        except Exception as e:
            print(f"Erro durante a execução: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                print("Driver encerrado")

if __name__ == "__main__":
    try:
        scraper = SixvoxScraper()
        scraper.executar_scraping()
    except Exception as e:
        logging.error(f"Erro na execução principal: {str(e)}")
