from django.shortcuts import render, redirect
from .utils import BaseDatosXML, categorizar_por_nlp, GestorEventos, COLA_MENSAJES_CHAT
from FiltroDeOferta.Oferta import Oferta, MotorOfertas

# 1. PANTALLA DE PORTADA (Elección de Rol)
def vista_portada(request):
    return render(request, 'core/portada.html')

# 2. PANTALLA DEL ESTUDIANTE (Formulario completo + Verificación OpenCV + NLP)
def vista_estudiante(request):
    db = BaseDatosXML()
    mensaje_exito = ""
    categoria_detectada = ""

    if request.method == 'POST':
        titulo = request.POST.get('titulo', 'Servicio Estudiantil')
        descripcion = request.POST.get('descripcion', '')
        precio_orig = float(request.POST.get('precio_original', 100))
        precio_desc = float(request.POST.get('precio_descuento', 80))
        universidad = request.POST.get('entidad', 'UMSS')
        ubicacion = request.POST.get('ubicacion', 'Cochabamba')
        modalidad = request.POST.get('modalidad', 'Presencial')
        
        # Analizamos la descripción con NLP para asignar categoría automáticamente
        categoria_detectada = categorizar_por_nlp(descripcion + " " + titulo)
        
        nueva_oferta = Oferta(
            titulo=titulo,
            categoria=categoria_detectada,
            precio_original=precio_orig,
            precio_descuento=precio_desc,
            modalidad=modalidad,
            ubicacion=ubicacion,
            entidad=universidad,
            fecha_expiracion=None,
            popularidad=4.5  # Puntaje inicial de verificación
        )
        
        db.guardar_oferta(nueva_oferta)
        # Disparamos el evento (Auditoria + Hilo de verificación visual OpenCV)
        GestorEventos.disparar('oferta_creada', nueva_oferta)
        mensaje_exito = f"¡Perfil verificado con OpenCV! Tu oferta se publicó en la categoría {categoria_detectada.upper()}."

    return render(request, 'core/estudiante.html', {
        'mensaje_exito': mensaje_exito,
        'categoria_detectada': categoria_detectada
    })

# 3. PANTALLA DEL CLIENTE / EMPLEADOR (Catálogo + Filtros de tu librería propia)
def vista_cliente(request):
    db = BaseDatosXML()
    servicios_priorizados = db.cargar_ofertas_priorizadas()
    
    # Usamos tu librería propia MotorOfertas
    motor = MotorOfertas(servicios_priorizados)
    
    filtro_cat = request.GET.get('categoria', 'todas')
    precio_max = request.GET.get('precio_max', '')

    if filtro_cat != 'todas':
        motor.filtrar_por_categoria(filtro_cat)
        
    if precio_max and precio_max.isdigit():
        motor.filtrar_por_rango_precio(0, float(precio_max))

    servicios_finales = motor.obtener_catalogo()

    return render(request, 'core/cliente.html', {
        'servicios': servicios_finales,
        'filtro_actual': filtro_cat,
        'precio_max': precio_max
    })

# 4. PANTALLA DE CHAT DE COORDINACIÓN (Cola FIFO)
def vista_chat(request, titulo_oferta):
    if request.method == 'POST':
        remitente = request.POST.get('remitente', 'Cliente')
        texto = request.POST.get('mensaje', '')
        if texto.strip():
            # Insertamos en la Cola FIFO (First-In, First-Out)
            COLA_MENSAJES_CHAT.append({'remitente': remitente, 'texto': texto})

    return render(request, 'core/chat.html', {
        'titulo_oferta': titulo_oferta,
        'mensajes': list(COLA_MENSAJES_CHAT)
    })

