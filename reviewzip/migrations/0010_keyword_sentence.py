# Generated by Django 3.1.6 on 2021-02-05 10:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviewzip', '0009_reviewfile_create_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='keyword',
            name='sentence',
            field=models.ManyToManyField(to='reviewzip.Sentence'),
        ),
    ]