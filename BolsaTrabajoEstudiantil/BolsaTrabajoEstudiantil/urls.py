from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.vista_portada, name='portada'),
    path('estudiante/', views.vista_estudiante, name='estudiante'),
    path('cliente/', views.vista_cliente, name='cliente'),
    path('chat/<str:titulo_oferta>/', views.vista_chat, name='chat'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
