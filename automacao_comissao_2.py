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

class SixvoxComissaoScraper:
    def __init__(self):
        # Obtém as credenciais das variáveis de ambiente
        self.supabase_url: str = os.environ.get('SUPABASE_URL_2', '')
        self.supabase_key: str = os.environ.get('SUPABASE_KEY_2', '')
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
        logging.info("Cliente Supabase inicializado com sucesso")
    
    def setup_driver(self, headless=True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service()
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logging.info("Driver do Chrome inicializado com sucesso" + (" em modo headless" if headless else " em modo visual"))
    
    def login(self):
        try:
            self.setup_driver(headless=True)
            self.driver.get("http://vhseguro.sixvox.com.br/")
            
            # Espera o campo de email estar disponível
            email = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="email"]'))
            )
            email.clear()
            email.send_keys(self.login_email)
            
            # Preenche a senha
            password = self.driver.find_element(By.XPATH, '//*[@id="xenha"]')
            password.clear()
            password.send_keys(self.login_senha)
            
            # Clica no botão de login
            login_button = self.driver.find_element(By.XPATH, '//*[@id="enviar"]')
            login_button.click()
            
            # Aguarda redirecionamento após login
            time.sleep(3)
            logging.info("Login realizado com sucesso!")
            return True
        except Exception as e:
            logging.error(f"Erro durante o login: {str(e)}")
            return False

    def navegar_para_relatorio_comissao(self):
        try:
            actions = [
                ('//*[@id="menu_relatorios"]', "click", "Menu Relatórios"),
                ('//*[@id="rel_confirma"]', "click", "Relatório de Confirma"),
                ('//*[@id="sub_confirma"]/a[1]', "click", "Sub-menu Confirma"),
                ("//input[contains(@onclick, 'command_argument') and contains(@onclick, 'alterar') and contains(@onclick, '64')]", "js_click", "Seleção de Relatório"),
            ]
            
            for xpath, action_type, description in actions:
                time.sleep(3)
                element = WebDriverWait(self.driver, 25).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                
                if action_type == "click":
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(1)
                    element.click()
                elif action_type == "js_click":
                    self.driver.execute_script("arguments[0].click();", element)
                    
                logging.info(f"Ação realizada: {description}")
            
            # Marca o checkbox saude_dental se existir
            try:
                checkbox = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="saude_dental"]'))
                )
                if not checkbox.is_selected():
                    checkbox.click()
                    logging.info("Checkbox saude_dental marcado")
            except:
                logging.info("Checkbox saude_dental não encontrado ou já marcado")
            
            # Executa o relatório
            submit_button = WebDriverWait(self.driver, 25).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Executar Relatório' and @name='gerar']"))
            )
            submit_button.click()
            
            logging.info("Aguardando carregamento do relatório de comissões...")
            time.sleep(20)
            
            # Verificar se a tabela foi carregada
            try:
                WebDriverWait(self.driver, 45).until(
                    EC.presence_of_element_located((By.XPATH, "//tr[@class='Freezing']"))
                )
                logging.info("Relatório de comissões carregado com sucesso!")
                return True
            except Exception as wait_error:
                logging.error(f"Tempo de espera excedido ao carregar o relatório: {str(wait_error)}")
                # Tenta verificar se há dados mesmo sem o cabeçalho "Freezing"
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//table//tr"))
                    )
                    logging.info("Tabela detectada, continuando com a extração...")
                    return True
                except:
                    return False
            
        except Exception as e:
            logging.error(f"Erro durante a navegação para relatório de comissões: {str(e)}")
            return False

    def limpar_valor_monetario(self, valor):
        """Remove símbolos monetários e converte para float"""
        if not valor or valor == '':
            return 0.0
            
        if isinstance(valor, (int, float)):
            return float(valor)
        
        try:
            # Remove R$, espaços e outros caracteres
            valor_limpo = str(valor).replace('R$', '').strip()
            
            # Se estiver vazio após limpeza
            if not valor_limpo:
                return 0.0
            
            # Formato brasileiro: remove pontos de milhares e converte vírgula para ponto
            valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
            
            return float(valor_limpo)
            
        except (ValueError, AttributeError) as e:
            logging.warning(f"Erro ao converter valor monetário '{valor}': {str(e)}")
            return 0.0
    
    def converter_data(self, data_str):
        """Converte string de data para formato YYYY-MM-DD"""
        if not data_str or str(data_str).strip() == '':
            return None
        
        try:
            data_limpa = str(data_str).strip()
            
            # Formato brasileiro: DD/MM/YYYY
            if '/' in data_limpa:
                data = datetime.strptime(data_limpa, '%d/%m/%Y')
                return data.strftime('%Y-%m-%d')
            
            # Formato alternativo: DD-MM-YYYY
            elif '-' in data_limpa and len(data_limpa.split('-')[0]) <= 2:
                data = datetime.strptime(data_limpa, '%d-%m-%Y')
                return data.strftime('%Y-%m-%d')
            
            # Se já estiver em formato ISO: YYYY-MM-DD
            elif '-' in data_limpa and len(data_limpa.split('-')[0]) == 4:
                data = datetime.strptime(data_limpa, '%Y-%m-%d')
                return data.strftime('%Y-%m-%d')
            
            else:
                logging.warning(f"Formato de data não reconhecido: {data_str}")
                return None
                
        except (ValueError, AttributeError) as e:
            logging.warning(f"Erro ao converter data '{data_str}': {str(e)}")
            return None

    def extrair_sku(self, texto):
        """Extrai o valor entre parênteses de um texto"""
        if not texto:
            return None
        match = re.search(r'\((.*?)\)', texto)
        return match.group(1) if match else None

    def converter_percentual(self, valor_str):
        """Converte string de percentual para float"""
        if not valor_str or valor_str.strip() == '':
            return 0.0
        try:
            return float(valor_str.replace('%', '').replace(',', '.').strip())
        except ValueError:
            return 0.0

    def extrair_dados_tabela_comissao(self):
        try:
            logging.info("Iniciando extração dos dados de comissões...")
            
            # Script JavaScript otimizado para extrair dados
            script_extracao = """
                const rows = Array.from(document.querySelectorAll('tr')).filter(row => 
                    !row.classList.contains('Freezing') && 
                    row.cells.length > 0 && 
                    row.cells[0] && 
                    row.cells[0].innerText.trim() !== '' &&
                    row.cells[0].innerText.includes('/')
                );
                return rows.map(row => Array.from(row.cells).map(cell => cell.innerText.trim()));
            """
            
            raw_data = self.driver.execute_script(script_extracao)
            dados = []
            
            logging.info(f"Processando {len(raw_data)} registros de comissões...")
            
            # Para debug - mostrar as primeiras 5 linhas dos dados brutos
            for i, row in enumerate(raw_data[:5]):
                logging.info(f"DEBUG - Linha {i+1} dados brutos ({len(row)} colunas): {row}")
            
            batch_size = 100
            for i in range(0, len(raw_data), batch_size):
                batch = raw_data[i:i+batch_size]
                batch_processed = []
                
                for row_index, row in enumerate(batch):
                    try:
                        # Validação básica do número de colunas - adaptável
                        if len(row) < 15:
                            logging.warning(f"Linha {i + row_index + 1} com apenas {len(row)} colunas - pulando")
                            continue
                        
                        # Conversão segura de parcela
                        def safe_int_convert(value, default=0):
                            if not value or str(value).strip() == '':
                                return default
                            try:
                                return int(''.join(filter(str.isdigit, str(value))) or default)
                            except (ValueError, TypeError):
                                return default
                        
                        # Conversão segura de percentual
                        def safe_percent_convert(value):
                            if not value or str(value).strip() == '':
                                return 0.0
                            try:
                                clean_value = str(value).replace('%', '').replace(',', '.').strip()
                                return float(clean_value) if clean_value else 0.0
                            except (ValueError, TypeError):
                                return 0.0
                        
                        # Mapeamento correto baseado na estrutura real do HTML
                        registro = {
                            # Informações básicas da venda (baseado na ordem real)
                            'vigencia': self.converter_data(row[0]) if len(row) > 0 else None,  # 15/11/2015
                            'status': str(row[1]).strip() if len(row) > 1 else '',  # Ativa
                            'corretor': str(row[2]).strip() if len(row) > 2 else '',  # Bruno Ravasco de Almeida - Corretor (4837)
                            'proposta': str(row[3]).strip() if len(row) > 3 else '',  # 3613834
                            'titular': str(row[4]).strip() if len(row) > 4 else '',  # ROSEMEIRE GOMES
                            'tipo': str(row[5]).strip() if len(row) > 5 else '',  # PF
                            'operadora': str(row[6]).strip() if len(row) > 6 else '',  # HAPVIDA CLINIPAM (266)
                            'administradora': str(row[7]).strip() if len(row) > 7 else '',  # -DIRETO
                            'parcela': safe_int_convert(row[8]) if len(row) > 8 else 0,  # 1
                            'base_de_calculo': self.limpar_valor_monetario(row[9]) if len(row) > 9 else 0.0,  # R$ 737,94
                            'data_repasse': self.converter_data(row[10]) if len(row) > 10 else None,  # 17/12/2024
                            'percentual_comissao': safe_percent_convert(row[11]) if len(row) > 11 else 0.0,  # 100.00
                            'valor_comissao': self.limpar_valor_monetario(row[12]) if len(row) > 12 else 0.0,  # R$ 813,41
                            'percentual_corretor': safe_percent_convert(row[13]) if len(row) > 13 else 0.0,  # 100.00
                            'comissao_paga_corretor': self.limpar_valor_monetario(row[14]) if len(row) > 14 else 0.0,  # R$ 737,94
                            'comissao_a_pagar': self.limpar_valor_monetario(row[15]) if len(row) > 15 else 0.0,  # R$ 737,94                            
                            'supervisor': str(row[16]).strip() if len(row) > 16 else '',  # Leandro Lombardi (4489)
                            'distribuidora': str(row[17]).strip() if len(row) > 17 else '',  # (vazio)
                            'equipe': str(row[18]).strip() if len(row) > 18 else '',  # Leandro Lombardi (37)
                            'cnpj_cpf': str(row[19]).strip() if len(row) > 19 else '',  # 12387735838
                            'data_cadastro': self.converter_data(row[20]) if len(row) > 20 else None,  # 06/11/2024
                            'cod_regra_corretor': safe_int_convert(row[21]) if len(row) > 21 else 0,  # 956
                            'cod_regra': safe_int_convert(row[22]) if len(row) > 22 else 0,  # 664
                            'modalidade': str(row[23]).strip() if len(row) > 23 else '',  # INDIVIDUAL SAÚDE (182)
                            'qtd_vidas': safe_int_convert(row[24]) if len(row) > 24 else 0,  # 1
                            'vencimento': self.converter_data(row[25]) if len(row) > 25 else None,  # 15/11/2024
                            'comissao_paga_supervisor': self.limpar_valor_monetario(row[26]) if len(row) > 26 else 0.0,  # R$ 0,00
                            'comissao_paga_gerente': self.limpar_valor_monetario(row[27]) if len(row) > 27 else 0.0,  # R$ 0,00
                            'comissao_paga_parceiro1': self.limpar_valor_monetario(row[28]) if len(row) > 28 else 0.0,  # R$ 0,00
                            'comissao_paga_parceiro2': self.limpar_valor_monetario(row[29]) if len(row) > 29 else 0.0,  # R$ 0,00
                            'tipo_corretor': str(row[30]).strip() if len(row) > 30 else '',  # DIAMOND
                            
                            # SKUs extraídos para melhor análise
                            'sku_corretor': self.extrair_sku(row[2]) if len(row) > 2 else None,  # (4837)
                            'sku_modalidade': self.extrair_sku(row[23]) if len(row) > 23 else None,  # (266)
                            'sku_operadora': self.extrair_sku(row[6]) if len(row) > 6 else None,  # (182)
                            'sku_administradora': None  # Não há SKU para administradora neste caso (-DIRETO)
                        }
                        
                        # Validação de qualidade dos dados
                        if (registro['vigencia'] is not None and 
                            registro['proposta'] and 
                            len(registro['proposta'].strip()) > 0 and
                            registro['corretor'] and 
                            len(registro['corretor'].strip()) > 0):
                            
                            batch_processed.append(registro)
                            
                            # Log das primeiras 3 linhas processadas com sucesso
                            if len(dados) + len(batch_processed) <= 3:
                                logging.info(f"DEBUG - Registro {len(dados) + len(batch_processed)} processado:")
                                logging.info(f"  Vigência: {registro['vigencia']}")
                                logging.info(f"  Status: {registro['status']}")
                                logging.info(f"  Proposta: {registro['proposta']}")
                                logging.info(f"  Corretor: {registro['corretor'][:50]}...")
                                logging.info(f"  Modalidade: {registro['modalidade']}")
                                logging.info(f"  Operadora: {registro['operadora']}")
                                logging.info(f"  Qtd Vidas: {registro['qtd_vidas']}")
                                logging.info(f"  Tipo Corretor: {registro['tipo_corretor']}")
                                logging.info(f"  Valor Comissão: {registro['valor_comissao']}")
                                logging.info(f"  Vencimento: {registro['vencimento']}")
                        else:
                            logging.warning(f"Linha {i + row_index + 1} rejeitada - dados essenciais faltando")
                            
                    except Exception as row_error:
                        logging.error(f"Erro ao processar linha {i + row_index + 1}: {str(row_error)}")
                        continue
                
                dados.extend(batch_processed)
                logging.info(f"Processado lote de {len(batch_processed)} registros... Total atual: {len(dados)}")
            
            # Mostrar amostra dos dados processados
            if dados:
                logging.info("Amostra dos primeiros 3 registros processados:")
                for i, registro in enumerate(dados[:3]):
                    logging.info(f"Registro {i+1}: Vigência={registro['vigencia']}, Proposta={registro['proposta']}, Corretor={registro['corretor'][:30]}...")
                
                logging.info(f"Extração de comissões concluída! Total de {len(dados)} registros válidos.")
                return dados
            else:
                logging.warning("Nenhum registro válido foi encontrado após o processamento.")
                return []
            
        except Exception as e:
            logging.error(f"Erro ao extrair dados da tabela de comissões: {str(e)}")
            return []

    def limpar_tabela_supabase(self):
        try:
            logging.info("Iniciando limpeza da tabela comissoes...")
            response = self.supabase.table('comissoes').delete().neq('id', 0).execute()
            logging.info("Tabela comissoes limpa com sucesso!")
            return True
        except Exception as e:
            logging.error(f"Erro ao limpar tabela de comissões: {str(e)}")
            return False

    def salvar_comissoes_no_supabase(self, dados):
        try:
            if self.limpar_tabela_supabase():
                logging.info(f"Salvando {len(dados)} registros de comissões no Supabase...")
                
                batch_size = 100
                for i in range(0, len(dados), batch_size):
                    batch = dados[i:i+batch_size]
                    
                    try:
                        response = self.supabase.table('comissoes').insert(batch).execute()
                        logging.info(f"Lote {i//batch_size + 1} salvo: {len(batch)} registros")
                        time.sleep(0.5)
                    except Exception as batch_error:
                        logging.error(f"Erro ao salvar lote {i//batch_size + 1}: {str(batch_error)}")
                        return False
                
                logging.info("Dados de comissões salvos com sucesso!")
                return True
            return False
        except Exception as e:
            logging.error(f"Erro ao salvar dados de comissões: {str(e)}")
            return False
    
    def executar_scraping_comissoes(self):
        try:
            if not self.login():
                raise Exception("Falha no login")
                
            if not self.navegar_para_relatorio_comissao():
                raise Exception("Falha na navegação para o relatório de comissões")
                
            dados = self.extrair_dados_tabela_comissao()
            if not dados:
                raise Exception("Nenhum dado de comissão extraído")
                
            if not self.salvar_comissoes_no_supabase(dados):
                raise Exception("Falha ao salvar dados de comissões no Supabase")
                
            logging.info("Processo de scraping de comissões concluído com sucesso!")
            return True
                
        except Exception as e:
            logging.error(f"Erro crítico durante a execução do scraping de comissões: {str(e)}")
            return False
                
        finally:
            if self.driver:
                self.driver.quit()
                logging.info("Driver do Chrome encerrado")

if __name__ == "__main__":
    try:
        scraper = SixvoxComissaoScraper()
        success = scraper.executar_scraping_comissoes()
        if not success:
            raise Exception("Falha na execução do scraping de comissões")
    except Exception as e:
        logging.error(f"Erro na execução principal: {str(e)}")
        exit(1)
