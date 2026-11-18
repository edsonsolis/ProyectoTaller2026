import os
import heapq
import threading
import unicodedata
import cv2
import numpy as np
from collections import deque
from xml.etree import ElementTree as ET
from datetime import datetime
from FiltroDeOferta.Oferta import Oferta

XML_PATH = os.path.join(os.path.dirname(__file__), '../servicios.xml')
COLA_MENSAJES_CHAT = deque(maxlen=50)

def quitar_tildes(texto: str) -> str:
    """Normaliza caracteres eliminando tildes para el procesamiento NLP (Punto 3)."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def analizar_texto_nlp(texto: str) -> dict:
    """Procesamiento de Lenguaje Natural: Tokenización y limpieza de texto (Punto 3)."""
    limpio = quitar_tildes(texto.lower())
    for c in [".", ",", ";", "!", "?", "-", "\n"]:
        limpio = limpio.replace(c, " ")
    tokens = limpio.split()
    return {'tokens': tokens, 'cantidad': len(tokens)}

class BaseDatosXML:
    """Patrón Singleton para gestionar XML y Cola de Prioridad (Puntos 1, 4 y 5)."""
    _instancia = None

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super(BaseDatosXML, cls).__new__(cls)
        return cls._instancia

    def cargar_ofertas_priorizadas(self) -> list:
        if not os.path.exists(XML_PATH):
            return []

        tree = ET.parse(XML_PATH)
        root = tree.getroot()
        cola_prioridad = []

        for idx, item in enumerate(root.findall('oferta')):
            fecha_str = item.find('fecha_expiracion').text if item.find('fecha_expiracion') is not None else ""
            fecha_exp = datetime.strptime(fecha_str, "%Y-%m-%d") if fecha_str else None
            
            oferta = Oferta(
                titulo=item.find('titulo').text,
                categoria=item.find('categoria').text,
                precio_original=float(item.find('precio_original').text),
                precio_descuento=float(item.find('precio_descuento').text),
                modalidad=item.find('modalidad').text,
                ubicacion=item.find('ubicacion').text,
                entidad=item.find('entidad').text,
                fecha_expiracion=fecha_exp,
                popularidad=float(item.find('popularidad').text)
            )
            # Añadimos atributos extra dinámicamente para la descripción y seguridad
            oferta.descripcion = item.find('descripcion').text if item.find('descripcion') is not None else "Sin descripción detallada."
            oferta.pin = item.find('pin').text if item.find('pin') is not None else "0000"
            
            # Usamos idx como desempate en heapq si dos ofertas tienen la misma popularidad
            heapq.heappush(cola_prioridad, (-oferta.popularidad, idx, oferta))

        ofertas_ordenadas = []
        while cola_prioridad:
            _, _, oferta = heapq.heappop(cola_prioridad)
            ofertas_ordenadas.append(oferta)
            
        return ofertas_ordenadas

    def guardar_oferta(self, oferta: Oferta, descripcion: str, pin: str):
        tree = ET.parse(XML_PATH)
        root = tree.getroot()

        nueva = ET.SubElement(root, 'oferta')
        ET.SubElement(nueva, 'titulo').text = oferta.titulo
        ET.SubElement(nueva, 'categoria').text = oferta.categoria
        ET.SubElement(nueva, 'descripcion').text = descripcion
        ET.SubElement(nueva, 'pin').text = pin
        ET.SubElement(nueva, 'precio_original').text = str(oferta.precio_original)
        ET.SubElement(nueva, 'precio_descuento').text = str(oferta.precio_descuento)
        ET.SubElement(nueva, 'modalidad').text = oferta.modalidad
        ET.SubElement(nueva, 'ubicacion').text = oferta.ubicacion
        ET.SubElement(nueva, 'entidad').text = oferta.entidad
        ET.SubElement(nueva, 'fecha_expiracion').text = ""
        ET.SubElement(nueva, 'popularidad').text = str(oferta.popularidad)

        tree.write(XML_PATH, encoding='utf-8', xml_declaration=True)

    def eliminar_oferta_segura(self, titulo_a_borrar: str, pin_ingresado: str) -> bool:
        """Solo elimina si el título y el PIN secreto coinciden."""
        if not os.path.exists(XML_PATH):
            return False

        tree = ET.parse(XML_PATH)
        root = tree.getroot()
        eliminado = False

        for item in root.findall('oferta'):
            titulo = item.find('titulo').text
            pin_guardado = item.find('pin').text if item.find('pin') is not None else "0000"
            if titulo == titulo_a_borrar and pin_guardado == pin_ingresado:
                root.remove(item)
                eliminado = True
                break

        if eliminado:
            tree.write(XML_PATH, encoding='utf-8', xml_declaration=True)
        return eliminado

    def calificar_oferta(self, titulo_oferta: str, estrellas: float):
        """Actualiza el promedio de popularidad en el XML."""
        if not os.path.exists(XML_PATH):
            return

        tree = ET.parse(XML_PATH)
        root = tree.getroot()

        for item in root.findall('oferta'):
            if item.find('titulo').text == titulo_oferta:
                pop_actual = float(item.find('popularidad').text)
                # Calculamos nuevo promedio redondeado a 1 decimal
                nuevo_promedio = round((pop_actual + estrellas) / 2, 1)
                item.find('popularidad').text = str(nuevo_promedio)
                break

        tree.write(XML_PATH, encoding='utf-8', xml_declaration=True)

# --- HILOS Y OPENCV (Puntos 2 y 6) ---
def procesar_imagen_accesibilidad(ruta_imagen: str):
    print(f"🧵 [HILO PARALELO {threading.current_thread().name}]: Procesando contraste con OpenCV...")
    if not os.path.exists(ruta_imagen):
        return
    img = cv2.imread(ruta_imagen)
    if img is None:
        return
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    img_accesible = cv2.cvtColor(cv2.merge((clahe.apply(l), a, b)), cv2.COLOR_LAB2BGR)
    cv2.imwrite(ruta_imagen, img_accesible)

def guardar_imagen_en_hilo(ruta_destino: str):
    threading.Thread(target=procesar_imagen_accesibilidad, args=(ruta_destino,)).start()

# --- BUS DE EVENTOS (Patrón Observer) ---
class GestorEventos:
    _suscriptores = {}

    @classmethod
    def suscribir(cls, tipo_evento: str, funcion_callback):
        cls._suscriptores.setdefault(tipo_evento, []).append(funcion_callback)

    @classmethod
    def disparar(cls, tipo_evento: str, datos):
        print(f"🔔 [EVENTO]: '{tipo_evento}'")
        for funcion in cls._suscriptores.get(tipo_evento, []):
            funcion(datos)

GestorEventos.suscribir('oferta_creada', lambda o: print(f"📝 [AUDITORÍA]: Publicado '{o.titulo}' por {o.entidad}"))
GestorEventos.suscribir('oferta_creada', lambda o: guardar_imagen_en_hilo(os.path.join(os.path.dirname(__file__), '../foto_estudiante.jpg')))


