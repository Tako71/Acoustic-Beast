import math
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse

_SIMPLE_STATIC = 'django.contrib.staticfiles.storage.StaticFilesStorage'

from noise.models import (
    NoiseMeasurement, MeasurementPoint, NoiseReport,
    RegulatoryDocument, CalculationStrategy,
)
from noise.calculators import (
    strategy_operation, strategy_function, strategy_day,
    get_recommendations, calculate, NORM_DB, T0_MIN,
)
from noise.forms import MeasurementInfoForm


# ---------------------------------------------------------------------------
# Calculators
# ---------------------------------------------------------------------------

class StrategyOperationTest(TestCase):

    @staticmethod
    def _pts(*args):
        return [{'noise_db': db, 'duration_min': dur} for db, dur in args]

    def test_single_full_day(self):
        # 10^8 * (480/480) = 10^8 → L = 80.0
        self.assertAlmostEqual(strategy_operation(self._pts((80.0, 480.0))), 80.0, places=5)

    def test_two_equal_half_day_each(self):
        # sum = 2 * 10^8 * 0.5 = 10^8 → 80.0
        self.assertAlmostEqual(strategy_operation(self._pts((80.0, 240.0), (80.0, 240.0))), 80.0, places=5)

    def test_zero_total_returns_zero(self):
        self.assertEqual(strategy_operation(self._pts((80.0, 0.0))), 0.0)

    def test_louder_gives_higher_result(self):
        low = strategy_operation(self._pts((70.0, 480.0)))
        high = strategy_operation(self._pts((90.0, 480.0)))
        self.assertGreater(high, low)

    def test_multiple_points_returns_float(self):
        result = strategy_operation(self._pts((70.0, 120.0), (80.0, 120.0), (90.0, 240.0)))
        self.assertIsInstance(result, float)
        self.assertGreater(result, 0)

    def test_formula_manual(self):
        # L=85, T=480 → 10*log10(10^8.5) = 85
        self.assertAlmostEqual(strategy_operation(self._pts((85.0, 480.0))), 85.0, places=5)


class StrategyFunctionTest(TestCase):

    @staticmethod
    def _pts(*args):
        return [{'noise_db': db, 'duration_min': dur} for db, dur in args]

    def test_single_full_day(self):
        # L_eq = 80.0, te/T0 = 1 → 80.0
        self.assertAlmostEqual(strategy_function(self._pts((80.0, 480.0))), 80.0, places=5)

    def test_higher_db_gives_higher_result(self):
        low = strategy_function(self._pts((70.0, 480.0)))
        high = strategy_function(self._pts((90.0, 480.0)))
        self.assertGreater(high, low)

    def test_returns_float(self):
        result = strategy_function(self._pts((75.0, 240.0), (85.0, 240.0)))
        self.assertIsInstance(result, float)

    def test_longer_exposure_increases_result(self):
        short = strategy_function(self._pts((80.0, 120.0)))
        long = strategy_function(self._pts((80.0, 480.0)))
        self.assertGreater(long, short)


class StrategyDayTest(TestCase):

    @staticmethod
    def _pts(*values):
        return [{'noise_db': v} for v in values]

    def test_single_point(self):
        self.assertAlmostEqual(strategy_day(self._pts(80.0)), 80.0, places=5)

    def test_uniform_values(self):
        self.assertAlmostEqual(strategy_day(self._pts(75.0, 75.0, 75.0)), 75.0, places=5)

    def test_result_between_min_and_max(self):
        result = strategy_day(self._pts(70.0, 80.0))
        self.assertGreater(result, 70.0)
        self.assertLess(result, 80.0)

    def test_higher_values_give_higher_result(self):
        low = strategy_day(self._pts(60.0, 65.0))
        high = strategy_day(self._pts(80.0, 85.0))
        self.assertGreater(high, low)


class GetRecommendationsTest(TestCase):

    def test_within_norm_returns_single_ok_message(self):
        recs = get_recommendations(NORM_DB - 1)
        self.assertEqual(len(recs), 1)
        self.assertIn('соответствует', recs[0])

    def test_exactly_at_norm_is_ok(self):
        recs = get_recommendations(NORM_DB)
        self.assertEqual(len(recs), 1)

    def test_exceeds_norm_returns_multiple(self):
        recs = get_recommendations(NORM_DB + 5)
        self.assertGreater(len(recs), 1)

    def test_exceeds_norm_first_line_mentions_value(self):
        recs = get_recommendations(85.0)
        self.assertIn('85.0', recs[0])

    def test_exceeds_norm_mentions_pdou(self):
        recs = get_recommendations(NORM_DB + 1)
        joined = ' '.join(recs)
        self.assertIn(str(int(NORM_DB)), joined)


