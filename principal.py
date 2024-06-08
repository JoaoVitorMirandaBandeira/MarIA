import numpy as np
import random
import json
import matplotlib.pyplot as plt
import pickle
from pyboy import PyBoy
from pyboy.utils import WindowEvent
import time
import os

class Ambiente:
    def __init__(self, nome_arquivo='mario.gb', modo_silencioso=True):
        tipo_janela = "headless" if modo_silencioso else "SDL2"
        self.pyboy = PyBoy(nome_arquivo, window=tipo_janela, debug=modo_silencioso)
        self.pyboy.set_emulation_speed(500)
        self.mario = self.pyboy.game_wrapper
        self.mario.start_game()

    def calcular_fitness(self):
        # TODO: Pode mudar o cálculo do fitness
        return self.mario.score * 2 + 2 * self.mario.level_progress + self.mario.time_left

    def fim_de_jogo(self):
        return self.mario.lives_left == 1 or self.mario.score < 0

    def reset(self):
        self.mario.reset_game()
        self.pyboy.tick()
        return self.get_estado()

    def passo(self, indice_acao, duracao):
        if self.fim_de_jogo():
            print("Fim de jogo detectado")
            return None, 0, 0, "Fim de Jogo"
        # TODO: Pode mudar as ações, ainda pode usar down e up
        acoes = {
            0: WindowEvent.PRESS_ARROW_LEFT,
            1: WindowEvent.PRESS_ARROW_RIGHT,
            2: WindowEvent.PRESS_BUTTON_A
        }
        acoes_liberacao = {
            0: WindowEvent.RELEASE_ARROW_LEFT,
            1: WindowEvent.RELEASE_ARROW_RIGHT,
            2: WindowEvent.RELEASE_BUTTON_A
        }

        acao = acoes.get(indice_acao, WindowEvent.PASS)
        self.pyboy.send_input(acao)
        for _ in range(duracao):
            self.pyboy.tick()

        acao_liberacao = acoes_liberacao.get(indice_acao, WindowEvent.PASS)
        self.pyboy.send_input(acao_liberacao)
        self.pyboy.tick()

        tempo_restante = self.mario.time_left
        progresso_nivel = self.mario.level_progress
        return self.get_estado(), self.calcular_fitness(), tempo_restante, progresso_nivel

    def get_estado(self):
        return np.asarray(self.mario.game_area())

    def fechar(self):
        self.pyboy.stop()

class Individuo:
    # TODO: Pode mudar a quantidade de ações e a duração
    def __init__(self):
        self.acoes = self.gerar_acoes_favoritas(5000, 2, 15)
        self.fitness = 0
        self.pontos_tempo = 0
        self.movimentos_direita = 0


    def gerar_acoes_favoritas(self,comprimento, peso_1, max_duration):
        acoes = []
        for _ in range(comprimento):
            # Gera um número com maior probabilidade para o número 1
            numero = random.choices([0, 1, 2], weights=[1, peso_1, 1], k=1)[0]
            acoes.append((numero, random.randint(1, max_duration)))
        return acoes


    # TODO: Fique à vontade para mudar a função de avaliação e adicionar/remover parâmetros
    def avaliar(self, ambiente):
        estado = ambiente.reset()
        fitness_total = 0
        tempo_maximo = 0
        movimentos_direita = 0
        jogo_terminou = False

        for acao, duracao in self.acoes:
            if jogo_terminou == "Fim de Jogo":
                break
            novo_estado, fitness, tempo_restante, jogo_terminou = ambiente.passo(acao, duracao)
            fitness_total += fitness
            tempo_maximo = max(tempo_maximo, tempo_restante)
            movimentos_direita += 1 if acao == 1 else 0
            estado = novo_estado

        pontos_tempo = 500 if tempo_maximo > 0 else 0
        self.fitness = fitness_total + pontos_tempo + movimentos_direita * 5
        return self.fitness , pontos_tempo , movimentos_direita

def save_log(file_name,text):
        with open(f"./logs/{timestamp_atual}-execucao/{file_name}.txt","a") as file:
            file.write(str(text) + '\n')

# A divisão é para dar numeros mais manejáveis
def avaliar_fitness(individuo, ambiente):
    fitness, pontos_tempo , movimentos_direita = individuo.avaliar(ambiente)
    fitness_normalizado = fitness / 10000
    return fitness_normalizado, pontos_tempo , movimentos_direita

def iniciar_individuos(populacao):
    return [Individuo() for _ in range(populacao)]

