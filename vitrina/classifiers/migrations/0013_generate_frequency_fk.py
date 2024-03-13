from django.db import migrations, models

frequency_dict = {
  'Kasmet': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/ANNUAL',
    'Code': 'ANNUAL',
    'hours': 8760,
    'title_en': 'Once a year',
    'current_values': [
      'Kasmet',
      'Kartą per metus',
      'kartą per metus',
      'Kas metus',
      'Metinis',
      'kasmet',
      'kas metus',
      'Vieną kartą per metus',
      'Kas metai',
      '1 metai',
      'Atnaujinama kiekvienais metais',
      'Duomenys atnaujinami kasmet',
      'Metai',
      'kartą į metus',
      '"Kas metus, pagal poreikį"',
      '1 karta per metus',
      'ne rečiau kaip kartą per metus',
      '"Pagal poreikį, archyve sugrupavimas pagal metus"',
      'kiekvienų metų vasario 15 d.',
      'Kiekvienais metais',
      'Teikiami kasmetiniai duomenys',
      'Kasmet.',
      'kas metai',
      'Kartą į metus',
      'Duomenys formuojami už kiekvienus metus',
      'kartą metuose – sausio 30 d.',
      '"Kas metus, sugrupavimas pagal metus"',
      '"metinis, ketvirtinis"',
      '"Kas metus, kas ketvirtį, pagal poreikį"'
    ]
  },
  'Dukart per metus': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/ANNUAL_2',
    'Code': 'ANNUAL_2',
    'hours': 4380,
    'title_en': 'Twice a year',
    'current_values': [
      'Dukart per metus',
      'Kartą per pusmetį',
      'Kas pusmetį',
      'kas 6 mėn.',
      'du kartus metuose – sausio 30 d. ir liepos 30 d.',
      'Du kartus per metus (kovą-balandį)',
      'Pusmetinis',
      'kas pusmetį',
      '2 kartus per metus',
      'Du kartus per metus'
    ]
  },
  'Triskart per metus': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/ANNUAL_3',
    'Code': 'ANNUAL_3',
    'hours': 2920,
    'title_en': 'Three times a year',
    'current_values': [
      'Triskart per metus'
    ]
  },
  'Kas 20 metų': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/BIDECENNIAL',
    'Code': 'BIDECENNIAL',
    'hours': 175200,
    'title_en': 'Every twenty years',
    'current_values': []
  },
  'Kas 2 metai': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/BIENNIAL',
    'Code': 'BIENNIAL',
    'hours': 17520,
    'title_en': 'Every twenty years',
    'current_values': [
      'Kas 2 metai',
      '"nupirkus paslaugas iš naujų tiekėjų, kas keli metai"'
    ]
  },
  'Kas 2 valandas': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/BIHOURLY',
    'Code': 'BIHOURLY',
    'hours': 2,
    'title_en': 'Every two hours',
    'current_values': []
  },
  'Kas 2 mėnesiai': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/BIMONTHLY',
    'Code': 'BIMONTHLY',
    'hours': 1440,
    'title_en': 'Every two months',
    'current_values': [
      'Kas 2 mėnesiai'
    ]
  },
  'Kas 2 savaitės': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/BIWEEKLY',
    'Code': 'BIWEEKLY',
    'hours': 336,
    'title_en': 'Every two weeks',
    'current_values': []
  },
  'Dažniau nei kasdien': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/CONT',
    'Code': 'CONT',
    'hours': 13,
    'title_en': 'More frequent than daily',
    'current_values': [
      'Dažniau nei kasdien'
    ]
  },
  'Kasdien': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/DAILY',
    'Code': 'DAILY',
    'hours': 24,
    'title_en': 'Once a day',
    'current_values': [
      'Kasdien',
      'Kiekvieną darbo dieną',
      'Kiekvieną dieną',
      'kasdien',
      '1 k. / 24 val.',
      '"kas kart įregistravus (išregistravus) registro objektą, įrašius duomenų pakeitimus. Statistiniai duomenys atnaujinami 1 kartą / d. d."',
      'kiekvieną dieną',
      'darbo dienomis',
      'Duomenys atnaujinami kiekvieną dieną 00.00 val',
      'Kartą į parą',
      'Kasdieną',
      '"kasdien, reliame laike"',
      'Kas dieną',
      '"dieninė, savaitinė"',
      '1/24 val.',
      '"Kasdien, nuolat."',
      '"Kasdien, realiu laiku"',
      '24 valandos',
      'Duomenys atnaujinami kasdien',
      '1/24 val',
      'kas 24 valandos'
    ]
  },
  'Dukart per dieną': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/DAILY_2',
    'Code': 'DAILY_2',
    'hours': 12,
    'title_en': 'Twice a day',
    'current_values': []
  },
  'Kas 10 metų': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/DECENNIAL',
    'Code': 'DECENNIAL',
    'hours': 87600,
    'title_en': 'Every ten years',
    'current_values': [
      'Kas 10 metų',
      'kas 6 metai'
    ]
  },
  'Kas valandą': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/HOURLY',
    'Code': 'HOURLY',
    'hours': 1,
    'title_en': 'Every hour',
    'current_values': [
      'Kas 15 minučių',
      'kas valandą',
      'Kas valandą'
    ]
  },
  'Nevienodu periodiškumu': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/IRREG',
    'Code': 'IRREG',
    'hours': 0,
    'title_en': 'At uneven intervals',
    'current_values': [
      'Nevienodu periodiškumu',
      'Periodiškai atnaujinamas'
    ]
  },
  'Kas mėnesį': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/MONTHLY',
    'Code': 'MONTHLY',
    'hours': 720,
    'title_en': 'Once a month',
    'current_values': [
      'Kas mėnesį',
      'kas mėnesį',
      'Kartą per mėnesį',
      'Mėnuo',
      '"Kas mėnesį, kas ketvirtį"',
      '1 k. / mėn.',
      'Kas mėnesį.',
      'atnaujinamas atsiradus naujiems duomenims kas mėnesį',
      '"kiekvieno mėnesio 1 d., kas pusmetį"',
      '"kas mėnesį, iki 20d."',
      'kievieną mėnesį',
      '"Kartą per mėnesį, atsiradus naujiems duomenims"',
      'mėnuo/ ketviris/ metai',
      '"PVM ir akcizo mokesčio - kas mėnesį, Pelno - kartą metuose."',
      'Vieną kartą per mėnesį',
      'kiekvieno mėnesio 11 d.'
    ]
  },
  'Dukart per mėnesį': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/MONTHLY_2',
    'Code': 'MONTHLY_2',
    'hours': 360,
    'title_en': 'Twice a month',
    'current_values': [
      'Dukart per mėnesį',
      '2-3 kartus per mėnesį',
      'per 10 d.d. nuo sprendimo priėmimo'
    ]
  },
  'Triskart per mėnesį': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/MONTHLY_3',
    'Code': 'MONTHLY_3',
    'hours': 240,
    'title_en': 'Three times a month',
    'current_values': []
  },
  'Neatnaujinamas': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/NEVER',
    'Code': 'NEVER',
    'hours': 0,
    'title_en': 'Never updated',
    'current_values': [
      'Neatnaujinamas',
      'neatnaujinamas',
      'neatnaujinama',
      '"Nebus atnaujinama, funkcijas perėmė VSDFV"',
      'Neatnaujinami',
      '"Nekaupiama, pasikeitė reglamentavimas"',
      '"Neatnaujinama, neteko galios (Įmonių bankroto įstatymo pakeitimas įsigaliojo nuo 2016-01-01)"',
      'Duomenys neatnaujinami',
      'Neatnaujinama',
      '"Nebus atnaujinama, nes Garantinio fondo administravimo funkcijas nuo 2017-01-01 perėmė VSDFV"',

    ]
  },
  'Neapibrėžtu periodiškumu': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/OTHER',
    'Code': 'OTHER',
    'hours': 0,
    'title_en': 'With unknown regularity',
    'current_values': [
      'Neapibrėžtu periodiškumu'
    ]
  },
  'Kas 4 metai': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/QUADRENNIAL',
    'Code': 'QUADRENNIAL',
    'hours': 35040,
    'title_en': 'Every four years',
    'current_values': [
      'Kas 4 metai',
      'Atnaujinama kas 4 metai',
      'kas 4 metai',
      'kas ketveri metai'
    ]
  },
  'Kas 3 mėnesiai': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/QUARTERLY',
    'Code': 'QUARTERLY',
    'hours': 2160,
    'title_en': 'Every three months',
    'current_values': [
      'Kas ketvirtį',
      'Kas 3 mėnesiai',
      'Kartą per ketvirtį',
      'kas ketvirtį',
      'ketv.',
      'ketvirtis',
      'kartą per ketvirtį',
      'ketvirtis/metai',
      'Kas ketvertį',
      '"Kartą per ketvirtį, didėjančiai nuo metų pradžios"',
      '4 kartus per metus',
      'duomenys atnaujinami kas ketvirtį',
      'Kas trys mėnesiai',
      'Duomenys atnaujinami kiekvieną ketvirtį',
      '3 mėnesiai',
      '"I ketv, pusm., metai"'
    ]
  },
  'Kas 5 metai': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/QUINQUENNIAL',
    'Code': 'QUINQUENNIAL',
    'hours': 43800,
    'title_en': 'Every five years',
    'current_values': [
      'Kas 5 metai',
      'Kas 5 metus',
      'kas 5 metai'
    ]
  },
  'Kas 30 metų': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/TRIDECENNIAL',
    'Code': 'TRIDECENNIAL',
    'hours': 262800,
    'title_en': 'Every thirty years',
    'current_values': []
  },
  'Kas 3 metai': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/TRIENNIAL',
    'Code': 'TRIENNIAL',
    'hours': 26280,
    'title_en': 'Every three years',
    'current_values': [
      'Kas 3 metai'
    ]
  },
  'Kas 3 valandos': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/TRIHOURLY',
    'Code': 'TRIHOURLY',
    'hours': 3,
    'title_en': 'Every three hours',
    'current_values': [
      'Kas 3 valandos'
    ]
  },
  'Nežinomas': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/UNKNOWN',
    'Code': 'UNKNOWN',
    'hours': 0,
    'title_en': 'Unknown interval',
    'current_values': [
      '',
      '-'
    ]
  },
  'Nepertraukiamas': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/UPDATE_CONT',
    'Code': 'UPDATE_CONT',
    'hours': 8760,
    'title_en': 'Without interruption',
    'current_values': [
      'nuolat',
      'Nuolat',
      'Nuolat.',
      '"Kasdien, realiame laike"',
      'realiame laike',
      'Pagal faktą',
      'Nepertraukiamas',
      'Pastovus',
      '"Nuolat, sugrupavimas pagal metus"',
      'Salių užimtumas atnaujinamas realiu laiku',
      'Realiu laiku',
      'Nuolatos',
      '"neatidėliojant, esant pokyčiams ir papildymams"',
      'realiuoju laiku',
      '"kas kartą, atsiradus pakeitimams sąraše"',
      'nuolatinis',
      'veikia realiu laiku',
      'pasikeitus duomenims',
      'Atnaujinami kai pasikeičia įmonių duomenys.',
      '"Pagal poreikį, pasikeitus duomenims."',
      'Priklauso nuo įvykių dažnumo',
      'Atnaujinimai vyksta nuolat',
      '"nereguliarus, esant pokyčiams"',
      'Duomenys nuolat atnaujinami',
      'Pasikeitus informacijai'
    ]
  },
  'Kas savaitę': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/WEEKLY',
    'Code': 'WEEKLY',
    'hours': 168,
    'title_en': 'Once a week',
    'current_values': [
      'Kas savaitę',
      '"Pasikeitus duomenims, kartą per savaitę"',
      'Atnaujinama kiekvieną savaitę',
      'kartą per savaitę',
      '"Ne rečiau, nei kartą per savaitę"',
      'kas savaitę',
      '"kas savaitę, pagal poreikį"',
      'Savaitinė ir ketvirtinė statistika',
      'per 5 darbo dienas nuo sprendimo priėmimo',
      'Ne rečiau nei kartą per savaitę',
      'pagal poreikį (esant pokyčiams) per 5 darbo dienas.',
      '"savaitė, mėnuo, ketvirtis, pusmetis, metai"',
      'per 7 d. nuo sprendimo priėmimo',
      'duomenys paskelbiami per 5 d. nuo sprendimo priėmimo'
    ]
  },
  'Dukart per savaitę': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/WEEKLY_2',
    'Code': 'WEEKLY_2',
    'hours': 84,
    'title_en': 'Twice a week',
    'current_values': [
      '"esant pokyčiams, per 3 d.d."',
      'Duomenys atnaujinami du kartus per savaitę',
      'Per 3 darbo dienas po radiacinės saugos reikalavimų atitikties nustatymo',
      'Informacija paskelbiama ne vėliau kaip per 3 darbo dienas nuo sprendimo priėmimo',
      'kas 3 dienas'
    ]
  },
  'Triskart per savaitę': {
    'URI': 'http://publications.europa.eu/resource/authority/frequency/WEEKLY_3',
    'Code': 'WEEKLY_3',
    'hours': 56,
    'title_en': 'Three times a week',
    'current_values': [
      'kas 2 dienas',
      'Vidutiniškai kas 2 darbo dienas'
    ]
  },
}


