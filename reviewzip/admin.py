from django.contrib import admin
from .models import Keyword, Sentence, Review, PendingUrl

# Register your models here.
admin.site.register(Keyword)
admin.site.register(Sentence)
admin.site.register(Review)
admin.site.register(PendingUrl)