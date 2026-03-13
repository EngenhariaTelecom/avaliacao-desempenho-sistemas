# 1. Análise Teórica da Cadeia de Markov

import numpy as np

# matriz de transição
P = np.array([
    [0.6, 0.3, 0.1],
    [0.2, 0.6, 0.2],
    [0.1, 0.3, 0.6]
])

# cálculo do vetor estacionário
autovalores, autovetores = np.linalg.eig(P.T)

# selecionar autovetor associado ao autovalor 1
pi = autovetores[:, np.isclose(autovalores, 1)]
pi = pi[:, 0]

# normalizar
pi = pi / np.sum(pi)

print("Vetor estacionário π:")
print(pi)


# 2. Vazão Média Teórica
taxas = np.array([0, 10, 50])

T_medio = np.dot(pi, taxas)

print("Vazão média teórica (Mbps):", T_medio)



# 3. Simulação da Cadeia (500 passos)
import random
from collections import Counter

P = [
    [0.6, 0.3, 0.1],
    [0.2, 0.6, 0.2],
    [0.1, 0.3, 0.6]
]

passos = 500
estado = 0
estados = []

for i in range(passos):
    estados.append(estado)
    estado = random.choices([0,1,2], weights=P[estado])[0]

# frequência observada
freq = Counter(estados)

print("Frequência dos estados:")
for s in range(3):
    print(f"Estado {s}: {freq[s]/passos:.3f}")


# 4. Script Python para Gerar Tráfego com iperf
import random
import subprocess
import time

# matriz de transição
P = [
    [0.6, 0.3, 0.1],
    [0.2, 0.6, 0.2],
    [0.1, 0.3, 0.6]
]

estado = 0
servidor = "10.0.0.2"   # alterar para IP do servidor
epocas = 50

for passo in range(epocas):

    estado = random.choices([0,1,2], weights=P[estado])[0]

    print(f"Passo {passo+1} - Estado {estado}")

    if estado == 0:
        print("Sem tráfego")
        time.sleep(5)

    elif estado == 1:
        print("Tráfego 10 Mbps")
        subprocess.run([
            "iperf",
            "-c", servidor,
            "-u",
            "-b", "10M",
            "-l", "1400",
            "-t", "5",
            "-y", "C"
        ])

    elif estado == 2:
        print("Tráfego 50 Mbps")
        subprocess.run([
            "iperf",
            "-c", servidor,
            "-u",
            "-b", "50M",
            "-l", "1400",
            "-t", "5",
            "-y", "C"
        ])

# 5. Servidor iperf

    # executar no terminal: iperf -s -u


# 6. O que você deve medir no relatório?

    # Vazão = bytes transmitidos / tempo total
    # tempo total = 250s

# OBSERVAÇÃO: Antes de rodar o script:

    # Terminal 1 (servidor)
    # iperf -s -u