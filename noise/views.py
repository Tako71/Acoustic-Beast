from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404

from .models import NoiseMeasurement, MeasurementPoint, NoiseReport, RegulatoryDocument
from .forms import MeasurementInfoForm
from . import calculators
from .pdf_generator import generate_pdf


def home(request):
    return render(request, 'index.html')


def docs(request):
    documents = RegulatoryDocument.objects.all()
    return render(request, 'docs.html', {'documents': documents})


def faq(request):
    return render(request, 'faq.html')


@login_required
def calculate_view(request):
    if request.method == 'POST':
        form = MeasurementInfoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            num_points = data['num_points']
            strategy = data['strategy']

            # Собираем точки замера из POST
            points = []
            errors = []
            for i in range(1, num_points + 1):
                noise_str = request.POST.get(f'noise_{i}', '').strip()
                duration_str = request.POST.get(f'duration_{i}', '').strip()
                try:
                    noise_db = float(noise_str)
                    if not (0 <= noise_db <= 200):
                        errors.append(f'Точка {i}: уровень шума должен быть от 0 до 200 дБ.')
                        continue
                    point = {'noise_db': noise_db}
                    if strategy in ('operation', 'function'):
                        dur = float(duration_str) if duration_str else None
                        if dur is None or dur <= 0:
                            errors.append(f'Точка {i}: укажите длительность больше 0.')
                            continue
                        point['duration_min'] = dur
                    points.append(point)
                except ValueError:
                    errors.append(f'Точка {i}: некорректное значение.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'noise/calculate.html', {
                    'form': form, 'num_points': num_points, 'strategy': strategy
                })

            # Сохраняем замер
            measurement = NoiseMeasurement.objects.create(
                user=request.user,
                company=data['company'],
                location=data['location'],
                strategy=strategy,
                num_points=num_points,
                notes=data['notes'],
            )
            MeasurementPoint.objects.bulk_create([
                MeasurementPoint(
                    measurement=measurement,
                    point_number=i,
                    noise_db=p['noise_db'],
                    duration_min=p.get('duration_min'),
                )
                for i, p in enumerate(points, start=1)
            ])

            # Расчёт
            result = calculators.calculate(strategy, points)

            # Сохраняем отчёт
            report = NoiseReport.objects.create(
                measurement=measurement,
                lex_8h=result['lex_8h'],
                std_deviation=result['std_deviation'],
                max_noise=result['max_noise'],
                min_noise=result['min_noise'],
                norm_value=result['norm_value'],
                exceeds_norm=result['exceeds_norm'],
                recommendations='\n'.join(result['recommendations']),
            )

            return redirect('result', pk=report.pk)

        # Форма невалидна
        num_points = request.POST.get('num_points', 1)
        strategy = request.POST.get('strategy', 'day')
        return render(request, 'noise/calculate.html', {
            'form': form, 'num_points': num_points, 'strategy': strategy
        })

    form = MeasurementInfoForm()
    return render(request, 'noise/calculate.html', {'form': form, 'num_points': 1, 'strategy': 'day'})


@login_required
def result_view(request, pk):
    report = get_object_or_404(
        NoiseReport.objects
        .select_related('measurement__user')
        .prefetch_related('measurement__points'),
        pk=pk,
    )
    if report.measurement.user != request.user and not request.user.is_staff:
        raise Http404
    points = report.measurement.points.all()
    recommendations = report.recommendations.split('\n')
    return render(request, 'noise/result.html', {
        'report': report,
        'points': points,
        'recommendations': recommendations,
    })


@login_required
def download_pdf(request, pk):
    report = get_object_or_404(
        NoiseReport.objects
        .select_related('measurement__user')
        .prefetch_related('measurement__points'),
        pk=pk,
    )
    if report.measurement.user != request.user and not request.user.is_staff:
        raise Http404
    pdf_bytes = generate_pdf(report)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report_{pk}.pdf"'
    return response


@login_required
def history_view(request):
    measurements = NoiseMeasurement.objects.filter(user=request.user).select_related('report')
    return render(request, 'noise/history.html', {'measurements': measurements})


def handler404(request, exception):
    return render(request, '404.html', status=404)
