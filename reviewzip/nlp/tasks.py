from django.db.utils import IntegrityError
from celery import shared_task
from reviewzip.models import Review, Sentence, Keyword, ReviewInfo
from konlpy.tag import Okt, Komoran
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

def sentiment_predict(sentences, model, tokenizer):
    """ 긍정/부정 예측 """
    stopwords = ['의','가','이','은','들','는','좀','잘','걍','과','도','를','으로','자','에','와','한','하다']
    max_len = 50

    komoran = Komoran()

    # 긍정 문장, 부정 문장 리스트
    pos_sents = []
    neg_sents = []

    for sentence in sentences:
        try:
            Sentence.objects.create(content=sentence) # 온전한 문장 데이터베이스에 저장
        except:
            pass # 이미 존재하는 문장이거나 기타 이유로 에러 발생 시 no create
        
        new_sentence = komoran.morphs(sentence.replace('[^ㄱ-ㅎㅏ-ㅣ가-힣 ]','')) # 토큰화
        new_sentence = [word for word in new_sentence if not word in stopwords] # 불용어 제거
        encoded = tokenizer.texts_to_sequences([new_sentence]) # 정수 인코딩
        pad_new = pad_sequences(encoded, maxlen = max_len) # 패딩
        score = float(model.predict(pad_new)) # 예측
        if score > 0.5:
            pos_sents.append(sentence)
        else:
            neg_sents.append(sentence)

    return pos_sents, neg_sents



def get_tokenized_sentences(sentences):
    """ 명사, 형용사만 가지는 토큰화된 문장 리스트를 반환 """

    # 추출할 품사: 명사, 어근, 형용사
    extracting_pos = ['NNG', 'NNP', 'XR', 'NF', 'NA', 'VA']

    # 너무 이상하게 쪼개면 다른 거 고려
    komoran = Komoran()

    # reviews 내용이 없으면 빈 리스트 리턴
    sent_tokenized = []

    # 토큰화된 문장 리스트 생성
    for sentence in sentences:
        temp = []
        # 이모티콘이 섞여 있으면 UnicodeDecodeError 발생
        try:
            for word, pos in komoran.pos(sentence, flatten=True):
                if pos in extracting_pos:
                    # 형용사는 끝에 '다'를 붙임
                    if pos in ['VA']:
                        word += '다'
                    # 품사 기준 추출할 단어이면 
                    temp.append(word)
        except:
            # 이모티콘 존재 등 문제가 되는 문장은 버리기
            pass
        
        sent_tokenized.append(temp)

    return sent_tokenized



def match_sentence_with_keyword(reviewzip, sentences, sent_tokenized, positive=True):
    """ 키워드랑 문장 매치시켜 데이터베이스에 키워드 저장 """

    # 20개의 빈도수 상위 키워드
    tokenizer = Tokenizer(num_words=20+1)
    tokenizer.fit_on_texts(sent_tokenized)

    # (word, index)
    top_keywords = list(tokenizer.word_index.items())[:20]
    # 그 중에서도 5번 이상 등장하는 키워드만 추림
    word_count_dic = list(tokenizer.word_counts.items())[:20]
    top_keywords = [keyword for idx, keyword in enumerate(top_keywords) if word_count_dic[idx][1] > 3]

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
    try:
        reviewzip = Review.objects.create(info=using_info)
    except IntegrityError:
        # 중간에 오류가 나서 ReviewInfo에 해당하는 Review 객체가 만들어진 경우
        Review.objects.only('info').get(info=using_info).delete()
        reviewzip = Review.objects.create(info=using_info)

    # 리뷰 데이터 읽어 pandas 객체 만들기
    print('reading csv file')
    data = pd.read_csv(file_path, encoding='utf-8', names=['review', 'rating'])
    # 중복된 데이터 제거
    data.drop_duplicates(subset=['review'], inplace=True)

    # review만 추출
    reviews = data.review.values

    # 모델 불러오기
    print('loading model and tokenizer')
    model = load_model('./models/komoran_model.h5')
    # 토크나이저 불러오기
    with open('./tokenizers/komoran_tokenizer.pickle', 'rb') as handle:
        tokenizer = pickle.load(handle)


    # 리뷰를 문장 단위로 쪼개기
    print('spliting reviews with sentences')
    sentences = []

    for review in reviews:
        # 리뷰 하나를 여러 문장으로 나눕니다
        sentences.extend(kss.split_sentences(review))

    # 각 문장에 대해 감성 분류
    pos_sents, neg_sents = sentiment_predict(sentences, model, tokenizer)


    # 유의미한 품사의 단어만 가지는 tokenized sentence 
    print('getting tokenized sentences')
    pos_sent_tokenized = get_tokenized_sentences(pos_sents)
    neg_sent_tokenized = get_tokenized_sentences(neg_sents)

    # 키워드 문장 매칭
    print('matching keywords with sentences')
    reviewzip = match_sentence_with_keyword(reviewzip, pos_sents, pos_sent_tokenized, positive=True)
    reviewzip = match_sentence_with_keyword(reviewzip, neg_sents, neg_sent_tokenized, positive=False)
    
    # reviewzip object 데이터베이스에 저장
    reviewzip.save()

    # 사용한 리뷰 파일 used = True 처리
    using_info.used = True
    using_info.save()