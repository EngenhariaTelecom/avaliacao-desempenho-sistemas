import numpy as np
import random
import time
import subprocess  # permite executar comandos do sistema (shell) a partir do Python
import csv


# Análise Teórica da Cadeia de Markov

# 1. Definição da Matriz de Transição P 
P = np.array([[0.6, 0.3, 0.1],
              [0.2, 0.6, 0.2],
              [0.1, 0.3, 0.6]])

# 2. Cálculo do vetor estacionário (Autovetores)
# Matematicamente, resolvemos pi * P = pi
autovalores, autovetores = np.linalg.eig(P.T)  # P.T - é a transposta da matriz P
pi = autovetores[:, np.isclose(autovalores, 1)].real # pega todas as linhas da coluna onde o autovalor foi 1
pi = pi / pi.sum()
pi = pi.flatten()

# 3. Taxas de cada estado (Mbps) 
taxas = np.array([0, 10, 50])

# 4. Vazão Média Teórica 
vazao_teorica = np.dot(pi, taxas)  # np.dot - é o produto escalar

print(f"\n------------ CALCULO TEORICO ------------")
print(f"Cálculo do vetor de regime estacionário (pi):")
print(f"Estado0 = {pi[0]:.2f}, Estado1 = {pi[1]:.2f}, Estado2 = {pi[2]:.2f}")
print(f"Vazão Média Teórica: {vazao_teorica:.2f} Mbps\n")

# ------------------------------------------------ / -------------------------------------------------------- #

# Simulação da Cadeia

# Configurações iniciais
passos = 500           # Quantidade de passos para a simulação 
estado_atual = 0       # Começamos no estado 0 (Ocioso)
historico_estados = [] # Lista para registrar o estado em cada passo 

# Matriz de Transição P (Probabilidades) 
# Linha 0: [0.6, 0.3, 0.1]
# Linha 1: [0.2, 0.6, 0.2]
# Linha 2: [0.1, 0.3, 0.6]

for _ in range(passos):
    r = random.random() # Sorteia um número entre 0 e 1
    
    if estado_atual == 0:
        if r < 0.6: 
            estado_atual = 0
        elif r < 0.9: # 0.6 + 0.3
            estado_atual = 1
        else: 
            estado_atual = 2
            
    elif estado_atual == 1:
        if r < 0.2: 
            estado_atual = 0
        elif r < 0.8: # 0.2 + 0.6
            estado_atual = 1
        else: 
            estado_atual = 2
            
    elif estado_atual == 2:
        if r < 0.1: 
            estado_atual = 0
        elif r < 0.4: # 0.1 + 0.3
            estado_atual = 1
        else: 
            estado_atual = 2
            
    historico_estados.append(estado_atual) # Guarda o estado sorteado 

# 3. Calcular a frequência observada 
freq0 = historico_estados.count(0) / passos
freq1 = historico_estados.count(1) / passos
freq2 = historico_estados.count(2) / passos

print(f"---- SIMULAÇÃO SIMPLES (500 passos) ----")
print(f"Frequência Estado 0 (Ocioso):   {freq0:.4f}")
print(f"Frequência Estado 1 (Moderado): {freq1:.4f}")
print(f"Frequência Estado 2 (Alto):     {freq2:.4f}")
print("-" * 40)

# ------------------------------------------------ / -------------------------------------------------------- #

# Geração de Tráfego Real

# --- 1. FUNÇÕES PARA FALAR COM O IMUNES ---

def pegar_id_ativo():
    """Descobre o ID do experimento rodando no IMUNES agora"""
    saida = subprocess.check_output("himage -l", shell=True).decode().strip()
    primeira_linha = saida.split("\n")[0]
    eid = primeira_linha.split()[0]
    return eid

def executar_no_imunes(comando):
    """Executa um comando e devolve o texto que aparecer na tela"""
    return subprocess.check_output(comando, shell=True).decode().strip()

# --- 2. CONFIGURAÇÕES ---

EID = pegar_id_ativo()
# print(f"ID do Experimento detectado: {EID}")

# Nomes dos nós usando o ID detectado
SERVIDOR = f"pc2@{EID}"
CLIENTE  = f"pc1@{EID}"
IP_SERVIDOR = "10.0.1.20" # IP real do PC2 configurado no IMUNES
NOME_ARQUIVO = "./02. Miniprojeto - Cadeia de Markov/resultado_experimento_200rep2.csv"

# Configurações do roteiro 
PASSOS = 200
DURACAO_EPOCA = 5
TAMANHO_PACOTE = 1400

# --- 3. PREPARAÇÃO ---
print(f"\n---- GERAÇÃO DE TRAFEGO REAL ----")
print(f"Iniciando servidor no nó {SERVIDOR}")
# Inicia o servidor iperf em segundo plano (&) 
subprocess.Popen(f"himage {SERVIDOR} iperf -s -u &", shell=True)
time.sleep(2)

estado_atual = 0
dados_para_salvar = [] 

# --- 4. LOOP DO EXPERIMENTO ---
# "with open" abre o arquivo com segurança
with open(NOME_ARQUIVO, mode='w', newline='') as ficheiro:
    escritor = csv.writer(ficheiro)
    
    # Escreve o cabeçalho no CSV 
    escritor.writerow(["Passo", "Estado", "Taxa Configurada", "Bytes Transmitidos"])

    for passo in range(1, PASSOS + 1):
        # Sorteio (Matriz P)
        r = random.random()
        if estado_atual == 0:
            if r < 0.6: estado_atual = 0
            elif r < 0.9: estado_atual = 1
            else: estado_atual = 2
        elif estado_atual == 1:
            if r < 0.2: estado_atual = 0
            elif r < 0.8: estado_atual = 1
            else: estado_atual = 2
        else:
            if r < 0.1: estado_atual = 0
            elif r < 0.4: estado_atual = 1
            else: estado_atual = 2

        bytes_enviados = 0
        taxa_str = "0M"

        if estado_atual == 0:
            taxa_str = "0M"
            time.sleep(DURACAO_EPOCA)
        else:
            taxa_str = "10M" if estado_atual == 1 else "50M"
            cmd = f"himage {CLIENTE} iperf -c {IP_SERVIDOR} -u -b {taxa_str} -l {TAMANHO_PACOTE} -t {DURACAO_EPOCA} -y C"
            try:
                saida = executar_no_imunes(cmd)
                bytes_enviados = int(saida.split(',')[8])
            except:
                bytes_enviados = 0

        # REGISTRO: Escreve no CMD e também no ARQUIVO CSV
        print(f"Passo {passo}: Estado {estado_atual} | Taxa {taxa_str} | Bytes: {bytes_enviados}")
        escritor.writerow([passo, estado_atual, taxa_str, bytes_enviados])
        
        # Guardar para o cálculo final
        dados_para_salvar.append(bytes_enviados)

# --- 5. FINALIZAÇÃO ---
subprocess.run(f"himage {SERVIDOR} pkill iperf", shell=True)

vazao_obs = (sum(dados_para_salvar) * 8) / (PASSOS * DURACAO_EPOCA * 1000000)

print("-" * 40)
print(f"Finalizado! Dados salvos em: {NOME_ARQUIVO}")
print(f"Vazão Média Observada: {vazao_obs:.2f} Mbps")