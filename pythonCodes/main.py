from funcoes import BreathEstimation, Apneia
from plotter import Plotter
import socket
import time
import threading
from picoscenes import Picoscenes
import numpy as np


def plot(estimador, plotter):
    # calculando a diferença de fase
    phase_diff = estimador.diferenca_de_fase(estimador.get_csi())

    # filtrando com hampel
    #estimador.hampel_jit(phase_diff, 10)

    # filtrando outliers pela tendência geral das subportadoras
    CSI_clean = estimador.outlier_channel_removal(phase_diff)
    #del phase_diff

    # aplicando passa baixas
    CSI_filtered = estimador.passa_baixas(CSI_clean)
    del CSI_clean

    plotter.update(phase_diff, CSI_filtered, sequencia=1)


def processamento(estimador, apneia, pkts_recv):

    start = time.time()
    # calculando a diferença de fase
    #start_pd = time.time()
    phase_diff = estimador.diferenca_de_fase(estimador.get_csi())
    #print(f"T phasediff: {time.time() - start_pd:.4f}")

    # filtrando com hampel
    #start_fmp = time.time()
    estimador.hampel_jit(phase_diff, 10)
    #print(f"T hampel: {time.time() - start_fmp:.4f}")

    # filtrando outliers pela tendência geral das subportadoras
    #start_out = time.time()
    CSI_clean = estimador.outlier_channel_removal(phase_diff)
    #print(f"T out: {time.time() - start_out:.4f}")
    del phase_diff

    # aplicando passa baixas
    #start_pb = time.time()
    CSI_filtered = estimador.passa_baixas(CSI_clean)
    #print(f"T passa baixas: {time.time() - start_pb:.4f}")
    del CSI_clean

    # aplicando PCA
    #start_pca = time.time()
    CSI_pca = estimador.pca(CSI_filtered)
    #del CSI_filtered
    #print(f"T pca: {time.time() - start_pca:.4f}")

    # buscando os picos da fft
    #start_fft = time.time()
    freq_resp_hz = estimador.busca_picos_fft(CSI_pca)
    del CSI_pca
    #print(f"T fft: {time.time() - start_fft:.4f}")

    #start_ap = time.time()
    apneia.registra_estimativa(float(freq_resp_hz) * 20)  ### mudar isso
    ocorrencia = apneia.apneia()
    #print(f"T apneia: {time.time() - start_ap:.4f}")

    print(f"\n\033[92mRespiração estimada: {float(freq_resp_hz) * 20}\033[0m")
    print(f"Tempo de execução {pkts_recv}: {time.time() - start:.4f}")
    print(f"Apneia: {ocorrencia}")



def main():
    ip = "127.0.0.1"
    port = 1025
    # conectando ao udp
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind((ip, port))
    print("Conectado ao UDP")

    # instanciando o objeto de processamento
    estimador = BreathEstimation()
    apneia = Apneia(qtd_de_estimativas=20)
    pkts_recv = 0

    # instanciando objeto plotter
    plotter = Plotter(tam_janela=2000, subport_plotar=[2, 10, 20, 25, 30, 40, 45, 55])
    plotter.update(np.zeros((2000, 57)), np.zeros((2000, 57)), pkts_recv)

    # recebendo os pacotes
    while True:
        pkt, _ = udp.recvfrom(8192)
        frames = Picoscenes(pkt)
        pkt = frames.raw[0]
        estimador.recebe_pacote_csi(pkt)
        pkts_recv += 1

        if pkts_recv % 40 == 0:
            start = time.time()
            plot(estimador, plotter)
            print(f"tempo plot: {time.time() - start}s")

        #if pkts_recv >= estimador.fs * 20 and pkts_recv % estimador.fs == 0:
            # abrindo uma thread para não atrasar a captura de pacotes
            #processamento(estimador, apneia, pkts_recv)


if __name__ == "__main__":
    main()
