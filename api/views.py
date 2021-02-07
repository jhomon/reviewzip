from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.pagination import PageNumberPagination
from reviewzip.models import Sentence, Review
from .serializers import SentenceSerializer

# Create your views here.
class SentenceViewSet(ReadOnlyModelViewSet):
    """ 키워드에 해당하는 리뷰 문장을 보여주기 위한 viewset """
    serializer_class = SentenceSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        keyword = self.request.GET.get('keyword')
        review_name = self.request.GET.get('review_name')
        positive = self.request.GET.get('positive')

        if positive == 'positive':
            review = Review.objects.prefetch_related('positive_keyword').get(name=review_name)
            return review.positive_keyword.prefetch_related('sentence').get(name=keyword).sentence.all()
        elif positive == 'negative':
            review = Review.objects.prefetch_related('negative_keyword').get(name=review_name)
            return review.negative_keyword.prefetch_related('sentence').get(name=keyword).sentence.all()

