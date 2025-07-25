# Generated by Django 5.0 on 2024-08-17 17:54

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Utility',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('thames_water', 'Thames Water'), ('severn_trent_water', 'Severn Trent Water')], db_index=True, max_length=255)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['pk'],
            },
        ),
        migrations.CreateModel(
            name='DMA',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(db_index=True, max_length=50)),
                ('name', models.CharField(max_length=255)),
                ('network_repr', models.JSONField(null=True)),
                ('geometry', django.contrib.gis.db.models.fields.MultiPolygonField(srid=27700)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('utility', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='utility_dmas', to='utilities.utility')),
            ],
            options={
                'ordering': ['pk'],
                'unique_together': {('utility', 'code')},
            },
        ),
    ]
