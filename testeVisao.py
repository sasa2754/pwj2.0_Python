from flask import Flask, Response
import cv2
import numpy as np
import socket
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebaseConfig.json")
firebase_admin.initialize_app(cred)


app = Flask(__name__) # Cria uma aplicação chamada app que vai definir as rotas e iniciar o servidor web

ESP32_IP = 'Endereço_ip_da_esp32' # Endereço IP da esp32
ESP32_PORT = 80 # Mesma porta configurada na ESP32

# Inicializa a webcam
cap = cv2.VideoCapture(0)

db = firestore.client()

def get_data_from_firebase(collection_name):
    collection_ref = db.collection(collection_name)
    docs = collection_ref.stream()

    for doc in docs:
        print(f'Documento ID: {doc.id}\n')
        print(f'Dados: {doc.to_dict()}\n')
        print("-" * 40)

# Função para enviar o erro para a ESP32
def send_error(error):
    try:
        # Cria um socket TPC (socket é um ponto de comunicação entre dois dispositivos de uma rede, ele permite a troca de dados entre dispositivos usando protocolos de rede, como o TCP, que é um protocolo que garante que os dados sejam entregues na ordem correta e sem falhas)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ESP32_IP, ESP32_PORT))
            s.sendall(f'{error}\n'.encode()) # O erro é enviado como uma string, para facilitar a leitura na ESP32, pois podemos ler cada linha de dados com o parâmetro final do \n e só converter depois com um .toInt
    except Exception as e:
        print(f'Erro ao enviar dados para a ESP32: {e}')



# Função pare detectar uma linha amarela
def detec_line_yellow(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # Converte o frame para HSV (tonalidade, saturação, valor) para melhor detecção das cores
    
    # Define o intervalo de cor da linha que queremos detectar
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([30, 255, 255])

    # Cria uma máscara para isolar a linha amarela (Pega qualquer coisa que estiver entre esse intervalo de cores)
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # Encontra o contorno da linha
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Se encontrar contornos, pega o maior entre eles, para evitar que pegue algo de errado
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest_contour)

        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"]) # Coordenada X do centro do contorno
            cy = int(M["m01"] / M["m00"]) # Coordenada Y do centro do contorno

            # Desenha o conrorno e o centro da imagem
            cv2.drawContours(frame, [largest_contour], -1, (0, 255, 0), 3)
            cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)

            # Calcula a posição relativa do centro do contorno em relação ao centro da imagem
            frame_center_x = frame.shape[1] // 2
            error = cx - frame_center_x # Erro de posição (quanto mais longe do centro, maior o erro)
            return frame, error
        
        return frame, None # Retorna None se não encontrar a linha
    
# Função pare detectar uma linha amarela
def detec_line_blue(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # Converte o frame para HSV (tonalidade, saturação, valor) para melhor detecção das cores
    
    # Define o intervalo de cor da linha que queremos detectar
    lower_blue = np.array([20, 100, 100])
    upper_blue = np.array([30, 255, 255])

    # Cria uma máscara para isolar a linha amarela (Pega qualquer coisa que estiver entre esse intervalo de cores)
    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # Encontra o contorno da linha
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Se encontrar contornos, pega o maior entre eles, para evitar que pegue algo de errado
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest_contour)

        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"]) # Coordenada X do centro do contorno
            cy = int(M["m01"] / M["m00"]) # Coordenada Y do centro do contorno

            # Desenha o conrorno e o centro da imagem
            cv2.drawContours(frame, [largest_contour], -1, (0, 255, 0), 3)
            cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)

            # Calcula a posição relativa do centro do contorno em relação ao centro da imagem
            frame_center_x = frame.shape[1] // 2
            error = cx - frame_center_x # Erro de posição (quanto mais longe do centro, maior o erro)
            return frame, error
        
        return frame, None # Retorna None se não encontrar a linha



def generate_frames():
    while True:
        # Lê um frame da câmera, sucess é um retorno boolean para ver se deu certo a captura, e frame é o a captura em si
        success, frame = cap.read()
        if not success:
            break
        else:
            # Processa a imagem para detectar a linha

            result = detec_line_yellow(frame)

            if result is not None:
                frame, error = result

                # Exibe o erro na imagem (Não é necessário, vou usar só para depurar o código)
                if error is not None:
                    cv2.putText(frame, f"Error: {error}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    # send_error(error) # Esse é necessário para enviar o erro para a ESP32 (o erro fica negativo se a linha estiver a esquerda do centro e positivo se estiver a direita do centro, precisa sempre tentar deixar ele em 0)

            # Converte o frame em jpeg pra diminuir o tamanho e facilitar a transmissão, ele retorna ret (status da codificação) e o buffer que pe a imagem codificada
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes() # Converte o buffer da imagem em bytes

            # Cada frame é enviado como uma resposta HTTP no formato multipart/x-mixed-replace, esse forma atualiza as imagens na mesma conexão HTTP, para que pareça um vídeo perfeito
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed') # Define a rota que o vídeo vai ser exibido
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame') # Configura a resposta HTTP para atualizar continuamente a imagem

data = get_data_from_firebase("deliveries", )
# Inicia o servidor Flask, acessível na rede no endereço 0.0.0.0 e na porta 5000, isso permite que seja acessado no navegador pela URL http://<IP>:5000/video_feed
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
