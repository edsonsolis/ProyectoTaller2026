import os
import time
from django.conf import settings
from django.shortcuts import render, redirect
from .utils import BaseDatosXML, analizar_texto_nlp, GestorEventos, obtener_cola_chat, guardar_imagen_en_hilo
from FiltroDeOferta.Oferta import Oferta, MotorOfertas

def vista_portada(request):
    return render(request, 'core/portada.html')

def vista_estudiante(request):
    db = BaseDatosXML()
    mensaje = ""
    tipo_alerta = "success"
    url_carnet_procesado = ""
    # 0. CERRAR SESIÓN DEL ESTUDIANTE
    if 'cerrar_sesion' in request.GET:
        request.session.flush()
        return redirect('portada')
    # 1. ELIMINAR OFERTA (Validando PIN)
    titulo_eliminar = request.GET.get('eliminar', '')
    if titulo_eliminar:
        pin_sesion = request.session.get('pin_actual', '')
        if db.eliminar_oferta_segura(titulo_eliminar, pin_sesion):
            mensaje = f"🗑️ Se eliminó correctamente '{titulo_eliminar}'."
        else:
            mensaje = "❌ No tienes permiso para eliminar esta publicación."
            tipo_alerta = "error"

    # 2. PUBLICAR NUEVA OFERTA + PROCESAR CARNET EN HILO OPENCV
    if request.method == 'POST':
        nombre = request.POST.get('nombre_estudiante', '').strip()
        pin = request.POST.get('pin', '').strip()
        request.session['estudiante_actual'] = nombre
        request.session['pin_actual'] = pin

        titulo = request.POST.get('titulo', '')
        carrera = request.POST.get('carrera', 'general')
        descripcion = request.POST.get('descripcion', '')
        precio_orig = float(request.POST.get('precio_original', 100))
        precio_desc = float(request.POST.get('precio_descuento', 80))
        universidad = request.POST.get('entidad', 'UMSS')
        ubicacion = request.POST.get('ubicacion', 'Cochabamba')
        modalidad = request.POST.get('modalidad', 'Presencial')
        
        # Guardar imagen subida y procesarla en Hilo Secundario con OpenCV
        archivo_carnet = request.FILES.get('carnet')
        if archivo_carnet:
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            ruta_guardado = os.path.join(settings.MEDIA_ROOT, 'carnet_verificado.jpg')
            with open(ruta_guardado, 'wb+') as destino:
                for chunk in archivo_carnet.chunks():
                    destino.write(chunk)
            
            # Lanzamos el hilo de OpenCV
            guardar_imagen_en_hilo(ruta_guardado)
            time.sleep(0.3) # Breve pausa para que el hilo alcance a escribir antes de recargar
            url_carnet_procesado = settings.MEDIA_URL + 'carnet_verificado.jpg'

        analisis_nlp = analizar_texto_nlp(descripcion)
        info_autor = f"{nombre} ({universidad})"
        
        nueva_oferta = Oferta(
            titulo=titulo,
            categoria=carrera,
            precio_original=precio_orig,
            precio_descuento=precio_desc,
            modalidad=modalidad,
            ubicacion=ubicacion,
            entidad=info_autor,
            fecha_expiracion=None,
            popularidad=5.0
        )
        
        db.guardar_oferta(nueva_oferta, descripcion, pin)
        GestorEventos.disparar('oferta_creada', nueva_oferta)
        mensaje = f"✅ ¡Publicado en {carrera.upper()}! (NLP analizó {analisis_nlp['cantidad']} palabras clave)."

    # 3. INICIAR SESIÓN EN MI CUENTA
    if 'buscar_cuenta' in request.GET:
        request.session['estudiante_actual'] = request.GET.get('autor', '').strip()
        request.session['pin_actual'] = request.GET.get('pin_login', '').strip()

    autor_actual = request.session.get('estudiante_actual', '')
    pin_actual = request.session.get('pin_actual', '')

    todas = db.cargar_ofertas_priorizadas()
    mis_ofertas = []
    if autor_actual and pin_actual:
        mis_ofertas = [o for o in todas if autor_actual.lower() in o.entidad.lower() and o.pin == pin_actual]

    return render(request, 'core/estudiante.html', {
        'mensaje': mensaje,
        'tipo_alerta': tipo_alerta,
        'autor_actual': autor_actual,
        'pin_actual': pin_actual,
        'mis_ofertas': mis_ofertas,
        'url_carnet': url_carnet_procesado
    })

def vista_cliente(request):
    db = BaseDatosXML()

    calificar_titulo = request.GET.get('calificar', '')
    puntos = request.GET.get('puntos', '')
    if calificar_titulo and puntos.isdigit():
        db.calificar_oferta(calificar_titulo, float(puntos))
        return redirect('cliente')

    servicios_priorizados = db.cargar_ofertas_priorizadas()
    motor = MotorOfertas(servicios_priorizados)
    
    filtro_cat = request.GET.get('categoria', 'todas')
    precio_max = request.GET.get('precio_max', '')

    if filtro_cat != 'todas':
        motor.filtrar_por_categoria(filtro_cat)
    if precio_max and precio_max.isdigit():
        motor.filtrar_por_rango_precio(0, float(precio_max))

    return render(request, 'core/cliente.html', {
        'servicios': motor.obtener_catalogo(),
        'filtro_actual': filtro_cat,
        'precio_max': precio_max
    })

def vista_chat(request, titulo_oferta):
    cola_actual = obtener_cola_chat(titulo_oferta)
    
    # Detectamos el rol según el botón desde donde hiciste clic (?rol=estudiante o ?rol=cliente)
    rol_param = request.GET.get('rol', 'cliente')
    es_estudiante = (rol_param == 'estudiante')
    
    nombre_est = request.session.get('estudiante_actual', 'Estudiante')
    rol_usuario = f"Estudiante ({nombre_est})" if es_estudiante else "Cliente Interesado"

    if request.method == 'POST':
        texto = request.POST.get('mensaje', '')
        if texto.strip():
            cola_actual.append({
                'remitente': rol_usuario,
                'es_estudiante': es_estudiante,
                'texto': texto
            })

    return render(request, 'core/chat.html', {
        'titulo_oferta': titulo_oferta,
        'mensajes': list(cola_actual),
        'es_estudiante': es_estudiante,
        'rol_usuario': rol_usuario
    })


