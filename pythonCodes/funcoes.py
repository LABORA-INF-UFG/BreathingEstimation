import numpy as np
from scipy import signal
from sklearn.decomposition import PCA
from numba import jit


@jit(nopython=True)
def _for_hampel_jit(array_copy, windowsize, n):
    k = 1.4826
    for idx in range(windowsize // 2, len(array_copy) - windowsize // 2):
        window = array_copy[idx - windowsize // 2:idx + windowsize // 2 + 1]
        median = np.median(window)  # calculate window median
        sigma = k * np.median(np.abs(window - median))  # calculate window Median Absolute Deviation (MAD)
        if np.abs(array_copy[idx] - median) > n * sigma:  # if the value at "idx" index is an outlier...
            array_copy[idx] = median  # replace it with the median of the window


class BreathEstimation:
    def __init__(self):

        # Frequência de amostragem
        self.fs = 100

        # Buffer de armazenamento
        self._buffer = np.zeros((2000, 171))  # referente a 20 segundos de dados amostrados em 100Hz
        self._buffer_preenchido = 0

        # ---- Definição de parâmetros ----
        # Número de sinais do PCA
        self.signals = 20

        # Intervalo de frequência onde buscará sinal (Hz)
        self.FminBreath = 0.2
        self.FmaxBreath = 1

        # Intervalo de frequência onde buscará sinal (Hz)
        self.FminHeart = 50/60
        self.FmaxHeart = 2

        # Séries da PCA anteriores a esta serão ignoradas:
        self.firstPCA = 1  # python começa a contar do 0

        self.potenciasPCA = []

    def salva_potenciasPCA(self, title):
        self.potenciasPCA = np.array(self.potenciasPCA).reshape(-1, self.signals - self.firstPCA)
        np.savetxt(f'{title}.txt', self.potenciasPCA, delimiter=',')

    def get_csi(self):
        return self._buffer

    def recebe_pacote_csi(self, pkt):
        # Recebe um pacote de dados CSI e armazena no buffer
        csi = pkt.get("CSI").get("Phase")
        if self._buffer_preenchido == self._buffer.shape[0]:
            self._buffer = np.roll(self._buffer, -1, axis=0)  # desloca os elementos do buffer, depende da ordem linha coluna
            self._buffer[-1, :] = csi

        else:
            self._buffer[self._buffer_preenchido, :] = csi
            self._buffer_preenchido += 1

    def diferenca_de_fase(self, csi):
        """
        Essa função tem como objetivo calcular a diferença de fase entre as subportadoras.
        Executa o cálculo de subtração entre subportadoras homólogas em antenas diferentes.
        Também executa o unwrap (desembrulhar) das fases e a centralização em zero dos valores (subtração da média).
        :param csi: numpy array de formato ou shape: (pacotes, subportadoras)
        :return: numpy array de shape: (pacotes, num_tones)
        """
        phase1 = csi[:, :57]
        phase2 = csi[:, 57:114]
        CSIiDiff = phase1 - phase2
        CSIiDiff = np.unwrap(CSIiDiff, axis=0)
        return CSIiDiff - np.mean(CSIiDiff, axis=0)

    def outlier_channel_removal(self, csi):
        """
        Essa função tem como objetivo remover outliers das subportadoras seguindo a tendência das subportadoras
        em geral, sendo que eles são substituídos pela média dos valores anteriores e posteriores (20 vizinhos).
        Diferente do filtro Hampel, em que cada subportadora é considerada individualmente, aqui os valores máximos
        e mínimos tolerados são definidos a partir da mediana dos máximos e mínimos de todas as subportadoras.
        :param csi: formato ou shape: (pacotes, subportadoras)
        :return: CSI filtrado sem outliers de formato (pacotes, subportadoras)
        """
        # embora já tenha o Hampel, esse filtro busca fazer com que todas as subportadoras tenham os valores próximos
        # já que o Hampel analisa subportadoras de forma individual, e não em conjunto.
        CSIclean = csi.copy()

        maxCSI = np.max(csi, axis=0)
        minCSI = np.min(csi, axis=0)

        # definindo limite máximo dos valores entre as subportadoras
        maxCSIthreshold = np.median(maxCSI) + 0.5 * (np.median(maxCSI) - np.median(minCSI))

        # definindo limite mínimo dos valores entre as subportadoras
        minCSIthreshold = np.median(minCSI) - 0.5 * (np.median(maxCSI) - np.median(minCSI))

        ############## possível gargalo aqui ################
        # buscando os valores que estão fora dos limites e substituindo pela média da vizinhanca
        outliers = np.where((csi > maxCSIthreshold) | (csi < minCSIthreshold))
        for idx, subport in zip(outliers[0], outliers[1]):
            if idx - 10 < 0:
                CSIclean[idx, subport] = np.mean(np.concatenate([csi[0:idx, subport], csi[idx + 1:idx + 11, subport]]))
            elif idx + 10 > csi.shape[0]:
                CSIclean[idx, subport] = np.mean(np.concatenate([csi[idx - 10:idx, subport], csi[idx + 1:, subport]]))
            else:
                CSIclean[idx, subport] = np.mean(np.concatenate([csi[idx - 10:idx, subport], csi[idx + 1:idx + 11, subport]]))

        return CSIclean

    def passa_baixas(self, csi):
        ################### não usei 3 / (100/2), pois já declaramos o fs na funcao ############
        filter = signal.butter(2, 3, 'low', fs=self.fs, output='sos')
        CSI_filtered = signal.sosfilt(filter, csi)
        return CSI_filtered

    def pca(self, csi):
        """
        Essa função tem como objetivo realizar a redução de dimensionalidade dos dados de entrada, utilizando a
        ferramenta PCA (Principal Component Analysis) do scikit-learn.
        :param csi: numpy array de formato ou shape: (pacotes, subportadoras)
        :return: CSI limpo com formato (pacotes, signals)
        """
        pca = PCA(n_components=self.signals)
        CSImPCA = pca.fit_transform(csi)
        return CSImPCA

    def busca_picos_fft(self, csi_pca):
        """
        Essa função tem como objetivo buscar os picos de frequência de interesse, que é diretamente a frequência
        de respiração da pessoa, em Hz.

        :param csi_pca: numpy array de forma (pacotes, signals)
        :return: frequencia de respiração em Hz (float)
        """
        dt = 1 / self.fs  # período, inverso da frequencia
        T = csi_pca.shape[0] * dt  # tempo total de captura
        df = 1 / T
        fNQ = (1 / dt) / 2
        fftFreq = np.arange(0, fNQ, df)
        intervaloMin = np.where(fftFreq >= self.FminBreath)[0][0]
        intervaloMax = np.where(fftFreq <= self.FmaxBreath)[0][-1]

        maxFFT = -1000
        maxIndex = 0

        for componente_pca in range(self.firstPCA, self.signals):
            fftPCA = np.fft.fft(csi_pca[:, componente_pca])
            fftPCA = np.abs(fftPCA[intervaloMin:intervaloMax + 1])
            max_tmp = fftPCA.max()
            self.potenciasPCA.append(max_tmp)
            max_idx_tmp = np.where(fftPCA == max_tmp)

            if max_tmp > maxFFT:
                maxFFT = max_tmp
                maxIndex = max_idx_tmp + intervaloMin

        # estimando taxa respiratória:
        freq_resp = fftFreq[maxIndex]
        print(fftFreq[intervaloMin:intervaloMax])
        return freq_resp

    def hampel_jit(self, array, windowsize, n=3):
        array_copy = np.zeros((array.shape[0] + ((windowsize // 2) * 2), array.shape[1]))
        if array_copy.ndim > 1:
            for subport in range(array_copy.shape[1]):
                array_copy[:, subport] = np.pad(array[:, subport], windowsize // 2, mode='edge')
                _for_hampel_jit(array_copy[:, subport], windowsize, n)

        else:
            array_copy = np.pad(array_copy, windowsize // 2, mode='edge')
            _for_hampel_jit(array_copy, windowsize, n)
        return array_copy[windowsize // 2:-windowsize // 2]


class Apneia:
    def __init__(self, qtd_de_estimativas: int = 20):
        self.buffer = []  # acumulador (estático, ou seja, apenas das N primeiras estimativas, não muda)
        self.len_buffer = 0
        self.estimativas_atuais = np.zeros(5)
        self.medianaEstimativas = -1
        self.qtd_de_estimativas = qtd_de_estimativas

    def registra_estimativa(self, estimativa: float):
        """
        Essa função registra a estimativa de frequência de respiração e registra em um buffer até enchê-lo.
        Caso o buffer esteja cheio, a estimativa é armazenada em um vetor que guarda sempre as 5 estimativas mais recentes.
        :param estimativa: float com a estimativa de frequência de respiração
        :return: None
        """
        if self.len_buffer < self.qtd_de_estimativas:
            self.buffer.append(estimativa)
            self.len_buffer = len(self.buffer)
            if self.qtd_de_estimativas - len(self.buffer) <= 5:
                self.estimativas_atuais = np.roll(self.estimativas_atuais, -1)
                self.estimativas_atuais[-1] = estimativa

        else:
            self.estimativas_atuais = np.roll(self.estimativas_atuais, -1)
            self.estimativas_atuais[-1] = estimativa

    def apneia(self):
        """
        Essa função calcula se há indício de uma apneia ou não. Para isso, ela usa o buffer de estimativas armazenadas
        e calcula a mediana delas. Caso mais de três estimativas recentes estejam diferentes da mediana, é acusado como
        possível apneia.
        :return: boolean indicando a presença ou não de apneia
        """
        if len(self.buffer) < self.qtd_de_estimativas:  # se o buffer ainda não está com a qtd necessária de estimativas
            print('Aguardando mais dados...')
            return False
        else:
            self.medianaEstimativas = np.median(self.buffer)  # calcula a mediana das estimativas do buffer
            resultado = np.logical_or(self.estimativas_atuais > self.medianaEstimativas + 0.1,
                                      self.estimativas_atuais < self.medianaEstimativas - 0.1)
            print(self.estimativas_atuais, self.medianaEstimativas)
            resultado = np.where(resultado == True)[0]
            if len(resultado) > 3:
                print('\033[1;31;40mApneia detectada!\033[0m')
                return True
            else:
                return False
