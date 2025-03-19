from django.db import migrations, models, transaction

import django.db.models.deletion
import parler.fields
import parler.models

HVD_CATEGORIES = [
    {
        "name": "Meteorological",
        "definition": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 3",
        "uri": "http://data.europa.eu/bna/c_164e0bf5",
        "translations": {
            "en": {
                "title": "Meteorological",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 3",
            },
            "lt": {
                "title": "Meteorologiniai duomenys",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 3",
            },
        },
    },
    {
        "name": "Companies and company ownership",
        "definition": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 5",
        "uri": "http://data.europa.eu/bna/c_a9135398",
        "translations": {
            "en": {
                "title": "Companies and company ownership",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 5",
            },
            "lt": {
                "title": "Bendrovių ir bendrovių valdymo nuosavybės teise duomenys",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 5",
            },
        },
    },
    {
        "name": "Geospatial",
        "definition": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 1",
        "uri": "http://data.europa.eu/bna/c_ac64a52d",
        "translations": {
            "en": {
                "title": "Geospatial",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 1",
            },
            "lt": {
                "title": "Geoerdviniai duomenys",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 1",
            },
        },
    },
    {
        "name": "Mobility",
        "definition": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 6",
        "uri": "http://data.europa.eu/bna/c_b79e35eb",
        "translations": {
            "en": {
                "title": "Mobility",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 6",
            },
            "lt": {
                "title": "Judumo duomenys",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 6",
            },
        },
    },
    {
        "name": "Earth observation and environment",
        "definition": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 2",
        "uri": "http://data.europa.eu/bna/c_dd313021",
        "translations": {
            "en": {
                "title": "Earth observation and environment",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 2",
            },
            "lt": {
                "title": "Žemės stebėjimo ir aplinkos duomenys	",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 2",
            },
        },
    },
    {
        "name": "Statistics",
        "definition": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 4",
        "uri": "http://data.europa.eu/bna/c_e1da4e07",
        "translations": {
            "en": {
                "title": "Statistics",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 4",
            },
            "lt": {
                "title": "Statistika",
                "description": "data sets as described in Commission Implementing Regulation (EU) 2023/138 of 21 December 2022 laying down a list of specific high-value datasets and the arrangements for their publication and re-use, Annex, Section 4",
            },
        },
    },
]


