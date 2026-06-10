from django import forms
from .models import STRATEGY_CHOICES


class MeasurementInfoForm(forms.Form):
    company  = forms.CharField(
        label='Название компании', max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ООО «ФАРМГРУПП СПб»'})
    )
    location = forms.CharField(
        label='Место проведения замеров', max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Склад хранения препаратов, цех №1'})
    )
    strategy = forms.ChoiceField(
        label='Стратегия расчёта', choices=STRATEGY_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    num_points = forms.IntegerField(
        label='Количество точек замеров', min_value=1, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '5'})
    )
    notes = forms.CharField(
        label='Примечания', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                     'placeholder': 'Условия проведения замеров, оборудование...'})
    )
