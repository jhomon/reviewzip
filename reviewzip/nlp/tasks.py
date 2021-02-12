from celery import shared_task
from reviewzip.models import Review, Sentence, Keyword, ReviewInfo
from konlpy.tag import Mecab, Okt
import kss
import pickle
import jpype
import pandas as pd
import numpy as np
import os
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import load_model


""" 이 아래부터는 리뷰 데이터 분석을 위한 함수들 """

def sentiment_predict(new_sentence, model, tokenizer):
    """ 긍정/부정 예측 """
    stopwords = ['도', '는', '다', '의', '가', '이', '은', '한', '에', '하', '고', '을', '를', '인', '듯', '과', '와', '네', '들', '듯', '지', '임', '게']
    max_len = 80

    if jpype.isJVMStarted():  
        jpype.attachThreadToJVM()

    okt = Okt()
    
    new_sentence = okt.morphs(new_sentence) # 토큰화
    new_sentence = [word for word in new_sentence if not word in stopwords] # 불용어 제거
    encoded = tokenizer.texts_to_sequences([new_sentence]) # 정수 인코딩
    pad_new = pad_sequences(encoded, maxlen = max_len) # 패딩
    score = float(model.predict(pad_new)) # 예측
    if score > 0.5:
        return 1
    else:
        return 0



def get_stemmed_sentences(reviews):
    """ 명사, 형용사만 가지는 토큰화된 문장 리스트를 반환 """

    if jpype.isJVMStarted():  
        jpype.attachThreadToJVM()

    # 너무 이상하게 쪼개면 customized konlpy 사용
    okt = Okt()

    # 추출할 품사: 명사, 형용사
    okt_extracting_pos = ['Noun', 'Adjective']

    # okt를 이용하여 단어 정제
    stop_words = ['입다', '사다', '하다', '시키다', '않다', '되다', '받다', '알다', '싶다', '파다', '있다', '살다', '비다', '듭니다', '이다', '떨다'\
        '진짜', '정말', '조금', '아주', '살짝', '생각', '그냥', '약간', '제가', '저랑', '매우', '제품',
        '것', '수', '요', '더', '거', '시', '쪽', '봉']

    # reviews 내용이 없으면 빈 리스트 리턴
    sent_tokenized = []

    # 토큰화된 문장 리스트 생성
    for review in reviews:
        temp = []
        for word, pos in okt.pos(review, norm=True, stem=True):
            if pos in okt_extracting_pos and word not in stop_words:
                # 품사가 명사, 형용사이고 stop_words가 아니면 
                temp.append(word)
        sent_tokenized.append(temp)

    return sent_tokenized



def match_sentence_with_keyword(reviewzip, sentences, sent_tokenized, positive=True):
    """ 키워드랑 문장 매치시켜 데이터베이스에 키워드 저장 """

    # 20개의 빈도수 상위 키워드
    tokenizer = Tokenizer(num_words=20+1)
    tokenizer.fit_on_texts(sent_tokenized)

    # (word, index)
    top_keywords = list(tokenizer.word_index.items())[:20]

    # 해당 토큰(키워드)가 존재하면 1, 없으면 0을 값으로 가지는 numpy matrix
    token_existance_mat = tokenizer.texts_to_matrix(sent_tokenized, mode='binary')

    for keyword, index in top_keywords:
        # 키워드를 무조건 새롭게 생성
        keyword_obj = Keyword.objects.create(name=keyword)

        # 열 인덱스가 일치하는(해당 키워드가 있는) 문장
        rows = np.where(token_existance_mat[:, index] == 1)[0]
        rows = rows.tolist()

        # 키워드가 존재하는 행들 rows에 있는 완전한 문장 sentences를 키워드랑 매칭시켜 저장
        for row in rows:
            keyword_obj.sentence.add(Sentence.objects.get(content__exact=sentences[row]))
            if positive:
                reviewzip.positive_keyword.add(keyword_obj)
            else:
                reviewzip.negative_keyword.add(keyword_obj)

    return reviewzip



@shared_task
def make_reviewzip():
    """ 아직 처리되지 않은 ReviewInfo로 Review 클래스 데이터 생성 """

    # 먼저 만들어진 ReviewInfo부터 처리
    try:
        using_info = ReviewInfo.objects.filter(used=False)\
            .order_by('create_date').only('file_path', 'used')[0]
        file_path = 'review_files/' + using_info.file_path
    except:
        # 처리할 파일이 없는 경우
        print("모든 파일이 이미 처리되었습니다.")
        return

    # Review 데이터 임시 생성
    reviewzip = Review.objects.create(info=using_info)

    # 리뷰 데이터 읽어 pandas 객체 만들기
    print('reading csv file')
    data = pd.read_csv(file_path, encoding='utf-8', names=['review', 'rating'])
    # 중복된 데이터 제거
    data.drop_duplicates(subset=['review'], inplace=True)

    # 모델 불러오기
    print('loading model and tokenizer')
    model = load_model('./models/sentiment_model.h5')
    # 토크나이저 불러오기
    with open('./tokenizers/sentiment_tokenizer.pickle', 'rb') as handle:
        tokenizer = pickle.load(handle)

    # 리뷰를 문장 단위로 쪼개기
    print('spliting reviews with sentences')
    pos_sent_objs = [] # 긍정 문장 Sentence 객체들 
    neg_sent_objs = [] # 부정 문장 Sentence 객체들
    pos_sents = [] # 긍정 키워드 추출을 위해 긍정 문장 모아놓은 배열
    neg_sents = [] # 부정 키워드 추출을 위해 부정 문장 모아놓은 배열
    reviews = data.review.values

    for review in reviews:
        # 리뷰 하나를 여러 문장으로 나눕니다
        sents = kss.split_sentences(review)
        # 각 문장에 대해 감성 분류
        for sent in sents:
            sentiment = sentiment_predict(sent.replace('[^ㄱ-ㅎㅏ-ㅣ가-힣 ]',''), model, tokenizer)
            if sentiment == 1:
                pos_sent_objs.append(Sentence(content=sent)) # 긍정 문장
                pos_sents.append(sent)
            else:
                neg_sent_objs.append(Sentence(content=sent)) # 부정 문장
                neg_sents.append(sent)


    # 긍정 문장, 부정 문장 bulk create
    # 기존에 데이터베이스에 존재하는 문장은 무시
    print("sentece data bulk create")
    Sentence.objects.bulk_create(pos_sent_objs, ignore_conflicts=True)
    Sentence.objects.bulk_create(neg_sent_objs, ignore_conflicts=True)

    # 명사, 형용사만 가지는 tokenized sentence 
    print('getting tokenized sentences')
    pos_sent_tokenized = get_stemmed_sentences(pos_sents)
    neg_sent_tokenized = get_stemmed_sentences(neg_sents)

    # 키워드 문장 매칭
    print('matching keywords with sentences')
    reviewzip = match_sentence_with_keyword(reviewzip, pos_sents, pos_sent_tokenized, positive=True)
    reviewzip = match_sentence_with_keyword(reviewzip, neg_sents, neg_sent_tokenized, positive=False)
    
    # reviewzip object 데이터베이스에 저장
    reviewzip.save()

    # 사용한 리뷰 파일 used = True 처리
    using_info.used = True
    using_info.save()