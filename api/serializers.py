from rest_framework import serializers
from reviewzip.models import Sentence, Keyword, Review

class SentenceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Sentence
        fields = ['content']