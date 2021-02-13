from django.db import models

# Create your models here.

class ReviewInfo(models.Model):
    """ 리뷰에 대한 기본적인 정보 """

    name = models.CharField(max_length=50) # 상품명
    file_path = models.FilePathField(path='review_files/', null=True) # csv 파일 경로
    url = models.URLField() # 해당 파일이 크롤링한 url
    thumbnail = models.ImageField(null=True, blank=True, upload_to="thumbnails/") # 제품 이미지
    used = models.BooleanField(default=False) # 해당 파일을 사용해서 Review 데이터를 만들었는지
    create_date = models.DateTimeField(auto_now_add=True) # 파일이 등록된 날짜

    def __str__(self):
        return self.name


class Sentence(models.Model):
    """ 리뷰 문장 단위 """

    content = models.TextField(unique=True)

    def __str__(self):
        return self.content


class Keyword(models.Model):
    """ 리뷰 키워드 """
    
    name = models.CharField(max_length=10)
    sentence = models.ManyToManyField(Sentence)

    def __str__(self):
        return self.name



class Review(models.Model):
    """ 리뷰 종합 분석 """

    info = models.OneToOneField(ReviewInfo, on_delete=models.CASCADE) # 리뷰에 대한 기본 정보
    create_date = models.DateTimeField(auto_now_add=True) # 업로드한 날짜
    watch = models.IntegerField(default=0) # 조회수
    positive_keyword = models.ManyToManyField(Keyword, blank=True, related_name="positive_keyword") # 긍정 키워드
    negative_keyword = models.ManyToManyField(Keyword, blank=True, related_name="negative_keyword") # 부정 키워드

    def __str__(self):
        return self.info.name


class PendingUrl(models.Model):
    """ 등록 대기 중인 리뷰 """

    url = models.URLField(unique=True) # 등록 대기 중인 제품 구매 페이지 url
    create_date = models.DateTimeField(auto_now_add=True) # 등록 요청된 날짜
    processed = models.BooleanField(default=False) # 처리 됐는지
    
    def __str__(self):
        return self.url
    