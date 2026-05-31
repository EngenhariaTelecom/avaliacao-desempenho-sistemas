"""
=============================================================
  DES — Simulação de Domínio de Colisão (CSMA/CD)
  Disciplina: Redes de Computadores / Simulação
=============================================================

CONCEITO GERAL:
  Dois computadores (A e B) compartilham um meio físico (cabo).
  Quando os dois transmitem "ao mesmo tempo" (dentro da janela
  de propagação), ocorre uma colisão. Ambos param, esperam um
  tempo aleatório (backoff) e tentam novamente.

PARÂMETROS FÍSICOS:
  - Velocidade:      10 Mbps = 10_000_000 bits/s
  - Propagação A→B:  3.33 ms  (tempo que o sinal leva de A até B)
  - Estação A:       chegada Poisson(λ pps), tamanho uniforme [20,1000] bytes
  - Estação B:       periódica a cada 40 ms, tamanho fixo 500 bytes
  - Fila:            5000 bytes por estação (descarta se cheia)
"""

import heapq          # fila de prioridade (min-heap) por tempo
import random         # gerador de números aleatórios
import math           # log para distribuição exponencial


# ─────────────────────────────────────────────────────────────
# BLOCO 1: CLASSES BASE (fornecidas pelo enunciado)
# ─────────────────────────────────────────────────────────────

class Event:
    """
    Classe base para todos os eventos do simulador.
    
    Todo evento tem um 'time' (momento em que acontece).
    O método __lt__ permite que o heapq compare eventos
    e sempre processe o de menor tempo primeiro.
    """
    def __init__(self, time):
        self.time = time                  # quando este evento ocorre (em segundos)

    def __lt__(self, other):
        # heapq usa isso para ordenar: menor time = maior prioridade
        return self.time < other.time

    def processing_event(self, simulator):
        # cada subclasse implementa o que acontece quando o evento é processado
        raise NotImplementedError("Subclasses devem implementar este método")


class Simulator:
    """
    Classe base do simulador.
    
    Mantém:
      - current_time: o "relógio" da simulação
      - event_queue:  a lista de eventos futuros (heap)
      - end_time:     quando parar
    """
    def __init__(self, end_time):
        self.current_time = 0             # relógio começa em zero
        self.event_queue  = []            # fila vazia inicialmente
        self.end_time     = end_time      # tempo de simulação em segundos

    def schedule(self, event):
        """Insere um evento na fila de prioridade."""
        heapq.heappush(self.event_queue, event)

    def run(self):
        """
        Loop principal da simulação:
        Retira o evento de menor tempo, avança o relógio,
        e chama o processing_event() daquele evento.
        Repete até a fila esvaziar ou o tempo acabar.
        """
        while self.event_queue and self.current_time < self.end_time:
            event = heapq.heappop(self.event_queue)   # pega o evento mais próximo
            self.current_time = event.time             # avança o relógio
            event.processing_event(self)               # processa o evento


# ─────────────────────────────────────────────────────────────
# BLOCO 2: CONSTANTES DO SISTEMA FÍSICO
# ─────────────────────────────────────────────────────────────

BANDWIDTH        = 10e6          # 10 Mbps em bits/segundo
PROP_DELAY       = 3.33e-3       # 3.33 ms = tempo de propagação A→B (e B→A)
MAX_QUEUE_BYTES  = 5000          # capacidade máxima da fila de cada estação
BACKOFF_SLOTS    = 10            # número de slots de backoff possíveis
SLOT_TIME        = 2 * PROP_DELAY  # slot = 2× propagação (padrão CSMA/CD)
# SLOT_TIME = 6.66 ms — tempo mínimo para detectar qualquer colisão


def transmission_time(size_bytes):
    """
    Calcula quanto tempo leva para transmitir 'size_bytes' bytes.
    
    Exemplo: 500 bytes = 4000 bits / 10_000_000 bps = 0.4 ms
    """
    return (size_bytes * 8) / BANDWIDTH


