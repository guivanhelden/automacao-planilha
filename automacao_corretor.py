from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from supabase import create_client, Client
import time
import logging
import os
import re
from typing import Optional

class SixvoxCorretorScraper:
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
        
        service = Service()
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        logging.info("Driver do Chrome inicializado com sucesso")
    
    def login(self):
        try:
            self.setup_driver()
            self.driver.get("http://vhseguro.sixvox.com.br/")
            
            # Espera o campo de email estar disponível
            email = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="email"]'))
            )
            email.send_keys(self.login_email)
            
            # Preenche a senha
            password = self.driver.find_element(By.XPATH, '//*[@id="xenha"]')
            password.send_keys(self.login_senha)
            
            # Clica no botão de login
            login_button = self.driver.find_element(By.XPATH, '//*[@id="enviar"]')
            login_button.click()
            logging.info("Login realizado com sucesso!")
            return True
        except Exception as e:
            logging.error(f"Erro durante o login: {str(e)}")
            return False

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

    def navegar_para_corretores(self):
        try:
            actions = [
                ('//*[@id="menu_equipe"]', "click", "Menu Equipe"),
                ('//*[@id="com_manual"]', "click", "Menu Página Equipe"),
                ('//*[@id="sub_manual"]/a[1]', "click", "Submenu Corretor"),
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
            
            logging.info("Aguardando carregamento da página de corretores...")
            time.sleep(5)
            
            # Verificar se a tabela foi carregada
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//table[@id='gv']"))
            )
            logging.info("Tabela de corretores carregada com sucesso!")
            
            return True
                
        except Exception as e:
            logging.error(f"Erro durante a navegação para corretores: {str(e)}")
            return False

    def extrair_dados_tabela_corretor(self):
        try:
            logging.info("Iniciando extração dos dados de corretores...")
            
            script_extracao = """
                const rows = Array.from(document.querySelectorAll('table[id="gv"] tr')).filter(row => 
                    !row.classList.contains('Freezing') && row.cells.length > 0);
                return rows.map(row => Array.from(row.cells).map(cell => cell.innerText.trim()));
            """
            
            raw_data = self.driver.execute_script(script_extracao)
            dados = []
            
            logging.info(f"Processando {len(raw_data)} registros de corretores...")
            
            for row in raw_data:
                if len(row) >= 6:  # Garantir que a linha tem células suficientes
                    # Extrair o código entre parênteses
                    codigo_completo = row[1] if len(row) > 1 else ''
                    codigo = self.extrair_sku(codigo_completo)
                    
                    # Extrair o tipo
                    tipo = row[4] if len(row) > 4 else ''
                    
                    # Extrair a equipe e o código da equipe
                    equipe_completa = row[5] if len(row) > 5 else ''
                    nome_equipe = equipe_completa.split(' (')[0] if ' (' in equipe_completa else equipe_completa
                    codigo_equipe = self.extrair_sku(equipe_completa)
                    
                    # Extrair data de entrada
                    data_entrada = self.converter_data(row[6]) if len(row) > 6 else None
                    
                    # Extrair corretor 
                    corretor_completo = row[2] if len(row) > 2 else ''
                    nome_corretor = corretor_completo.split(' (')[0] if ' (' in corretor_completo else corretor_completo
                    
                    registro = {
                        'codigo': codigo,
                        'nome_corretor': nome_corretor,
                        'tipo': tipo,
                        'nome_equipe': nome_equipe,
                        'equipe_completa': equipe_completa,  # FORMATO ORIGINAL COMPLETO
                        'codigo_equipe': codigo_equipe,
                        'data_entrada': data_entrada
                    }
                    
                    dados.append(registro)
            
            if dados:
                logging.info(f"Extração concluída! Total de {len(dados)} corretores encontrados.")
                return dados
            else:
                logging.warning("Nenhum corretor foi encontrado após o processamento.")
                return []
            
        except Exception as e:
            logging.error(f"Erro ao extrair dados da tabela de corretores: {str(e)}")
            return []

    def atualizar_corretores_no_supabase(self, dados):
        try:
            logging.info(f"Atualizando dados de {len(dados)} corretores no Supabase...")
            
            sucessos = 0
            erros = 0
            nao_encontrados = 0
            
            batch_size = 50
            for i in range(0, len(dados), batch_size):
                batch = dados[i:i+batch_size]
                logging.info(f"Processando lote {i//batch_size + 1} - corretores {i+1} a {min(i+batch_size, len(dados))}")
                
                for corretor in batch:
                    try:
                        # Converter o código para int para match com sku_corretor
                        sku_corretor = int(corretor['codigo']) if corretor['codigo'] else None
                        
                        if sku_corretor is None:
                            logging.warning(f"Corretor sem código válido: {corretor['nome_corretor']}")
                            erros += 1
                            continue
                        
                        # Converter codigo_equipe para int também
                        sku_equipe = int(corretor['codigo_equipe']) if corretor['codigo_equipe'] else None
                        
                        # Preparar os dados para atualização - INCLUINDO SUPERVISOR
                        dados_atualizacao = {
                            'nome_corretor': corretor['nome_corretor'],
                            'grade': corretor['tipo'],
                            'equipe': corretor['equipe_completa'],
                            'sku_equipe': sku_equipe,
                            'supervisor': corretor['equipe_completa']  # FORMATO ORIGINAL COMPLETO COM CÓDIGO
                        }
                        
                        # Fazer o UPDATE onde sku_corretor = codigo extraído
                        response = self.supabase.table('corretor_bd').update(dados_atualizacao).eq('sku_corretor', sku_corretor).execute()
                        
                        # Verificar se algum registro foi atualizado
                        if response.data and len(response.data) > 0:
                            sucessos += 1
                            if sucessos <= 5:  # Log das primeiras 5 atualizações para debug
                                logging.info(f"Corretor atualizado - SKU: {sku_corretor}, Nome: {corretor['nome_corretor']}, Tipo: {corretor['tipo']}, Supervisor: {corretor['equipe_completa']}")
                        else:
                            nao_encontrados += 1
                            if nao_encontrados <= 10:  # Log dos primeiros 10 não encontrados
                                logging.warning(f"Corretor não encontrado na base - SKU: {sku_corretor}, Nome: {corretor['nome_corretor']}")
                        
                    except ValueError as ve:
                        logging.error(f"Erro de conversão para corretor {corretor['nome_corretor']}: {str(ve)}")
                        erros += 1
                    except Exception as e:
                        logging.error(f"Erro ao atualizar corretor {corretor['nome_corretor']}: {str(e)}")
                        erros += 1
                
                # Pequena pausa entre lotes para não sobrecarregar o Supabase
                time.sleep(1)
            
            logging.info(f"Resultado da atualização:")
            logging.info(f"  - Sucessos: {sucessos}")
            logging.info(f"  - Não encontrados: {nao_encontrados}")
            logging.info(f"  - Erros: {erros}")
            
            return sucessos > 0
            
        except Exception as e:
            logging.error(f"Erro geral ao atualizar dados de corretores: {str(e)}")
            return False
    
    def executar_scraping_corretores(self):
        try:
            if not self.login():
                raise Exception("Falha no login")
                
            if not self.navegar_para_corretores():
                raise Exception("Falha na navegação para a página de corretores")
                
            dados = self.extrair_dados_tabela_corretor()
            if not dados:
                raise Exception("Nenhum dado de corretor extraído")
                
            if not self.atualizar_corretores_no_supabase(dados):
                raise Exception("Falha ao atualizar dados de corretores no Supabase")
                
            logging.info("Processo de scraping de corretores concluído com sucesso!")
            return True
                
        except Exception as e:
            logging.error(f"Erro crítico durante a execução do scraping de corretores: {str(e)}")
            return False
                
        finally:
            if self.driver:
                self.driver.quit()
                logging.info("Driver do Chrome encerrado")

if __name__ == "__main__":
    try:
        scraper = SixvoxCorretorScraper()
        success = scraper.executar_scraping_corretores()
        if not success:
            raise Exception("Falha na execução do scraping de corretores")
    except Exception as e:
        logging.error(f"Erro na execução principal: {str(e)}")
        exit(1)
