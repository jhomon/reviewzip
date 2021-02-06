from rest_framework.decorators import api_view
from rest_framework.decorators import parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from reviewzip.models import Sentence, Review
from .serializers import SentenceSerializer

# Create your views here.

@api_view(['GET'])
#@parser_classes([JSONParser])
def get_sentences_with_keyword(request, format=None):
    """
    review에서 keyword가 들어간 문장들을 리턴
    """
    keyword = request.GET.get('keyword')
    review_name = request.GET.get('review_name')
    positive = request.GET.get('positive')

    if positive == 'positive':
        review = Review.objects.prefetch_related('positive_keyword').get(name=review_name)
        queryset = \
            review.positive_keyword.prefetch_related('sentence').get(name=keyword).sentence
    elif positive == 'negative':
        review = Review.objects.prefetch_related('negative_keyword').get(name=review_name)
        queryset = \
            review.negative_keyword.prefetch_related('sentence').get(name=keyword).sentence

    serializer = SentenceSerializer(queryset, many=True)
    return Response(serializer.data)
