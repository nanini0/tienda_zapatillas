from rest_framework import viewsets
from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer

class ProductoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo permite:
    - GET /api/productos/
    - GET /api/productos/
    """
    queryset = Producto.objects.all() 
    serializer_class = ProductoSerializer
    

class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo permite:
    - GET /api/categorias/
    - GET /api/categorias/
    """
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    