def selecao(individuos, k=3):
    # TODO: Implementar seleção por torneio
    pais = []
    for _ in range(k):
        # Seleciona um subconjunto aleatório de indivíduos
        candidatos = random.sample(individuos, k)

        # Seleciona o indivíduo com maior fitness no subconjunto
        melhor_candidato = max(candidatos, key=lambda i: i.fitness)
        pais.append(melhor_candidato)
    return pais
    
def cruzamento(pai1, pai2,taxa_cruzamento=0.3):
    # TODO: Implementar cruzamento
    filho1 = Individuo()
    filho2 = Individuo()

    for i, (acao1, duracao1) in enumerate(pai1.acoes):
        acao2, duracao2 = pai2.acoes[i]

        # Realiza cruzamento com base na taxa de cruzamento
        if random.random() < taxa_cruzamento:
            filho1.acoes[i] = (acao2, duracao2)
            filho2.acoes[i] = (acao1, duracao1)
        else:
            filho1.acoes[i] = (acao1, duracao1)
            filho2.acoes[i] = (acao2, duracao2)

    return filho1, filho2

def mutacao(individuo, taxa_mutacao=0.1):
    # TODO: Implementar mutação
    for i, (acao, duracao) in enumerate(individuo.acoes):
    # Realiza mutação com base na taxa de mutação
        if random.random() < taxa_mutacao:
            # Muta a ação
            acao_mutada = random.choice([0, 1, 2])  # Altera para outra ação aleatória
            duracao_mutada = random.randint(1, 10)  # Altera a duração para um valor aleatório

            individuo.acoes[i] = (acao_mutada, duracao_mutada)

    return individuo  # A função não retorna nada

def imprimir_acoes_individuo(individuo):
    nomes_acoes = ["esquerda", "direita", "A"]
    acoes = [f"{nomes_acoes[acao]} por {duracao} ticks" for acao, duracao in individuo.acoes]
    return acoes

def algoritmo_genetico(populacao, ambiente, geracoes=100):
    melhor_individuo = None
    melhor_fitness = -np.inf

    for geracao in range(geracoes):
        save_log(f"geracao-{timestamp_atual}",f"-----------Geracao {geracao}----------")
        for individuo in populacao:
            individuo.fitness, individuo.pontos_tempo , individuo.movimentos_direita = avaliar_fitness(individuo, ambiente)
            print(f"Fitness: {individuo.fitness}")
            save_log(f"geracao-{timestamp_atual}",f"Movimentos a direita: {individuo.movimentos_direita} , Pontos Tempo: {individuo.movimentos_direita}, Fitness: {str(individuo.fitness)}")

        selecionadas = selecao(populacao,3)
        descendentes = []
        while len(descendentes) < len(populacao) - len(selecionadas):
            pai1, pai2 = random.sample(selecionadas, 2)
            filho1, filho2 = cruzamento(pai1, pai2,0.3)
            descendentes.extend([filho1, filho2])

        for filho in descendentes:
            filho = mutacao(filho)

        populacao = selecionadas + descendentes

        fitness_atual = max(individuo.fitness for individuo in populacao)
        individuo_atual = max(populacao, key=lambda n: n.fitness)
        if fitness_atual > melhor_fitness:
            melhor_fitness = fitness_atual
            melhor_individuo = individuo_atual

        print(f"Geração {geracao}: Melhor Fitness {melhor_fitness}")
        save_log(f"geracao-{timestamp_atual}",f"Geração {geracao}: Melhor Fitness {melhor_fitness}")
        #print(f"Melhores Ações: {imprimir_acoes_individuo(melhor_individuo)}")

    return melhor_individuo

def rodar_melhor_modelo(ambiente, melhor_individuo):
    while True:
        estado = ambiente.reset()
        for acao in melhor_individuo.acoes:
            estado, fitness, tempo_restante, progresso_nivel = ambiente.passo(acao)

        print("Loop completado, reiniciando...")

ambiente = Ambiente(modo_silencioso=False)
populacao = iniciar_individuos(10)
def criar_diretorios(caminho):
    os.makedirs(caminho, exist_ok=True)
    print(f"Pasta '{caminho}' criada com sucesso!")

timestamp_atual = time.time()
criar_diretorios('logs')
criar_diretorios(f"logs/{timestamp_atual}-execucao")
algoritmo_genetico(populacao, ambiente)

# TODO: O que fazer com tamanho dos indivíduos? Podem aumentar ao longo do tempo?