from django.core.files.base import ContentFile
from django.core.files import File
from celery import shared_task
from reviewzip.models import PendingUrl, ReviewInfo
import requests
import re
import lxml
import csv
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from reviewzip.nlp.tasks import make_reviewzip


@shared_task
def pend_product_url(product_url):
    """ 제품 요청 들어온 url을 pending """

    # 등록되어 있지 않은 url
    PendingUrl.objects.create(url=product_url)

    # 크롤링 함수 큐에 넣기
    crawling_start.delay()


@shared_task
def crawling_start():
    """ 크롤링 base 함수 크롤링 후 ReviewFIle 생성 """
    
    # driver 설정 - css, 이미지는 로드하지 않는다
    options = Options()
    options.page_load_strategy = 'eager'
    
    driver = webdriver.Chrome(options=options)
    # driver 전체 화면
    driver.maximize_window()

    # 별점 크롤링을 위해 re 미리 compile
    regexp = re.compile('\d+')

    # 크롤링할 url 
    # 가장 먼저 등록된 url
    pending_url = PendingUrl.objects.filter(processed=False).order_by('create_date')[0]
    # 저장할 csv 파일 이름
    url_id = str(pending_url.id)

    # selenium은 클릭 하는 역할이고, 텍스트 크롤링은 bs4로 한다
    # selenium은 selnium 태그를 반환하고, bs4는 실제 태그를 반환한다
    crawling_url = pending_url.url
    driver.get(crawling_url)

    # csv 파일로 저장하는 게 깔끔
    # 한글이므로 utf-8 인코딩
    f = open(url_id + '.csv', 'a+', encoding='utf-8', newline='')
    wr = csv.writer(f)

    # 크롤링 가능한 사이트인지 찾는 정규 표현식
    site_reg = re.compile('musinsa|coupang')
    # 크롤링 가능한 url이면
    if site_reg.search(crawling_url):
        # 무신사 url이면
        if 'musinsa' in crawling_url:
            crawling_musinsa(driver, crawling_url, regexp, f, wr, url_id)

    # csv 파일 닫기
    f.close()

    # 크롤링이 끝나면 chrome 종료
    driver.quit()

    # 만들어진 csv 파일 삭제
    os.remove(url_id + '.csv')

    # pending_url processed 처리
    pending_url.processed = True
    pending_url.save()


def crawling_musinsa(driver, crawling_url, regexp, f, wr, url_id):
    """ PendingUrl을 주소로 젒속해서 크롤링 후 ReviewFile 데이터 생성 """
    
    # 화면을 읽은 뒤 bs4가 파싱
    html = driver.page_source
    soup = BeautifulSoup(html, 'lxml')

    # 제품 이미지 get
    image = soup.select('.product-img img')[0]
    image_link = "https:" + image["src"]

    # 제품 이름 get
    product_name = soup.select('.product_title em')[0].text.strip()
    print(product_name)

    # 일반 후기 탭을 클릭
    driver.find_element_by_id('estimate_goods').click()
    # driver.implicitly_wait(1)

    page = 1
    # 마지막 페이지 도달할 때까지 반복
    while True:
        # 화면을 읽은 뒤 bs4가 파싱
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        # 한 페이지의 리뷰들을 찾아 리스트로 반환
        # 일반 후기 뿐만이 아니라 다른 후기들도 읽어들이게 되는 문제 발생 -> 클래스를 특정해서 해결
        reviews = soup.select('.list-estimate span.content-review')

        # .score10 이면 별점 5점
        scores_raw = soup.select('.list-estimate .n-score .score')
        scores = []
        for score_tag in scores_raw:
            scores.append(int(regexp.findall(str(score_tag))[0]) / 2)

        # csv 파일로 저장하는 게 깔끔
        # .text는 태그 안에 있는 내용만 추출
        for (idx, review) in enumerate(reviews):
            wr.writerow([ review.text.strip() ] + [ scores[idx] ])

        # 몇 페이지를 크롤링 중인 지 출력
        print("page:", page)
        print(len(scores), len(reviews))

        # 리뷰 다음 페이지로 이동
        # 마지막 페이지에 도착하면 반복문 종료
        page += 1
        next = driver.find_element_by_css_selector('.list-estimate .pagination')
        try:
            # 단순 @class는 클래스 전체가 일치하는 지 확인하고 //는 루트 요소부터 전부 탐색한다 
            # .//는 현재 노드의 하위 노드 탐색
            if(page % 5 == 1):
                next.find_element_by_xpath('.//a[contains(@class, "next")]').click()
            else:
                next.find_element_by_xpath(".//a[text()=" + str(page) + " and not(text()[2])]").click()
        except Exception as e:
            print(e)
            print("리뷰 마지막 페이지 도착")
            break


    # ReviewInfo 데이터 생성
    review_info = ReviewInfo(url=crawling_url) # url 설정
    review_info.name = product_name # name 설정
    # file 설정
    # 여기에서 에러 발생. File class는 codec cp949??? 확인해보니 UTF-8
    review_info.file.save(url_id + '.csv', File(f), save=False)
    
    # thumbnail 설정
    review_info.thumbnail.save(url_id + '.jpg', ContentFile(requests.get(image_link).content), save=False)

    # ReviewInfo 데이터 저장
    review_info.save()

    # make_reveiwzip 함수 큐에 넣기
    make_reviewzip.delay()
