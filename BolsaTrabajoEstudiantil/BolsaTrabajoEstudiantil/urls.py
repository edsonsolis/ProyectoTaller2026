from django.contrib import admin
from django.urls import path
from core.views import pagina_inicio # Importamos tu vista

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', pagina_inicio, name='inicio'), # Ruta raíz (http://127.0.0)
]
