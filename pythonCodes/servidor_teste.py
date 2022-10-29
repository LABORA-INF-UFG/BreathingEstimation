import socket
from time import sleep

file = "F:\Dados CSI\Apneia1_0-Alex-Intel 5300-Rapida-Sentado_frente-FFZ-_1m-Intel 5300-22_09_2022-18_37-99_93Hz-32R-87bpm.txt"

ip = "127.0.0.1"
port = 999

# criando o servidor udp
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print("Conectado ao UDP")

# enviando os pacotes
with open(file, "r") as f:
    data = f.readlines()

idx = 0
tam = len(data)

while True:
    if idx >= tam:
        idx = 0
    pkt = bytes(data[idx], "utf-8")
    print(len(pkt))
    udp.sendto(pkt, (ip, port))
    print(f"Pacote {idx} enviado")
    idx += 1
    sleep(0.01)
