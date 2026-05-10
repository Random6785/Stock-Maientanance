from django.forms import BooleanField
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

f = BooleanField(required=False)
print("off:", f.to_python("off"))
print("on:", f.to_python("on"))
print("empty string:", f.to_python(""))
print("False:", f.to_python("False"))
print("false:", f.to_python("false"))
