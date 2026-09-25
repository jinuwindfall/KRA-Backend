from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Employee, EmployeeMemo


class EmployeeMemoAPITests(APITestCase):
	def setUp(self):
		self.hr_user = User.objects.create_user(
			username='hruser',
			password='secret123',
			first_name='HR',
			last_name='User',
		)
		self.hr_employee = Employee.objects.create(
			user=self.hr_user,
			emp_id='HR001',
			designation='HR Manager',
			role=Employee.ROLE_HR,
		)

		self.staff_user = User.objects.create_user(
			username='staffuser',
			password='secret123',
			first_name='Staff',
			last_name='User',
		)
		self.staff_employee = Employee.objects.create(
			user=self.staff_user,
			emp_id='ST001',
			designation='Executive',
			role=Employee.ROLE_STAFF,
		)

		self.appraiser_user = User.objects.create_user(
			username='appraiseruser',
			password='secret123',
			first_name='Appraiser',
			last_name='User',
		)
		self.appraiser_employee = Employee.objects.create(
			user=self.appraiser_user,
			emp_id='AP001',
			designation='Lead',
			role=Employee.ROLE_APPRAISER,
		)

		self.client.force_authenticate(user=self.hr_user)

	def test_hr_can_create_memo_and_it_persists(self):
		url = reverse('api_employee_memos', kwargs={'pk': self.staff_employee.pk})
		payload = {'memo': 'Repeated late arrivals in March.'}

		response = self.client.post(url, payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertTrue(
			EmployeeMemo.objects.filter(
				employee=self.staff_employee,
				memo='Repeated late arrivals in March.',
				created_by=self.hr_employee,
			).exists()
		)

	def test_staff_memo_list_returns_saved_entries(self):
		EmployeeMemo.objects.create(
			employee=self.staff_employee,
			memo='Needs improvement in documentation quality.',
			created_by=self.hr_employee,
		)

		url = reverse('api_employee_memos', kwargs={'pk': self.staff_employee.pk})
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]['memo'], 'Needs improvement in documentation quality.')

	def test_cannot_add_memo_for_non_staff_employee(self):
		url = reverse('api_employee_memos', kwargs={'pk': self.appraiser_employee.pk})
		response = self.client.post(url, {'memo': 'Not allowed memo target'}, format='json')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(EmployeeMemo.objects.count(), 0)

	def test_grouped_endpoint_includes_staff_memos(self):
		EmployeeMemo.objects.create(
			employee=self.staff_employee,
			memo='Follow-up memo for Q1 review.',
			created_by=self.hr_employee,
		)

		url = reverse('api_employee_memos_grouped')
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]['id'], self.staff_employee.id)
		self.assertEqual(len(response.data[0]['memos']), 1)
		self.assertEqual(response.data[0]['memos'][0]['memo'], 'Follow-up memo for Q1 review.')

	def test_hr_can_create_memo_with_deduction(self):
		url = reverse('api_employee_memos', kwargs={'pk': self.staff_employee.pk})
		payload = {'memo': 'Unapproved leave.', 'deduction': '2.50'}

		response = self.client.post(url, payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data['deduction'], '2.50')
		memo = EmployeeMemo.objects.get(employee=self.staff_employee)
		self.assertEqual(str(memo.deduction), '2.50')

	def test_memo_deduction_must_be_non_negative(self):
		url = reverse('api_employee_memos', kwargs={'pk': self.staff_employee.pk})
		response = self.client.post(url, {'memo': 'Bad value', 'deduction': '-1'}, format='json')

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(EmployeeMemo.objects.count(), 0)

	def test_hr_can_update_memo_deduction(self):
		memo = EmployeeMemo.objects.create(
			employee=self.staff_employee,
			memo='Initial note',
			deduction='1.00',
			created_by=self.hr_employee,
		)

		url = reverse('api_employee_memo_detail', kwargs={'pk': self.staff_employee.pk, 'memo_id': memo.id})
		response = self.client.patch(url, {'deduction': '3.00'}, format='json')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		memo.refresh_from_db()
		self.assertEqual(str(memo.deduction), '3.00')

	def test_hr_can_delete_memo(self):
		memo = EmployeeMemo.objects.create(
			employee=self.staff_employee,
			memo='To be removed',
			deduction='1.00',
			created_by=self.hr_employee,
		)

		url = reverse('api_employee_memo_detail', kwargs={'pk': self.staff_employee.pk, 'memo_id': memo.id})
		response = self.client.delete(url)

		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
		self.assertFalse(EmployeeMemo.objects.filter(pk=memo.id).exists())
