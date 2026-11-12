from django.shortcuts import render
from .utils import BaseDatosXML, categorizar_por_nlp, GestorEventos
from FiltroDeOferta.Oferta import Oferta, MotorOfertas

def pagina_inicio(request):
    db = BaseDatosXML()
    
    # 1. CREACIÓN DE OFERTA MEDIANTE NLP Y DISPARO DE EVENTO
    texto_usuario = request.GET.get('descripcion', '')
    categoria_detectada = ""
    
    if texto_usuario:
        categoria_detectada = categorizar_por_nlp(texto_usuario)
        nueva_of = Oferta(
            titulo=texto_usuario if len(texto_usuario) < 40 else texto_usuario[:37] + "...", 
            categoria=categoria_detectada, 
            precio_original=120.0, 
            precio_descuento=100.0, 
            modalidad="Remoto", 
            ubicacion="Cochabamba", 
            entidad="Estudiante Verificado", 
            fecha_expiracion=None, 
            popularidad=4.7
        )
        db.guardar_oferta(nueva_of)
        
        # Disparamos el evento oficial del sistema
        GestorEventos.disparar('oferta_creada', nueva_of)

    # 2. CARGA DESDE XML CON COLA DE PRIORIDAD
    servicios_priorizados = db.cargar_ofertas_priorizadas()
    
    # 3. FILTRADO EFICIENTE USANDO TU LIBRERÍA PROPIA (MotorOfertas)
    filtro_cat = request.GET.get('filtro_categoria', 'todas')
    motor = MotorOfertas(servicios_priorizados)
    
    if filtro_cat != 'todas':
        motor.filtrar_por_categoria(filtro_cat)
        
    servicios_finales = motor.obtener_catalogo()
    
    return render(request, 'core/inicio.html', {
        'servicios': servicios_finales,
        'categoria_detectada': categoria_detectada,
        'filtro_actual': filtro_cat
    })

