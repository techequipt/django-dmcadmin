from django.contrib import admin

from . import models


@admin.register(models.ManageTask)
class ManageTaskAmin(admin.ModelAdmin):
    pass
