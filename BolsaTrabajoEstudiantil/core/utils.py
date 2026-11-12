import os
import heapq
from xml.etree import ElementTree as ET
from datetime import datetime
from FiltroDeOferta.Oferta import Oferta
import threading
import cv2
import numpy as np
import unicodedata
from collections import deque

# Ruta absoluta al archivo XML
XML_PATH = os.path.join(os.path.dirname(__file__), '../servicios.xml')

class BaseDatosXML:
    """Patrón Singleton para gestionar el archivo XML y las estructuras dinámicas."""
    _instancia = None

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super(BaseDatosXML, cls).__new__(cls)
        return cls._instancia

    def cargar_ofertas_priorizadas(self) -> list:
        """Lee el XML y organiza las ofertas en una Cola de Prioridad (Punto 1)."""
        if not os.path.exists(XML_PATH):
            return []

        tree = ET.parse(XML_PATH)
        root = tree.getroot()
        
        # Cola de prioridad en Python 
        # Como queremos prioridad de MAYOR popularidad a menor, guardamos la popularidad en negativo
        cola_prioridad = []
        contador = 0  # <-- 1. AGREGAMOS UN CONTADOR DE DESEMPATE AQUÍ

        for item in root.findall('oferta'):
            fecha_str = item.find('fecha_expiracion').text
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
            
            # < 2. MODIFICAMOS EL HEAPPUSH: Ponemos el contador en medio de la tupla
            heapq.heappush(cola_prioridad, (-oferta.popularidad, contador, oferta))
            contador += 1  # Incrementamos para la siguiente oferta

        # Extraemos los elementos de la cola en orden estricto de prioridad
        ofertas_ordenadas = []
        while cola_prioridad:
            # <-- 3. RECIBIMOS LAS 3 VARIABLES: prioridad, index, oferta
            prioridad, index, oferta = heapq.heappop(cola_prioridad)
            ofertas_ordenadas.append(oferta)
            
        return ofertas_ordenadas

    def guardar_oferta(self, oferta: Oferta):
        """Añade una nueva oferta al documento XML (Punto 4)."""
        tree = ET.parse(XML_PATH)
        root = tree.getroot()

        nueva_oferta = ET.SubElement(root, 'oferta')
        ET.SubElement(nueva_oferta, 'titulo').text = oferta.titulo
        ET.SubElement(nueva_oferta, 'categoria').text = oferta.categoria
        ET.SubElement(nueva_oferta, 'precio_original').text = str(oferta.precio_original)
        ET.SubElement(nueva_oferta, 'precio_descuento').text = str(oferta.precio_descuento)
        ET.SubElement(nueva_oferta, 'modalidad').text = oferta.modalidad
        ET.SubElement(nueva_oferta, 'ubicacion').text = oferta.ubicacion
        ET.SubElement(nueva_oferta, 'entidad').text = oferta.entidad
        
        fecha_str = oferta.fecha_expiracion.strftime("%Y-%m-%d") if oferta.fecha_expiracion else ""
        ET.SubElement(nueva_oferta, 'fecha_expiracion').text = fecha_str
        ET.SubElement(nueva_oferta, 'popularidad').text = str(oferta.popularidad)
        ET.indent(tree, space="    ")
        tree.write(XML_PATH, encoding='utf-8', xml_declaration=True)


def procesar_imagen_accesibilidad(ruta_imagen: str):
    """Función que ejecuta filtros OpenCV en un hilo secundario (Punto 2 y 6)."""
    # Simulamos un retraso o carga pesada para demostrar el paralelismo
    import time
    time.sleep(2) 
    
    # Verificamos si la imagen existe
    if not os.path.exists(ruta_imagen):
        return

    # 1. Leer la imagen usando OpenCV
    img = cv2.imread(ruta_imagen)
    if img is None:
        return

    # 2. Aplicar filtro de accesibilidad (Mejora de Contraste para baja visión)
    # Convertimos a formato LAB para ecualizar el brillo sin dañar los colores originales
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Ecualizamos el canal de luminosidad (L) para maximizar el contraste
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l_channel)
    
    # Fusionamos los canales de vuelta y guardamos
    limg = cv2.merge((cl, a_channel, b_channel))
    img_accesible = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    
    # Sobreescribimos la imagen con la versión de alto contraste optimizada
    cv2.imwrite(ruta_imagen, img_accesible)

