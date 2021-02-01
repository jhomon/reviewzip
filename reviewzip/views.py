from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.db.models import Q
from .models import Review

# Create your views here.
class IndexView(TemplateView):
    """ 메인 페이지 """

    template_name = "reviewzip/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 최근 올라온 리뷰집 5개 
        context['recent_reviewzips'] = Review.objects.order_by('-create_date')[:5]
        # 조회수 높은 리뷰집 5개
        context['popular_reviewzips'] = Review.objects.order_by('-watch')[:5]
        return context



class ReviewDetailView(DetailView):
    """ 리뷰집 자세히 보기 """

    model = Review
    template_name = "reviewzip/detail.html"

    def get_object(self):
        review = super().get_object()
        # 조회수 1 증가
        review.watch += 1
        review.save()
        return review

    

class ReviewListView(ListView):
    """ 리뷰집 검색 결과 리스트 """

    model = Review
    template_name = 'reviewzip/list.html'
    paginate_by = 10
    
    """ 검색 결과에 해당하는 쿼리 조회 """
    def get_queryset(self):
        q = self.request.GET.get('q', '')
        review_list = Review.objects.order_by('-watch')
        review_list = review_list.filter(
            Q(name__icontains=q) | # 제품명으로 검색
            Q(url__icontains=q) | # 제품 페이지 url로 검색
            Q(positive_keyword__name__icontains=q) # 긍정 키워드로 검색
        ).distinct()
        return review_list