class CalculateTest(TestCase):

    @staticmethod
    def _day(* values):
        return [{'noise_db': v} for v in values]

    @staticmethod
    def _op(*args):
        return [{'noise_db': db, 'duration_min': dur} for db, dur in args]

    def test_returns_all_required_keys(self):
        result = calculate('day', self._day(75.0, 80.0))
        for k in ('lex_8h', 'std_deviation', 'max_noise', 'min_noise', 'norm_value', 'exceeds_norm', 'recommendations'):
            self.assertIn(k, result)

    def test_day_within_norm(self):
        result = calculate('day', self._day(60.0, 65.0))
        self.assertFalse(result['exceeds_norm'])
        self.assertLess(result['lex_8h'], NORM_DB)

    def test_day_exceeds_norm(self):
        result = calculate('day', self._day(90.0, 95.0))
        self.assertTrue(result['exceeds_norm'])

    def test_operation_full_day_80db(self):
        result = calculate('operation', self._op((80.0, 480.0)))
        self.assertAlmostEqual(result['lex_8h'], 80.0, places=2)

    def test_function_full_day_80db(self):
        result = calculate('function', self._op((80.0, 480.0)))
        self.assertAlmostEqual(result['lex_8h'], 80.0, places=2)

    def test_std_deviation_zero_for_uniform(self):
        result = calculate('day', self._day(80.0, 80.0, 80.0))
        self.assertAlmostEqual(result['std_deviation'], 0.0, places=5)

    def test_max_and_min_noise(self):
        result = calculate('day', self._day(70.0, 80.0, 90.0))
        self.assertEqual(result['max_noise'], 90.0)
        self.assertEqual(result['min_noise'], 70.0)

    def test_norm_value_constant(self):
        result = calculate('day', self._day(75.0))
        self.assertEqual(result['norm_value'], NORM_DB)

    def test_recommendations_is_list(self):
        result = calculate('day', self._day(75.0))
        self.assertIsInstance(result['recommendations'], list)

    def test_lex_8h_rounded_to_two_places(self):
        result = calculate('day', self._day(73.3, 76.7, 81.1))
        decimals = len(str(result['lex_8h']).split('.')[-1])
        self.assertLessEqual(decimals, 2)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class NoiseMeasurementModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('muser', password='pass')

    def test_str_contains_company_and_location(self):
        m = NoiseMeasurement.objects.create(
            user=self.user, company='ФАРМГРУПП', location='Цех №1',
            strategy='day', num_points=3,
        )
        self.assertIn('ФАРМГРУПП', str(m))
        self.assertIn('Цех №1', str(m))

    def test_user_fk(self):
        m = NoiseMeasurement.objects.create(
            user=self.user, company='Co', location='Loc', strategy='day', num_points=2,
        )
        self.assertEqual(m.user, self.user)

    def test_default_ordering_newest_first(self):
        m1 = NoiseMeasurement.objects.create(
            user=self.user, company='A', location='L', strategy='day', num_points=1,
        )
        m2 = NoiseMeasurement.objects.create(
            user=self.user, company='B', location='L', strategy='day', num_points=1,
        )
        qs = list(NoiseMeasurement.objects.filter(user=self.user))
        self.assertEqual(qs[0], m2)

    def test_cascade_delete_removes_points(self):
        m = NoiseMeasurement.objects.create(
            user=self.user, company='Co', location='Loc', strategy='day', num_points=2,
        )
        MeasurementPoint.objects.create(measurement=m, point_number=1, noise_db=75.0)
        m.delete()
        self.assertEqual(MeasurementPoint.objects.count(), 0)


class MeasurementPointModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('puser', password='pass')
        self.measurement = NoiseMeasurement.objects.create(
            user=self.user, company='Co', location='Loc', strategy='operation', num_points=2,
        )

    def test_str_contains_number_and_db(self):
        p = MeasurementPoint.objects.create(
            measurement=self.measurement, point_number=1, noise_db=75.5,
        )
        self.assertIn('1', str(p))
        self.assertIn('75.5', str(p))

    def test_duration_optional(self):
        p = MeasurementPoint.objects.create(
            measurement=self.measurement, point_number=1, noise_db=75.0,
        )
        self.assertIsNone(p.duration_min)

    def test_related_name_points(self):
        MeasurementPoint.objects.create(measurement=self.measurement, point_number=1, noise_db=72.0)
        MeasurementPoint.objects.create(measurement=self.measurement, point_number=2, noise_db=78.0)
        self.assertEqual(self.measurement.points.count(), 2)

    def test_ordering_by_point_number(self):
        MeasurementPoint.objects.create(measurement=self.measurement, point_number=2, noise_db=78.0)
        MeasurementPoint.objects.create(measurement=self.measurement, point_number=1, noise_db=72.0)
        nums = list(self.measurement.points.values_list('point_number', flat=True))
        self.assertEqual(nums, [1, 2])


class NoiseReportModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('ruser', password='pass')
        self.measurement = NoiseMeasurement.objects.create(
            user=self.user, company='Co', location='Loc', strategy='day', num_points=1,
        )

    def _make_report(self, lex_8h, exceeds):
        return NoiseReport.objects.create(
            measurement=self.measurement,
            lex_8h=lex_8h, std_deviation=1.0,
            max_noise=lex_8h + 2, min_noise=lex_8h - 2,
            exceeds_norm=exceeds, recommendations='Rec',
        )

    def test_str_shows_превышение(self):
        r = self._make_report(85.0, True)
        self.assertIn('ПРЕВЫШЕНИЕ', str(r))

    def test_str_shows_норма(self):
        r = self._make_report(75.0, False)
        self.assertIn('норма', str(r))

    def test_one_to_one_reverse(self):
        r = self._make_report(75.0, False)
        self.assertEqual(self.measurement.report, r)

    def test_cascade_delete_with_measurement(self):
        self._make_report(75.0, False)
        self.measurement.delete()
        self.assertEqual(NoiseReport.objects.count(), 0)

    def test_default_norm_value(self):
        r = self._make_report(75.0, False)
        self.assertEqual(r.norm_value, 80.0)


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

class MeasurementInfoFormTest(TestCase):

    @staticmethod
    def _data(**kwargs):
        base = {
            'company': 'Test Co',
            'location': 'Room 1',
            'strategy': 'day',
            'num_points': 5,
            'notes': '',
        }
        base.update(kwargs)
        return base

    def test_valid_form(self):
        self.assertTrue(MeasurementInfoForm(data=self._data()).is_valid())

    def test_company_required(self):
        form = MeasurementInfoForm(data=self._data(company=''))
        self.assertFalse(form.is_valid())
        self.assertIn('company', form.errors)

    def test_location_required(self):
        form = MeasurementInfoForm(data=self._data(location=''))
        self.assertFalse(form.is_valid())
        self.assertIn('location', form.errors)

    def test_invalid_strategy(self):
        self.assertFalse(MeasurementInfoForm(data=self._data(strategy='wrong')).is_valid())

    def test_num_points_min_1(self):
        self.assertFalse(MeasurementInfoForm(data=self._data(num_points=0)).is_valid())

    def test_num_points_max_50(self):
        self.assertFalse(MeasurementInfoForm(data=self._data(num_points=51)).is_valid())

    def test_num_points_boundary_valid(self):
        self.assertTrue(MeasurementInfoForm(data=self._data(num_points=1)).is_valid())
        self.assertTrue(MeasurementInfoForm(data=self._data(num_points=50)).is_valid())

    def test_notes_optional(self):
        self.assertTrue(MeasurementInfoForm(data=self._data(notes='')).is_valid())

    def test_all_strategies_valid(self):
        for s in ('operation', 'function', 'day'):
            form = MeasurementInfoForm(data=self._data(strategy=s))
            self.assertTrue(form.is_valid(), f'strategy={s} should be valid')


# ---------------------------------------------------------------------------
# Views — authentication
# ---------------------------------------------------------------------------

@override_settings(STATICFILES_STORAGE=_SIMPLE_STATIC)
class ViewAuthRedirectTest(TestCase):

    def test_calculate_redirects_to_login(self):
        r = self.client.get(reverse('calculate'))
        self.assertRedirects(r, '/login/?next=/calculate/')

    def test_history_redirects_to_login(self):
        r = self.client.get(reverse('history'))
        self.assertRedirects(r, '/login/?next=/history/')

    def test_result_redirects_to_login(self):
        r = self.client.get(reverse('result', kwargs={'pk': 1}))
        self.assertRedirects(r, '/login/?next=/result/1/')

    def test_download_pdf_redirects_to_login(self):
        r = self.client.get(reverse('download_pdf', kwargs={'pk': 1}))
        self.assertRedirects(r, '/login/?next=/result/1/pdf/')


# ---------------------------------------------------------------------------
# Views — public pages
# ---------------------------------------------------------------------------