# ─────────────────────────────────────────────────────────────
# BLOCO 3: EVENTOS CONCRETOS
# ─────────────────────────────────────────────────────────────

class ArrivalEvent(Event):
    """
    Representa a chegada de um novo pacote na fila de uma estação.
    
    Ao ser processado:
      1. Verifica se a fila tem espaço → insere ou descarta
      2. Se a estação estava ociosa → agenda StartTransmissionEvent
      3. Agenda o próximo ArrivalEvent (processo de chegada continua)
    """
    def __init__(self, time, station_id, pkt_size):
        super().__init__(time)
        self.station_id = station_id   # 'A' ou 'B'
        self.pkt_size   = pkt_size     # tamanho do pacote em bytes

    def processing_event(self, sim):
        station = sim.stations[self.station_id]

        # ── Verifica espaço na fila ──────────────────────────
        if station['queue_bytes'] + self.pkt_size <= MAX_QUEUE_BYTES:
            station['queue'].append(self.pkt_size)   # adiciona à fila
            station['queue_bytes'] += self.pkt_size
        else:
            station['packets_dropped'] += 1           # fila cheia → descarte
            # (não agenda transmissão nem continua)

        # ── Se a estação está livre, inicia transmissão ──────
        # (a fila pode ter ficado vazia entre eventos, por isso checamos)
        if not station['transmitting'] and station['queue']:
            sim.schedule(StartTransmissionEvent(sim.current_time, self.station_id))

        # ── Agenda a próxima chegada desta estação ───────────
        # (isso é o que cria o fluxo contínuo de pacotes)
        sim.schedule_next_arrival(self.station_id, sim.current_time)


class StartTransmissionEvent(Event):
    """
    A estação tenta começar a transmitir o próximo pacote da fila.
    
    Verifica se há colisão:
      - Colisão: outra estação está transmitindo E seu sinal
                 ainda não chegou aqui (dentro da janela de propagação)
      - Sem colisão: inicia tx normalmente, agenda EndTransmissionEvent
    """
    def __init__(self, time, station_id):
        super().__init__(time)
        self.station_id = station_id

    def processing_event(self, sim):
        station = sim.stations[self.station_id]

        # Sem pacotes na fila → nada a fazer
        if not station['queue']:
            return

        # ── Verifica se há colisão ───────────────────────────
        #
        # Colisão ocorre se a outra estação estiver transmitindo
        # E ainda não tiver terminado de propagar seu sinal até aqui.
        #
        # Exemplo: A começa em t=0. Sinal chega em B em t=3.33ms.
        # Se B começa antes de t=3.33ms → B "não viu" o sinal de A → COLISÃO.
        #
        other_id = 'B' if self.station_id == 'A' else 'A'
        other    = sim.stations[other_id]
        me       = station

        collision = False
        if other['transmitting']:
            # Quando o sinal da outra estação chegaria aqui?
            signal_arrival = other['tx_start_time'] + PROP_DELAY
            if sim.current_time < signal_arrival:
                # Ainda não chegou → não vemos o canal ocupado → COLISÃO
                collision = True

        if collision:
            # ── Trata colisão ────────────────────────────────
            sim.total_collisions += 1
            me['collisions']     += 1
            other['collisions']  += 1

            # Ambas as estações param de transmitir
            me['transmitting']    = False
            other['transmitting'] = False

            # Ambas fazem backoff (espera aleatória)
            sim.schedule(BackoffEvent(sim.current_time, self.station_id))
            sim.schedule(BackoffEvent(sim.current_time, other_id))

        else:
            # ── Inicia transmissão sem colisão ───────────────
            pkt_size = me['queue'][0]   # pega o próximo pacote (não remove ainda)
            tx_time  = transmission_time(pkt_size)

            me['transmitting']   = True
            me['tx_start_time']  = sim.current_time
            me['tx_pkt_size']    = pkt_size

            # Agenda o fim desta transmissão
            sim.schedule(EndTransmissionEvent(
                sim.current_time + tx_time,
                self.station_id
            ))


