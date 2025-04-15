import cv2
import subprocess
import numpy as np
import requests
import time
import threading
from tkinter import *
from PIL import Image, ImageTk

# Configuración de la API
API_URL = "https://api-lectores-cci.onrender.com/validar_placa/"
DELAY_ESCANEO = 5  # Tiempo de espera entre escaneos en segundos
DURACION_MENSAJE = 3  # Segundos que dura el mensaje antes de volver a "No detecta"

# Crear ventana principal
ventana_qr = Tk()
ventana_qr.title("Sistema gestor de escaneo CCI Ingeniería")
ventana_qr.minsize(width=480, height=600)
ventana_qr.config(padx=35, pady=35)

# Centrar ventana
def centrar_ventana(ventana, ancho, alto):
    pantalla_ancho = ventana.winfo_screenwidth()
    pantalla_alto = ventana.winfo_screenheight()
    x = (pantalla_ancho // 2) - (ancho // 2)
    y = (pantalla_alto // 2) - (alto // 2)
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

centrar_ventana(ventana_qr, 300, 500)

# Inicializar captura de video
capture = cv2.VideoCapture(0)
if not capture.isOpened():
    print("No se pudo abrir la cámara.")
else:
    print("Cámara abierta correctamente.")

ultimo_escaneo = 0  # Control de tiempo entre escaneos

def validar_placa(placa):
    """Envía la placa a la API en un hilo separado y actualiza la interfaz."""
    def proceso_validacion():
        response = requests.post(API_URL, json={"placa": placa})
        if response.status_code == 200:
            data = response.json()
            mensaje = data.get("mensaje", "Sin respuesta")
            permitido = data.get("permitido", False)
            puesto = data.get("puesto", None)

            if permitido:
                etiqueta_resultado.config(text=mensaje, fg='green')
                if puesto:
                    etiqueta_puesto.config(text=f"Puesto asignado: {puesto}", fg='blue')
                else:
                    etiqueta_puesto.config(text="")
            else:
                etiqueta_resultado.config(text=mensaje, fg='red')
                etiqueta_puesto.config(text="")

            # Volver a "No detecta" después de 3 segundos
            ventana_qr.after(DURACION_MENSAJE * 1000, limpiar_mensaje)

        else:
            etiqueta_resultado.config(text="Error al validar placa", fg='red')
            etiqueta_puesto.config(text="")
            ventana_qr.after(DURACION_MENSAJE * 1000, limpiar_mensaje)

    threading.Thread(target=proceso_validacion, daemon=True).start()

def limpiar_mensaje():
    """Restablece los mensajes después de un tiempo."""
    etiqueta_resultado.config(text="No detecta", fg='red')
    etiqueta_puesto.config(text="")

def extraer_placa(data):
    """Extrae la placa del contenido del QR."""
    lineas = data.split("\n")
    placa = None

    for linea in lineas:
        if "Placa:" in linea:
            placa = linea.split(": ")[1].strip()
            break

    return placa

def actualizar_video():
    """Captura un frame de la cámara y detecta códigos QR sin afectar la fluidez."""
    global ultimo_escaneo
    ret, frame = capture.read()
    if ret:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (400, 300))
        img = Image.fromarray(frame)
        img_tk = ImageTk.PhotoImage(image=img)
        etiqueta_video.img_tk = img_tk
        etiqueta_video.configure(image=img_tk)

        # Detección de QR en un hilo separado para evitar bloqueos
        threading.Thread(target=detectar_qr, args=(frame,), daemon=True).start()

    ventana_qr.after(10, actualizar_video)

def detectar_qr(frame):
    """Detecta QR en un frame y procesa la información."""
    global ultimo_escaneo
    qrDetector = cv2.QRCodeDetector()
    data, bbox, _ = qrDetector.detectAndDecode(frame)

    if data and (time.time() - ultimo_escaneo > DELAY_ESCANEO):
        ultimo_escaneo = time.time()
        etiqueta_resultado.config(text=f'QR Detectado', fg='blue')

        placa = extraer_placa(data)
        if placa:
            validar_placa(placa)
        else:
            etiqueta_resultado.config(text="Placa no encontrada en QR", fg='red')
            etiqueta_puesto.config(text="")
            ventana_qr.after(DURACION_MENSAJE * 1000, limpiar_mensaje)

def volver_main():
    """Libera la cámara y cierra la ventana."""
    capture.release()
    ventana_qr.destroy()
    subprocess.Popen(["python", "main.py"])

Label(ventana_qr, text="Acerque el QR al recuadro", font=("Arial", 15)).grid(column=0, row=0, pady=10)

etiqueta_video = Label(ventana_qr)
etiqueta_video.grid(column=0, row=1)

etiqueta_resultado = Label(ventana_qr, text="No detecta", font=("Arial", 12), fg='red')
etiqueta_resultado.grid(column=0, row=2, pady=10)

etiqueta_puesto = Label(ventana_qr, text="", font=("Arial", 12), fg='blue')
etiqueta_puesto.grid(column=0, row=3, pady=5)

boton_volver = Button(ventana_qr, text="Regresar", font=("Arial", 14), command=volver_main)
boton_volver.grid(column=0, row=4, pady=10)

actualizar_video()
ventana_qr.mainloop()
