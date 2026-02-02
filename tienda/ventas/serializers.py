from rest_framework import serializers
from .models import Categoria, ImagenProducto, Producto

class ImagenProductoSerializer(serializers.ModelSerializer):
    imagen_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ImagenProducto
        fields = ['id', 'imagen_url', 'orden', 'is_principal', 'descripcion']
    
    def get_imagen_url(self, obj):
        if obj.imagen:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.imagen.url)
            return obj.imagen.url
        return None

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'descripcion', 'slug']


class ProductoSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(read_only=True)
    categoria_id = serializers.PrimaryKeyRelatedField(
        queryset=Categoria.objects.all(),
        source='categoria',
        write_only=True
    )
    imagen_url = serializers.SerializerMethodField()
    imagenes = ImagenProductoSerializer(many=True, read_only=True)
    
    # Campos calculados para ofertas
    precio_final = serializers.SerializerMethodField()
    ahorro = serializers.SerializerMethodField()
    tiene_oferta_vigente = serializers.SerializerMethodField()
    
    # Campos para mostrar precio original cuando hay oferta
    precio_original_display = serializers.SerializerMethodField()
    
    # Campos para mostrar fechas de oferta formateadas
    fecha_inicio_oferta = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, allow_null=True)
    fecha_fin_oferta = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, allow_null=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'descripcion', 'precio', 
            'categoria', 'categoria_id', 'slug', 'is_active', 
            'imagen_url', 'imagenes', 'marca', 'color', 
            'is_recommended', 'created_at', 'updated_at',
            # Nuevos campos de oferta
            'is_oferta', 'precio_original', 'descuento_porcentaje',
            'fecha_inicio_oferta', 'fecha_fin_oferta',
            # Campos calculados
            'precio_final', 'ahorro', 'tiene_oferta_vigente',
            'precio_original_display'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at', 'precio_final', 'ahorro', 'tiene_oferta_vigente']

    def get_imagen_url(self, obj):
        """Devuelve la URL de la imagen principal"""
        if obj.imagen:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.imagen.url)
            return obj.imagen.url
        return None
    
    def get_precio_final(self, obj):
        """Devuelve el precio final con descuento aplicado"""
        return obj.precio_final
    
    def get_ahorro(self, obj):
        """Devuelve la cantidad ahorrada"""
        return obj.ahorro
    
    def get_tiene_oferta_vigente(self, obj):
        """Indica si la oferta está vigente"""
        return obj.tiene_oferta_vigente
    
    def get_precio_original_display(self, obj):
        """Devuelve el precio original para mostrar (cuando hay oferta)"""
        if obj.tiene_oferta_vigente and obj.precio_original:
            return obj.precio_original
        return None
    
    def validate_descuento_porcentaje(self, value):
        """Valida que el porcentaje de descuento esté entre 0 y 100"""
        if value < 0 or value > 100:
            raise serializers.ValidationError("El descuento debe estar entre 0% y 100%")
        return value
    
    def validate(self, data):
        """Validaciones adicionales"""
        # Validar fechas de oferta
        fecha_inicio = data.get('fecha_inicio_oferta')
        fecha_fin = data.get('fecha_fin_oferta')
        
        if fecha_inicio and fecha_fin:
            if fecha_inicio >= fecha_fin:
                raise serializers.ValidationError({
                    'fecha_fin_oferta': 'La fecha de fin debe ser posterior a la fecha de inicio'
                })
        
        # Si hay descuento, validar que haya precio original o calcularlo
        descuento = data.get('descuento_porcentaje', 0)
        is_oferta = data.get('is_oferta', False)
        
        if is_oferta and descuento > 0:
            # Si estamos creando/actualizando y no hay precio_original,
            # usar el precio actual como original
            precio = data.get('precio', getattr(self.instance, 'precio', None))
            if precio and 'precio_original' not in data and not getattr(self.instance, 'precio_original', None):
                data['precio_original'] = precio
        
        return data
    
    def create(self, validated_data):
        """Crear producto con manejo especial para ofertas"""
        # Separar datos de relaciones si existen
        categoria = validated_data.pop('categoria', None)
        
        # Crear producto
        producto = Producto.objects.create(**validated_data)
        
        return producto
    
    def update(self, instance, validated_data):
        """Actualizar producto con manejo especial para ofertas"""
        # Actualizar campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Guardar para activar la lógica del save()
        instance.save()
        return instance

class ProductoListSerializer(serializers.ModelSerializer):
    """Serializador optimizado para listados de productos"""
    categoria = serializers.StringRelatedField()
    imagen_url = serializers.SerializerMethodField()
    precio_final = serializers.SerializerMethodField()
    precio_original_display = serializers.SerializerMethodField()
    tiene_oferta_vigente = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'precio', 'precio_final',
            'precio_original_display', 'categoria', 'slug', 
            'imagen_url', 'marca', 'color',
            'is_oferta', 'descuento_porcentaje', 
            'tiene_oferta_vigente', 'is_recommended'
        ]
    
    def get_imagen_url(self, obj):
        if obj.imagen:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.imagen.url)
            return obj.imagen.url
        return None
    
    def get_precio_final(self, obj):
        return obj.precio_final
    
    def get_precio_original_display(self, obj):
        """Devuelve el precio original para mostrar (cuando hay oferta)"""
        if obj.tiene_oferta_vigente and obj.precio_original:
            return obj.precio_original
        return None