class EndTransmissionEvent(Event):
    """
    A transmissão terminou com sucesso.
    
    Ao ser processado:
      1. Remove o pacote da fila (foi enviado)
      2. Atualiza métricas de vazão
      3. Se ainda há pacotes na fila → agenda próxima transmissão
    """
    def __init__(self, time, station_id):
        super().__init__(time)
        self.station_id = station_id

    def processing_event(self, sim):
        station = sim.stations[self.station_id]

        # Não estava transmitindo (foi cancelado por colisão) → ignora
        if not station['transmitting']:
            return

        # ── Pacote transmitido com sucesso ───────────────────
        pkt_size = station['queue'].pop(0)        # remove da fila
        station['queue_bytes'] -= pkt_size
        station['transmitting']  = False
        station['bytes_sent']   += pkt_size       # contabiliza vazão

        # ── Próximo pacote na fila? ──────────────────────────
        if station['queue']:
            sim.schedule(StartTransmissionEvent(sim.current_time, self.station_id))


class BackoffEvent(Event):
    """
    Após uma colisão, a estação espera um tempo aleatório
    antes de tentar transmitir novamente.
    
    O backoff é: random.randint(0, BACKOFF_SLOTS) × SLOT_TIME
    Isso espalha as retransmissões no tempo, reduzindo nova colisão.
    """
    def __init__(self, time, station_id):
        super().__init__(time)
        self.station_id = station_id

    def processing_event(self, sim):
        station = sim.stations[self.station_id]
        station['backoffs'] += 1

        # Tempo de espera aleatório
        wait = random.randint(0, BACKOFF_SLOTS) * SLOT_TIME

        # Após o backoff, tenta transmitir novamente
        sim.schedule(StartTransmissionEvent(
            sim.current_time + wait,
            self.station_id
        ))


# ─────────────────────────────────────────────────────────────
# BLOCO 4: O SIMULADOR PRINCIPAL
# ─────────────────────────────────────────────────────────────

