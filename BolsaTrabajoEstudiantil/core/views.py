from django.shortcuts import render, redirect
from .utils import BaseDatosXML, analizar_texto_nlp, GestorEventos, COLA_MENSAJES_CHAT
from FiltroDeOferta.Oferta import Oferta, MotorOfertas

def vista_portada(request):
    return render(request, 'core/portada.html')

def vista_estudiante(request):
    db = BaseDatosXML()
    mensaje = ""
    tipo_alerta = "success"

    # 1. ELIMINAR OFERTA (Validando PIN)
    titulo_eliminar = request.GET.get('eliminar', '')
    if titulo_eliminar:
        pin_sesion = request.session.get('pin_actual', '')
        if db.eliminar_oferta_segura(titulo_eliminar, pin_sesion):
            mensaje = f"🗑️ Se eliminó correctamente '{titulo_eliminar}'."
        else:
            mensaje = "❌ No tienes permiso para eliminar esta publicación."
            tipo_alerta = "error"

    # 2. PUBLICAR NUEVA OFERTA
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
            popularidad=5.0  # Empieza con 5.0 estrellas
        )
        
        db.guardar_oferta(nueva_oferta, descripcion, pin)
        GestorEventos.disparar('oferta_creada', nueva_oferta)
        mensaje = f"✅ ¡Publicado en {carrera.upper()}! (NLP procesó {analisis_nlp['cantidad']} palabras clave)."

    # 3. INICIAR SESIÓN EN MI CUENTA (Nombre + PIN)
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
        'mis_ofertas': mis_ofertas
    })

def vista_cliente(request):
    db = BaseDatosXML()

    # 1. RECIBIR CALIFICACIÓN DE ESTRELLAS
    calificar_titulo = request.GET.get('calificar', '')
    puntos = request.GET.get('puntos', '')
    if calificar_titulo and puntos.isdigit():
        db.calificar_oferta(calificar_titulo, float(puntos))
        return redirect('cliente') # Recarga limpia para ver el nuevo orden en la Cola de Prioridad

    # 2. CARGAR Y FILTRAR CON TU LIBRERÍA PROPIA
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
    if request.method == 'POST':
        remitente = request.POST.get('remitente', 'Cliente')
        texto = request.POST.get('mensaje', '')
        if texto.strip():
            COLA_MENSAJES_CHAT.append({'remitente': remitente, 'texto': texto})

    return render(request, 'core/chat.html', {
        'titulo_oferta': titulo_oferta,
        'mensajes': list(COLA_MENSAJES_CHAT)
    })

