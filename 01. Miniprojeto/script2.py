# ===============================================================
# Experimento de Avaliação de Desempenho de TCP sob Perda de Pacotes
#
# Este script automatiza a execução de experimentos no ambiente
# de simulação IMUNES para avaliar o comportamento de diferentes
# algoritmos de controle de congestionamento TCP (Reno e Cubic).
#
# O experimento consiste na geração simultânea de tráfego TCP e UDP,
# onde o fluxo TCP é utilizado para análise de retransmissões,
# enquanto o fluxo UDP atua como tráfego concorrente para provocar
# congestionamento na rede.
#
# Para aumentar a probabilidade de retransmissões, foram aplicadas
# as seguintes modificações no enlace entre os roteadores:
#   - Redução do tamanho da fila de transmissão dos roteadores.
#   - Configuração de diferentes valores de BER (Bit Error Rate).
#   - Inserção artificial de perda de pacotes utilizando o "netem".
#
# Foram realizadas duas variações do experimento, alterando apenas
# a taxa de perda de pacotes no roteador:
#   • 0.1% de perda
#   • 2% de perda
#
# Durante cada execução, o tráfego TCP é capturado utilizando
# tcpdump e posteriormente analisado com tshark para contabilizar:
#   - Número total de segmentos TCP enviados
#   - Número de retransmissões TCP
#
# Os resultados são armazenados em um arquivo CSV para posterior
# análise estatística e comparação entre os algoritmos TCP.
# ===============================================================


import subprocess
import csv
import time


# ---------- Funções auxiliares ----------

def get_active_eid():
    """Detecta automaticamente o EID ativo do IMUNES."""
    
    # Executa o comando que lista os experimentos ativos no IMUNES
    out = subprocess.check_output("himage -l", shell=True).decode().strip()
    
    # Pega a primeira linha da saída
    first_line = out.split("\n")[0]
    
    # O primeiro campo da linha corresponde ao EID
    eid = first_line.split()[0]
    
    return eid


def run(cmd):
    """Executa um comando sem capturar saída, mostrando no console."""
    
    # Imprime o comando no terminal para acompanhamento
    print(cmd)
    
    # Executa o comando no shell
    subprocess.run(cmd, shell=True, check=True)


def run_output(cmd):
    """Executa um comando e retorna a saída como string."""
    
    # Executa o comando e retorna a saída convertida para string
    return subprocess.check_output(cmd, shell=True).decode().strip()


def wait_iperf_server(pc):
    
    # Tenta verificar se o servidor iperf iniciou corretamente
    for _ in range(20):   # tenta até 20 vezes
        
        # Verifica se a porta 5001 está em escuta
        out = run_output(f"himage {pc} ss -ltn | grep ':5001' || true")
        
        # Se encontrou algo significa que o servidor está ativo
        if out.strip() != "":
            return
        
        # Aguarda 1 segundo antes de tentar novamente
        time.sleep(1)


# ---------- Configurações gerais ----------

# Detecta automaticamente o EID do experimento ativo no IMUNES
EID = get_active_eid()

print("EID detectado:", EID)

# Nome do arquivo CSV onde serão armazenados os resultados
RESULT_FILE = "result_experimento.csv"

# Variantes de algoritmo de controle de congestionamento TCP a serem testadas
TCP_VARIANTS = ["reno", "cubic"]

# Valores de BER (Bit Error Rate) utilizados no enlace entre os roteadores
BERS = [1000000, 100000]   # 1e-6 e 1e-5

# testes anteriores (comentados)
# teste - BERS = [10000, 1000]   # 1e-4 e 1e-3
# teste - UDP_RATES = [900, 1000]     # Mbps

# Taxas de tráfego UDP utilizadas para gerar congestionamento
UDP_RATES = [800, 900]

# Número de repetições de cada experimento
REPS = 8


# PCs do IMUNES

# Monta o identificador completo das VMs com o EID
PC1 = f"pc1@{EID}"
PC2 = f"pc2@{EID}"
PC3 = f"pc3@{EID}"
PC4 = f"pc4@{EID}"


# IPs utilizados no experimento

# IP do servidor TCP
TCP_SERVER_IP = "10.0.3.20"

# IP do servidor UDP
UDP_SERVER_IP = "10.0.4.20"

# IP de origem do tráfego TCP (cliente)
TCP_SRC_IP = "10.0.0.20"


# Caminho do arquivo PCAP dentro da VM
PCAP_PATH = "/fluxo.pcap"


# ---------- Script principal ----------

