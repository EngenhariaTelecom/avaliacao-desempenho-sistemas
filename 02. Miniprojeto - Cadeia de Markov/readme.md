# Análise Teórica da Cadeia de Markov - Cálculo Manual

Este documento apresenta a modelagem matemática e o cálculo do regime estacionário para o sistema de monitoramento de banda.

## 1. Definição dos Estados

O sistema é classificado em três estados de consumo, cada um associado a uma taxa de transferência:

| Estado | Significado | Taxa    |
| :---:  | :---        | :---    |
| 0      | Ocioso      | 0 Mbps  |
| 1      | Moderado    | 10 Mbps |
| 2      | Alto        | 50 Mbps |

---

## 2. Matriz de Transição ($P$)

A matriz de probabilidade de transição define a chance de o sistema mudar de um estado para outro em cada intervalo de tempo:

$$
P = \begin{bmatrix}
0.6 & 0.3 & 0.1 \\
0.2 & 0.6 & 0.2 \\
0.1 & 0.3 & 0.6
\end{bmatrix}
$$

### Interpretação da Matriz
Se o sistema está no **Estado 0 (Ocioso)**, ele apresenta:
* **60%** de chance de continuar ocioso.
* **30%** de chance de ir para o estado moderado.
* **10%** de chance de ir para o estado alto.

---

## 3. Cálculo do Vetor de Regime Estacionário ($\pi$)

O objetivo é encontrar o vetor $\pi = (\pi_0, \pi_1, \pi_2)$ que satisfaça a condição de equilíbrio $\pi \cdot P = \pi$.

### Sistema de Equações
A partir da multiplicação matricial, obtemos o seguinte sistema:

1. $\pi_0 = 0.6\pi_0 + 0.2\pi_1 + 0.1\pi_2$
2. $\pi_1 = 0.3\pi_0 + 0.6\pi_1 + 0.3\pi_2$
3. $\pi_2 = 0.1\pi_0 + 0.2\pi_1 + 0.6\pi_2$

**Restrição de Probabilidade:**
4. $\pi_0 + \pi_1 + \pi_2 = 1$

### Resolução Passo a Passo
1. **Isolando $\pi_2$ na Equação 1:**
   $0.4\pi_0 - 0.2\pi_1 = 0.1\pi_2$  
   $4\pi_0 - 2\pi_1 = \pi_2$ **(Equação 5)**

2. **Substituindo a Equação 5 na Equação 3:**
   $\pi_2 = 0.1\pi_0 + 0.2\pi_1 + 0.6(4\pi_0 - 2\pi_1)$  
   Resultando na relação: $\pi_1 = 1.5\pi_0$ **(Equação 6)**

3. **Substituindo os valores na Restrição (Equação 4):**
   $\pi_0 + 1.5\pi_0 + \pi_0 = 1$  
   $3.5\pi_0 = 1$

### Resultado Final
Após as substituições, obtemos as probabilidades de longo prazo:

* **$\pi_0 = 0.286$** (Ocioso)
* **$\pi_1 = 0.429$** (Moderado)
* **$\pi_2 = 0.286$** (Alto)

Portanto, o vetor de regime estacionário é:
> **$\pi = (0.286, 0.429, 0.286)$**