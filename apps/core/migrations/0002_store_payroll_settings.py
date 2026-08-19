from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="store",
            name="auto_payroll_close_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="store",
            name="payroll_pay_day",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Day of the following month used as the payroll payment date.",
                null=True,
                validators=[MinValueValidator(1), MaxValueValidator(28)],
            ),
        ),
    ]