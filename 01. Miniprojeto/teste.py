import subprocess
import csv
import time

# ---------- Funções auxiliares ----------

def get_active_eid():
    out = subprocess.check_output("himage -l", shell=True).decode().strip()
    first_line = out.split("\n")[0]
    eid = first_line.split()[0]
    return eid


def run(cmd):
    print(cmd)
    subprocess.run(cmd, shell=True, check=True)


def run_output(cmd):
    return subprocess.check_output(cmd, shell=True).decode().strip()


def wait_iperf_server(pc):
    for _ in range(20):
        out = run_output(f"himage {pc} ss -ltn | grep ':5001' || true")
        if out.strip() != "":
            return
        time.sleep(1)


# ---------- Configurações ----------

EID = get_active_eid()
print("EID detectado:", EID)

RESULT_FILE = "./result_experimento_sem_perda.csv"

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

with open(RESULT_FILE, "w", newline="") as f:

    writer = csv.writer(f)

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


    for tcp in TCP_VARIANTS:

        print(f"\n=== TCP {tcp} ===")

        run(f"himage {PC1} sysctl -w net.ipv4.tcp_congestion_control={tcp}")
        run(f"himage {PC2} sysctl -w net.ipv4.tcp_congestion_control={tcp}")


        for ber in BERS:

            print(f"\nConfig BER {ber}")

            run(f"sudo vlink -BER {ber} -eid {EID} router1:router2")

            run(f"himage router1@{EID} ip link set dev eth2 txqueuelen 10")
            run(f"himage router2@{EID} ip link set dev eth0 txqueuelen 10")

            run(f"himage router1@{EID} tc qdisc del dev eth2 root || true")
            run(f"himage router2@{EID} tc qdisc del dev eth0 root || true")

            #run(f"himage router1@{EID} tc qdisc add dev eth2 root netem loss 0.1%")
            #run(f"himage router2@{EID} tc qdisc add dev eth0 root netem loss 0.1%")


            for udp in UDP_RATES:

                print(f"\nUDP {udp} Mbps")

                run(f"himage {PC4} pkill iperf || true")
                run(f"himage {PC4} iperf -s -u -D")

                run(f"himage {PC3} pkill iperf || true")
                run(f"himage {PC3} bash -c 'iperf -c {UDP_SERVER_IP} -u -b {udp}M &'")

                time.sleep(2)


                for rep in range(1, REPS + 1):

                    print(f"\nExecução {rep}")

                    run(f"himage {PC2} pkill iperf || true")
                    time.sleep(1)

                    run(f"himage {PC2} iperf -s -D")

                    wait_iperf_server(PC2)

                    run(f"himage {PC1} pkill tcpdump || true")
                    time.sleep(1)

                    run(f"himage {PC1} tcpdump -i eth0 -s 0 -w {PCAP_PATH} host {TCP_SERVER_IP} &")

                    time.sleep(2)

                    # Executa teste TCP
                    saida = run_output(f"himage {PC1} iperf -c {TCP_SERVER_IP} -t 30 -f m | grep sec | tail -1")

                    vazao_tcp = float(saida.split()[-2])

                    time.sleep(2)

                    run(f"himage {PC1} pkill tcpdump || true")

                    LOCAL_PCAP = f"./fluxo_{tcp}_{ber}_{udp}_{rep}.pcap"

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

                    # eficiência
                    efficiency = tcp_bytes / frame_bytes if frame_bytes > 0 else 0
                    efficiency = round(efficiency, 3)

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

                    run(f"rm -f {LOCAL_PCAP}")


                run(f"himage {PC3} pkill iperf || true")
                run(f"himage {PC4} pkill iperf || true")


print("\nExperimento finalizado. Resultados salvos em", RESULT_FILE)