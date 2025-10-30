import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
user, created = User.objects.get_or_create(
    username='admin', defaults={'email': 'admin@gmail.com'}
)
user.email = 'admin@gmail.com'
user.is_staff = True
user.is_superuser = True
user.set_password('Password123')
user.save()
print('Created' if created else 'Updated')
