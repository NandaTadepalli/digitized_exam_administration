from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0001_initial'),  # Replace with your latest migration name
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE exam_slot DROP INDEX uq_exam_slot_time;",
            reverse_sql="ALTER TABLE exam_slot ADD UNIQUE INDEX uq_exam_slot_time (exam_date, start_time, end_time, slot_code);"
        ),
    ]
