Mėnesinis naujienlaiškis - {{ month_year }}

# Mėnesinis naujienlaiškis - {{ month_year }}

{% if blog_posts %}
## Naujausi tinklaraščio įrašai

{% for post in blog_posts %}
- [{{ post.month }} {{ post.day }} d.] [{{ post.title|default:"Skaityti įrašą" }}](https://{{ domain }}{{ post.url }})  
{% endfor %}

{% endif %}
{% if datasets %}
## Nauji duomenų rinkiniai

{% for dataset in datasets %}
### {{ dataset.title }}
[Peržiūrėti duomenų rinkinį](https://{{ domain }}/datasets/{{ dataset.id }}/)  
{% if dataset.description %}{{ dataset.description|truncatechars:200 }}{% endif %}
{% endfor %}
{% endif %}

Pagarbiai,  
Valstybės skaitmeninių sprendimų agentūra  
---

*Šį laišką gavote, nes užsiprenumeravote mūsų naujienlaiškį.*  
*[Atsisakyti prenumeratos]({{ unsubscribe_url }})*