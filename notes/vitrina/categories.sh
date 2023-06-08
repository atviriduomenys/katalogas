# 2022-10-19 19:06 Fix category tree migration

poetry run python manage.py shell
from treebeard.mp_tree import MP_Node
from vitrina.classifiers.models import Category
c = Category()
c._str2int('0001')
c._int2str(1)
c._int2str(30)
c.get_sorted_pos_queryset()
MP_Node._get_path(None, 1, 1)

Category.objects.all().delete()

a = Category.add_root(title='A', featured=False)
a.refresh_from_db()
a.add_child(title='A -> A', featured=False)
a_b = a.add_child(title='A -> B', featured=False)
a_b.refresh_from_db()

b = Category.add_root(title='B', featured=False)
b.refresh_from_db()

d = Category.add_root(title='D', featured=False)
d.refresh_from_db()

c = Category.add_root(title='C', featured=False)
c.refresh_from_db()

k = Category.add_root(title='K', featured=False)
k.refresh_from_db()

h = Category.add_root(title='H', featured=False)
h.refresh_from_db()

exit()
