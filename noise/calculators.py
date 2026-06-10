import math
import numpy as np

NORM_DB = 80.0
T0_MIN = 480.0  # базовая длительность рабочего дня, мин


def strategy_operation(points):
    """
    Стратегия 1 — на основе рабочих операций (ГОСТ ISO 9612-2016).
    points: list of dict {'noise_db': float, 'duration_min': float}
    L_EX,8h = 10 * log10( sum[ 10^(0.1*L_m) * (T_m / T0) ] )
    """
    total = sum(10 ** (0.1 * p['noise_db']) * (p['duration_min'] / T0_MIN) for p in points)
    return 10 * math.log10(total) if total > 0 else 0.0


def strategy_function(points):
    """
    Стратегия 2 — на основе трудовой функции (ГОСТ ISO 9612-2016).
    points: list of dict {'noise_db': float, 'duration_min': float}
    L_EX,8h = L_p,A,eqTe + 10*log10(Te/T0)
    где L_p,A,eqTe = 10*log10( (1/N)*sum[10^(0.1*L_i)] )
    """
    values = [p['noise_db'] for p in points]
    te = sum(p['duration_min'] for p in points)
    l_eq = 10 * math.log10(sum(10 ** (0.1 * v) for v in values) / len(values))
    return l_eq + 10 * math.log10(te / T0_MIN)


def strategy_day(points):
    """
    Стратегия 3 — на основе рабочего дня (ГОСТ ISO 9612-2016).
    points: list of dict {'noise_db': float}
    L_EX,8h = 10 * log10( (1/N) * sum[ 10^(0.1*L_i) ] )
    """
    values = [p['noise_db'] for p in points]
    total = sum(10 ** (0.1 * v) for v in values)
    return 10 * math.log10(total / len(values))


def get_recommendations(lex_8h):
    """Возвращает список рекомендаций при превышении ПДУ."""
    if lex_8h <= NORM_DB:
        return ['Уровень шума соответствует нормативным требованиям СанПиН 2.2.4.3359-16.']
    recs = [
        f'Эквивалентный уровень шума ({lex_8h:.1f} дБ) превышает ПДУ ({NORM_DB} дБ).',
        'Рекомендуется принять следующие меры:',
        '1. Использовать шумопоглощающие материалы на стенах и потолке рабочей зоны.',
        '2. Установить шумоизоляционные экраны и перегородки вблизи источника шума.',
        '3. Рассмотреть перемещение шумного оборудования в отдельное помещение.',
        '4. Обеспечить регулярное техническое обслуживание оборудования.',
        '5. Обязать персонал использовать СИЗ органов слуха (наушники, беруши).',
        '6. Ввести регламентированные перерывы при длительной работе в шумной зоне.',
        '7. Провести повторные замеры после реализации защитных мер.',
    ]
    return recs


def calculate(strategy, points):
    """
    Основная функция расчёта. Возвращает dict с результатами.
    strategy: 'operation' | 'function' | 'day'
    points: list of dict
    """
    calculators = {
        'operation': strategy_operation,
        'function':  strategy_function,
        'day':       strategy_day,
    }
    lex_8h = calculators[strategy](points)
    values = [p['noise_db'] for p in points]

    return {
        'lex_8h':        round(lex_8h, 2),
        'std_deviation': round(float(np.std(values)), 2),
        'max_noise':     max(values),
        'min_noise':     min(values),
        'norm_value':    NORM_DB,
        'exceeds_norm':  lex_8h > NORM_DB,
        'recommendations': get_recommendations(lex_8h),
    }
