from django.contrib import admin
from .models import NoiseMeasurement, MeasurementPoint, NoiseReport, CalculationStrategy, RegulatoryDocument


class MeasurementPointInline(admin.TabularInline):
    model = MeasurementPoint
    extra = 0


@admin.register(NoiseMeasurement)
class NoiseMeasurementAdmin(admin.ModelAdmin):
    list_display = ('company', 'location', 'strategy', 'num_points', 'user', 'created_at')
    list_filter = ('strategy', 'created_at')
    search_fields = ('company', 'location', 'user__username')
    inlines = [MeasurementPointInline]


@admin.register(NoiseReport)
class NoiseReportAdmin(admin.ModelAdmin):
    list_display = ('measurement', 'lex_8h', 'norm_value', 'exceeds_norm', 'created_at')
    list_filter = ('exceeds_norm',)


@admin.register(CalculationStrategy)
class CalculationStrategyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')


@admin.register(RegulatoryDocument)
class RegulatoryDocumentAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'title', 'order')
    ordering = ('order',)