def guardar_imagen_en_hilo(ruta_destino: str):
    """Inicializa y arranca el hilo paralelo para no bloquear el servidor."""
    hilo = threading.Thread(target=procesar_imagen_accesibilidad, args=(ruta_destino,))
    hilo.start()

COLA_MENSAJES_CHAT = deque(maxlen=50)

def quitar_tildes(texto: str) -> str:
    """Normaliza caracteres eliminando tildes para mejorar la precisión del NLP."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def categorizar_por_nlp(descripcion_texto: str) -> str:
    """Clasificador NLP básico por Bolsa de Palabras para categorizar servicios (Punto 3)."""
    # 1. Normalización del texto (Pasar a minúsculas y limpiar caracteres)
    texto_limpio = descripcion_texto.lower()
    for caracter in [".", ",", ";", "!", "?", "-", "\n"]:
        texto_limpio = texto_limpio.replace(caracter, " ")
        
    # 2. Diccionario de palabras clave (Léxico por categoría)
    diccionario_categorias = {
        'sistemas': ['programacion', 'python', 'codigo', 'web', 'software', 'computadora', 'redes', 'java', 'html', 'desarrollo'],
        'medicina': ['inyectables', 'enfermeria', 'presion', 'salud', 'medico', 'clinica', 'paciente', 'signos', 'curacion'],
        'mecanica': ['motores', 'frenos', 'auto', 'mantenimiento', 'taller', 'vehiculo', 'reparacion', 'aceite', 'mecanico'],
        'derecho': ['legal', 'abogado', 'contrato', 'asesoria', 'demanda', 'ley', 'defensa', 'tramites', 'juridico'],
        'quimica': [],
        'agronomia': ['cultivo', 'tierra', 'plagas', 'riego', 'cosecha', 'suelo', 'plantas', 'ganado', 'fertilizante'],
        'humanidades': ['redaccion', 'traduccion', 'historia', 'psicologia', 'ensayo', 'idiomas', 'ingles', 'literatura'],
        'electronica': [],
        'arquitectura':[]
    }
    
    # 3. Tokenización (Dividir el texto en palabras individuales)
    palabras = texto_limpio.split()
    
    # 4. Conteo de coincidencias
    conteo_coincidencias = {cat: 0 for cat in diccionario_categorias}
    
    for palabra in palabras:
        for categoria, palabras_clave in diccionario_categorias.items():
            if palabra in palabras_clave:
                conteo_coincidencias[categoria] += 1
                
    # 5. Obtener la categoría con mayor puntuación
    categoria_ganadora = max(conteo_coincidencias, key=conteo_coincidencias.get)
    
    # Si ninguna palabra coincidió, le asignamos una categoría por defecto
    if conteo_coincidencias[categoria_ganadora] == 0:
        return 'general'
        
    return categoria_ganadora
class GestorEventos:
    """Implementación del Patrón Observer / Bus de Eventos (Requisito: Eventos)."""
    _suscriptores = {}

    @classmethod
    def suscribir(cls, tipo_evento: str, funcion_callback):
        if tipo_evento not in cls._suscriptores:
            cls._suscriptores[tipo_evento] = []
        cls._suscriptores[tipo_evento].append(funcion_callback)

    @classmethod
    def disparar(cls, tipo_evento: str, datos):
        print(f"🔔 [EVENTO DISPARADO]: '{tipo_evento}'")
        if tipo_evento in cls._suscriptores:
            for funcion in cls._suscriptores[tipo_evento]:
                funcion(datos)

# --- DEFINICIÓN DE OYENTES (LISTENERS) ---

def oyente_auditoria(oferta):
    """Oyente 1: Registra en consola cada nueva publicación."""
    print(f"📝 [AUDITORÍA EVENTO]: Se registró '{oferta.titulo}' en la categoría [{oferta.categoria.upper()}].")

def oyente_procesamiento_visual(oferta):
    """Oyente 2: Dispara el hilo de OpenCV de forma automática al crearse una oferta."""
    ruta_demo = os.path.join(os.path.dirname(__file__), '../foto_estudiante.jpg')
    if os.path.exists(ruta_demo):
        print("🎨 [EVENTO VISUAL]: Iniciando hilo de mejora de contraste OpenCV...")
        guardar_imagen_en_hilo(ruta_demo)

# Registramos los oyentes al evento 'oferta_creada'
GestorEventos.suscribir('oferta_creada', oyente_auditoria)
GestorEventos.suscribir('oferta_creada', oyente_procesamiento_visual)  