@override_settings(STATICFILES_STORAGE=_SIMPLE_STATIC)
class PublicViewsTest(TestCase):

    def test_home_200(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)

    def test_docs_200(self):
        self.assertEqual(self.client.get(reverse('docs')).status_code, 200)

    def test_faq_200(self):
        self.assertEqual(self.client.get(reverse('faq')).status_code, 200)


# ---------------------------------------------------------------------------
# Views — calculate
# ---------------------------------------------------------------------------

@override_settings(STATICFILES_STORAGE=_SIMPLE_STATIC)
class CalculateViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('calc_user', password='pass123')
        self.client.login(username='calc_user', password='pass123')

    def test_get_returns_200(self):
        self.assertEqual(self.client.get(reverse('calculate')).status_code, 200)

    def test_post_day_redirects_to_result(self):
        r = self.client.post(reverse('calculate'), {
            'company': 'Завод', 'location': 'Цех', 'strategy': 'day',
            'num_points': 3,
            'noise_1': '75.0', 'noise_2': '80.0', 'noise_3': '85.0',
        })
        self.assertEqual(r.status_code, 302)
        report = NoiseReport.objects.first()
        self.assertIsNotNone(report)
        self.assertRedirects(r, reverse('result', kwargs={'pk': report.pk}))

    def test_post_operation_strategy(self):
        r = self.client.post(reverse('calculate'), {
            'company': 'Co', 'location': 'Loc', 'strategy': 'operation',
            'num_points': 2,
            'noise_1': '78.0', 'duration_1': '240',
            'noise_2': '82.0', 'duration_2': '240',
        })
        self.assertEqual(r.status_code, 302)

    def test_post_function_strategy(self):
        r = self.client.post(reverse('calculate'), {
            'company': 'Co', 'location': 'Loc', 'strategy': 'function',
            'num_points': 2,
            'noise_1': '78.0', 'duration_1': '240',
            'noise_2': '82.0', 'duration_2': '240',
        })
        self.assertEqual(r.status_code, 302)

    def test_invalid_form_returns_200(self):
        r = self.client.post(reverse('calculate'), {
            'company': '', 'location': '', 'strategy': 'day', 'num_points': 0,
        })
        self.assertEqual(r.status_code, 200)

    def test_points_saved_via_bulk_create(self):
        self.client.post(reverse('calculate'), {
            'company': 'Co', 'location': 'Loc', 'strategy': 'day',
            'num_points': 3,
            'noise_1': '70.0', 'noise_2': '75.0', 'noise_3': '80.0',
        })
        m = NoiseMeasurement.objects.get(user=self.user)
        self.assertEqual(m.points.count(), 3)

    def test_exceeds_norm_flag_set(self):
        self.client.post(reverse('calculate'), {
            'company': 'Co', 'location': 'Loc', 'strategy': 'day',
            'num_points': 1, 'noise_1': '95.0',
        })
        self.assertTrue(NoiseReport.objects.get(measurement__user=self.user).exceeds_norm)

    def test_within_norm_flag_set(self):
        self.client.post(reverse('calculate'), {
            'company': 'Co', 'location': 'Loc', 'strategy': 'day',
            'num_points': 1, 'noise_1': '60.0',
        })
        self.assertFalse(NoiseReport.objects.get(measurement__user=self.user).exceeds_norm)

    def test_invalid_noise_value_shows_error(self):
        r = self.client.post(reverse('calculate'), {
            'company': 'Co', 'location': 'Loc', 'strategy': 'day',
            'num_points': 1, 'noise_1': 'abc',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(NoiseReport.objects.count(), 0)

    def test_missing_duration_for_operation_shows_error(self):
        r = self.client.post(reverse('calculate'), {
            'company': 'Co', 'location': 'Loc', 'strategy': 'operation',
            'num_points': 1, 'noise_1': '80.0',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(NoiseReport.objects.count(), 0)


# ---------------------------------------------------------------------------
# Views — result
# ---------------------------------------------------------------------------

@override_settings(STATICFILES_STORAGE=_SIMPLE_STATIC)
class ResultViewTest(TestCase):

    def _make_report(self, user):
        m = NoiseMeasurement.objects.create(
            user=user, company='Co', location='Loc', strategy='day', num_points=1,
        )
        MeasurementPoint.objects.create(measurement=m, point_number=1, noise_db=75.0)
        return NoiseReport.objects.create(
            measurement=m, lex_8h=75.0, std_deviation=0.0,
            max_noise=75.0, min_noise=75.0, exceeds_norm=False,
            recommendations='Всё в норме.',
        )

    def setUp(self):
        self.user = User.objects.create_user('rv_user', password='pass')
        self.other = User.objects.create_user('other_user', password='pass')
        self.client.login(username='rv_user', password='pass')

    def test_owner_gets_200(self):
        report = self._make_report(self.user)
        self.assertEqual(self.client.get(reverse('result', kwargs={'pk': report.pk})).status_code, 200)

    def test_other_user_gets_404(self):
        report = self._make_report(self.other)
        self.assertEqual(self.client.get(reverse('result', kwargs={'pk': report.pk})).status_code, 404)

    def test_nonexistent_pk_gives_404(self):
        self.assertEqual(self.client.get(reverse('result', kwargs={'pk': 99999})).status_code, 404)

    def test_staff_can_view_any_report(self):
        staff = User.objects.create_user('staff_user', password='pass', is_staff=True)
        self.client.logout()
        self.client.login(username='staff_user', password='pass')
        report = self._make_report(self.user)
        self.assertEqual(self.client.get(reverse('result', kwargs={'pk': report.pk})).status_code, 200)

    def test_result_page_contains_company_name(self):
        report = self._make_report(self.user)
        r = self.client.get(reverse('result', kwargs={'pk': report.pk}))
        self.assertContains(r, 'Co')
        self.assertContains(r, 'Отчёт')


# ---------------------------------------------------------------------------
# Views — history
# ---------------------------------------------------------------------------

@override_settings(STATICFILES_STORAGE=_SIMPLE_STATIC)
class HistoryViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('hist_user', password='pass')
        self.client.login(username='hist_user', password='pass')

    def test_empty_history_200(self):
        r = self.client.get(reverse('history'))
        self.assertEqual(r.status_code, 200)

    def test_empty_history_shows_placeholder(self):
        self.assertContains(self.client.get(reverse('history')), 'Расчётов пока нет')

    def test_own_measurement_appears(self):
        NoiseMeasurement.objects.create(
            user=self.user, company='МойЗавод', location='Цех', strategy='day', num_points=1,
        )
        self.assertContains(self.client.get(reverse('history')), 'МойЗавод')

    def test_other_user_measurement_hidden(self):
        other = User.objects.create_user('other3', password='pass')
        NoiseMeasurement.objects.create(
            user=other, company='ЧужаяКомпания', location='Loc', strategy='day', num_points=1,
        )
        self.assertNotContains(self.client.get(reverse('history')), 'ЧужаяКомпания')

    def test_multiple_own_measurements(self):
        for i in range(3):
            NoiseMeasurement.objects.create(
                user=self.user, company=f'Завод{i}', location='Loc', strategy='day', num_points=1,
            )
        r = self.client.get(reverse('history'))
        self.assertContains(r, 'Завод0')
        self.assertContains(r, 'Завод2')


# ---------------------------------------------------------------------------
# Views — download_pdf
# ---------------------------------------------------------------------------

@override_settings(STATICFILES_STORAGE=_SIMPLE_STATIC)
class DownloadPdfViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('pdf_user', password='pass')
        self.other = User.objects.create_user('pdf_other', password='pass')
        self.client.login(username='pdf_user', password='pass')

    def _make_report(self, user):
        m = NoiseMeasurement.objects.create(
            user=user, company='Co', location='Loc', strategy='day', num_points=2,
        )
        MeasurementPoint.objects.create(measurement=m, point_number=1, noise_db=75.0)
        MeasurementPoint.objects.create(measurement=m, point_number=2, noise_db=78.0)
        return NoiseReport.objects.create(
            measurement=m, lex_8h=76.5, std_deviation=1.5,
            max_noise=78.0, min_noise=75.0, exceeds_norm=False,
            recommendations='OK',
        )

    def test_owner_gets_pdf(self):
        report = self._make_report(self.user)
        r = self.client.get(reverse('download_pdf', kwargs={'pk': report.pk}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')

    def test_pdf_content_disposition(self):
        report = self._make_report(self.user)
        r = self.client.get(reverse('download_pdf', kwargs={'pk': report.pk}))
        self.assertIn(f'report_{report.pk}.pdf', r['Content-Disposition'])

    def test_other_user_gets_404(self):
        report = self._make_report(self.other)
        r = self.client.get(reverse('download_pdf', kwargs={'pk': report.pk}))
        self.assertEqual(r.status_code, 404)

    def test_nonexistent_report_gives_404(self):
        self.assertEqual(self.client.get(reverse('download_pdf', kwargs={'pk': 99999})).status_code, 404)
