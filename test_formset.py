import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from inventory_app.forms import InventoryUsageLogFormSet
from django.http import QueryDict

post_data = QueryDict(mutable=True)
post_data.update({
    'inventoryusagelog_set-TOTAL_FORMS': '1',
    'inventoryusagelog_set-INITIAL_FORMS': '0',
    'inventoryusagelog_set-MIN_NUM_FORMS': '0',
    'inventoryusagelog_set-MAX_NUM_FORMS': '1000',
    'inventoryusagelog_set-0-item': '1', # Needs to be valid item ID
    'inventoryusagelog_set-0-amount_taken': '0.500',
    'inventoryusagelog_set-0-amount_used': '0.200',
    'inventoryusagelog_set-0-amount_returned': '0.300',
    'inventoryusagelog_set-0-DELETE': 'off',
})

formset = InventoryUsageLogFormSet(post_data, prefix='inventoryusagelog_set')
print("Is valid:", formset.is_valid())
print("Errors:", formset.errors)
if formset.is_valid():
    for form in formset.forms:
        print("Cleaned data:", form.cleaned_data)
