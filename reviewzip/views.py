from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.db.models import Q
from django.contrib import messages
from .models import Review
from .tasks import add_product_url

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
    paginate_by = 6
    
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


""" POST로 온 url에 해당하는 리뷰가 등록되어 있는지 확인
    없으면 데이터베이스에 추가 
"""
# 일단 무조건 요청 url 추가하게 celery task에 넣음
def add_review(request):
    if request.method == 'POST':
        product_url = request.POST.get('product_url')
        if product_url == '':
            messages.warning(request, 'url을 입력해주세요')
        else:
            try:
                # 해당 url이 등록되어 있으면
                obj = Review.objects.get(url=product_url)
                messages.warning(request, '해당 url은 이미 등록되어 있습니다. 해당 url을 검색해보세요.')
            except:
                # 등록되어 있지 않으면
                messages.info(request, '해당 url 등록 요청이 완료 되었습니다. 등록되기까지 시간이 걸립니다.')
                add_product_url.delay(product_url)
        
        return render(request, 'reviewzip/list.html')