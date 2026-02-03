from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer, ProductoListSerializer

class ProductoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Producto.objects.filter(is_active=True)
    serializer_class = ProductoSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = ['nombre', 'descripcion', 'marca']
    ordering_fields = ['precio', 'created_at', 'nombre', 'descuento_porcentaje']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        categoria = self.request.query_params.get('categoria')
        if categoria:
            queryset = queryset.filter(categoria__id=categoria)
        
        precio_min = self.request.query_params.get('precio_min')
        precio_max = self.request.query_params.get('precio_max')
        
        if precio_min:
            queryset = queryset.filter(precio__gte=precio_min)
        if precio_max:
            queryset = queryset.filter(precio__lte=precio_max)
        
        solo_ofertas = self.request.query_params.get('solo_ofertas')
        if solo_ofertas and solo_ofertas.lower() == 'true':
            queryset = queryset.filter(is_oferta=True)
        
        ofertas_vigentes = self.request.query_params.get('ofertas_vigentes')
        if ofertas_vigentes and ofertas_vigentes.lower() == 'true':
            ahora = timezone.now()
            queryset = queryset.filter(
                is_oferta=True,
                fecha_inicio_oferta__lte=ahora,
                fecha_fin_oferta__gte=ahora
            )
        
        descuento_min = self.request.query_params.get('descuento_min')
        if descuento_min:
            queryset = queryset.filter(descuento_porcentaje__gte=descuento_min)
        
        solo_recomendados = self.request.query_params.get('solo_recomendados')
        if solo_recomendados and solo_recomendados.lower() == 'true':
            queryset = queryset.filter(is_recommended=True)
        
        color = self.request.query_params.get('color')
        if color:
            queryset = queryset.filter(color=color)
        
        queryset = queryset.select_related('categoria').prefetch_related('imagenes')
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProductoListSerializer
        return ProductoSerializer
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        metadatos = {
            'filtros_disponibles': {
                'categoria': 'ID de categoría para filtrar',
                'precio_min': 'Precio mínimo (ej: precio_min=50)',
                'precio_max': 'Precio máximo (ej: precio_max=200)',
                'solo_ofertas': 'true/false - Solo productos en oferta',
                'ofertas_vigentes': 'true/false - Solo ofertas con fechas válidas',
                'solo_recomendados': 'true/false - Solo productos recomendados',
                'descuento_min': 'Porcentaje mínimo de descuento (ej: descuento_min=20)',
                'color': 'Color del producto (ej: color=negro)',
                'search': 'Búsqueda por nombre, descripción o marca',
                'ordering': 'Ordenar por: precio, -precio, nombre, created_at, -created_at, descuento_porcentaje'
            }
        }
        
        queryset = self.filter_queryset(self.get_queryset())
        metadatos['conteos'] = {
            'total': queryset.count(),
            'ofertas': queryset.filter(is_oferta=True).count(),
            'recomendados': queryset.filter(is_recommended=True).count()
        }
        
        response.data = {
            'meta': metadatos,
            'results': response.data
        }
        
        return response


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    ordering_fields = ['nombre', 'created_at']
    ordering = ['nombre']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        solo_con_productos = self.request.query_params.get('solo_con_productos')
        if solo_con_productos and solo_con_productos.lower() == 'true':
            queryset = queryset.filter(productos__is_active=True).distinct()
        
        con_ofertas = self.request.query_params.get('con_ofertas')
        if con_ofertas and con_ofertas.lower() == 'true':
            queryset = queryset.filter(productos__is_oferta=True).distinct()
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        categorias_con_info = []
        for categoria in self.get_queryset():
            categoria_data = CategoriaSerializer(categoria, context={'request': request}).data
            
            productos_categoria = categoria.productos.filter(is_active=True)
            categoria_data['estadisticas'] = {
                'total_productos': productos_categoria.count(),
                'productos_en_oferta': productos_categoria.filter(is_oferta=True).count(),
                'productos_recomendados': productos_categoria.filter(is_recommended=True).count()
            }
            
            producto_destacado = productos_categoria.filter(is_recommended=True).first()
            if producto_destacado:
                categoria_data['producto_destacado'] = {
                    'id': producto_destacado.id,
                    'nombre': producto_destacado.nombre,
                    'precio_final': float(producto_destacado.precio_final),
                    'imagen_url': request.build_absolute_uri(producto_destacado.imagen.url) if producto_destacado.imagen else None
                }
            
            categorias_con_info.append(categoria_data)
        
        response.data = categorias_con_info
        return response