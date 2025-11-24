# Generated migration for seat selection feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ve',
            name='vi_tri_ghe',
            field=models.JSONField(
                default=list,
                blank=True,
                help_text='Danh sách vị trí ghế đã chọn, ví dụ: ["A1", "A2", "B3"]',
                verbose_name='Vị trí ghế'
            ),
        ),
    ]