DATASET_TYPES = [
    {
        "code": "CODE_LIST",
        "label": "Code list",
        "definition": "A code list is a complete set of data element values of a coded simple data element.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/CODE_LIST",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Code list",
                "description": "A code list is a complete set of data element values of a coded simple data element.",
            },
            "lt": {
                "title": "Kodų sąrašas",
                "description": "Kodų sąrašas yra pilnas užkoduoto paprasto duomenų elemento reikšmių rinkinys.",
            },
        },
    },
    {
        "code": "CORE_COMP",
        "label": "Core component",
        "definition": "A core component is a context-free semantic building block for creating clear and meaningful data models, vocabularies and information exchange packages.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/CORE_COMP",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Core component",
                "description": "A core component is a context-free semantic building block for creating clear and meaningful data models, vocabularies and information exchange packages.",
            },
            "lt": {
                "title": "Pagrindinis komponentas",
                "description": "Pagrindinis komponentas yra nuo konteksto nepriklausomas semantinis blokas, skirtas kurti aiškius ir prasmingas duomenų modelius, žodynus ir informacijos mainų paketus.",
            },
        },
    },
    {
        "code": "DOMAIN_MODEL",
        "label": "Domain model",
        "definition": "A domain model is a conceptual view of a system or an information exchange that identifies the entities involved and their relationships.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/DOMAIN_MODEL",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Domain model",
                "description": "A domain model is a conceptual view of a system or an information exchange that identifies the entities involved and their relationships.",
            },
            "lt": {
                "title": "Domeno modelis",
                "description": "Domeno modelis yra konceptuali sistemos ar informacijos mainų peržiūra, kuri identifikuoja susijusius objektus ir jų ryšius.",
            },
        },
    },
    {
        "code": "IEPD",
        "label": "Information exchange package description",
        "definition": "An information exchange package (IEP) description is a collection of artefacts that define and describe the structure and content of an IEP. An Information Exchange Package Documentation has a specific information exchange context and may refer to other semantic assets.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/IEPD",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Information exchange package description",
                "description": "An information exchange package (IEP) description is a collection of artefacts that define and describe the structure and content of an IEP. An Information Exchange Package Documentation has a specific information exchange context and may refer to other semantic assets.",
            },
            "lt": {
                "title": "Informacijos mainų paketo aprašas",
                "description": "Informacijos mainų paketo (IMP) aprašas yra artefaktų rinkinys, apibrėžiantis ir aprašantis IMP struktūrą ir turinį. Informacijos mainų paketo dokumentacija turi specifinį informacijos mainų kontekstą ir gali nurodyti į kitus semantinius išteklius.",
            },
        },
    },
    {
        "code": "MAPPING",
        "label": "Mapping",
        "definition": "A mapping is a relationship between a concept in one vocabulary and one or more concepts in another.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/MAPPING",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Mapping",
                "description": "A mapping is a relationship between a concept in one vocabulary and one or more concepts in another.",
            },
            "lt": {
                "title": "Priskyrimas",
                "description": "Priskyrimas yra ryšys tarp sąvokos viename žodyne ir vienos ar kelių sąvokų kitame.",
            },
        },
    },
    {
        "code": "NAL",
        "label": "Name authority list",
        "definition": "A name authority list is a controlled vocabulary for use in naming particular entities consistently.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/NAL",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Name authority list",
                "description": "A name authority list is a controlled vocabulary for use in naming particular entities consistently.",
            },
            "lt": {
                "title": "Institucijų pavadinimų sąrašas",
                "description": "Institucijų pavadinimų sąrašas yra kontroliuojamas žodynas, skirtas nuosekliam tam tikrų objektų įvardijimui.",
            },
        },
    },
    {
        "code": "ONTOLOGY",
        "label": "Ontology",
        "definition": "An ontology is a formal, explicit specification of a shared conceptualisation.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/ONTOLOGY",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Ontology",
                "description": "An ontology is a formal, explicit specification of a shared conceptualisation.",
            },
            "lt": {
                "title": "Ontologija",
                "description": "Ontologija yra formalus, aiškus bendros konceptualizacijos aprašymas.",
            },
        },
    },
    {
        "code": "SCHEMA",
        "label": "Schema",
        "definition": "A schema is a concrete view on a system or information exchange, describing the structure, content and semantics of data.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/SCHEMA",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Schema",
                "description": "A schema is a concrete view on a system or information exchange, describing the structure, content and semantics of data.",
            },
            "lt": {
                "title": "Schema",
                "description": "Schema yra konkretus sistemos ar informacijos mainų vaizdas, aprašantis duomenų struktūrą, turinį ir semantiką.",
            },
        },
    },
    {
        "code": "DSCRP_SERV",
        "label": "Service description",
        "definition": "A service description is a set of documents that describe the interface to and semantics of a service.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/DSCRP_SERV",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Service description",
                "description": "A service description is a set of documents that describe the interface to and semantics of a service.",
            },
            "lt": {
                "title": "Paslaugos aprašas",
                "description": "Paslaugos aprašas yra dokumentų rinkinys, apibūdinantis paslaugos sąsają ir semantiką.",
            },
        },
    },
    {
        "code": "STATISTICAL",
        "label": "Statistical data",
        "definition": "Statistical data is data which holds information that is of a statistical nature.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/STATISTICAL",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Statistical data",
                "description": "Statistical data is data which holds information that is of a statistical nature.",
            },
            "lt": {
                "title": "Statistika",
                "description": "Statistiniai duomenys yra duomenys, kuriuose saugoma statistinio pobūdžio informacija.",
            },
        },
    },
    {
        "code": "SYNTAX_ECD_SCHEME",
        "label": "Syntax encoding scheme",
        "definition": 'Syntax Encoding Schemes indicate that the value is a string formatted in accordance with a formal notation, such as "2000-01-01" as the standard expression of a date.',
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/SYNTAX_ECD_SCHEME",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Syntax encoding scheme",
                "description": 'Syntax Encoding Schemes indicate that the value is a string formatted in accordance with a formal notation, such as "2000-01-01" as the standard expression of a date.',
            },
            "lt": {
                "title": "Sintaksės kodavimo schema",
                "description": 'Sintaksės kodavimo schemos nurodo, kad reikšmė yra tekstinė eilutė, suformatuota pagal formalų žymėjimą, pavyzdžiui, "2000-01-01" kaip standartinė datos išraiška.',
            },
        },
    },
    {
        "code": "TAXONOMY",
        "label": "Taxonomy",
        "definition": "A taxonomy is a scheme of categories and subcategories that can be used to sort and otherwise organise items of knowledge or information.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/TAXONOMY",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Taxonomy",
                "description": "A taxonomy is a scheme of categories and subcategories that can be used to sort and otherwise organise items of knowledge or information.",
            },
            "lt": {
                "title": "Sistematika",
                "description": "Sistematika yra kategorijų ir subkategorijų schema, kuri gali būti naudojama rūšiuoti ir kitaip organizuoti žinių ar informacijos elementus.",
            },
        },
    },
    {
        "code": "THESAURUS",
        "label": "Thesaurus",
        "definition": "A thesaurus is a controlled and structured vocabulary in which concepts are represented by terms, organised so that relationships between concepts are made explicit, and preferred terms are accompanied by lead-in entries for synonyms or quasi-synonyms.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/THESAURUS",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Thesaurus",
                "description": "A thesaurus is a controlled and structured vocabulary in which concepts are represented by terms, organised so that relationships between concepts are made explicit, and preferred terms are accompanied by lead-in entries for synonyms or quasi-synonyms.",
            },
            "lt": {
                "title": "Tezauras",
                "description": "Tezauras yra kontroliuojamas ir struktūruotas žodynas, kuriame sąvokos išreiškiamos terminais, organizuotais taip, kad būtų aiškūs ryšiai tarp sąvokų, o pageidaujami terminai papildyti įvadiniais sinonimų ar kvazi-sinonimų įrašais.",
            },
        },
    },
    {
        "code": "APROF",
        "label": "Application profile",
        "definition": "An application profile is a profile which specifies and describes the metadata used in a particular application.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/APROF",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Application profile",
                "description": "An application profile is a profile which specifies and describes the metadata used in a particular application.",
            },
            "lt": {
                "title": "Programos profilis",
                "description": "Programos profilis yra profilis, kuris nurodo ir aprašo konkrečioje programoje naudojamus metaduomenis.",
            },
        },
    },
    {
        "code": "STYLES",
        "label": "Style sheets",
        "definition": "Style sheets are a set of rules which describes the presentation of a document written in a markup language.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/STYLES",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Style sheets",
                "description": "Style sheets are a set of rules which describes the presentation of a document written in a markup language.",
            },
            "lt": {
                "title": "Stilių aprašai",
                "description": "Stilių aprašai yra taisyklių rinkinys, aprašantis žymėjimo kalba parašyto dokumento pateikimą.",
            },
        },
    },
    {
        "code": "ATTO_LEX",
        "label": "ATTO table – EUR-Lex domain",
        "definition": "Table of EUR-Lex domain in ATTO, internal translation manager application of the Publications Office of the European Union.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/ATTO_LEX",
        "is_used": False,
        "translations": {
            "en": {
                "title": "ATTO table – EUR-Lex domain",
                "description": "Table of EUR-Lex domain in ATTO, internal translation manager application of the Publications Office of the European Union.",
            },
            "lt": {
                "title": 'ATTO lentelė – „EUR-Lex" sritis',
                "description": "EUR-Lex srities lentelė ATTO sistemoje, Europos Sąjungos leidinių biuro vidinėje vertimų valdymo programoje.",
            },
        },
    },
    {
        "code": "ATTO_PUB",
        "label": "ATTO table – Publications domain",
        "definition": "Table of Publications domain in ATTO, internal translation manager application of the Publications Office of the European Union.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/ATTO_PUB",
        "is_used": False,
        "translations": {
            "en": {
                "title": "ATTO table – Publications domain",
                "description": "Table of Publications domain in ATTO, internal translation manager application of the Publications Office of the European Union.",
            },
            "lt": {
                "title": "ATTO lentelė – leidinių sritis",
                "description": "Leidinių srities lentelė ATTO sistemoje, Europos Sąjungos leidinių biuro vidinėje vertimų valdymo programoje.",
            },
        },
    },
    {
        "code": "GEOSPATIAL",
        "label": "Geospatial data",
        "definition": "Geospatial data is data that has explicit geographic positioning information included within it in either vector or raster format.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/GEOSPATIAL",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Geospatial data",
                "description": "Geospatial data is data that has explicit geographic positioning information included within it in either vector or raster format.",
            },
            "lt": {
                "title": "Geoerdviniai duomenys",
                "description": "Geoerdviniai duomenys yra duomenys, kuriuose yra aiški geografinė padėties informacija vektoriniu arba rasteriniu formatu.",
            },
        },
    },
    {
        "code": "TEST_DATA",
        "label": "Test data",
        "definition": "Test data is data which is created for use in tests, which should be syntactically correct but which may not necessarily represent any real-world phenomena, e.g. datasets with 'dummy data', typically used in system integration.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/TEST_DATA",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Test data",
                "description": "Test data is data which is created for use in tests, which should be syntactically correct but which may not necessarily represent any real-world phenomena, e.g. datasets with 'dummy data', typically used in system integration.",
            },
            "lt": {
                "title": "Bandymo duomenys",
                "description": 'Bandymo duomenys yra duomenys, sukurti naudoti bandymuose, kurie turėtų būti sintaksiškai teisingi, bet nebūtinai atspindi realius reiškinius, pvz., duomenų rinkiniai su „netikrais duomenimis", paprastai naudojami sistemų integracijai.',
            },
        },
    },
    {
        "code": "SYNTHETIC_DATA",
        "label": "Synthetic data",
        "definition": "Synthetic data is data which is (artificially) created entirely or partially for use in tests, and to meet specific needs or conditions in the real-world that (existing) real-world data may not represent, e.g. anonymised datasets, typically used for proof of concept or simulation.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/SYNTHETIC_DATA",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Synthetic data",
                "description": "Synthetic data is data which is (artificially) created entirely or partially for use in tests, and to meet specific needs or conditions in the real-world that (existing) real-world data may not represent, e.g. anonymised datasets, typically used for proof of concept or simulation.",
            },
            "lt": {
                "title": "Dirbtiniai duomenys",
                "description": "Dirbtiniai duomenys yra visiškai arba iš dalies (dirbtinai) sukurti duomenys, skirti naudoti bandymuose ir patenkinti specifines realaus pasaulio reikmes ar sąlygas, kurių esami realaus pasaulio duomenys gali neatspindėti, pvz., anonimizuoti duomenų rinkiniai, paprastai naudojami koncepcijos įrodymui ar simuliacijai.",
            },
        },
    },
    {
        "code": "GLOSSARY",
        "label": "Glossary",
        "definition": "A glossary is a simple list of terms and their definitions. A glossary focuses on creating a complete list of the terminology of domain-specific terms and acronyms.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/GLOSSARY",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Glossary",
                "description": "A glossary is a simple list of terms and their definitions. A glossary focuses on creating a complete list of the terminology of domain-specific terms and acronyms.",
            },
            "lt": {
                "title": "Žodynėlis",
                "description": "Žodynėlis yra paprastas terminų ir jų apibrėžimų sąrašas. Žodynėlis orientuotas į išsamaus srities specifinių terminų ir akronimų terminologijos sąrašo sudarymą.",
            },
        },
    },
    {
        "code": "DIRECTORY",
        "label": "Directory",
        "definition": "A directory contains information about individual entities (e.g. persons) and their (probably) hierarchical organisation and related entities. It is used to browse individuals in their organisational context.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/DIRECTORY",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Directory",
                "description": "A directory contains information about individual entities (e.g. persons) and their (probably) hierarchical organisation and related entities. It is used to browse individuals in their organisational context.",
            },
            "lt": {
                "title": "Žinynas",
                "description": "Žinynas apima informaciją apie atskirus objektus (pvz., asmenis) ir jų (tikėtiną) hierarchinę organizaciją bei susijusius objektus. Jis naudojamas naršyti asmenis jų organizaciniame kontekste.",
            },
        },
    },
    {
        "code": "HVD",
        "label": "High-value dataset",
        "definition": "Dataset whose re-use is associated with important benefits for society, the environment and the economy, in particular because of its suitability for the creation of value-added services, applications and new, high-quality and decent jobs, and of the number of potential beneficiaries of the value-added services and applications based on this dataset.",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/HVD",
        "is_used": False,
        "translations": {
            "en": {
                "title": "High-value dataset",
                "description": "Dataset whose re-use is associated with important benefits for society, the environment and the economy, in particular because of its suitability for the creation of value-added services, applications and new, high-quality and decent jobs, and of the number of potential beneficiaries of the value-added services and applications based on this dataset.",
            },
            "lt": {
                "title": "Didelės vertės duomenų rinkinys",
                "description": "Duomenų rinkinys, kurio pakartotinis naudojimas yra susijęs su svarbiais privalumais visuomenei, aplinkai ir ekonomikai, ypač dėl jo tinkamumo kurti pridėtinės vertės paslaugas, programas ir naujas, kokybiškas ir deramas darbo vietas, bei galimų naudos gavėjų skaičiaus iš pridėtinės vertės paslaugų ir programų, pagrįstų šiuo duomenų rinkiniu.",
            },
        },
    },
    {
        "code": "RELEASE",
        "label": "Release",
        "definition": "dataset that accompanies and describes other published datasets, for instance in the scope of the EU Vocabularies publications; it may contain information about differences between the state of the concerned dataset on last publication and on current publication",
        "uri": "https://publications.europa.eu/resource/authority/dataset-type/RELEASE",
        "is_used": False,
        "translations": {
            "en": {
                "title": "Release",
                "description": "dataset that accompanies and describes other published datasets, for instance in the scope of the EU Vocabularies publications; it may contain information about differences between the state of the concerned dataset on last publication and on current publication",
            },
            "lt": {
                "title": "Laida",
                "description": "Duomenų rinkinys, kuris lydi ir aprašo kitus paskelbtus duomenų rinkinius, pavyzdžiui, ES žodynų publikacijų apimtyje; jame gali būti informacija apie skirtumus tarp susijusio duomenų rinkinio būsenos paskutinėje publikacijoje ir dabartinėje publikacijoje.",
            },
        },
    },
]


