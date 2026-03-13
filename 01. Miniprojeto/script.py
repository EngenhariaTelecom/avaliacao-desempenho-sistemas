"""
----------------------------------------------------------------------------------
SCRIPT DE EXPERIMENTO TCP - IMUNES

Este script automatiza experimentos de desempenho TCP.
O experimento avalia o impacto de:

- Algoritmos de controle de congestionamento TCP (reno, cubic)
- Taxa de erro de bits (BER) no enlace
- Tráfego de fundo UDP

Para cada configuração o script:

1. Configura o algoritmo TCP nos hosts
2. Ajusta BER e perda de pacotes no enlace
3. Gera tráfego UDP de fundo
4. Executa fluxo TCP usando iperf
5. Captura pacotes com tcpdump
6. Extrai métricas usando tshark:
   - vazão TCP
   - número de retransmissões
   - taxa de retransmissão
   - eficiência do TCP

Os resultados são salvos em um arquivo CSV para posterior análise estatística.
----------------------------------------------------------------------------------
"""

import subprocess  # permite executar comandos do sistema (shell) a partir do Python
import csv  # biblioteca para escrever arquivos CSV
import time  # biblioteca para trabalhar com tempo (sleep, etc)

# ---------- Funções auxiliares ----------

# executa o comando "himage -l" para listar os ambientes virtuais ativos
def get_active_eid():
    out = subprocess.check_output("himage -l", shell=True).decode().strip()
    first_line = out.split("\n")[0]
    eid = first_line.split()[0]
    return eid

# imprime o comando antes de executá-lo
def run(cmd):
    print(cmd)
    subprocess.run(cmd, shell=True, check=True)

# executa o comando e captura a saída retornada
def run_output(cmd):
    return subprocess.check_output(cmd, shell=True).decode().strip()

# tenta verificar até 20 vezes se o servidor iperf já está ouvindo na porta 5001
def wait_iperf_server(pc):
    for _ in range(20):
        out = run_output(f"himage {pc} ss -ltn | grep ':5001' || true")
        if out.strip() != "":
            return
        time.sleep(1)


# ---------- Configurações ----------

EID = get_active_eid()
print("EID detectado:", EID)

# nome do arquivo CSV onde os resultados serão armazenados
RESULT_FILE = "./result_experimento_loss2.csv"

# fatores com seus respectivos níveis
TCP_VARIANTS = ["reno", "cubic"]
BERS = [1000000, 100000]
UDP_RATES = [800, 900]
REPS = 8


PC1 = f"pc1@{EID}"
PC2 = f"pc2@{EID}"
PC3 = f"pc3@{EID}"
PC4 = f"pc4@{EID}"

TCP_SERVER_IP = "10.0.3.20"
UDP_SERVER_IP = "10.0.4.20"
TCP_SRC_IP = "10.0.0.20"

PCAP_PATH = "/fluxo.pcap"


# ---------- Script principal ----------

