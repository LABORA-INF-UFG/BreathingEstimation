from funcoes import BreathEstimation, Apneia
import ast
import time


file = r"F:\Projetos\Dados CSI\Apneia1_0-Alex-Intel 5300-Rapida-Sentado_frente-FFZ-_1m-Intel 5300-22_09_2022-18_37-99_93Hz-32R-87bpm.txt"
txt = "1_1"
with open(file, "r") as f:
    dat = f.readlines()

dat = [ast.literal_eval(i) for i in dat]
tam = len(dat)


def main():
    # instanciando o objeto de processamento
    estimador = BreathEstimation()
    apneia = Apneia(qtd_de_estimativas=20)
    pkts_recv = 0
    # recebendo os pacotes
    while True:
        start = time.time()
        #####################################
        if pkts_recv >= tam:                #
            #estimador.salva_potenciasPCA(txt)
            break                           #
        #####################################
        estimador.recebe_pacote_csi(dat[pkts_recv])
        pkts_recv += 1

        if pkts_recv >= estimador.fs * 20 and pkts_recv % estimador.fs == 0:
            # calculando a diferença de fase
            phase_diff = estimador.diferenca_de_fase(estimador.get_csi())

            # filtrando com hampel
            estimador.hampel_jit(phase_diff, 10)

            # filtrando outliers pela tendência geral das subportadoras
            CSI_clean = estimador.outlier_channel_removal(phase_diff)
            del phase_diff

            # aplicando passa baixas
            CSI_filtered = estimador.passa_baixas(CSI_clean)
            del CSI_clean

            # aplicando PCA
            CSI_pca = estimador.pca(CSI_filtered)
            del CSI_filtered

            # buscando os picos da fft
            freq_resp_hz = estimador.busca_picos_fft(CSI_pca)
            del CSI_pca

            print("\033[1;31;40mRespiração estimada:\033[0m", float(freq_resp_hz) * 90)
            apneia.registra_estimativa(float(freq_resp_hz) * 90)
            ocorrencia = apneia.apneia()
            print(f"Tempo de execução {pkts_recv}:", time.time() - start)
        time.sleep(0.01)


if __name__ == "__main__":
    main()
