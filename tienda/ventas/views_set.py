from rest_framework import viewsets
from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer

class ProductoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo permite:
    - GET /api/productos/
    - GET /api/productos/
    """
    queryset = Producto.objects.all()  #define que datos va a mostrar
    serializer_class = ProductoSerializer #define que serializador va a usar

    #personalizar consultas

    def get_queryset(self):
        #este metodo decide que productos se van a devolver\
        queryset = Producto.objects.all()

        categoria = self.request.query_params.get('categoria')
        precio_min = self.request.query_params.get('precio_min')
        precio_max = self.request.query_params.get('precio_max')

        if categoria:
            queryset = queryset.filter(categoria__id=categoria)
        
        if precio_min:
            queryset = queryset.filter(precio__gte=precio_min)
        if precio_max:
            queryset = queryset.filter(precio__lte=precio_max)
        return queryset
    

class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo permite:
    - GET /api/categorias/
    - GET /api/categorias/
    """
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    