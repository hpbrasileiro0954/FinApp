from django.contrib import admin
from .models import Param, Category, Entry, Fact

admin.site.register(Param)
admin.site.register(Category)
admin.site.register(Entry)
admin.site.register(Fact)