def populate_hvd_categories(apps, schema_editor):
    with transaction.atomic():
        HvdCategory = apps.get_model("vitrina_datasets", "HvdCategory")
        HvdCategoryTranslation = apps.get_model(
            "vitrina_datasets", "HvdCategoryTranslation"
        )

        for category_data in HVD_CATEGORIES:
            hvd_category = HvdCategory.objects.create(
                name=category_data["name"],
                definition=category_data["definition"],
                uri=category_data["uri"],
            )
            for lang_code, translations in category_data["translations"].items():
                HvdCategoryTranslation.objects.create(
                    master_id=hvd_category.id,
                    language_code=lang_code,
                    title=translations["title"],
                    description=translations["description"],
                )


def reverse_populate_hvd_categories(apps, schema_editor):
    with transaction.atomic():
        HvdCategory = apps.get_model("vitrina_datasets", "HvdCategory")
        Dataset = apps.get_model("vitrina_datasets", "Dataset")

        for dataset in Dataset.objects.all():
            dataset.hvd_category.clear()

        cursor = schema_editor.connection.cursor()
        cursor.execute("DELETE FROM vitrina_datasets_hvdcategory_translation")

        HvdCategory.objects.all().delete()


def populate_dataset_types(apps, schema_editor):
    with transaction.atomic():
        DatasetType = apps.get_model("vitrina_datasets", "DatasetType")
        DatasetTypeTranslation = apps.get_model(
            "vitrina_datasets", "DatasetTypeTranslation"
        )

        for type_data in DATASET_TYPES:
            dataset_type = DatasetType.objects.create(
                code=type_data["code"],
                label=type_data["label"],
                definition=type_data["definition"],
                uri=type_data["uri"],
                is_used=type_data["is_used"],
            )

            for lang_code, translations in type_data["translations"].items():
                DatasetTypeTranslation.objects.create(
                    master_id=dataset_type.id,
                    language_code=lang_code,
                    title=translations["title"],
                    description=translations["description"],
                )


