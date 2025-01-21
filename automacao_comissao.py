from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from supabase import create_client
import time
import logging
import os

class SixvoxScraper:
    def __init__(self):
        # Obtém as credenciais das variáveis de ambiente
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_KEY')
        self.login_email = os.environ.get('LOGIN')
        self.login_senha = os.environ.get('SENHA')
        
        if not all([self.supabase_url, self.supabase_key, self.login_email, self.login_senha]):
            raise ValueError("Variáveis de ambiente necessárias não encontradas")
            
        self.driver = None
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Configuração do logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        service = Service()
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        logging.info("Driver do Chrome inicializado com sucesso")
    
    def login(self):
        try:
            self.setup_driver()
            self.driver.get("http://vhseguro.sixvox.com.br/")
            
            email = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="email"]'))
            )
            email.send_keys(self.login_email)
            
            password = self.driver.find_element(By.XPATH, '//*[@id="xenha"]')
            password.send_keys(self.login_senha)
            
            login_button = self.driver.find_element(By.XPATH, '//*[@id="enviar"]')
            login_button.click()
            logging.info("Login realizado com sucesso!")
            return True
        except Exception as e:
            logging.error(f"Erro durante o login: {str(e)}")
            return False

    def navegar_para_relatorio(self):
        try:
            actions = [
                ('//*[@id="menu_relatorios"]', "click", "Menu Relatórios"),
                ('//*[@id="rel_confirma"]', "click", "Relatório de Confirma"),
                ('//*[@id="sub_confirma"]/a[1]', "click", "Sub-menu Confirma"),
                ("//input[contains(@onclick, 'command_argument') and contains(@onclick, 'alterar') and contains(@onclick, '64')]", "js_click", "Seleção de Relatório"),
            ]
            
            for xpath, action_type, description in actions:
                time.sleep(2)  # Aumentado para maior estabilidade
                element = WebDriverWait(self.driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                
                if action_type == "click":
                    element.click()
                elif action_type == "js_click":
                    self.driver.execute_script("arguments[0].click();", element)
                    
                logging.info(f"Ação realizada: {description}")
            
            # Marca o checkbox saude_dental
            checkbox = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="saude_dental"]'))
            )
            if not checkbox.is_selected():
                checkbox.click()
                logging.info("Checkbox saude_dental marcado")
            
            submit_button = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Executar Relatório' and @name='gerar']"))
            )
            submit_button.click()
            
            logging.info("Aguardando carregamento do relatório...")
            time.sleep(15)
            
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.XPATH, "//tr[@class='Freezing']"))
                )
                logging.info("Relatório carregado com sucesso!")
                return True
            except Exception as wait_error:
                logging.error(f"Tempo de espera excedido ao carregar o relatório: {str(wait_error)}")
                return False
            
        except Exception as e:
            logging.error(f"Erro durante a navegação: {str(e)}")
            return False

    def limpar_valor_monetario(self, valor):
        if isinstance(valor, str):
            valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
            try:
                return float(valor)
            except ValueError:
                return 0.0
        return 0.0
    
    def converter_data(self, data_str):
        if not data_str or data_str.strip() == '':
            return None
        try:
            data = datetime.strptime(data_str.strip(), '%d/%m/%Y')
            return data.isoformat()[:10]  # Retorna no formato YYYY-MM-DD
        except:
            return None

    def extrair_dados_tabela(self):
        try:
            logging.info("Iniciando extração dos dados...")
            
            script_extracao = """
                const rows = Array.from(document.querySelectorAll('tr')).filter(row => !row.classList.contains('Freezing') && row.cells.length > 0);
                return rows.map(row => Array.from(row.cells).map(cell => cell.innerText.trim()));
            """
            
            raw_data = self.driver.execute_script(script_extracao)
            dados = []
            
            logging.info(f"Processando {len(raw_data)} registros...")
            
            batch_size = 100
            for i in range(0, len(raw_data), batch_size):
                batch = raw_data[i:i+batch_size]
                batch_processed = []
                
                for row in batch:
                    try:
                        # Verifica se há colunas suficientes (agora no mínimo 20)
                        if len(row) >= 21:
                            registro = {
                                'vigencia': self.converter_data(row[0]),
                                'status': row[1],
                                'corretor': row[2],
                                'proposta': row[3],
                                'titular': row[4],
                                'tipo': row[5],
                                'operadora': row[6],
                                'administradora': row[7],
                                'parcela': int(row[8] or 0),
                                'base_de_calculo': self.limpar_valor_monetario(row[9]),
                                'data_repasse': self.converter_data(row[10]),
                                'percentual_comissao': float(row[11].replace('%', '') or 0),
                                'valor_comissao': self.limpar_valor_monetario(row[12]),
                                'percentual_corretor': float(row[13].replace('%', '') or 0),
                                'comissao_paga_corretor': self.limpar_valor_monetario(row[14]),
                                'comissao_a_pagar': self.limpar_valor_monetario(row[15]),
                                'supervisor': row[16],
                                'distribuidora': row[17],
                                'equipe': row[18],
                                'cnpj/cpf': row[19],  # Nova coluna adicionada
                                'data_cadastro': row[20]  # Nova coluna adicionada
                            }
                            if registro['vigencia'] is not None:
                                batch_processed.append(registro)
                    except Exception as row_error:
                        logging.error(f"Erro ao processar linha: {str(row_error)}")
                        continue
                
                dados.extend(batch_processed)
                logging.info(f"Processado lote de {len(batch_processed)} registros... Total atual: {len(dados)}")
            
            if dados:
                logging.info(f"Extração concluída! Total de {len(dados)} registros válidos.")
                return dados
            else:
                logging.warning("Nenhum registro válido foi encontrado após o processamento.")
                return []
            
        except Exception as e:
            logging.error(f"Erro ao extrair dados da tabela: {str(e)}")
            return []

    def limpar_tabela_supabase(self):
        try:
            logging.info("Iniciando limpeza da tabela dimensao_comissao...")
            self.supabase.table('dimensao_comissao').delete().neq('id', 0).execute()
            logging.info("Tabela dimensao_comissao limpa com sucesso!")
            return True
        except Exception as e:
            logging.error(f"Erro ao limpar tabela: {str(e)}")
            return False

    def salvar_no_supabase(self, dados):
        try:
            if self.limpar_tabela_supabase():
                logging.info(f"Salvando {len(dados)} registros no Supabase...")
                self.supabase.table('dimensao_comissao').insert(dados).execute()
                logging.info("Dados salvos com sucesso!")
                return True
            return False
        except Exception as e:
            logging.error(f"Erro ao salvar dados: {str(e)}")
            return False
    
    def executar_scraping(self):
        try:
            if not self.login():
                raise Exception("Falha no login")
                
            if not self.navegar_para_relatorio():
                raise Exception("Falha na navegação para o relatório")
                
            dados = self.extrair_dados_tabela()
            if not dados:
                raise Exception("Nenhum dado extraído")
                
            if not self.salvar_no_supabase(dados):
                raise Exception("Falha ao salvar dados no Supabase")
                
            logging.info("Processo de scraping concluído com sucesso!")
            return True
            
        except Exception as e:
            logging.error(f"Erro crítico durante a execução do scraping: {str(e)}")
            return False
            
        finally:
            if self.driver:
                self.driver.quit()
                logging.info("Driver do Chrome encerrado")

if __name__ == "__main__":
    try:
        scraper = SixvoxScraper()
        success = scraper.executar_scraping()
        if not success:
            raise Exception("Falha na execução do scraping")
    except Exception as e:
        logging.error(f"Erro na execução principal: {str(e)}")
        exit(1)
