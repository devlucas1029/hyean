# artWork/views.py
import requests.exceptions
import requests
from django.shortcuts import render
import random  #난수 생성 함수 모듈
import asyncio  #비동기 작업을 위한 asyncio 모듈
import aiohttp  #비동기 HTTP 클라이언트 라이브러리인 aiohttp를 가져오며, 비동기적으로 HTTP 요청 및 응답을 받아올 수 있다.
from django.shortcuts import render  #장고에서 HTML 템프릿을 랜더링하기 위한 render함수 가져옴
from urllib.parse import urlencode  #딕셔너리를 쿼리 문자열로 변환하는데 사용
from haystack.query import SearchQuerySet
from django.http import JsonResponse


# def index(request):
#    return render(request, 'index.html')



class OpenAPIView:
    """templates의 openapi.html만 바라보게 하기 위해 사용"""
    pass

# 이미지 및 작품 데이터 캐싱을 위한 딕셔너리
cached_data = {
    'images': {},  # 이미지 데이터 저장을 위한 빈 딕셔너리
    'art_names': set(),  # 작품명을 저장하기 위한 빈 집합(set)
    'art_dimensions': {},  # 작품의 가로 세로 정보를 저장하기 위한 빈 딕셔너리
    'art_info': {}  # 작품 id, 카테고리 정보를 저장하기 위한 빈 딕셔너리
}

async def fetch(session, url, cache_key=None):
    """비동기적으로 데이터를 가져오고 캐싱처리 진행"""
    global cached_data  # 함수 내에서 cached_data를 수정하기 위해 전역변수 선언

    if cache_key and cache_key in cached_data['images']:  # cache_key가 주어졌고, 딕셔너리에 있다면
        return cached_data['images'][cache_key]  # 캐시된 데이터 반환

    try:
        async with session.get(url) as response:  # 비동기 실행 후, 응답을 response 변수에 저장 후 응답대기
            if response.status != 200:  # HTTP 응답 코드가 200(성공)이 아닌 경우
                return None  # None 반환
            data = await response.json()  # 응답객체에서 json 데이터를 비동기적으로 추출 후 data 저장
            if cache_key:  # cache_key가 있는 경우 이미지값을 딕셔너리에 저장
                cached_data['images'][cache_key] = data
            return data  # 캐시키와 이미지값을 호출 시 반환
    except aiohttp.ClientError as e:  # aiohttp의 클라이언트 에러 발생 시
        print(f"HTTP 요청 오류: {e}")  # 오류 메시지 출력
        return None  # None 반환

async def get_data(base_url, session):
    """비동기적으로 기본 데이터를 가져오고 캐싱"""
    tasks = []  # 비동기 작업들을 저장할 빈 리스트 생성
    for page_number in range(0, 5):  # 0부터 4까지의 페이지에 대해 반복
        params = {  # API 요청을 위한 파라미터 설정
            "serviceKey": "gKat/nvnmi8i9zoiX+JsGzCTsAV75gkvU71APhj8FbnH3yX4kiZMuseZunM0ZpcvKZaMD0XsmeBHW8dVj8HQxg==",
            "pageNo": str(page_number),
            "numOfRows": "10",
            "returnType": "json",
            "engNlty": "Republic of Korea"
        }
        full_url = base_url + '?' + urlencode(params)  # 기본 URL과 매개변수를 조합하여 전체 URL 생성
        tasks.append(fetch(session, full_url))  # 비동기 함수를 호출하여 생성된 URL에서 데이터를 가져오는 작업 생성 후 tasks 리스트에 추가

    responses = await asyncio.gather(*tasks)  # tasks 리스트에 있는 모든 비동기 작업을 동시에 실행

    for response in responses:  # 비동기적으로 실행한 HTTP 요청 결과를 담고 있는 리스트로, 반복문 사용
        if response is None:  # 응답이 없는 경우
            continue  # 반복문 계속 진행
        items = response.get('response', {}).get('body', {}).get('items', [])  # 응답에서 작품 정보를 추출하며, 위 내용중 하나라도 존재하지 않으면 빈 리스트 반환
        if items:  # 응답에서 추출한 작품 정보가 존재하는지 확인
            for item in items:  # 작품 정보가 있을 경우 각 작품 정보에 대해 반복
                art_name = item.get('artNm')  # 작품명 가져오기
                artCd = item.get('artCd')
                if art_name:  # 작품명이 존재할 경우
                    art_name_stripped = art_name.strip()  # 작품명 있을 경우 양쪽 공백 제거 후 변수에 할당
                    if art_name_stripped:  # 작품명이 존재할 경우
                        cached_data['art_names'].add(art_name_stripped)  # 캐싱된 데이터에 작품명 추가. 중복된 작품은 추가하지 않는다.
                        categry = item.get('categry') if item.get('categry') else '기타'  # 작품 카테고리, 없는 경우 기타 입력
                        cached_data['art_dimensions'][art_name_stripped] = {  # 가로, 세로 값 딕셔너리 저장
                            'art_width': generate_dimension(), # 가로 랜덤 생성 후 저장
                            'art_vrticl': generate_dimension(), # 세로 랜덤 생성 후 저장
                        }
                        cached_data['art_info'][art_name_stripped] = { # 작품 일련번호, 카테고리 값 딕셔너리 저장
                            'artCd': artCd, # 작품 일련번호 저장
                            'categry': categry # 작품 카테고리 저장
                        }


