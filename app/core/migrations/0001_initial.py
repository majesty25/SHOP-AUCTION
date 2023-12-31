# Generated by Django 3.1.7 on 2023-10-23 22:58

import core.models
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('email', models.EmailField(max_length=255, unique=True)),
                ('name', models.CharField(max_length=255, validators=[django.core.validators.MinLengthValidator(3)])),
                ('is_active', models.BooleanField(default=True)),
                ('image', models.ImageField(null=True, upload_to=core.models.user_image_file_path)),
                ('is_supplier', models.BooleanField(default=False)),
                ('is_staff', models.BooleanField(default=False)),
                ('ref_code', models.IntegerField(default=0)),
                ('ref_source', models.IntegerField(default=0)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, core.models.ResizeImageMixin),
        ),
        migrations.CreateModel(
            name='PasswordReset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reset_request', models.BooleanField(default=False)),
                ('verified_request', models.BooleanField(default=False)),
                ('validation_code', models.CharField(blank=True, max_length=255)),
                ('reset_time', models.DateTimeField()),
                ('user', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='password_reset', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