class CollisionSimulator(Simulator):
    """
    Simulador do domínio de colisão.
    
    Herda de Simulator e adiciona:
      - Estado das duas estações (fila, bytes enviados, métricas)
      - Lógica de geração de chegadas (Poisson para A, periódica para B)
      - Coleta de métricas ao final
    """

    def __init__(self, end_time, lambda_a):
        """
        end_time: duração da simulação em segundos
        lambda_a: taxa de chegada da estação A (pacotes por segundo)
        """
        super().__init__(end_time)
        self.lambda_a         = lambda_a
        self.total_collisions = 0

        # ── Estado de cada estação ───────────────────────────
        # Toda a informação de uma estação fica num dicionário.
        self.stations = {
            'A': {
                'queue':          [],     # lista de tamanhos de pacotes em espera
                'queue_bytes':    0,      # total de bytes na fila (para checar limite)
                'transmitting':   False,  # está transmitindo agora?
                'tx_start_time':  0,      # quando começou a transmissão atual
                'tx_pkt_size':    0,      # tamanho do pacote sendo transmitido
                'bytes_sent':     0,      # total de bytes enviados com sucesso
                'collisions':     0,      # quantas colisões envolveu
                'backoffs':       0,      # quantos backoffs fez
                'packets_dropped':0,      # pacotes descartados por fila cheia
            },
            'B': {
                'queue':          [],
                'queue_bytes':    0,
                'transmitting':   False,
                'tx_start_time':  0,
                'tx_pkt_size':    0,
                'bytes_sent':     0,
                'collisions':     0,
                'backoffs':       0,
                'packets_dropped':0,
            },
        }

    def setup(self):
        """
        Agenda os primeiros eventos para iniciar a simulação.
        Chame este método antes de run().
        """
        # Primeira chegada de A: amostra da distribuição exponencial
        # (interburst de Poisson = exponencial com média 1/λ)
        first_a = random.expovariate(self.lambda_a)
        pkt_a   = random.randint(20, 1000)           # tamanho uniforme [20,1000] bytes
        self.schedule(ArrivalEvent(first_a, 'A', pkt_a))

        # Primeira chegada de B: periódica, começa em t=0
        self.schedule(ArrivalEvent(0.0, 'B', 500))   # 500 bytes fixo

    def schedule_next_arrival(self, station_id, current_time):
        """
        Agenda a próxima chegada para uma estação.
        
        Para A: tempo é exponencialmente distribuído (Poisson)
        Para B: tempo é fixo a cada 40ms (periódico)
        """
        if station_id == 'A':
            inter_arrival = random.expovariate(self.lambda_a)
            pkt_size      = random.randint(20, 1000)
            t_next        = current_time + inter_arrival
        else:  # B
            inter_arrival = 0.040    # 40 ms = 0.040 s
            pkt_size      = 500
            t_next        = current_time + inter_arrival

        if t_next < self.end_time:   # só agenda se ainda está dentro da simulação
            self.schedule(ArrivalEvent(t_next, station_id, pkt_size))

    def results(self):
        """
        Calcula e imprime as métricas de desempenho.
        
        Vazão = bytes enviados com sucesso × 8 / tempo total
        """
        T = self.end_time   # tempo total em segundos

        print("=" * 55)
        print("  RESULTADOS DA SIMULAÇÃO")
        print(f"  Duração: {T:.1f} s   |   λ_A = {self.lambda_a} pps")
        print("=" * 55)

        for sid in ['A', 'B']:
            s = self.stations[sid]
            throughput_bps = (s['bytes_sent'] * 8) / T
            throughput_mbps = throughput_bps / 1e6
            print(f"\n  Estação {sid}:")
            print(f"    Bytes enviados com sucesso : {s['bytes_sent']:>10,} bytes")
            print(f"    Vazão efetiva              : {throughput_bps:>10,.0f} bps  ({throughput_mbps:.4f} Mbps)")
            print(f"    Colisões                   : {s['collisions']:>10,}")
            print(f"    Backoffs                   : {s['backoffs']:>10,}")
            print(f"    Pacotes descartados        : {s['packets_dropped']:>10,}")

        print(f"\n  Total de colisões            : {self.total_collisions:>10,}")
        print("=" * 55)


# ─────────────────────────────────────────────────────────────
# BLOCO 5: EXECUÇÃO
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    random.seed(42)   # semente fixa para reprodutibilidade

    # Parâmetros da simulação
    SIMULATION_TIME = 10.0    # segundos de simulação
    LAMBDA_A        = 50      # 50 pacotes/segundo (taxa Poisson de A)

    print(f"\nIniciando simulação: {SIMULATION_TIME}s, λ_A={LAMBDA_A} pps\n")

    # Cria e configura o simulador
    sim = CollisionSimulator(
        end_time  = SIMULATION_TIME,
        lambda_a  = LAMBDA_A,
    )
    sim.setup()   # agenda os primeiros eventos

    # Roda a simulação
    sim.run()

    # Exibe os resultados
    sim.results()

    # ── Experimento extra: varia a carga de A ─────────────────
    print("\n\n  EXPERIMENTO: Variando λ_A\n")
    print(f"  {'λ_A (pps)':<12} {'Vazão A (Mbps)':<16} {'Vazão B (Mbps)':<16} {'Colisões':<10}")
    print("  " + "-"*56)

    for lam in [10, 25, 50, 100, 200, 500]:
        random.seed(42)
        s = CollisionSimulator(end_time=10.0, lambda_a=lam)
        s.setup()
        s.run()

        th_a = (s.stations['A']['bytes_sent'] * 8) / 10.0 / 1e6
        th_b = (s.stations['B']['bytes_sent'] * 8) / 10.0 / 1e6
        print(f"  {lam:<12} {th_a:<16.4f} {th_b:<16.4f} {s.total_collisions:<10}")