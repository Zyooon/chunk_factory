import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from apps.crawler.config import (
    MIN_TEXT_LENGTH,
    NAVER_BLOG_MAX_ARTICLES_PER_KEYWORD,
    NAVER_BLOG_SEARCH_KEYWORDS,
    NAVER_BLOG_SEARCH_MAX_PAGES,
    NAVER_BLOG_URLS,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from apps.crawler.storage import (
    add_crawl_log_entry,
    is_already_crawled,
    load_crawl_log,
    save_crawl_log,
    save_text_document,
)
from apps.crawler.utils import get_collected_at, normalize_whitespace, polite_sleep


# ============================================================
# naver_blog.py
# ------------------------------------------------------------
# 네이버 블로그 검색 결과에서 글 URL을 찾고,
# 각 블로그 글에서 제목과 본문을 추출해 txt로 저장하는 모듈입니다.
#
# 전체 흐름:
#
# 1. 키워드로 네이버 블로그 검색 URL 생성
# 2. 검색 결과 HTML 요청
# 3. 검색 결과에서 blog.naver.com 글 링크 추출
# 4. 각 블로그 글에 접근
# 5. mainFrame iframe이 있으면 실제 본문 URL로 재요청
# 6. 제목과 본문 텍스트 추출
# 7. crawled_data/naver_blog/에 txt 저장
# ============================================================


@dataclass
class NaverBlogArticle:
    """
    네이버 블로그 글 하나의 수집 결과입니다.
    """

    title: str
    url: str
    body_text: str


def fetch_html(url: str) -> str | None:
    """
    URL에 접근해서 HTML 문자열을 가져옵니다.

    네이버는 User-Agent 없이 요청하면 차단될 가능성이 있으므로
    반드시 User-Agent를 포함합니다.

    Args:
        url:
            요청할 URL입니다.

    Returns:
        HTML 문자열 또는 None입니다.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return response.text

    except requests.RequestException as error:
        print(f"[NAVER][FETCH ERROR] url={url}")
        print(f"[NAVER][FETCH ERROR] detail={error}")
        return None


def build_naver_blog_search_url(keyword: str, page: int = 1) -> str:
    """
    네이버 블로그 검색 URL을 생성합니다.

    Args:
        keyword:
            검색 키워드입니다.

        page:
            검색 결과 페이지 번호입니다.
            네이버 검색은 start 파라미터가 1, 11, 21... 형태로 증가합니다.

    Returns:
        네이버 블로그 검색 URL입니다.
    """
    start = 1 + ((page - 1) * 10)

    params = {
        "where": "blog",
        "query": keyword,
        "start": start,
    }

    return "https://search.naver.com/search.naver?" + urlencode(params)


def is_probable_naver_blog_article_url(url: str) -> bool:
    """
    URL이 네이버 블로그 글 URL일 가능성이 높은지 판단합니다.

    검색 결과에는 블로그 홈, 프로필, 카테고리 등도 섞일 수 있습니다.
    그래서 실제 글 URL로 보이는 것만 최대한 남깁니다.

    허용 예:
    - https://blog.naver.com/blog_id/223456789012
    - https://m.blog.naver.com/blog_id/223456789012
    - https://blog.naver.com/PostView.naver?blogId=...&logNo=...

    Args:
        url:
            검사할 URL입니다.

    Returns:
        글 URL로 보이면 True, 아니면 False입니다.
    """
    parsed = urlparse(url)

    if "blog.naver.com" not in parsed.netloc:
        return False

    # PostView.naver 형식
    if "PostView.naver" in parsed.path:
        query = parse_qs(parsed.query)
        return "blogId" in query and "logNo" in query

    # /블로그아이디/글번호 형식
    # 예: /abc123/223456789012
    path_parts = [part for part in parsed.path.split("/") if part]

    if len(path_parts) >= 2:
        maybe_log_no = path_parts[1]
        if re.fullmatch(r"\d{8,}", maybe_log_no):
            return True

    return False


def normalize_naver_blog_url(url: str) -> str:
    """
    네이버 블로그 URL을 가능한 한 표준 형태로 정리합니다.

    모바일 주소 m.blog.naver.com은 blog.naver.com으로 바꿉니다.
    네이버 검색 결과에서 불필요한 fragment가 붙은 경우도 제거합니다.

    Args:
        url:
            원본 URL입니다.

    Returns:
        정리된 URL입니다.
    """
    parsed = urlparse(url)

    scheme = "https"
    netloc = parsed.netloc.replace("m.blog.naver.com", "blog.naver.com")
    path = parsed.path
    query = parsed.query

    normalized = parsed._replace(
        scheme=scheme,
        netloc=netloc,
        path=path,
        query=query,
        fragment="",
    )

    return normalized.geturl()


def extract_blog_links_from_search(html: str, max_links: int) -> list[str]:
    """
    네이버 블로그 검색 결과 HTML에서 블로그 글 URL을 추출합니다.

    특정 CSS selector 하나에 의존하지 않고,
    전체 a[href] 중 blog.naver.com 링크를 찾은 뒤
    실제 글 URL 가능성이 높은 것만 필터링합니다.

    Args:
        html:
            검색 결과 HTML입니다.

        max_links:
            최대 추출 개수입니다.

    Returns:
        중복 제거된 블로그 글 URL 목록입니다.
    """
    soup = BeautifulSoup(html, "lxml")

    links: list[str] = []
    seen: set[str] = set()

    for a_tag in soup.select("a[href]"):
        href = a_tag.get("href", "").strip()

        if not href:
            continue

        if "blog.naver.com" not in href:
            continue

        normalized_url = normalize_naver_blog_url(href)

        if not is_probable_naver_blog_article_url(normalized_url):
            continue

        if normalized_url in seen:
            continue

        seen.add(normalized_url)
        links.append(normalized_url)

        if len(links) >= max_links:
            break

    return links


def search_naver_blog_article_urls(keyword: str) -> list[str]:
    """
    키워드 하나로 네이버 블로그 검색을 수행하고 글 URL 목록을 반환합니다.

    Args:
        keyword:
            검색 키워드입니다.

    Returns:
        네이버 블로그 글 URL 목록입니다.
    """
    print(f"[NAVER][SEARCH] keyword={keyword}")

    found_urls: list[str] = []
    seen: set[str] = set()

    for page in range(1, NAVER_BLOG_SEARCH_MAX_PAGES + 1):
        search_url = build_naver_blog_search_url(keyword=keyword, page=page)

        print(f"[NAVER][SEARCH] page={page}, url={search_url}")

        polite_sleep()

        html = fetch_html(search_url)

        if html is None:
            continue

        remaining_count = NAVER_BLOG_MAX_ARTICLES_PER_KEYWORD - len(found_urls)

        if remaining_count <= 0:
            break

        links = extract_blog_links_from_search(
            html=html,
            max_links=remaining_count,
        )

        for link in links:
            if link in seen:
                continue

            seen.add(link)
            found_urls.append(link)

            if len(found_urls) >= NAVER_BLOG_MAX_ARTICLES_PER_KEYWORD:
                break

        if len(found_urls) >= NAVER_BLOG_MAX_ARTICLES_PER_KEYWORD:
            break

    print(f"[NAVER][SEARCH] found={len(found_urls)}")

    for index, url in enumerate(found_urls, start=1):
        print(f"[NAVER][SEARCH] {index}. {url}")

    return found_urls


def resolve_naver_blog_iframe(original_url: str, html: str) -> tuple[str, str]:
    """
    네이버 블로그 원본 HTML에서 mainFrame iframe을 찾아 실제 본문 HTML을 가져옵니다.

    네이버 블로그 글은 보통 iframe#mainFrame 안에 본문이 있습니다.
    따라서 원본 페이지 HTML만 보면 본문이 없을 수 있습니다.

    Args:
        original_url:
            검색 결과에서 얻은 원본 URL입니다.

        html:
            원본 URL의 HTML입니다.

    Returns:
        (실제 본문 URL, 실제 본문 HTML) 튜플입니다.
    """
    soup = BeautifulSoup(html, "lxml")
    iframe = soup.select_one("iframe#mainFrame")

    if iframe is None:
        return original_url, html

    iframe_src = iframe.get("src")

    if not iframe_src:
        return original_url, html

    article_url = urljoin("https://blog.naver.com", iframe_src)

    print("[NAVER] iframe detected.")
    print(f"[NAVER] resolved article url: {article_url}")

    polite_sleep()

    iframe_html = fetch_html(article_url)

    if iframe_html is None:
        return original_url, html

    return article_url, iframe_html


def extract_title(soup: BeautifulSoup) -> str:
    """
    네이버 블로그 HTML에서 제목을 추출합니다.

    네이버 블로그 에디터 버전에 따라 제목 selector가 다를 수 있으므로
    여러 selector를 순서대로 시도합니다.
    """
    title_selectors = [
        ".se-title-text",
        ".se-title-text span",
        ".pcol1",
        ".htitle",
        "h3.se_textarea",
        "title",
    ]

    for selector in title_selectors:
        element = soup.select_one(selector)

        if element is None:
            continue

        title = normalize_whitespace(element.get_text(" ", strip=True))

        if not title:
            continue

        title = title.replace(": 네이버 블로그", "").strip()

        if title:
            return title

    return "untitled_naver_blog"


def remove_noise_elements(soup: BeautifulSoup) -> None:
    """
    본문 추출 전 불필요한 HTML 요소를 제거합니다.
    """
    for tag in soup.select("script, style, noscript, iframe"):
        tag.decompose()

    noise_selectors = [
        ".u_likeit",
        ".post_btn",
        ".wrap_postcomment",
        ".area_comment",
        ".section_t1",
        ".blog2_series",
        ".lyr_popup",
        ".spi_default",
        ".post_footer",
        ".comment_module",
        ".naver-splugin",
    ]

    for selector in noise_selectors:
        for tag in soup.select(selector):
            tag.decompose()


def extract_body_text(soup: BeautifulSoup) -> str:
    """
    네이버 블로그 HTML에서 본문 텍스트를 추출합니다.
    """
    remove_noise_elements(soup)

    body_selectors = [
        "div.se-main-container",
        "div#postViewArea",
        "div.post-view",
        "div.se_component_wrap",
        "div#post-view",
    ]

    for selector in body_selectors:
        body = soup.select_one(selector)

        if body is None:
            continue

        text = body.get_text(" ", strip=True)
        text = normalize_whitespace(text)

        if text:
            return text

    body = soup.select_one("body")

    if body:
        return normalize_whitespace(body.get_text(" ", strip=True))

    return ""


def parse_naver_blog_article(url: str, html: str) -> NaverBlogArticle | None:
    """
    네이버 블로그 본문 HTML에서 제목과 본문을 추출합니다.
    """
    soup = BeautifulSoup(html, "lxml")

    title = extract_title(soup)
    body_text = extract_body_text(soup)

    if len(body_text) < MIN_TEXT_LENGTH:
        print(
            f"[NAVER][SKIP] body text too short. "
            f"title={title}, length={len(body_text)}"
        )
        return None

    return NaverBlogArticle(
        title=title,
        url=url,
        body_text=body_text,
    )


def collect_single_naver_blog(url: str, log: dict, keyword: str = "") -> bool:
    """
    네이버 블로그 글 URL 1개를 수집하고 txt 파일로 저장합니다.
    """
    print(f"[NAVER] collecting: {url}")

    polite_sleep()

    original_html = fetch_html(url)

    if original_html is None:
        return False

    article_url, article_html = resolve_naver_blog_iframe(
        original_url=url,
        html=original_html,
    )

    article = parse_naver_blog_article(
        url=article_url,
        html=article_html,
    )

    if article is None:
        return False

    saved_path = save_text_document(
        source_type="naver_blog",
        title=article.title,
        url=article.url,
        collected_at=get_collected_at(),
        body_text=article.body_text,
        extra_metadata={
            "collector": "naver_blog",
        },
        keyword=keyword,
    )

    print(f"[NAVER] saved: {saved_path}")

    add_crawl_log_entry(url, "naver_blog", article.title, log)
    save_crawl_log(log)

    return True


def collect_naver_blogs_from_direct_urls(log: dict) -> tuple[int, int]:
    """
    config.py의 NAVER_BLOG_URLS에 직접 넣은 URL들을 수집합니다.

    Returns:
        (성공 개수, 실패 개수)
    """
    if not NAVER_BLOG_URLS:
        print("[NAVER][DIRECT] no urls configured.")
        return 0, 0

    success_count = 0
    fail_count = 0

    for url in NAVER_BLOG_URLS:
        if is_already_crawled(url, log):
            print(f"[NAVER][SKIP] already crawled: {url}")
            continue

        if collect_single_naver_blog(url, log):
            success_count += 1
        else:
            fail_count += 1

    print(f"[NAVER][DIRECT] completed. success={success_count}, fail={fail_count}")

    return success_count, fail_count


def collect_naver_blogs_from_search(log: dict) -> tuple[int, int]:
    """
    config.py의 NAVER_BLOG_SEARCH_KEYWORDS를 기준으로 검색 수집을 수행합니다.

    Returns:
        (성공 개수, 실패 개수)
    """
    if not NAVER_BLOG_SEARCH_KEYWORDS:
        print("[NAVER][SEARCH] no keywords configured.")
        return 0, 0

    success_count = 0
    fail_count = 0

    global_seen_urls: set[str] = set()

    for keyword in NAVER_BLOG_SEARCH_KEYWORDS:
        article_urls = search_naver_blog_article_urls(keyword)

        for article_url in article_urls:
            if is_already_crawled(article_url, log):
                print(f"[NAVER][SKIP] already crawled: {article_url}")
                continue

            if article_url in global_seen_urls:
                print(f"[NAVER][SKIP] duplicated url: {article_url}")
                continue

            global_seen_urls.add(article_url)

            if collect_single_naver_blog(article_url, log, keyword=keyword):
                success_count += 1
            else:
                fail_count += 1

    print(f"[NAVER][SEARCH] completed. success={success_count}, fail={fail_count}")

    return success_count, fail_count


def collect_naver_blogs() -> tuple[int, int]:
    """
    네이버 블로그 전체 수집 실행 함수입니다.

    두 가지 방식을 모두 지원합니다.

    1. NAVER_BLOG_URLS에 직접 입력한 글 URL 수집
    2. NAVER_BLOG_SEARCH_KEYWORDS로 검색해서 글 URL을 찾은 뒤 수집

    Returns:
        (전체 성공 개수, 전체 실패 개수)
    """
    log = load_crawl_log()
    direct_success, direct_fail = collect_naver_blogs_from_direct_urls(log)
    search_success, search_fail = collect_naver_blogs_from_search(log)

    total_success = direct_success + search_success
    total_fail = direct_fail + search_fail

    print(f"[NAVER] total completed. success={total_success}, fail={total_fail}")

    return total_success, total_fail