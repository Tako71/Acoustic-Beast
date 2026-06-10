from django.db import models
from django.contrib.auth.models import User


STRATEGY_CHOICES = [
    ('operation', 'На основе рабочих операций'),
    ('function',  'На основе трудовой функции'),
    ('day',       'На основе рабочего дня'),
]


class CalculationStrategy(models.Model):
    code         = models.CharField(max_length=20, unique=True, choices=STRATEGY_CHOICES)
    name         = models.CharField(max_length=255)
    description  = models.TextField()
    formula_hint = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Стратегия расчёта'
        verbose_name_plural = 'Стратегии расчёта'

    def __str__(self):
        return self.name


class RegulatoryDocument(models.Model):
    title       = models.CharField(max_length=512)
    short_name  = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    file_url    = models.URLField(blank=True)
    order       = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Нормативный документ'
        verbose_name_plural = 'Нормативные документы'
        ordering = ['order']

    def __str__(self):
        return self.short_name


class NoiseMeasurement(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='measurements')
    company    = models.CharField(max_length=255, verbose_name='Название компании')
    location   = models.CharField(max_length=255, verbose_name='Место проведения')
    strategy   = models.CharField(max_length=20, choices=STRATEGY_CHOICES, verbose_name='Стратегия расчёта')
    num_points = models.IntegerField(verbose_name='Количество точек замеров')
    notes      = models.TextField(blank=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Замер шума'
        verbose_name_plural = 'Замеры шума'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.company} — {self.location} ({self.created_at:%d.%m.%Y})'


class MeasurementPoint(models.Model):
    measurement  = models.ForeignKey(NoiseMeasurement, on_delete=models.CASCADE, related_name='points')
    point_number = models.IntegerField(verbose_name='Номер точки')
    noise_db     = models.FloatField(verbose_name='Уровень шума, дБ')
    duration_min = models.FloatField(null=True, blank=True, verbose_name='Длительность, мин')

    class Meta:
        verbose_name = 'Точка замера'
        verbose_name_plural = 'Точки замера'
        ordering = ['point_number']

    def __str__(self):
        return f'Точка {self.point_number}: {self.noise_db} дБ'


class NoiseReport(models.Model):
    measurement     = models.OneToOneField(NoiseMeasurement, on_delete=models.CASCADE, related_name='report')
    lex_8h          = models.FloatField(verbose_name='L_EX,8h, дБ')
    std_deviation   = models.FloatField(verbose_name='Стандартное отклонение')
    max_noise       = models.FloatField(verbose_name='Максимальное значение, дБ')
    min_noise       = models.FloatField(verbose_name='Минимальное значение, дБ')
    norm_value      = models.FloatField(default=80.0, verbose_name='ПДУ, дБ')
    exceeds_norm    = models.BooleanField(verbose_name='Превышение нормы')
    recommendations = models.TextField(verbose_name='Рекомендации')
    chart_path      = models.CharField(max_length=512, blank=True)
    pdf_path        = models.CharField(max_length=512, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Отчёт'
        verbose_name_plural = 'Отчёты'

    def __str__(self):
        status = 'ПРЕВЫШЕНИЕ' if self.exceeds_norm else 'норма'
        return f'Отчёт #{self.pk}: {self.lex_8h:.1f} дБ ({status})'
