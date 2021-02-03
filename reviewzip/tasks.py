from celery import shared_task
from reviewzip.models import Review, Sentence, Keyword, PendingUrl

""" 입력받은 리뷰 csv 파일로부터
    해당 리뷰들을 문장 단위로 쪼개고 긍정, 부정을 판단
    키워드 추출하고 문장에 히당하는 키워드 매핑하여
    키워드, 문장을 데이터베이스(모델) 에 저장
 """
@shared_task
def predict_sentiment(file):
    pass

@shared_task
def match_keyword(sentence):
    pass

@shared_task
def add_product_url(product_url):
    # 등록되어 있지 않은 url
    PendingUrl.objects.create(url=product_url)
    