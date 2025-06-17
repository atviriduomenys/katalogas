### **DUOMENŲ TEIKIMO-GAVIMO SUTARTIS**

2025 m. gegužės 22 d., Vilnius

{{ odrl_data["assigner"][0]["ex:companyName"] }}, juridinio asmens kodas {{ odrl_data["assigner"][0]["ex:companyCode"] }}, registruotos buveinės adresas {{ odrl_data["assigner"][0]["ex:address"] }}, atstovaujama/as {{ odrl_data["assigner"][0]["ex:representative"] }}, veikiančio pagal Teikėjas įgaliojimus (toliau – **Duomenų teikėjas**)

ir

{{ odrl_data["assignee"][0]["ex:companyName"] }}, juridinio asmens kodas {{ odrl_data["assignee"][0]["ex:companyCode"] }}, registruotos buveinės adresas {{ odrl_data["assignee"][0]["ex:address"] }}, atstovaujama/as {{ odrl_data["assignee"][0]["ex:representative"] }}, veikiančio pagal Gavėjo įgaliojimus (toliau – **Duomenų gavėjas**),

toliau Duomenų teikėjas ir Duomenų gavėjas kartu vadinami Šalimis, o kiekvienas atskirai – Šalimi, sudaro šią duomenų teikimo-gavimo sutartį (toliau – Sutartis):

**1 SĄVOKOS**

1.1 Šioje Sutartyje toliau nurodytos sąvokos, parašytos iš didžiosios raidės, turi tokias reikšmes:

1.1.1 **Duomenys** – aktų, faktų ar informacijos ir tokių aktų, faktų ar informacijos rinkinių skaitmeninė Duomenys – aktų, faktų ar informacijos ir tokių aktų, faktų ar informacijos rinkinių skaitmeninė Duomenys – aktų, faktų ar informacijos ir tokių aktų, faktų ar informacijos rinkinių skaitmeninė

1.1.2 **Duomenų rinkinio pavadinimas** – {{ odrl_data["permission"][0]["target"]["ex:name"] }}.

**3 DUOMENŲ TEIKIMO IR GAVIMO TEISINIS PAGRINDAS**

3.1. Duomenų teikėjas teikia Duomenis vadovaujantis:

3.1.1. Reglamento 6 straipsnio 1 dalies c punktu

{% if odrl_data["ex:other_assigner_legislations"] %}
3.1.2. **{{ odrl_data["ex:other_assigner_legislations"] }}**

3.1.3. Kitais Duomenų teikėjo veiklą reglamentuojančiais Lietuvos Respublikoje galiojančiais teisės aktais.
{% else %}
3.1.2. Kitais Duomenų teikėjo veiklą reglamentuojančiais Lietuvos Respublikoje galiojančiais teisės aktais.
{% endif %}

3.2. Duomenų gavėjas gauna Duomenis vadovaujantis:

3.2.1. Reglamento 6 straipsnio 1 dalies c punktu

{% if odrl_data["ex:other_assignee_legislations"] %}
3.2.2. **{{ odrl_data["ex:other_assignee_legislations"] }}**

3.2.3. Kitais Duomenų gavėjo veiklą reglamentuojančiais Lietuvos Respublikoje galiojančiais teisės aktais.
{% else %}
3.2.2. Kitais Duomenų gavėjo veiklą reglamentuojančiais Lietuvos Respublikoje galiojančiais teisės aktais.
{% endif %}

**7 DUOMENŲ TEIKIMO SĄLYGOS**

7.1 Teisių sąrašas:

{% for clause in odrl_data["permission"][0]["target"]["ex:scopes"] %}
7.1.{{ loop.index }}. {{ clause }}
{% endfor %}

**8 KAINA, ATSISKAITYMO TVARKA**

{% for clause in odrl_data['ex:paymentTerms'] %}
8.{{ loop.index }}. {{ clause }}
{% endfor %}

**9 PAPILDOMI DUOMENYS**

9.1. Sutarties šablono kontrolinė suma: template_checksum:{{ template_checksum }}

9.2. JSON formato sutarties duomenų kontrolinė suma: json_checksum:{{ json_checksum }}

| **Duomenų teikėjas**                                | **Duomenų gavėjas**                                 |
|-----------------------------------------------------|-----------------------------------------------------|
| {{ odrl_data["assigner"][0]["ex:companyName"] }}    | {{ odrl_data["assignee"][0]["ex:companyName"] }}    |
| {{ odrl_data["assigner"][0]["ex:companyCode"] }}    | {{ odrl_data["assignee"][0]["ex:companyCode"] }}    |
| {{ odrl_data["assigner"][0]["ex:address"] }}        | {{ odrl_data["assignee"][0]["ex:address"] }}        |
| {{ odrl_data["assigner"][0]["ex:email"] }}          | {{ odrl_data["assignee"][0]["ex:email"] }}          |
| {{ odrl_data["assigner"][0]["ex:phone"] }}          | {{ odrl_data["assignee"][0]["ex:phone"] }}          |
| {{ odrl_data["assigner"][0]["ex:personal_code"] }}  | {{ odrl_data["assignee"][0]["ex:personal_code"] }}  |
| {{ odrl_data["assigner"][0]["ex:representative"] }} | {{ odrl_data["assignee"][0]["ex:representative"] }} |
| `_________________________`                         | `_________________________`                         |
| _Vardas, pavardė, parašas_                          | _Vardas, pavardė, parašas_                          |
