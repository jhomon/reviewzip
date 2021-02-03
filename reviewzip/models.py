from django.db import models

# Create your models here.

class Keyword(models.Model):
    """ 리뷰 키워드 """
    
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Sentence(models.Model):
    """ 리뷰 문장 단위 """

    content = models.TextField()

    def __str__(self):
        return self.content


class Review(models.Model):
    """ 리뷰 종합 분석 """

    name = models.CharField(max_length=30) # 상품명
    thumbnail = models.ImageField(upload_to="thumbnails/") # 제품 썸네일
    url = models.URLField(unique=True) # 제품 구매 페이지 url
    csv = models.FileField(upload_to="review_files/", null=True, blank=True) # 리뷰 파일.csv
    create_date = models.DateTimeField(auto_now_add=True) # 업로드한 날짜
    watch = models.IntegerField(default=0) # 조회수
    positive_keyword = models.ManyToManyField(Keyword, blank=True, related_name="positive_keyword") # 긍정 키워드
    negative_keyword = models.ManyToManyField(Keyword, blank=True, related_name="negative_keyword") # 부정 키워드
    positive_sentence = models.ManyToManyField(Sentence, blank=True, related_name="positive_sentence") # 긍정 문장
    negative_sentence = models.ManyToManyField(Sentence, blank=True, related_name="negative_sentence") # 부정 문장

    def __str__(self):
        return self.name


class PendingUrl(models.Model):
    """ 등록 대기 중인 리뷰 """

    url = models.URLField(unique=True) # 등록 대기 중인 제품 구매 페이지 url
    create_date = models.DateTimeField(auto_now_add=True) # 등록 요청된 날짜
    
    def __str__(self):
        return self.url
    