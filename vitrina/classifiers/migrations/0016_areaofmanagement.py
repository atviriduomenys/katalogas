from django.db import migrations, models


def populate_area_of_management(apps, schema_editor):
    AreaOfManagement = apps.get_model("vitrina_classifiers", "AreaOfManagement")
    initial_data = [
        (1, "Nepriskirta", "Unassigned"),
        (
            2,
            "Lietuvos Respublikos ekonomikos ir inovacijų ministerija",
            "Ministry of the Economy and Innovation of the Republic of Lithuania",
        ),
        (
            3,
            "Lietuvos Respublikos energetikos ministerija",
            "Ministry of Energy of the Republic of Lithuania",
        ),
        (
            4,
            "Lietuvos Respublikos finansų ministerija",
            "Ministry of Finance of the Republic of Lithuania",
        ),
        (
            5,
            "Lietuvos Respublikos krašto apsaugos ministerija",
            "Ministry of National Defence of the Republic of Lithuania",
        ),
        (
            6,
            "Lietuvos Respublikos kultūros ministerija",
            "Ministry of Culture of the Republic of Lithuania",
        ),
        (
            7,
            "Lietuvos Respublikos socialinės apsaugos ir darbo ministerija",
            "Ministry of Social Security and Labour of the Republic of Lithuania",
        ),
        (
            8,
            "Lietuvos Respublikos susisiekimo ministerija",
            "Ministry of Transport and Communications of the Republic of Lithuania",
        ),
        (
            9,
            "Lietuvos Respublikos sveikatos apsaugos ministerija",
            "Ministry of Health of the Republic of Lithuania",
        ),
        (
            10,
            "Lietuvos Respublikos švietimo, mokslo ir sporto ministerija",
            "Ministry of Education, Science and Sport of the Republic of Lithuania",
        ),
        (
            11,
            "Lietuvos Respublikos teisingumo ministerija",
            "Ministry of Justice of the Republic of Lithuania",
        ),
        (
            12,
            "Lietuvos Respublikos užsienio reikalų ministerija",
            "Ministry of Foreign Affairs of the Republic of Lithuania",
        ),
        (
            13,
            "Lietuvos Respublikos vidaus reikalų ministerija",
            "Ministry of the Interior of the Republic of Lithuania",
        ),
        (
            14,
            "Lietuvos Respublikos žemės ūkio ministerija",
            "Ministry of Agriculture of the Republic of Lithuania",
        ),
        (15, "Savivaldybės", "Municipalities"),
        (
            16,
            "Vyriausybei atsakingos institucijos",
            "Government Accountable Institutions",
        ),
        (
            17,
            "Prezidentūrai atsakingos institucijos",
            "Institutions Accountable to the Office of the President",
        ),
        (
            18,
            "Seimui atsakingos institucijos",
            "Institutions Accountable to the Office of the Seimas",
        ),
        (19, "Verslas", "Business Sector"),
        (20, "Lietuvos Aukščiausiasis Teismas", "Supreme Court of Lithuania"),
        (21, "Nevyriausybinės organizacijos", "Non-Governmental Organizations"),
        (
            22,
            "Lietuvos Respublikos aplinkos ministerija",
            "Ministry of Environment of the Republic of Lithuania",
        ),
    ]
    for id, name_lt, name_en in initial_data:
        AreaOfManagement.objects.create(id=id, name_lt=name_lt, name_en=name_en)


class Migration(migrations.Migration):
    dependencies = [
        ("vitrina_classifiers", "0014_merge_20231114_0754"),
    ]

    operations = [
        migrations.CreateModel(
            name="AreaOfManagement",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("name_lt", models.CharField(max_length=255, verbose_name="Name LT")),
                ("name_en", models.CharField(max_length=255, verbose_name="Name EN")),
            ],
            options={
                "verbose_name": "Area of Management",
                "verbose_name_plural": "Areas of Management",
                "db_table": "area_of_management",
            },
        ),
        migrations.RunPython(populate_area_of_management),
    ]