# abre o arquivo CSV para escrita
with open(RESULT_FILE, "w", newline="") as f:

    writer = csv.writer(f)

    # escreve o cabeçalho do CSV
    writer.writerow([
        "rep",
        "algoritmo",
        "ber",
        "bg_udp_mbps",
        "vazao_tcp",
        "retrans_total",
        "taxa_retrans",
        "efficiency"
    ])

    # percorre cada algoritmo TCP definido
    for tcp in TCP_VARIANTS:

        print(f"\n=== TCP {tcp} ===")

        # configura o algoritmo TCP no pc1 e pc2
        run(f"himage {PC1} sysctl -w net.ipv4.tcp_congestion_control={tcp}")
        run(f"himage {PC2} sysctl -w net.ipv4.tcp_congestion_control={tcp}")

        # percorre cada valor de BER
        for ber in BERS:

            print(f"\nConfig BER {ber}")

            # configura o BER no enlace entre router1 e router2
            run(f"sudo vlink -BER {ber} -eid {EID} router1:router2")

            # reduz o tamanho da fila de transmissão no router1 e router2 para 10
            run(f"himage router1@{EID} ip link set dev eth2 txqueuelen 10")
            run(f"himage router2@{EID} ip link set dev eth0 txqueuelen 10")

            # remove qualquer qdisc anterior do router1 e router2
            run(f"himage router1@{EID} tc qdisc del dev eth2 root || true")
            run(f"himage router2@{EID} tc qdisc del dev eth0 root || true")

            # adiciona perda artificial de 0.2% no router1 e router2
            run(f"himage router1@{EID} tc qdisc add dev eth2 root netem loss 2%")
            run(f"himage router2@{EID} tc qdisc add dev eth0 root netem loss 2%")


            # percorre cada taxa de tráfego UDP
            for udp in UDP_RATES:

                print(f"\nUDP {udp} Mbps")

                # encerra qualquer iperf anterior no pc4
                run(f"himage {PC4} pkill iperf || true")
                # inicia servidor UDP no pc4
                run(f"himage {PC4} iperf -s -u -D")
                # encerra iperf anterior no pc3
                run(f"himage {PC3} pkill iperf || true")
                # inicia cliente UDP no pc3 gerando tráfego de fundo
                run(f"himage {PC3} bash -c 'iperf -c {UDP_SERVER_IP} -u -b {udp}M &'")

                time.sleep(2)

                # executa as 8 repetições do experimento
                for rep in range(1, REPS + 1):

                    print(f"\nExecução {rep}")

                    # mata servidores iperf antigos no pc2
                    run(f"himage {PC2} pkill iperf || true")
                    time.sleep(1)

                    # inicia servidor TCP no pc2
                    run(f"himage {PC2} iperf -s -D")
                    wait_iperf_server(PC2)

                    # encerra tcpdump antigo
                    run(f"himage {PC1} pkill tcpdump || true")
                    time.sleep(1)

                    # inicia captura de pacotes no pc1
                    run(f"himage {PC1} tcpdump -i eth0 -s 0 -w {PCAP_PATH} host {TCP_SERVER_IP} &")
                    time.sleep(2)

                    # Executa teste TCP de 30 segundos
                    saida = run_output(f"himage {PC1} iperf -c {TCP_SERVER_IP} -t 30 -f m | grep sec | tail -1")

                    # extrai o valor da vazão da saída do iperf
                    vazao_tcp = float(saida.split()[-2])

                    time.sleep(2)

                    # encerra captura tcpdump
                    run(f"himage {PC1} pkill tcpdump || true")

                    LOCAL_PCAP = f"./fluxo_{tcp}_{ber}_{udp}_{rep}.pcap"

                    # copia o arquivo pcap do pc1 para a máquina local
                    run(f"sudo hcp {PC1}:{PCAP_PATH} {LOCAL_PCAP}")

                    # ---------- métricas tshark ----------

                    # total de segmentos de dados enviados (pc1 -> pc2)
                    total_enviado = int(run_output(
                        f'tshark -r {LOCAL_PCAP} -Y "ip.src=={TCP_SRC_IP} and tcp.len>0" | wc -l'
                    ))

                    # total de retransmissões
                    retrans_total = int(run_output(
                        f'tshark -r {LOCAL_PCAP} -Y "ip.src=={TCP_SRC_IP} and tcp.len>0 and '
                        f'(tcp.analysis.retransmission or tcp.analysis.fast_retransmission)" | wc -l'
                    ))

                    # taxa de retransmissão
                    taxa_retrans = retrans_total / total_enviado if total_enviado > 0 else 0
                    taxa_retrans = round(taxa_retrans, 3)

                    # ---------- eficiência TCP ----------

                    # soma dos bytes de payload TCP
                    tcp_bytes = int(run_output(
                        f'tshark -r {LOCAL_PCAP} -Y "ip.addr=={TCP_SERVER_IP}" '
                        f'-T fields -e tcp.len | awk \'{{sum+=$1}} END {{print sum}}\''
                    ))

                    # soma dos bytes totais do frame
                    frame_bytes = int(run_output(
                        f'tshark -r {LOCAL_PCAP} -Y "ip.addr=={TCP_SERVER_IP}" '
                        f'-T fields -e frame.len | awk \'{{sum+=$1}} END {{print sum}}\''
                    ))

                    # calcula eficiência (payload útil / bytes totais transmitidos)
                    efficiency = tcp_bytes / frame_bytes if frame_bytes > 0 else 0
                    efficiency = round(efficiency, 3)

                    # grava os resultados no CSV
                    writer.writerow([
                        rep,
                        tcp,
                        ber,
                        udp,
                        vazao_tcp,
                        retrans_total,
                        taxa_retrans,
                        efficiency
                    ])

                    print("Vazao:", vazao_tcp)
                    print("Retransmissoes:", retrans_total)

                    # remove o arquivo pcap local após análise
                    run(f"rm -f {LOCAL_PCAP}")

                # encerra tráfego UDP após terminar as repetições
                run(f"himage {PC3} pkill iperf || true")
                run(f"himage {PC4} pkill iperf || true")


print("\nExperimento finalizado. Resultados salvos em", RESULT_FILE)