def reverse_populate_dataset_types(apps, schema_editor):
    with transaction.atomic():
        DatasetType = apps.get_model("vitrina_datasets", "DatasetType")
        DatasetTypeTranslation = apps.get_model(
            "vitrina_datasets", "DatasetTypeTranslation"
        )
        Dataset = apps.get_model("vitrina_datasets", "Dataset")
        for dataset in Dataset.objects.all():
            dataset.type.clear()

        DatasetTypeTranslation.objects.all().delete()
        DatasetType.objects.all().delete()


def copy_type_to_resource_subclass(apps, schema_editor):
    Dataset = apps.get_model("vitrina_datasets", "Dataset")

    for dataset in Dataset.objects.all():
        current_types = dataset.type.all()
        dataset.resource_subclass.add(*current_types)


def clear_old_type_relationships(apps, schema_editor):
    Dataset = apps.get_model("vitrina_datasets", "Dataset")
    Through = Dataset.type.through
    old_relations = list(
        Through.objects.all().values("dataset_id", "resourcesubclass_id")
    )

    schema_editor.connection.migration_state = getattr(
        schema_editor.connection, "migration_state", {}
    )
    schema_editor.connection.migration_state["type_relations"] = old_relations

    for dataset in Dataset.objects.all():
        dataset.type.clear()


