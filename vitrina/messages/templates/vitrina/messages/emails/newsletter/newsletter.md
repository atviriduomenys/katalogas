Mėnesinis naujienlaiškis - {{ month_year }}

# Mėnesinis naujienlaiškis - {{ month_year }}

{% if blog_posts %}
## Naujausi tinklaraščio įrašai

{% for post in blog_posts %}
- [{{ post.month }} {{ post.day }} d.] [{{ post.title|default:"Skaityti įrašą" }}](https://{{ domain }}{{ post.url }})  
{% endfor %}

{% endif %}
{% if top_datasets %}
## Nauji duomenų rinkiniai

{% for dataset in top_datasets %}
### {{ dataset.title }}
[Peržiūrėti duomenų rinkinį](https://{{ domain }}/datasets/{{ dataset.id }}/)  
{% if dataset.description %}{{ dataset.description|truncatechars:200 }}{% endif %}
{% endfor %}

{% endif %}
{% if list_datasets %}
#### Likusiu duomenų rinkinių sąrašas
{% for dataset in list_datasets %}
- [{{ dataset.month }} {{ dataset.day }} d.] [{{ dataset.title }}](https://{{ domain }}/datasets/{{ dataset.id }}/)  
{% endfor %}
{% endif %}

Pagarbiai,  
Valstybės skaitmeninių sprendimų agentūra  
---

*Šį laišką gavote, nes užsiprenumeravote mūsų naujienlaiškį.*  
*[Atsisakyti prenumeratos]({{ unsubscribe_url }})*