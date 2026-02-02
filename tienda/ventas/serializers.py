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
    
    # Campos calculados
    precio_final = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    ahorro = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    tiene_oferta_vigente = serializers.BooleanField(read_only=True)
    precio_original_display = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        allow_null=True
    )

    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'descripcion', 'precio', 
            'categoria', 'categoria_id', 'slug', 'is_active', 
            'imagen_url', 'imagenes', 'marca', 'color', 
            'is_recommended', 'created_at', 'updated_at',
            # Campos de oferta
            'is_oferta', 'precio_original', 'descuento_porcentaje',
            'fecha_inicio_oferta', 'fecha_fin_oferta',
            # Campos calculados
            'precio_final', 'ahorro', 'tiene_oferta_vigente',
            'precio_original_display'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']

    def get_imagen_url(self, obj):
        if obj.imagen:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.imagen.url)
            return obj.imagen.url
        return None
    
    def validate_descuento_porcentaje(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("El descuento debe estar entre 0% y 100%")
        return value
    
    def validate(self, data):
        fecha_inicio = data.get('fecha_inicio_oferta')
        fecha_fin = data.get('fecha_fin_oferta')
        
        if fecha_inicio and fecha_fin and fecha_inicio >= fecha_fin:
            raise serializers.ValidationError({
                'fecha_fin_oferta': 'La fecha de fin debe ser posterior a la fecha de inicio'
            })
        
        return data

class ProductoListSerializer(serializers.ModelSerializer):
    categoria = serializers.StringRelatedField()
    imagen_url = serializers.SerializerMethodField()
    precio_final = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    precio_original_display = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True, 
        allow_null=True
    )
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