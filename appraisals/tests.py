from datetime import date

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from appraisals.models import Appraisal, KRA
from employees.models import Department, Employee


class AppraisalPeriodFilterTests(APITestCase):
	def setUp(self):
		self.department = Department.objects.create(name='Engineering')

		self.hr_user = User.objects.create_user(username='hr1', password='pass1234')
		self.hr_employee = Employee.objects.create(
			user=self.hr_user,
			emp_id='HR001',
			designation='HR Manager',
			role=Employee.ROLE_HR,
			department=self.department,
		)

		self.staff_user = User.objects.create_user(username='staff1', password='pass1234')
		self.staff_employee = Employee.objects.create(
			user=self.staff_user,
			emp_id='ST001',
			designation='Engineer',
			role=Employee.ROLE_STAFF,
			department=self.department,
		)

		self.appraisal_jan_mar = Appraisal.objects.create(
			employee=self.staff_employee,
			appraisal_type='Quarterly',
			period_from=date(2026, 1, 1),
			period_to=date(2026, 3, 31),
			status=Appraisal.STATUS_SUBMITTED,
		)
		self.appraisal_apr_jun = Appraisal.objects.create(
			employee=self.staff_employee,
			appraisal_type='Quarterly',
			period_from=date(2026, 4, 1),
			period_to=date(2026, 6, 30),
			status=Appraisal.STATUS_DRAFT,
		)

		KRA.objects.create(
			appraisal=self.appraisal_jan_mar,
			section=KRA.SECTION_KRA,
			sl_no=1,
			title='Quality',
			description='Improve quality',
			max_mark=10,
		)
		KRA.objects.create(
			appraisal=self.appraisal_apr_jun,
			section=KRA.SECTION_KRA,
			sl_no=1,
			title='Delivery',
			description='Improve delivery',
			max_mark=10,
		)

		self.client.force_authenticate(user=self.hr_user)

	def test_appraisal_list_filters_by_period_overlap(self):
		url = reverse('api_appraisals')
		response = self.client.get(url, {'period_from': '2026-02-01', 'period_to': '2026-03-15'})

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		returned_ids = {item['id'] for item in response.data}
		self.assertSetEqual(returned_ids, {self.appraisal_jan_mar.id})

	def test_appraisal_list_without_period_filters_preserves_behavior(self):
		url = reverse('api_appraisals')
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		returned_ids = {item['id'] for item in response.data}
		self.assertSetEqual(returned_ids, {self.appraisal_jan_mar.id, self.appraisal_apr_jun.id})

	def test_invalid_period_filter_returns_400(self):
		url = reverse('api_appraisals')
		response = self.client.get(url, {'period_from': '2026-04-01', 'period_to': '2026-03-01'})

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn('period_from', response.data)

	def test_kra_list_filters_by_appraisal_period_overlap(self):
		url = reverse('api_kras')
		response = self.client.get(url, {'period_from': '2026-04-01', 'period_to': '2026-05-15'})

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		returned_kra_ids = {item['id'] for item in response.data}
		expected_kra_ids = set(
			KRA.objects.filter(appraisal=self.appraisal_apr_jun).values_list('id', flat=True)
		)
		self.assertSetEqual(returned_kra_ids, expected_kra_ids)

	def test_template_apply_is_limited_to_selected_period(self):
		url = reverse('api_kra_template')
		payload = {
			'frame_config': {'steps': {'kra_objectives': True}},
			'period_from': '2026-01-01',
			'period_to': '2026-03-31',
			'rows': [
				{
					'section': KRA.SECTION_KRA,
					'sl_no': 1,
					'max_mark': '25.00',
				}
			],
		}

		response = self.client.post(url, payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['applied_appraisal_count'], 1)
		self.assertEqual(response.data['period_from'], '2026-01-01')
		self.assertEqual(response.data['period_to'], '2026-03-31')

		self.appraisal_jan_mar.refresh_from_db()
		self.appraisal_apr_jun.refresh_from_db()

		self.assertEqual(self.appraisal_jan_mar.frame_config, {'steps': {'kra_objectives': True}})
		self.assertNotEqual(self.appraisal_apr_jun.frame_config, {'steps': {'kra_objectives': True}})

		jan_kra = KRA.objects.get(appraisal=self.appraisal_jan_mar, section=KRA.SECTION_KRA, sl_no=1)
		apr_kra = KRA.objects.get(appraisal=self.appraisal_apr_jun, section=KRA.SECTION_KRA, sl_no=1)
		self.assertEqual(str(jan_kra.max_mark), '25.00')
		self.assertEqual(str(apr_kra.max_mark), '10.00')

	def test_template_apply_does_not_update_partial_overlap_period(self):
		url = reverse('api_kra_template')
		payload = {
			'frame_config': {'steps': {'kra_objectives': True, 'competencies': False}},
			'period_from': '2026-04-01',
			'period_to': '2026-04-30',
			'rows': [
				{
					'section': KRA.SECTION_KRA,
					'sl_no': 1,
					'max_mark': '18.00',
				}
			],
		}

		previous_frame_config = self.appraisal_apr_jun.frame_config
		response = self.client.post(url, payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['applied_appraisal_count'], 0)

		self.appraisal_apr_jun.refresh_from_db()
		self.assertEqual(self.appraisal_apr_jun.frame_config, previous_frame_config)

		apr_kra = KRA.objects.get(appraisal=self.appraisal_apr_jun, section=KRA.SECTION_KRA, sl_no=1)
		self.assertEqual(str(apr_kra.max_mark), '10.00')

	def test_template_get_prefers_exact_period_match(self):
		url = reverse('api_kra_template')

		annual_payload = {
			'frame_config': {'mode': 'annual-2026'},
			'period_from': '2026-01-01',
			'period_to': '2026-12-31',
			'rows': [
				{
					'section': KRA.SECTION_KRA,
					'sl_no': 1,
					'max_mark': '30.00',
				}
			],
		}
		monthly_payload = {
			'frame_config': {'mode': 'monthly-apr-2026'},
			'period_from': '2026-04-01',
			'period_to': '2026-04-30',
			'rows': [
				{
					'section': KRA.SECTION_KRA,
					'sl_no': 1,
					'max_mark': '12.00',
				}
			],
		}

		annual_save = self.client.post(url, annual_payload, format='json')
		monthly_save = self.client.post(url, monthly_payload, format='json')
		self.assertEqual(annual_save.status_code, status.HTTP_200_OK)
		self.assertEqual(monthly_save.status_code, status.HTTP_200_OK)

		annual_get = self.client.get(url, {'period_from': '2026-01-01', 'period_to': '2026-12-31'})
		self.assertEqual(annual_get.status_code, status.HTTP_200_OK)
		self.assertEqual(annual_get.data['frame_config'], {'mode': 'annual-2026'})
		self.assertEqual(annual_get.data['period_from'], '2026-01-01')
		self.assertEqual(annual_get.data['period_to'], '2026-12-31')

		monthly_get = self.client.get(url, {'period_from': '2026-04-01', 'period_to': '2026-04-30'})
		self.assertEqual(monthly_get.status_code, status.HTTP_200_OK)
		self.assertEqual(monthly_get.data['frame_config'], {'mode': 'monthly-apr-2026'})
		self.assertEqual(monthly_get.data['period_from'], '2026-04-01')
		self.assertEqual(monthly_get.data['period_to'], '2026-04-30')

	def test_available_periods_endpoint_returns_distinct_periods(self):
		url = reverse('api_appraisal_periods')
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		returned_periods = {
			(item['period_from'].isoformat(), item['period_to'].isoformat())
			for item in response.data
		}
		self.assertSetEqual(
			returned_periods,
			{
				('2026-01-01', '2026-03-31'),
				('2026-04-01', '2026-06-30'),
			},
		)