async def get_image_data(image_api_url, session):
    """비동기적으로 이미지 데이터를 가져오고 캐싱"""
    image_info_dict = {}  # 이미지 정보를 저장할 빈 딕셔너리 생성
    tasks = []  # 비동기 작업들을 저장할 빈 리스트 생성

    for art_name in cached_data['art_names']:  # 이미지를 가져올 작품명을 반복하여 가져옴
        image_params = {  # 이미지를 가져오기 위한 파라미터 설정
            "serviceKey": "gKat/nvnmi8i9zoiX+JsGzCTsAV75gkvU71APhj8FbnH3yX4kiZMuseZunM0ZpcvKZaMD0XsmeBHW8dVj8HQxg==",
            "pageNo": "1",
            "numOfRows": "10",
            "returnType": "json",
            "artNm": art_name
        }
        full_url = image_api_url + '?' + urlencode(image_params)  # 이미지 API의 전체 URL 생성
        tasks.append(fetch(session, full_url, cache_key=full_url))  # 이미지 데이터를 가져오는 비동기 함수 fetch 호출

    responses = await asyncio.gather(*tasks)  # tasks 리스트에 있는 모든 비동기 작업을 동시에 실행

    for image_response in responses:
        if image_response:  # 이미지 응답이 존재하는 경우
            image_data = image_response.get('response', {}).get('body', {}).get('items', [])  # 이미지 데이터가 있는지 확인
            if image_data:  # 이미지 데이터가 있는 경우
                for image_item in image_data:  # 이미지 항목을 반복하여 가져옴
                    art_name = image_item.get('artNm', '')  # 작품명 가져오기
                    file_name = image_item.get('fileNm', '')  # 파일명 가져오기
                    file_url = image_item.get('fileUrl', '')  # 파일 URL 가져오기
                    artCd = image_item.get('artCd', '') # 작품 일련번호 가져오기
                    if art_name and file_name and file_url:  # 작품명, 파일명, 파일 URL이 모두 존재하는 경우에만 처리
                        file_name_prefix = file_name[:4]  # 파일 이름의 앞 4글자 추출
                        art_width = generate_dimension()  # 가로 크기 랜덤 생성
                        art_vrticl = generate_dimension()  # 세로 크기 랜덤 생성
                        price = random.randint(100, 1000) * 10000
                        image_info_dict[file_name_prefix] = {  # 이미지 정보를 딕셔너리에 저장
                            'art_name': art_name,  # 작품명 저장
                            'file_name': file_name,  # 파일명 저장
                            'file_url': file_url,  # 파일 URL 저장
                            'art_width': art_width,  # 가로 길이 저장
                            'art_vrticl': art_vrticl,  # 세로 길이 저장
                            'artCd': artCd,  # 작품 일련번호 저장
                            'categry': cached_data['art_info'].get(art_name, {}).get('categry', ''),  # 카테고리 저장
                            'price': price
                        }
                        cached_data['images'][artCd] = { # artCd를 키로 사용하여 이미지 정보를 캐싱
                            'art_name': art_name,  # 작품명 저장
                            'file_name': file_name,  # 파일명 저장
                            'file_url': file_url,  # 파일 URL 저장
                            'art_width': art_width,  # 가로 길이 저장
                            'art_vrticl': art_vrticl,  # 세로 길이 저장
                            'price': price,
                        }

    return list(image_info_dict.values())  # 이미지 정보 딕셔너리의 값을 리스트로 반환하여 저장

def generate_dimension():
    """가로, 세로 크기 랜덤 생성"""
    return random.randint(100, 300)  # 100에서 300 사이의 랜덤한 값 반환

