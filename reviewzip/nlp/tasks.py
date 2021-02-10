from celery import shared_task
from reviewzip.models import Review, Sentence, Keyword, ReviewInfo
from konlpy.tag import Mecab, Okt
import kss
import pickle
import jpype
import pandas as pd
import os
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import load_model
from krwordrank.word import KRWordRank


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
    if(score > 0.5):
        return 1
    else:
        return 0


def get_stemmed_keywords(reviews):
    """ 형용사, 동사는 원형으로 변환한 reviews의 키워드를 반환 """

    #JAVA_HOME = "C:\Program Files\Java\jdk-15.0.1\bin\server"
    
    if jpype.isJVMStarted():  
        jpype.attachThreadToJVM()

    # 너무 이상하게 쪼개면 customized konlpy 사용
    okt = Okt()

    # okt를 이용하여 단어 정제
    stop_words = ['입다', '사다', '하다', '시키다', '않다', '되다', '받다', '알다', '싶다', '파다', '있다', '살다', '비다', '듭니다', '이다', '떨다'\
        '진짜', '정말', '조금', '아주', '살짝', '생각', '그냥', '약간', '제가', '저랑', '매우',]

    # reviews 내용이 하나 이하이면 빈 리스트 리턴
    try:
        keyword_extractor = KRWordRank(min_count=5, max_length=10)
        keywords, rank, graph = keyword_extractor.extract(reviews, beta=0.85)
    except:
        return []

    keywords_stemmed = {}
    for word, score in keywords.items():
        word_pos = okt.pos(word, stem=True)

        # 불용어로만 이루어진 corpus이면 건너뜁니다
        if len(word_pos) == 1 and word_pos[0][0] in stop_words:
            continue

        # 형용사, 동사면 기본형을 keyword_set에 추가 
        if len(word_pos) == 1 and word_pos[0][1] in ['Adjective', 'Verb']:
            if word_pos[0][0] not in keywords_stemmed:
                keywords_stemmed[word_pos[0][0]] = score
            else:
                keywords_stemmed[word_pos[0][0]] += score
        # 부사, 조사, 이모티콘으로만 이루어진 형태소는 버립니다
        elif len(word_pos) == 1 and word_pos[0][1] in ['Adverb', 'Josa', 'KoreanParticle']:
            pass
        # 명사 두 개로 쪼갰으면 원래 단어를 keyword_set에 추가
        else:
            keywords_stemmed[word] = score

    # 동사의 활용 형태가 하나의 키워드로 통합되면서 score가 바뀌었으니 다시 sort
    # sorted는 (키, 값) 배열을 반환
    # 20개의 키워드를 가지는 리스트 리턴
    keywords_stemmed = list(map(lambda x: x[0], sorted(keywords_stemmed.items(), key=lambda x:x[1], reverse=True)[:20]))
    return keywords_stemmed


def get_verb_indices(reviews):
    """ [동사 또는 형용사]를 포함하는 인덱스들을 값으로 가지는 딕셔너리 반환 """

    if jpype.isJVMStarted():  
        jpype.attachThreadToJVM()

    okt = Okt()

    verb_indices = {}
    stop_words = ['입다', '사다', '하다', '시키다', '않다', '되다', '받다', '알다', '싶다', '파다', '있다', '살다', '비다', '듭니다', '이다', '떨다'\
    '진짜', '정말', '조금', '아주', '살짝', '생각', '그냥', '약간', '제가', '저랑', '매우',]

    for idx, sent in enumerate(reviews):
        for word, pos in okt.pos(sent, stem=True):
            if pos in ['Adjective', 'Verb'] and word not in stop_words:
                try:
                    verb_indices[word].append(idx)
                except KeyError:
                    verb_indices[word] = []
        return verb_indices



def match_sentence_with_keyword(reviewzip, sentences, verb_indices, keywords, positive=True):
    """ 키워드랑 문장 매치시켜 데이터베이스에 키워드 저장 """

    for keyword in keywords:
        # 키워드를 무조건 새롭게 생성
        keyword_obj = Keyword.objects.create(name=keyword)

        for idx, sent in enumerate(sentences):
            # '어깨가'처럼 문장 내에서 찾을 수 있는 경우
            if keyword in sent:
                keyword_obj.sentence.add(Sentence.objects.get(content__exact=sent))
                if positive:
                    reviewzip.positive_keyword.add(keyword_obj)
                else:
                    reviewzip.negative_keyword.add(keyword_obj)
            # 키워드가 동사, 형용사 원형이어서 원래 문장에서 찾을 수 없는 경우
            try:
                if idx in verb_indices[keyword]:
                    keyword_obj.sentence.add(Sentence.objects.get(content__exact=sent))
                    if positive:
                        reviewzip.positive_keyword.add(keyword_obj)
                    else:
                        reviewzip.negative_keyword.add(keyword_obj)
            except KeyError:
                pass
    
    return reviewzip



@shared_task
def make_reviewzip():
    """ 아직 처리되지 않은 ReviewInfo로 Review 클래스 데이터 생성 """

    # 먼저 만들어진 ReviewInfo부터 처리
    try:
        using_info = ReviewInfo.objects.filter(used=False).order_by('create_date')[0]
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
            #Sentence.objects.create(content=sent)
            sentiment = sentiment_predict(sent.replace('[^ㄱ-ㅎㅏ-ㅣ가-힣 ]',''), model, tokenizer)
            if sentiment == 1:
                pos_sent_objs.append(Sentence(content=sent)) # 긍정 문장
                pos_sents.append(sent)
            else:
                neg_sent_objs.append(Sentence(content=sent)) # 부정 문장
                neg_sents.append(sent)


    # 긍정 문장, 부정 문장 bulk create
    print("sentece data bulk create")
    Sentence.objects.bulk_create(pos_sent_objs, ignore_conflicts=True)
    Sentence.objects.bulk_create(neg_sent_objs, ignore_conflicts=True)

    # 긍정 키워드, 부정 키워드 얻기
    print('getting keywords')
    pos_keywords = get_stemmed_keywords(pos_sents)
    neg_keywords = get_stemmed_keywords(neg_sents)
    
    # 동사 원형 키워드를 키로, 해당 키워드를 포함하는 문장의 인덱스들을 값으로 가지는 딕셔너리 
    print('getting review indices with verb in reviews')
    pos_verb_indices = get_verb_indices(pos_sents)
    neg_verb_indices = get_verb_indices(neg_sents)

    # 키워드 문장 매칭
    print('matching keywords with sentences')
    reviewzip = match_sentence_with_keyword(reviewzip, pos_sents, pos_verb_indices, pos_keywords, positive=True)
    reviewzip = match_sentence_with_keyword(reviewzip, neg_sents, neg_verb_indices, neg_keywords, positive=False)
    
    # reviewzip object 데이터베이스에 저장
    reviewzip.save()

    # 사용한 리뷰 파일 used = True 처리
    using_info.used = True
    using_info.save()