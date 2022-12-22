import cv2
import numpy as np


EXIBITION_TYPE = "adaptive"


class Plotter:
    def __init__(self, tam_janela: int, qtd_subports: int):
        self.tam_janela = tam_janela
        self.nsub = qtd_subports
        self.buffer_img = np.zeros((570, tam_janela, 3))

    def put_text(self, img):
        img = cv2.rectangle(img, (0,0), (25, 57*10), (0,0,0), -1)
        for i in range(self.nsub):
            img = cv2.putText(img, text=str(i), org=(5, 10*(i+1)), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                              fontScale=0.4, color=(255,255,255), thickness=1, bottomLeftOrigin=False)
        return img

    def expand_image(self, image):
        new_img = np.zeros((self.nsub * 10, self.tam_janela), np.uint8)
        chunks = self.nsub  # quantidade de subportadoras
        for i in range(chunks):  # expandindo o tamanho de cada subportadora -> cada uma 15 pixels de altura
            new_img[i*10:(i+1)*10, :] = image[i, :]
        return new_img

    def vec2image(self, vector, type:str = "mean"):
        """
        Transforma um vetor de valores arbitrário em uma imagem contida no intervalo [0, 255].
        É uma operação de MinMax scaler no fim das contas.
        :param vector: np.ndarray
        :param type: str in ["mean", "abs", "iqr", "adaptive"]
        :return: np.ndarray
        """
        #print(f"Minimo vetor {np.min(vector)}, Maximo vetor: {np.max(vector)}")

        if type == "mean":
            min = -38
            max = 38
        elif type == "abs":
            min = -70
            max = 68
        elif type == "iqr":
            min = -35
            max = 35
        elif type == "adaptive":
            Q1, Q3 = np.quantile(vector, [0.25, 0.75])
            IQR = Q3 - Q1
            min = (Q1 - 1.5 * IQR)
            max = Q3 + 1.5 * IQR
        else:
            raise ValueError(f"Valor de tipo de minimo e maximo invalido: {type}")

        #################################################
        #array_min_max = [[max, min]] * vector.shape[0]  # esse vetor força os limites min e max aparecer no vetor de valores
        #vector = np.concatenate((vector, array_min_max), axis=1)  # lembrando que devem ser removidas as 2 ultimas colunas na hora de plotar
        ###########################################################

        vector = (vector - min) / (max - min)
        vector = vector * 255
        return vector.astype(np.uint8)

    def update(self, phase_diff: np.ndarray, invariant=True):
        phase_diff = phase_diff.T[:, -1 * self.tam_janela:]
        img = self.vec2image(phase_diff, type=EXIBITION_TYPE)
        img = self.expand_image(img)  # expandindo a quantidade de pixels da imagem no axis 0
        heatmap = cv2.applyColorMap(img, cv2.COLORMAP_HSV)
        if invariant:
            self.buffer_img = np.roll(self.buffer_img, (0, -20, 0), axis=(0, 1, 2))
            self.buffer_img[:, -20:, :] = heatmap[:, -22:, :]
            heatmap = self.put_text(self.buffer_img)

        else:
            heatmap = self.put_text(heatmap[:, :, :])

        cv2.imshow('heatmap', heatmap)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            exit()