async def openapi_view(request):
    """View 함수로, 비동기적으로 데이터를 가져오고 렌더링"""
    base_url = "http://apis.data.go.kr/5710000/benlService/nltyArtList"  # 기본 URL 설정
    image_api_url = "http://apis.data.go.kr/5710000/benlService/artImgList"  # 이미지 API URL 설정

    async with aiohttp.ClientSession() as session:  # aiohttp의 ClientSession 객체를 사용하여 비동기적으로 세션 생성
        await get_data(base_url, session)  # get_data 함수를 사용하여 작품 정보를 가져오며, 비동기적으로 실행
        image_info_list = await get_image_data(image_api_url, session)  # 이미지 정보를 비동기적으로 가져옴

    # 데이터를 정상적으로 불러오지 못한 경우, 빈 리스트 또는 오류 메시지 출력
    if not image_info_list:  # 이미지 정보 리스트가 비어있는 경우
        image_info_list = [{"art_name": "자료 없음", "file_url": "", "price": 0}]  # "No data available" 메시지 출력

    return render(request, 'index.html', {'image_info_list': image_info_list})  # 가져온 데이터

async def search(request):  # 서치 함수임!!!!!!!!!!!!!!!!!!!!!!!
    image_api_url = "http://apis.data.go.kr/5710000/benlService/artImgList"

    search_query = request.GET.get('q', '')
    print(f"검색한 내용: {search_query}")

    art_list = []

    if search_query:  # 검색어가 있는 경우에만 API 요청
        async with aiohttp.ClientSession() as session:
            try:
                image_params = {
                    "serviceKey": "gKat/nvnmi8i9zoiX+JsGzCTsAV75gkvU71APhj8FbnH3yX4kiZMuseZunM0ZpcvKZaMD0XsmeBHW8dVj8HQxg==",
                    "pageNo": "0",
                    "numOfRows": "100",
                    "returnType": "json",
                    "artNm": search_query
                }
                full_image_url = image_api_url + '?' + urlencode(image_params)
                #print(f"요청 URL: {full_image_url}")
                image_response = await fetch(session, full_image_url)
                #print(f"API 응답: {image_response}")

                if image_response and 'response' in image_response and 'body' in image_response[
                    'response'] and 'items' in image_response['response']['body']:
                    items = image_response['response']['body']['items']
                    if isinstance(items, dict):
                        items = [items]

                    seen_art_cds = set() # 이미 추가된 일련번호를 저장할 집합

                    for item in items:
                        art_cd = item.get('artCd', '')
                        art_name = item.get('artNm', '')
                        if art_cd in seen_art_cds: # 이미 추가된 일련번호면 건너뛰기
                            continue
                        if art_name and search_query in art_name:
                            price = random.randint(1000,10000) * 10000 # 랜덤 가격 생성
                            art_info = {
                                'artCd': item.get('artCd', ''),
                                'art_name': art_name,
                                'fileNm': item.get('fileNm', ''),
                                'image_url': item.get('fileUrl', ''),
                                'price': price #랜덤 가격 추가
                            }
                            art_list.append(art_info)
                            seen_art_cds.add(art_cd) # 집합엥 추가하여 중복 체크
                    #print(f"리스트 확인: {art_list}")

            except Exception as e:
                print(f"API 요청 실패: {e}")

    print(f"검색어: {search_query}, 검색결과 {art_list}")
    return render(request, 'search.html', {'search_query': search_query, 'art_list': art_list})


async def infiniteView(request):
    """View 함수로, 비동기적으로 데이터를 가져오고 렌더링"""
    base_url = "http://apis.data.go.kr/5710000/benlService/nltyArtList"  # 기본 URL 설정
    image_api_url = "http://apis.data.go.kr/5710000/benlService/artImgList"  # 이미지 API URL 설정

    async with aiohttp.ClientSession() as session:  # aiohttp의 ClientSession 객체를 사용하여 비동기적으로 세션 생성
        await get_data(base_url, session)  # get_data 함수를 사용하여 작품 정보를 가져오며, 비동기적으로 실행
        image_info_list = await get_image_data(image_api_url, session)  # 이미지 정보를 비동기적으로 가져옴

    # 데이터를 정상적으로 불러오지 못한 경우, 빈 리스트 또는 오류 메시지 출력
    if not image_info_list:  # 이미지 정보 리스트가 비어있는 경우
        image_info_list = [{"art_name": "자료 없음", "file_url": "", "price": 0}]  # "No data available" 메시지 출력
    return JsonResponse({'image_info_list': image_info_list})