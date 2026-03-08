# Este script além de aplicar as configurações solicitadas no projeto, aletramos o tamanho da fila do rotedor para forçar retransmissões.

# Alterado BER, Taxa UDP para forçar retransmissão

import subprocess
import csv
import time

# ---------- Funções auxiliares ----------
def get_active_eid():
    """Detecta automaticamente o EID ativo do IMUNES."""
    out = subprocess.check_output("himage -l", shell=True).decode().strip()
    first_line = out.split("\n")[0]
    eid = first_line.split()[0]
    return eid

def run(cmd):
    """Executa um comando sem capturar saída, mostrando no console."""
    print(cmd)
    subprocess.run(cmd, shell=True, check=True)

def run_output(cmd):
    """Executa um comando e retorna a saída como string."""
    return subprocess.check_output(cmd, shell=True).decode().strip()

def wait_iperf_server(pc):
    for _ in range(20):   # tenta até 20 vezes
        out = run_output(f"himage {pc} ss -ltn | grep ':5001' || true")
        if out.strip() != "":
            return
        time.sleep(1)


# ---------- Configurações gerais ----------
EID = get_active_eid()
print("EID detectado:", EID)

RESULT_FILE = "result2.csv"

TCP_VARIANTS = ["reno", "cubic"]
#BERS = [1000000, 100000]   # 1e-6 e 1e-5
BERS = [10000, 1000]   # 1e-4 e 1e-3
UDP_RATES = [900, 1000]     # Mbps
REPS = 8

# PCs do IMUNES
PC1 = f"pc1@{EID}"
PC2 = f"pc2@{EID}"
PC3 = f"pc3@{EID}"
PC4 = f"pc4@{EID}"

# IPs
TCP_SERVER_IP = "10.0.3.20"
UDP_SERVER_IP = "10.0.4.20"
TCP_SRC_IP = "10.0.0.20"

# Caminho do PCAP dentro da VM
PCAP_PATH = "/fluxo.pcap"


# ---------- Script principal ----------
with open(RESULT_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["tcp", "ber", "udp", "rep", "segmentos", "retransmissoes"])

    for tcp in TCP_VARIANTS:

        print(f"\n=== TCP {tcp} ===")
        # Configura TCP congestion control nas VMs que trafegam TCP
        run(f"himage {PC1} sysctl -w net.ipv4.tcp_congestion_control={tcp}")
        run(f"himage {PC2} sysctl -w net.ipv4.tcp_congestion_control={tcp}")

        for ber in BERS:

            print(f"\nConfig BER {ber}")
            # Configura BER entre roteadores (host)
            run(f"sudo vlink -BER {ber} -eid {EID} router1:router2")

            # REDUZ FILA DO ROTEADOR 
            run(f"himage router1@{EID} ip link set dev eth2 txqueuelen 10")
            run(f"himage router2@{EID} ip link set dev eth0 txqueuelen 10")

            for udp in UDP_RATES:

                print(f"\nUDP {udp} Mbps")

                # Inicia servidores UDP nas VMs
                run(f"himage {PC4} pkill iperf || true")
                run(f"himage {PC4} iperf -s -u -D")  # servidor UDP em daemon

                run(f"himage {PC3} pkill iperf || true")
                # cliente UDP rodando em background na VM
                run(f"himage {PC3} bash -c 'iperf -c {UDP_SERVER_IP} -u -b {udp}M &'")
                time.sleep(2)

                for rep in range(1, REPS + 1):

                    print(f"\nExecução {rep}")

                    # Limpa e inicia servidor TCP
                    run(f"himage {PC2} pkill iperf || true")
                    time.sleep(1)
                    run(f"himage {PC2} iperf -s -D")
                    wait_iperf_server(PC2)

                    # Captura tráfego TCP na VM
                    run(f"himage {PC1} pkill tcpdump || true")
                    time.sleep(1)
                    run(f"himage {PC1} tcpdump -i eth0 -s 0 -w {PCAP_PATH} host {TCP_SERVER_IP} &")

                    time.sleep(2)  # espera tcpdump iniciar

                    # Cliente TCP
                    run(f"himage {PC1} iperf -c {TCP_SERVER_IP} -t 30")

                    time.sleep(2)

                    # Para captura
                    run(f"himage {PC1} pkill tcpdump || true")

                    # Copia o arquivo .pcap da VM para máquina local dentro da pasta 'capturas'
                    LOCAL_PCAP = f"./fluxo_{tcp}_{ber}_{udp}_{rep}.pcap"
                    run(f"sudo hcp {PC1}:{PCAP_PATH} {LOCAL_PCAP}")

                    # Analisa segmentos e retransmissões diretamente na maquina local
                    seg = run_output(
                        f'tshark -r {LOCAL_PCAP} -Y "ip.src=={TCP_SRC_IP} and tcp.len>0" | wc -l'
                    )
                    ret = run_output(
                        f'tshark -r {LOCAL_PCAP} -Y "tcp.analysis.retransmission or tcp.analysis.fast_retransmission" | wc -l'
                    )

                    writer.writerow([tcp, ber, udp, rep, seg, ret])

                    print(f"Segmentos: {seg}, Retransmissões: {ret}")

                    # Apaga o arquivo pcap para não encher o disco
                    run(f"rm -f {LOCAL_PCAP}")

                # Para servidores UDP
                run(f"himage {PC3} pkill iperf || true")
                run(f"himage {PC4} pkill iperf || true")

print("\nExperimento finalizado. Resultados salvos em", RESULT_FILE)