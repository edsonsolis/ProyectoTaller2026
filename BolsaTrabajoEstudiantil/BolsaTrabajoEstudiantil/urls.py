from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.vista_portada, name='portada'),                   # Pantalla 1: Elegir Rol
    path('estudiante/', views.vista_estudiante, name='estudiante'),  # Pantalla 2: Publicar y Verificar
    path('cliente/', views.vista_cliente, name='cliente'),           # Pantalla 3: Buscar y Filtrar
    path('chat/<str:titulo_oferta>/', views.vista_chat, name='chat'),# Pantalla 4: Sala de Coordinación
]