def restore_old_type_relationships(apps, schema_editor):
    Dataset = apps.get_model("vitrina_datasets", "Dataset")
    ResourceSubclass = apps.get_model("vitrina_datasets", "ResourceSubclass")

    migration_state = getattr(schema_editor.connection, "migration_state", {})
    old_relations = migration_state.get("type_relations", [])

    for relation in old_relations:
        dataset = Dataset.objects.get(id=relation["dataset_id"])
        resource_subclass = ResourceSubclass.objects.get(
            id=relation["resourcesubclass_id"]
        )
        dataset.type.add(resource_subclass)


def reverse_copy_type_to_resource_subclass(apps, schema_editor):
    # The `resource_subclass` field will be removed in the reverse migration.
    pass


class Migration(migrations.Migration):
    dependencies = [
        (
            "vitrina_datasets",
            "0007_alter_dataset_organization",
        ),
    ]

    operations = [
        # Makes PostgreSQL check constraints after each statement rather than after whole transaction.
        migrations.RunSQL(
            "SET CONSTRAINTS ALL IMMEDIATE", reverse_sql="SET CONSTRAINTS ALL DEFERRED"
        ),
        migrations.RenameModel(old_name="Type", new_name="ResourceSubclass"),
        migrations.RenameModel(
            old_name="TypeTranslation", new_name="ResourceSubclassTranslation"
        ),
        migrations.AlterModelOptions(
            name="resourcesubclass",
            options={
                "verbose_name": "Resurso poklasis",
                "verbose_name_plural": "Resurso poklasiai",
            },
        ),
        migrations.AlterField(
            model_name='resourcesubclass',
            name='name',
            field=models.CharField(max_length=255, unique=True, verbose_name='Kodinis pavadinimas'),
        ),
        migrations.AlterModelOptions(
            name="resourcesubclasstranslation",
            options={
                "default_permissions": (),
                "managed": True,
                "verbose_name": "Resurso poklasis Translation",
            },
        ),
        migrations.AlterModelTable(
            name="resourcesubclass",
            table=None,
        ),
        migrations.AlterModelTable(
            name="resourcesubclasstranslation",
            table="vitrina_datasets_resourcesubclass_translation",
        ),
        migrations.AddField(
            model_name="dataset",
            name="resource_subclass",
            field=models.ManyToManyField(
                blank=True,
                to="vitrina_datasets.ResourceSubclass",
                verbose_name="Resurso poklasiai",
            ),
        ),
        migrations.RunPython(
            copy_type_to_resource_subclass,
            reverse_code=reverse_copy_type_to_resource_subclass,
        ),
        migrations.CreateModel(
            name="DatasetType",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=255, verbose_name="Kodinis pavadinimas"
                    ),
                ),
                (
                    "label",
                    models.CharField(max_length=255, verbose_name="Pilnas pavadinimas"),
                ),
                ("definition", models.TextField(verbose_name="Apibūdinimas")),
                (
                    "uri",
                    models.CharField(
                        max_length=255, verbose_name="Nuorodą į kontroliuojamą žodyną"
                    ),
                ),
                (
                    "is_used",
                    models.BooleanField(default=False, verbose_name="Naudojamas"),
                ),
            ],
            options={
                "verbose_name": "Duomenų rinkinio tipas",
                "verbose_name_plural": "Duomenų rinkinio tipai",
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="DatasetTypeTranslation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        db_index=True, max_length=15, verbose_name="Language"
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="Pavadinimas")),
                ("description", models.TextField(verbose_name="Aprašymas")),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="vitrina_datasets.datasettype",
                    ),
                ),
            ],
            options={
                "verbose_name": "Duomenų rinkinio tipas Translation",
                "db_table": "vitrina_datasets_datasettype_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="HvdCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=255, verbose_name="Pilnas pavadinimas"),
                ),
                ("definition", models.TextField(verbose_name="Apibūdinimas")),
                (
                    "uri",
                    models.URLField(
                        max_length=255, verbose_name="Nuoroda į kontroliuojama žodyną"
                    ),
                ),
            ],
            options={
                "verbose_name": "Didelės vertės duomenų kategorija",
                "verbose_name_plural": "Didelės vertės duomenų kategorijos",
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="HvdCategoryTranslation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        db_index=True, max_length=15, verbose_name="Language"
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="Pavadinimas")),
                ("description", models.TextField(verbose_name="Aprašymas")),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="vitrina_datasets.hvdcategory",
                    ),
                ),
            ],
            options={
                "verbose_name": "Didelės vertės duomenų kategorija Translation",
                "db_table": "vitrina_datasets_hvdcategory_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="LegalResource",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uri",
                    models.URLField(
                        max_length=255, verbose_name="Nuoroda į taikomą teisės aktą"
                    ),
                ),
            ],
            options={
                "verbose_name": "Teisinis išteklis",
                "verbose_name_plural": "Teisiniai ištekliai",
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name="dataset",
            name="applicable_legislation",
            field=models.ManyToManyField(
                help_text="Nuoroda į taikomą teisęs aktą",
                to="vitrina_datasets.LegalResource",
                verbose_name="Taikomi teisės aktai",
            ),
        ),
        migrations.AddField(
            model_name="dataset",
            name="hvd_category",
            field=models.ManyToManyField(
                to="vitrina_datasets.HvdCategory",
                verbose_name="Didelės vertės duomenų kategorijos",
            ),
        ),
        migrations.RunPython(
            clear_old_type_relationships, restore_old_type_relationships
        ),
        migrations.AlterField(
            model_name="dataset",
            name="type",
            field=models.ManyToManyField(
                blank=True,
                db_table="dataset_types",
                to="vitrina_datasets.DatasetType",
                verbose_name="Duomenų rinkinio tipai",
            ),
        ),
        migrations.RunPython(
            populate_hvd_categories,
            reverse_populate_hvd_categories,
        ),
        migrations.RunPython(
            populate_dataset_types,
            reverse_populate_dataset_types,
        ),
        # Delays constraint checks until transaction is completed (needed for reversing migrations).
        migrations.RunSQL(
            "SET CONSTRAINTS ALL DEFERRED", reverse_sql="SET CONSTRAINTS ALL IMMEDIATE"
        ),
    ]
