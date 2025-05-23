# Generated by Django 5.1.7 on 2025-03-22 15:13

import datetime
import django.db.models.deletion
import django.db.models.expressions
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quotes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('company', models.CharField(blank=True, max_length=100)),
                ('address', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('default_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('unit_type', models.CharField(choices=[('ft', 'Linear Feet'), ('sqft', 'Square Feet'), ('hour', 'Hour'), ('item', 'Per Item')], max_length=20)),
                ('active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Quote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='Line Striping Quote', max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(default=datetime.datetime(2025, 4, 21, 15, 13, 40, 60727, tzinfo=datetime.timezone.utc))),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('sent', 'Sent to Client'), ('viewed', 'Viewed by Client'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('expired', 'Expired')], default='draft', max_length=20)),
                ('time_period', models.CharField(choices=[('standard', '8am-5pm (Standard)'), ('evening', '5pm-2am (Evening Rate, +$500)'), ('weekend', 'Weekend/Holiday (+$700)')], default='standard', max_length=20)),
                ('evening_fee', models.DecimalField(decimal_places=2, default=500.0, max_digits=10)),
                ('weekend_fee', models.DecimalField(decimal_places=2, default=700.0, max_digits=10)),
                ('number_of_days', models.IntegerField(default=1)),
                ('discount_percentage', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('access_token', models.CharField(editable=False, max_length=32, unique=True)),
                ('verification_code', models.CharField(editable=False, max_length=6)),
                ('notes', models.TextField(blank=True)),
                ('job_location', models.TextField(blank=True)),
                ('expected_completion_date', models.DateField(blank=True, null=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quotes', to='quotes.client')),
            ],
        ),
        migrations.CreateModel(
            name='QuoteItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=10)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_price', models.GeneratedField(db_persist=True, expression=django.db.models.expressions.CombinedExpression(models.F('quantity'), '*', models.F('unit_price')), output_field=models.DecimalField(decimal_places=2, max_digits=10))),
                ('notes', models.TextField(blank=True)),
                ('quote', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='quotes.quote')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='quotes.service')),
            ],
        ),
    ]
