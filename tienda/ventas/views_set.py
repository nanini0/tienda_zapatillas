from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer, ProductoListSerializer

class ProductoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo permite:
    - GET /api/productos/ - Listar todos los productos
    - GET /api/productos/{id}/ - Ver detalle de un producto
    Filtros disponibles:
    - categoria: ID de categoría
    - precio_min: Precio mínimo
    - precio_max: Precio máximo
    - solo_ofertas: true/false - Solo productos en oferta
    - ofertas_vigentes: true/false - Solo ofertas con fechas válidas
    - solo_recomendados: true/false - Solo productos recomendados
    - descuento_min: Porcentaje mínimo de descuento
    - search: Búsqueda por nombre, descripción o marca
    - ordering: Ordenar por precio, nombre, created_at, descuento_porcentaje
    """
    queryset = Producto.objects.filter(is_active=True)  # Solo productos activos
    serializer_class = ProductoSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    # Campos por los que se puede buscar
    search_fields = ['nombre', 'descripcion', 'marca']
    
    # Campos por los que se puede ordenar
    ordering_fields = ['precio', 'created_at', 'nombre', 'descuento_porcentaje']
    ordering = ['-created_at']  # Orden por defecto: más recientes primero

    def get_queryset(self):
        """
        Aplicar filtros personalizados
        """
        queryset = super().get_queryset()
        
        # Filtrar por categoria
        categoria = self.request.query_params.get('categoria')
        if categoria:
            queryset = queryset.filter(categoria__id=categoria)
        
        # Filtrar por rango de precio
        precio_min = self.request.query_params.get('precio_min')
        precio_max = self.request.query_params.get('precio_max')
        
        if precio_min:
            queryset = queryset.filter(precio__gte=precio_min)
        if precio_max:
            queryset = queryset.filter(precio__lte=precio_max)
        
        # Filtrar solo productos en oferta
        solo_ofertas = self.request.query_params.get('solo_ofertas')
        if solo_ofertas and solo_ofertas.lower() == 'true':
            queryset = queryset.filter(is_oferta=True)
        
        # Filtrar solo ofertas vigentes (con fechas válidas)
        ofertas_vigentes = self.request.query_params.get('ofertas_vigentes')
        if ofertas_vigentes and ofertas_vigentes.lower() == 'true':
            ahora = timezone.now()
            queryset = queryset.filter(
                is_oferta=True,
                fecha_inicio_oferta__lte=ahora,
                fecha_fin_oferta__gte=ahora
            )
        
        # Filtrar por porcentaje mínimo de descuento
        descuento_min = self.request.query_params.get('descuento_min')
        if descuento_min:
            queryset = queryset.filter(descuento_porcentaje__gte=descuento_min)
        
        # Filtrar productos recomendados
        solo_recomendados = self.request.query_params.get('solo_recomendados')
        if solo_recomendados and solo_recomendados.lower() == 'true':
            queryset = queryset.filter(is_recommended=True)
        
        # Filtrar por color
        color = self.request.query_params.get('color')
        if color:
            queryset = queryset.filter(color=color)
        
        # Optimización: select_related para evitar N+1 queries
        queryset = queryset.select_related('categoria')
        
        # Optimización: prefetch_related para imágenes
        queryset = queryset.prefetch_related('imagenes')
        
        return queryset
    
    def get_serializer_class(self):
        """
        Usar serializador optimizado para listados
        y detallado para vista individual
        """
        if self.action == 'list':
            return ProductoListSerializer
        return ProductoSerializer
    
    def list(self, request, *args, **kwargs):
        """
        Sobrescribir para agregar metadatos útiles en la respuesta
        """
        response = super().list(request, *args, **kwargs)
        
        # Agregar metadatos sobre los filtros disponibles
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
        
        # Agregar conteos
        queryset = self.filter_queryset(self.get_queryset())
        metadatos['conteos'] = {
            'total': queryset.count(),
            'ofertas': queryset.filter(is_oferta=True).count(),
            'recomendados': queryset.filter(is_recommended=True).count()
        }
        
        # Envolver la respuesta con metadatos
        response.data = {
            'meta': metadatos,
            'results': response.data
        }
        
        return response


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API de solo lectura para categorías
    Solo permite:
    - GET /api/categorias/ - Listar todas las categorías
    - GET /api/categorias/{id}/ - Ver detalle de una categoría
    
    Filtros disponibles:
    - solo_con_productos: true/false - Solo categorías con productos activos
    - con_ofertas: true/false - Solo categorías con productos en oferta
    """
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    ordering_fields = ['nombre', 'created_at']
    ordering = ['nombre']  # Orden alfabético por defecto

    def get_queryset(self):
        """
        Aplicar filtros personalizados para categorías
        """
        queryset = super().get_queryset()
        
        # Filtrar categorías que tienen productos activos
        solo_con_productos = self.request.query_params.get('solo_con_productos')
        if solo_con_productos and solo_con_productos.lower() == 'true':
            queryset = queryset.filter(productos__is_active=True).distinct()
        
        # Filtrar categorías que tienen productos en oferta
        con_ofertas = self.request.query_params.get('con_ofertas')
        if con_ofertas and con_ofertas.lower() == 'true':
            queryset = queryset.filter(productos__is_oferta=True).distinct()
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """
        Sobrescribir para agregar conteo de productos por categoría
        """
        response = super().list(request, *args, **kwargs)
        
        # Agregar información adicional a cada categoría
        categorias_con_info = []
        for categoria in self.get_queryset():
            # Serializar la categoría
            categoria_data = CategoriaSerializer(categoria, context={'request': request}).data
            
            # Agregar estadísticas
            productos_categoria = categoria.productos.filter(is_active=True)
            categoria_data['estadisticas'] = {
                'total_productos': productos_categoria.count(),
                'productos_en_oferta': productos_categoria.filter(is_oferta=True).count(),
                'productos_recomendados': productos_categoria.filter(is_recommended=True).count()
            }
            
            # Agregar producto destacado (si hay)
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