from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime
from supabase import create_client, Client
import re
import logging
import os
from typing import Optional

class SixvoxScraper:
    def __init__(self):
        # Obtém as credenciais das variáveis de ambiente
        self.supabase_url: str = os.environ.get('SUPABASE_URL', '')
        self.supabase_key: str = os.environ.get('SUPABASE_KEY_ROLESECRET', '')
        self.login_email: str = os.environ.get('LOGIN', '')
        self.login_senha: str = os.environ.get('SENHA', '')
        
        if not all([self.supabase_url, self.supabase_key, self.login_email, self.login_senha]):
            raise ValueError("Variáveis de ambiente necessárias não encontradas")
            
        self.driver: Optional[webdriver.Chrome] = None
        # Inicializando o cliente Supabase com type hints
        self.supabase: Client = create_client(
            supabase_url=self.supabase_url,
            supabase_key=self.supabase_key
        )
        
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
        
        # Usando webdriver_manager para gerenciar o ChromeDriver
        service = Service(ChromeDriverManager().install())
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

    def limpar_valor_monetario(self, valor):
        """Remove símbolos monetários e converte para float"""
        if isinstance(valor, str):
            valor = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
            try:
                return float(valor)
            except ValueError:
                return 0.0
        return 0.0
    
    def converter_data(self, data_str):
        """Converte string de data para formato DD/MM/YYYY"""
        if not data_str or data_str.strip() == '':
            return None
        try:
            data = datetime.strptime(data_str.strip(), '%d/%m/%Y')
            return data.strftime('%d/%m/%Y')
        except:
            return None

    def extrair_sku(self, texto):
        """Extrai o valor entre parênteses de um texto"""
        if not texto:
            return None
        match = re.search(r'\((.*?)\)', texto)
        return match.group(1) if match else None

    def formatar_cod_corretor(self, codigo):
        if not codigo:
            return None
        try:
            return int(str(codigo)[-4:])
        except (ValueError, IndexError):
            return None

    def navegar_para_relatorio(self):
        try:
            actions = [
                ('//*[@id="menu_relatorios"]', "click", "Menu Relatórios"),
                ('//*[@id="rel_vendas"]', "click", "Relatório de Vendas"),
                ('//*[@id="sub_vendas"]/a[1]', "click", "Sub-menu Vendas"),
                ("//input[contains(@onclick, 'command_argument') and contains(@onclick, 'alterar') and contains(@onclick, '63')]", "js_click", "Seleção de Relatório"),
            ]
            
            for xpath, action_type, description in actions:
                time.sleep(2)
                element = WebDriverWait(self.driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                
                if action_type == "click":
                    element.click()
                elif action_type == "js_click":
                    self.driver.execute_script("arguments[0].click();", element)
                    
                logging.info(f"Ação realizada: {description}")
            
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
                    if len(row) >= 28:
                        registro = {
                            'administradora': row[1] if len(row) > 1 else '',
                            'sku_administradora': self.extrair_sku(row[1]) if len(row) > 1 else None,
                            'corretor': row[2] if len(row) > 2 else '',
                            'sku_corretor': self.extrair_sku(row[2]) if len(row) > 2 else None,
                            'data_cadastro': self.converter_data(row[3]) if len(row) > 3 else None,
                            'data_venda': self.converter_data(row[4]) if len(row) > 4 else None,
                            'modalidade': row[5] if len(row) > 5 else '',
                            'sku_modalidade': self.extrair_sku(row[5]) if len(row) > 5 else None,
                            'operadora': row[6] if len(row) > 6 else '',
                            'sku_operadora': self.extrair_sku(row[6]) if len(row) > 6 else None,
                            'tipo': row[7] if len(row) > 7 else '',
                            'titular': row[8] if len(row) > 8 else '',
                            'valor': self.limpar_valor_monetario(row[9]) if len(row) > 9 else 0.0,
                            'taxa': row[10] if len(row) > 10 else '',
                            'proposta': row[11] if len(row) > 11 else '',
                            'qtd_vidas': int(row[12] or 0) if len(row) > 12 else 0,
                            'qtd_taxas': int(row[13] or 0) if len(row) > 13 else 0,
                            'mes_aniversario': row[14] if len(row) > 14 else '',
                            'grupo': row[15] if len(row) > 15 else '',
                            'plano': row[16] if len(row) > 16 else '',
                            'status': row[17] if len(row) > 17 else '',
                            'cpf_cnpj': row[18] if len(row) > 18 else '',
                            'vigencia': self.converter_data(row[19]) if len(row) > 19 else None,
                            'supervisor': row[20] if len(row) > 20 else '',
                            'sku_supervisor': self.extrair_sku(row[20]) if len(row) > 20 else None,
                            'gerente': row[21] if len(row) > 21 else '',
                            'distribuidora': row[22] if len(row) > 22 else '',
                            'cidade': row[23] if len(row) > 23 else '',
                            'uf': row[24] if len(row) > 24 else '',
                            'tipo_corretor': row[25] if len(row) > 25 else '',
                            'parceiro': row[26] if len(row) > 26 else '',
                            'vencimento': self.converter_data(row[27]) if len(row) > 27 else None,
                            'cod_corretor': self.formatar_cod_corretor(row[28]) if len(row) > 28 else None
                        }
                        
                        if registro['vigencia'] is not None:
                            batch_processed.append(registro)
                
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
            logging.info("Iniciando limpeza da tabela vendas...")
            response = self.supabase.table('vendas').delete().neq('id', 0).execute()
            logging.info("Tabela vendas limpa com sucesso!")
            return True
        except Exception as e:
            logging.error(f"Erro ao limpar tabela: {str(e)}")
            return False

    def salvar_no_supabase(self, dados):
        try:
            if self.limpar_tabela_supabase():
                logging.info(f"Salvando {len(dados)} registros no Supabase...")
                response = self.supabase.table('vendas').insert(dados).execute()
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
