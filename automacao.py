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
        
        # Aguarda a tabela carregar completamente
        print("Aguardando carregamento da tabela...")
        time.sleep(10)  # Aumenta o tempo de espera
        
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
        
        # Executa o script JavaScript para obter todos os dados de uma vez
        raw_data = driver.execute_script(script_extracao)
        dados = []
        
        print(f"Processando {len(raw_data)} registros...")

        if len(raw_data) > 0:
            print("Estrutura do primeiro registro:")
            print(f"Número de colunas: {len(raw_data[0])}")
            print("Conteúdo:", raw_data[0])
        
        # Processa os dados em lotes
        batch_size = 100
        for i in range(0, len(raw_data), batch_size):
            batch = raw_data[i:i+batch_size]
            batch_processed = []
            
            for row in batch:
                try:
                        # Extrai os SKUs
                        sku_administradora = extrair_sku(row[1]) if len(row) > 1 else None
                        sku_corretor = extrair_sku(row[2]) if len(row) > 2 else None
                        sku_modalidade = extrair_sku(row[5]) if len(row) > 5 else None
                        sku_operadora = extrair_sku(row[6]) if len(row) > 6 else None
                        sku_supervisor = extrair_sku(row[20]) if len(row) > 20 else None
                        
                        registro = {
                            'administradora': row[1] if len(row) > 1 else '',
                            'sku_administradora': sku_administradora,
                            'corretor': row[2] if len(row) > 2 else '',
                            'sku_corretor': sku_corretor,
                            'data_cadastro': converter_data(row[3]) if len(row) > 3 else None,
                            'data_venda': converter_data(row[4]) if len(row) > 4 else None,
                            'modalidade': row[5] if len(row) > 5 else '',
                            'sku_modalidade': sku_modalidade,
                            'operadora': row[6] if len(row) > 6 else '',
                            'sku_operadora': sku_operadora,
                            'tipo': row[7] if len(row) > 7 else '',
                            'titular': row[8] if len(row) > 8 else '',
                            'valor': limpar_valor_monetario(row[9]) if len(row) > 9 else 0.0,
                            'taxa': row[10] if len(row) > 10 else '',
                            'proposta': row[11] if len(row) > 11 else '',
                            'qtd_vidas': int(row[12] or 0) if len(row) > 12 else 0,
                            'qtd_taxas': int(row[13] or 0) if len(row) > 13 else 0,
                            'mes_aniversario': row[14] if len(row) > 14 else '',
                            'grupo': row[15] if len(row) > 15 else '',
                            'plano': row[16] if len(row) > 16 else '',
                            'status': row[17] if len(row) > 17 else '',
                            'cpf_cnpj': row[18] if len(row) > 18 else '',
                            'vigencia': converter_data(row[19]) if len(row) > 19 else None,
                            'supervisor': row[20] if len(row) > 20 else '',
                            'sku_supervisor': sku_supervisor,
                            'gerente': row[21] if len(row) > 21 else '',
                            'distribuidora': row[22] if len(row) > 22 else '',
                            'cidade': row[23] if len(row) > 23 else '',
                            'uf': row[24] if len(row) > 24 else '',
                            'tipo_corretor': row[25] if len(row) > 25 else '',
                            'parceiro': row[26] if len(row) > 26 else '',
                            'vencimento': converter_data(row[27]) if len(row) > 27 else None,
                            'cod_corretor': formatar_cod_corretor(row[28]) if len(row) > 28 else None
                        }
                        
                        # Verifica se é um registro válido (tem pelo menos alguns campos obrigatórios preenchidos)
                   if registro['proposta'] or registro['titular']:
                        batch_processed.append(registro)
                    
                except Exception as row_error:
                    print(f"Erro ao processar linha: {str(row_error)}")
                    print(f"Conteúdo da linha com erro: {row}")
                    continue
            
            dados.extend(batch_processed)
            print(f"Processado lote de {len(batch_processed)} registros... Total atual: {len(dados)}")
        
        if len(dados) > 0:
            print(f"Extração concluída! Total de {len(dados)} registros válidos.")
            # Debug: Mostra exemplo do primeiro registro processado
            print("Exemplo do primeiro registro processado:")
            print(dados[0])
            return dados
        else:
            print("Nenhum registro válido foi encontrado após o processamento.")
            return []

    except Exception as e:
            print(f"Erro ao extrair dados da tabela: {str(e)}")
            # Debug: Tenta encontrar a tabela novamente
            tabelas = driver.find_elements(By.TAG_NAME, "table")
            print(f"Número de tabelas encontradas na página: {len(tabelas)}")
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
                # Adiciona tempo de espera extra após a navegação
                print("Aguardando carregamento completo da página...")
                time.sleep(10)
                
                # Tenta extrair os dados
                dados = extrair_dados_tabela(driver)
                if dados:
                    print(f"Dados extraídos com sucesso! Total: {len(dados)} registros")
                    if salvar_no_supabase(dados):
                        print("Processo completado com sucesso!")
                    else:
                        print("Falha ao salvar dados no Supabase")
                else:
                    print("Nenhum dado foi extraído - Verificando HTML da página...")
                    print(driver.page_source[:1000])  # Imprime parte do HTML para debug
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
