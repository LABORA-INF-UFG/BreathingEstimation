import matplotlib.pyplot as plt
from time import time

'''
Amplitude and Phase plotter
---------------------------
Plot Amplitude and Phase of CSI frame_info
and update the plots in the same window.
Initiate Plotter with bandwidth, and
call update with CSI value.
Adicional:
'''

__all__ = [
    'Plotter'
]


class Plotter:
    def __init__(self,tam_janela: int, subport_plotar: list):

        self.start = time()
        self.nsub_desejada = len(subport_plotar)

        self.tamanho_janela = tam_janela

        self.janela_cheia = False  # nao mexer
        self.nsub = 57

        self.fig, axs = plt.subplots(2, figsize=(16, 9))

        self.ax_raw_phase = axs[0]
        self.ax_phase_proc = axs[1]

        self.fig.suptitle('Real Time phase Diff monitoring')
        self.ax_raw_phase.set_ylabel('Raw Phase Diff')
        self.ax_raw_phase.set_ylim([-2, 2])

        self.ax_phase_proc.set_ylabel('Processed Phase Diff')
        self.ax_phase_proc.set_ylim([-2, 2])

        self.bg = 0
        self.ln = [0] * self.nsub
        self.ln2 = [0] * self.nsub

        self.subport_plotar = subport_plotar

    def update(self, raw_phase, proc_phase, sequencia):
        raw_phase = raw_phase.T
        proc_phase = proc_phase.T
        if sequencia == 0:
            amplitudes = raw_phase[0, :]

            for i in range(self.nsub_desejada):
                (self.ln[i],) = self.ax_raw_phase.plot(range(self.tamanho_janela), amplitudes, animated=True, label=str(self.subport_plotar[i]))
                (self.ln2[i],) = self.ax_phase_proc.plot(range(self.tamanho_janela), amplitudes, animated=True, label=str(self.subport_plotar[i]))

            plt.show(block=False)
            plt.pause(1)
            self.bg = self.fig.canvas.copy_from_bbox(self.fig.bbox)

            for i in range(self.nsub_desejada):
                self.ax_raw_phase.draw_artist(self.ln[i])
                self.ax_phase_proc.draw_artist(self.ln2[i])

            self.ax_raw_phase.legend()
            self.fig.canvas.blit(self.fig.bbox)

        else:
            self.fig.canvas.restore_region(self.bg)

            # tenho que plotar todos os valores armazenados de cada subcarrier por vez
            for idx in range(len(self.subport_plotar)):
                raw = raw_phase[self.subport_plotar[idx], :]
                proc = proc_phase[self.subport_plotar[idx], :]
                self.ln[idx].set_ydata(raw)
                self.ln2[idx].set_ydata(proc)
                self.ax_raw_phase.draw_artist(self.ln[idx])
                self.ax_phase_proc.draw_artist(self.ln2[idx])
                self.fig.canvas.blit(self.fig.bbox)

            self.ax_raw_phase.legend()
            self.fig.canvas.flush_events()
            plt.pause(0.005)