# Abre o arquivo CSV para armazenar os resultados
with open(RESULT_FILE, "w", newline="") as f:
    
    writer = csv.writer(f)
    
    # Escreve o cabeçalho do arquivo CSV
    writer.writerow(["tcp", "ber", "udp", "rep", "segmentos", "retransmissoes"])

    # Loop para testar cada algoritmo de controle de congestionamento TCP
    for tcp in TCP_VARIANTS:

        print(f"\n=== TCP {tcp} ===")
        
        # Configura o algoritmo TCP nas máquinas que geram tráfego TCP
        run(f"himage {PC1} sysctl -w net.ipv4.tcp_congestion_control={tcp}")
        run(f"himage {PC2} sysctl -w net.ipv4.tcp_congestion_control={tcp}")

        # Loop para testar diferentes BERs
        for ber in BERS:

            print(f"\nConfig BER {ber}")
            
            # Configura BER entre os roteadores
            run(f"sudo vlink -BER {ber} -eid {EID} router1:router2")

            # REDUZ FILA DO ROTEADOR 
            # Reduz o tamanho da fila de transmissão para provocar perdas por congestionamento
            run(f"himage router1@{EID} ip link set dev eth2 txqueuelen 10")
            run(f"himage router2@{EID} ip link set dev eth0 txqueuelen 10")

            # remove regra anterior (se existir)
            run(f"himage router1@{EID} tc qdisc del dev eth2 root || true")
            run(f"himage router2@{EID} tc qdisc del dev eth0 root || true")

            # adiciona perda de 2% e salva no arquivo chamado result_experimento_2loss
            #run(f"himage router1@{EID} tc qdisc add dev eth2 root netem loss 2%")
            #run(f"himage router2@{EID} tc qdisc add dev eth0 root netem loss 2%")

            # adiciona perda de 0.1% e salva no arquivo chamado result_experimento_01loss
            # Adiciona perda artificial de pacotes no enlace para provocar retransmissões TCP
            run(f"himage router1@{EID} tc qdisc add dev eth2 root netem loss 0.1%")
            run(f"himage router2@{EID} tc qdisc add dev eth0 root netem loss 0.1%")

            # Loop para diferentes taxas de tráfego UDP (usado como tráfego concorrente)
            for udp in UDP_RATES:

                print(f"\nUDP {udp} Mbps")

                # Inicia servidores UDP nas VMs
                
                # Mata instâncias anteriores de iperf
                run(f"himage {PC4} pkill iperf || true")
                
                # Inicia servidor UDP em background
                run(f"himage {PC4} iperf -s -u -D")

                run(f"himage {PC3} pkill iperf || true")
                
                # Cliente UDP gerando tráfego contínuo
                run(f"himage {PC3} bash -c 'iperf -c {UDP_SERVER_IP} -u -b {udp}M &'")
                
                time.sleep(2)

                # Executa múltiplas repetições do experimento
                for rep in range(1, REPS + 1):

                    print(f"\nExecução {rep}")

                    # Limpa e inicia servidor TCP
                    run(f"himage {PC2} pkill iperf || true")
                    
                    time.sleep(1)
                    
                    run(f"himage {PC2} iperf -s -D")
                    
                    # Aguarda servidor iniciar
                    wait_iperf_server(PC2)

                    # Captura tráfego TCP na VM
                    
                    run(f"himage {PC1} pkill tcpdump || true")
                    
                    time.sleep(1)
                    
                    # Inicia captura de pacotes TCP
                    run(f"himage {PC1} tcpdump -i eth0 -s 0 -w {PCAP_PATH} host {TCP_SERVER_IP} &")

                    time.sleep(2)  # espera tcpdump iniciar

                    # Cliente TCP gera tráfego por 30 segundos
                    run(f"himage {PC1} iperf -c {TCP_SERVER_IP} -t 30")

                    time.sleep(2)

                    # Para captura
                    run(f"himage {PC1} pkill tcpdump || true")

                    # Copia o arquivo .pcap da VM para máquina local dentro da pasta 'capturas'
                    LOCAL_PCAP = f"./fluxo_{tcp}_{ber}_{udp}_{rep}.pcap"
                    
                    run(f"sudo hcp {PC1}:{PCAP_PATH} {LOCAL_PCAP}")

                    # Analisa segmentos e retransmissões diretamente na maquina local
                    
                    # Conta número de segmentos TCP enviados
                    seg = run_output(
                        f'tshark -r {LOCAL_PCAP} -Y "ip.src=={TCP_SRC_IP} and tcp.len>0" | wc -l'
                    )
                    
                    # Conta retransmissões TCP detectadas pelo Wireshark
                    ret = run_output(
                        f'tshark -r {LOCAL_PCAP} -Y "tcp.analysis.retransmission or tcp.analysis.fast_retransmission" | wc -l'
                    )

                    # Salva resultado no CSV
                    writer.writerow([tcp, ber, udp, rep, seg, ret])

                    print(f"Segmentos: {seg}, Retransmissões: {ret}")

                    # Apaga o arquivo pcap para não encher o disco
                    run(f"rm -f {LOCAL_PCAP}")

                # Para servidores UDP após terminar as repetições
                run(f"himage {PC3} pkill iperf || true")
                run(f"himage {PC4} pkill iperf || true")

print("\nExperimento finalizado. Resultados salvos em", RESULT_FILE)