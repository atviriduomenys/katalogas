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
{% if dataset.description %}{{ dataset.description|truncatechars:200 }}{% endif %}
**Statusas:** {{ dataset.status_display }}
[Peržiūrėti duomenų rinkinį](https://{{ domain }}/datasets/{{ dataset.id }}/)

{% endfor %}
{% endif %}

---

*Šį laišką gavote, nes užsiprenumeravote mūsų naujienlaiškį.*  
*[Atsisakyti prenumeratos]({{ unsubscribe_url }})*