def generate_frequency_fk_for_datasets(apps, schema_editor):
    Frequency = apps.get_model("vitrina_classifiers", "Frequency")
    Dataset = apps.get_model("vitrina_datasets", "Dataset")

    for title, data in frequency_dict.items():
        Frequency.objects.update_or_create(
            title=title,
            defaults={
              'uri': data['URI'],
              'code': data['Code'],
              'hours': data['hours'],
              'title_en': data['title_en']
            }
        )

    Frequency.objects.exclude(title__in=frequency_dict.keys()).delete()

    for dataset in Dataset.objects.filter(frequency__isnull=True):
        frequency_title = 'Nežinomas'
        for title, data in frequency_dict.items():
            if dataset.update_frequency in data['current_values']:
                frequency_title = title
                break
        frequency = Frequency.objects.get(title=frequency_title)
        dataset.frequency = frequency
        dataset.save(update_fields=['frequency'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_datasets', '0022_auto_20231110_1704'),
        ('vitrina_classifiers', '0012_auto_20230619_1315'),
    ]

    operations = [
        migrations.AddField(
            model_name='frequency',
            name='code',
            field=models.CharField(unique=True, max_length=255, verbose_name='Kodas', null=True, blank=True),
        ),
        migrations.AlterField(
          model_name='frequency',
          name='hours',
          field=models.IntegerField(blank=True, null=True, verbose_name='Valandos'),
        ),
        migrations.RunPython(generate_frequency_fk_for_datasets),
    ]
