from funcoes import BreathEstimation, Apneia
from new_plotter import Plotter
import socket
import time
import threading
from picoscenes import Picoscenes



def plot(estimador, plotter, qtd_pkts_to_plot):
    while True:
        # plottando os pacotes a cada 20 pacotes recebidos (20 ms)
        if estimador.pkt_count % 20 == 0 and estimador.buffer_preenchido:
            # calculando a diferença de fase somente da quantidade certa de pacotes a serem visualizados.
            phase_diff = estimador.diferenca_de_fase(estimador.get_csi()[:, -1*qtd_pkts_to_plot:])
            plotter.update(phase_diff, invariant=False)


def recebe_pacote(estimador, udp):
    while True:
        pkt, _ = udp.recvfrom(8192)
        frames = Picoscenes(pkt)
        pkt = frames.raw[0]
        estimador.recebe_pacote_csi(pkt)


def processamento(estimador, apneia, pkts_recv):
    start = time.time()
    # calculando a diferença de fase
    phase_diff = estimador.diferenca_de_fase(estimador.get_csi())

    # filtrando com hampel
    estimador.hampel_jit(phase_diff, 10)

    # filtrando outliers pela tendência geral das subportadoras
    CSI_clean = estimador.outlier_channel_removal(phase_diff)
    del phase_diff

    # aplicando passa baixas (removendo altas frequências)
    CSI_filtered = estimador.passa_baixas(CSI_clean)
    del CSI_clean

    # aplicando PCA  (parte mais demorada!)
    CSI_pca = estimador.pca(CSI_filtered)

    # buscando os picos da fft
    freq_resp_hz = estimador.busca_picos_fft(CSI_pca)
    del CSI_pca

    apneia.registra_estimativa(float(freq_resp_hz) * estimador.segundos_buffer)
    ocorrencia = apneia.apneia()

    print(f"\n\033[92mRespiração estimada: {float(freq_resp_hz) * estimador.segundos_buffer}\033[0m")
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

    # instanciando objeto plotter
    qtd_pkts_to_plot = 1000
    plotter = Plotter(tam_janela=qtd_pkts_to_plot, qtd_subports=57)

    # abrindo uma thread para receber os pacotes, pois assim não teremos atrasos na hora de processar.
    # ficar alerta com o buffer!
    thread_recv = threading.Thread(target=recebe_pacote, args=(estimador, udp,))
    thread_recv.start()

    # abrindo uma thread para plottar os pacotes, pois assim não teremos atrasos na hora de processar.
    thread_plot = threading.Thread(target=plot, args=(estimador, plotter, qtd_pkts_to_plot))
    thread_plot.start()

    while True:
        # realizando o processamento sobre os pacotes a cada 100 pacotes recebidos (1s)
        if estimador.pkt_count >= estimador.fs * estimador.segundos_buffer and estimador.pkt_count % estimador.fs == 0:
            processamento(estimador, apneia, estimador.pkt_count)


if __name__ == "__main__":
    main()
