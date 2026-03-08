import subprocess
import csv
import time

EID = "i5491"
RESULT_FILE = "resultados.csv"

TCP_VARIANTS = ["reno", "cubic"]
BERS = [1000000, 100000]   # 1e-6 e 1e-5
UDP_RATES = [800, 900]
REPS = 8

PC1 = f"pc1@{EID}"
PC2 = f"pc2@{EID}"
PC3 = f"pc3@{EID}"
PC4 = f"pc4@{EID}"

TCP_SERVER_IP = "10.0.3.20"
UDP_SERVER_IP = "10.0.4.20"
TCP_SRC_IP = "10.0.0.20"


def run(cmd):
    print(cmd)
    subprocess.run(cmd, shell=True)


def run_output(cmd):
    return subprocess.check_output(cmd, shell=True).decode().strip()


with open(RESULT_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["tcp", "ber", "udp", "rep", "segmentos", "retransmissoes"])

    for tcp in TCP_VARIANTS:

        print(f"\n=== TCP {tcp} ===")
        run(f"sysctl -w net.ipv4.tcp_congestion_control={tcp}")

        for ber in BERS:

            print(f"Config BER {ber}")
            run(f"sudo vlink -BER {ber} -eid {EID} router1:router2")

            for udp in UDP_RATES:

                print(f"UDP {udp} Mbps")

                run(f"himage {PC4} iperf -s -u -D")
                run(f"himage {PC3} iperf -c {UDP_SERVER_IP} -u -b {udp}M -t 40 -D")

                for rep in range(1, REPS + 1):

                    print(f"Execução {rep}")

                    run(f"himage {PC2} pkill iperf || true")
                    run(f"himage {PC2} iperf -s -D")

                    run(f"himage {PC1} tcpdump -i eth0 -s 0 -w /tmp/fluxo.pcap host {TCP_SERVER_IP} and tcp &")

                    time.sleep(2)

                    run(f"himage {PC1} iperf -c {TCP_SERVER_IP} -t 30")

                    time.sleep(2)

                    run(f"himage {PC1} pkill tcpdump")

                    run(f'himage {PC1} cat /tmp/fluxo.pcap > fluxo.pcap')

                    seg = run_output(
                        f'tshark -r fluxo.pcap -Y "ip.src=={TCP_SRC_IP} and tcp.len>0" 2>/dev/null | wc -l'
                    )

                    ret = run_output(
                        'tshark -r fluxo.pcap -Y "tcp.analysis.retransmission or tcp.analysis.fast_retransmission" 2>/dev/null | wc -l'
                    )

                    writer.writerow([tcp, ber, udp, rep, seg, ret])

                    run("rm -f fluxo.pcap")

                run(f"himage {PC3} pkill iperf")
                run(f"himage {PC4} pkill iperf")