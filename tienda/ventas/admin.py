from django.contrib import admin
from .models import Categoria, Producto
from django.utils.html import format_html

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'slug', 'created_at')
    search_fields = ('nombre',)
    prepopulated_fields = {'slug': ('nombre',)}
    ordering = ('-created_at',)
    list_display_links = ('id','nombre',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'nombre', 'categoria',
        'precio', 'color', 'is_active',
        'imagen_preview', 'created_at'
    )
    list_display_links = ('id','nombre',)


    list_select_related = ('categoria',)

    list_editable = ('precio', 'color', 'is_active')

    date_hierarchy = 'created_at'

    prepopulated_fields = {'slug': ('nombre',)}

    def imagen_preview(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit:cover;" />',
                obj.imagen.url
            )
        return "-"
    
    imagen_preview.short_description = "Imagen"