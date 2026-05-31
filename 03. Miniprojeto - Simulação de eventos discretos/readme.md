# Mini-Projeto Simulação a Eventos Discretos (DES)

## 1. Fundamentação Teórica

A Simulação a Eventos Discretos (Discrete Event Simulation - DES) é uma técnica de modelagem computacional que permite representar o comportamento dinâmico de sistemas ao longo do tempo. Os sistemas são modelados como uma sequência de eventos que ocorrem em instantes distintos. Cada evento modifica o estado do sistema, que permanece constante entre um evento e outro.


### Componentes de uma Simulação a Eventos Discretos

• Relógio de simulação: Mantém o tempo atual simulado.

• Lista de eventos futuros: Estrutura ordenada por tempo com os próximos eventos agendados.

• Eventos: Ocorrências instantâneas que alteram o estado do sistema.

• Estado do sistema: Conjunto de variáveis que representam o sistema em dado instante.

• Métricas de desempenho: Variáveis coletadas ao longo da simulação (ex: tempo de resposta, utilização, perdas).

## 2. Arcabouço Base Orientado a Objetos para DES

A seguir, apresentamos as duas classes base fundamentais da arquitetura orientada a objetos para simuladores a eventos discretos. O simulador utiliza uma fila de eventos priorizada, organizada por tempo, para garantir que os eventos sejam processados em ordem cronológica. Essa fila é implementada em Python utilizando o módulo heapq, que mantém a propriedade de mı́nimo através do método especial lt () da classe Event.

```python
c l a s s Event :
    def
    i n i t ( s e l f , time ) :
    s e l f . time = time
    def
    l t ( s e l f , other ) :
    # D e f i n e a ordem de p r i o r i d a d e na f i l a de e v e n t o s
    r e t u r n s e l f . time < o t h e r . time
    def processing event ( s e l f , simulator ) :
    # Deve s e r implementado p e l a s s u b c l a s s e s
    r a i s e NotImplementedError ( ” S u b c l a s s e s devem implementar e s t e m t o d o ” )

import heapq
c l a s s Simulator :
    def
    i n i t ( s e l f , end time ) :
    s e l f . current time = 0
    s e l f . e v e n t q u e u e = [ ] # f i l a de e v e n t o s f u t u r o s
    s e l f . end time = end time
    def schedule ( s e l f , event ) :
    # I n s e r e e v e n t o na f i l a p r i o r i z a d a
    heapq . heappush ( s e l f . e v e n t q u e u e , e v e n t )
    d e f run ( s e l f ) :
    # P r o c e s s a o s e v e n t o s em ordem t e m p o r a l
    w h i l e s e l f . e v e n t q u e u e and s e l f . c u r r e n t t i m e < s e l f . e n d t i m e :
        e v e n t = heapq . heappop ( s e l f . e v e n t q u e u e )
        s e l f . c u r r e n t t i m e = e v e n t . time
        event . p r o c e s s i n g e v e n t ( s e l f )
```

OBS.: Estas classes deverão ser usadas para construção do DES proposto na sequência. Os eventos devem ser derivados da classe Event e o simulador derivado da classe Simulator.

# Proposta de Trabalho 1: Simulação de Domı́nio de Colisão

## Objetivo

Avaliar o desempenho de duas estações compartilhando um meio fı́sico com colisões, utilizando simulação a eventos discretos.

### Descrição

• Estação A envia pacotes com chegada Poisson ( pps), tamanho uniforme entre 20 e 1000 bytes.

• Estação B envia pacotes periódicos a cada 40ms, tamanho fixo de 500 bytes.

• Velocidade de transmissão: 10 Mbps.

• Tempo de propagação: 3,33ms (tempo entre A e B).

• Colisões são detectadas se transmissões começarem dentro do intervalo de propagação.

• Estações esperam e fazem backoff aleatório se detectarem canal ocupado.

• Fila de 5000 bytes por estação.

### Métricas

• Vazão efetiva por estação (em bps).

• Total de colisões.

• Número de backoffs por estação.