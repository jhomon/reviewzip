from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.db.models import Q
from django.contrib import messages
from .models import Review, PendingUrl, ReviewInfo
from .crawling.tasks import pend_product_url
from .common.tasks import increase_watch

# Create your views here.
class IndexView(TemplateView):
    """ 메인 페이지 """

    template_name = "reviewzip/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 최근 올라온 리뷰집 5개 
        context['recent_reviewzips'] = Review.objects.only("info").order_by('-create_date')[:5].prefetch_related('info')
        # 조회수 높은 리뷰집 5개
        context['popular_reviewzips'] = Review.objects.only("info").order_by('-watch')[:5].prefetch_related('info')
        return context



class ReviewDetailView(DetailView):
    """ 리뷰집 자세히 보기 """

    model = Review
    template_name = "reviewzip/detail.html"
    queryset = Review.objects.only('info', 'positive_keyword', 'negative_keyword')

    def get_object(self):
        review = super().get_object()
        # 조회수 1 증가
        increase_watch.delay(review.id)
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
            Q(info__name__icontains=q) | # 제품명으로 검색
            Q(info__url__icontains=q) | # 제품 페이지 url로 검색
            Q(positive_keyword__name__icontains=q) # 긍정 키워드로 검색
        ).distinct()
        return review_list


def add_request(request):
    """ POST로 넘겨받은 등록 요청 url이 존재하는 지 검토 후 등록 """
    if request.method == 'POST':
        product_url = request.POST.get('product_url')
        if product_url == '':
            messages.warning(request, 'url을 입력해주세요')
        else:
            try:
                # 해당 url의 리뷰가 이미 등록되어 있으면
                ReviewInfo.get(url=product_url)
                messages.warning(request, '해당 url은 이미 등록되어 있습니다. 해당 url을 검색해보세요.')
            except:
                # 해당 url의 리뷰가 등록되어 있지 않으면
                try:
                    # 해당 url이 등록 대기 중이면
                    PendingUrl.objects.get(url=product_url)
                    messages.warning(request, '해당 url은 등록 요청이 되어 검토 중입니다.')
                except:
                    # 해당 url 리뷰도 존재하지 않고 등록 대기 중도 아니면
                    messages.info(request, '해당 url 등록 요청이 완료 되었습니다. 등록되기까지 시간이 걸립니다.')
                    pend_product_url.delay(product_url)
        
        return render(request, 'reviewzip/list.html')