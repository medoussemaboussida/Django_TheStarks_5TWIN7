from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from PIL import Image
from io import BytesIO


class ImageProcessingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='p')
        self.client = APIClient()
        self.client.login(username='u', password='p')

    def _dummy_image(self, color=(255, 0, 0)):
        img = Image.new('RGB', (10, 10), color=color)
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        return SimpleUploadedFile('t.jpg', buffer.getvalue(), content_type='image/jpeg')

    def test_upload_image(self):
        url = reverse('image_upload')
        resp = self.client.post(url, {'image': self._dummy_image()}, format='multipart')
        self.assertEqual(resp.status_code, 201)
        self.assertIn('id', resp.data)

    def test_analyze_without_image(self):
        url = reverse('image_analyze')
        resp = self.client.post(url, data={})
        self.assertEqual(resp.status_code, 400)

    def test_generate_image(self):
        url = reverse('image_generate')
        resp = self.client.post(url, {'description': 'test'}, format='json')
        self.assertIn(resp.status_code, (201, 502))
