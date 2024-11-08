# import numpy as np
# import matplotlib
# import cv2 as cv
# import sys

# cap = cv.VideoCapture(0) #Cria um objeto de captura de vídeo para ler quadro a quadro

# while True:
#     # ret é um valor booleano que diz se a leitura foi bem-sucedida, frame é o quadro atual do vídeo, a função cap.read() retorna esses dois valores
#     ret, frame = cap.read()

#     if not ret:
#         # print("Falha ao capturar vídeo")
#         print("Fim do vídeo")
#         break

    

#     # Exibe o vídeo com os contornos e centro de massa desenhados em uma janela que pode ser nomeada
#     cv.imshow("Câmera", frame)

#     # Aguarda 1 milissegundo por uma tecla pressionada, se a tecla pressionada for q, o programa encerra o loop e fecha a janela
#     if cv.waitKey(1) & 0xFF == ord('q'):
#         break

# # Libera o objeto de captura do vídeo, fechando o arquivo
# cap.release()
# # Fecha todas as janelas abertas pelo openCV
# cv.destroyAllWindows()





from flask import Flask, Response
import cv2

app = Flask(__name__)

# Inicializa a webcam
cap = cv2.VideoCapture(0)  # Altere o índice se tiver múltiplas câmeras

def generate_frames():
    while True:
        # Lê um frame da câmera
        success, frame = cap.read()
        if not success:
            break
        else:
            # Codifica o frame como JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # Envia o frame como uma resposta HTTP
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
