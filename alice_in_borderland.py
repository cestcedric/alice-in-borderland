import os
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed


START_URL = "https://alice-in-borderland.com/manga/alice-in-borderland-chapter-1/"
OUTPUT_PATH = os.path.join(os.getcwd(), "pdf")
COMPRESSION = 100
CONCURRENCY = 8


def handle_chapter(url: str) -> str | None:
    title, filename = get_chapter_name(url)
    print(title)

    # Still load page even if we could check for existence: we want the link to the next chapter
    chapter = requests.get(url)
    soup = BeautifulSoup(chapter.content, "html.parser")
    content = soup.find("div", class_="entry-content").find("p")

    output_path = os.path.join(OUTPUT_PATH, filename)
    if os.path.isfile(output_path):
        print(f"Already exists!")
    else:
        pages = get_pages(content)
        create_pdf(pages, output_path)

    return get_next_chapter_url(soup)


def get_chapter_name(url: str) -> tuple[str]:
    parts = url.split("/")[-2].split("-")
    title = " ".join(word[0].upper() + word[1:] for word in parts)
    filename = "_".join(parts) + ".pdf"
    return title, filename


def get_pages(soup: BeautifulSoup) -> list:
    page_links = [img["src"] for img in soup.find_all("img")]
    pages = [None] * len(page_links)

    def download(params: tuple[str, int]) -> None:
        url, idx = params
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        if img.mode != "RGB":
            img = img.convert("RGB")

        if COMPRESSION < 100:
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=COMPRESSION)
            buffer.seek(0)
            img = Image.open(buffer)

        pages[idx] = img
        return f"Page {idx + 1} / {len(page_links)}"

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [
            executor.submit(download, (url, idx)) for idx, url in enumerate(page_links)
        ]
    for future in as_completed(futures):
        print(future.result())

    return pages


def get_next_chapter_url(soup: BeautifulSoup) -> str | None:
    nav_next = soup.find("div", class_="nav-next")

    if nav_next is None:
        return None

    return nav_next.find("a")["href"]


def create_pdf(pages: list, output_path: str) -> None:
    pages[0].save(output_path, save_all=True, append_images=pages[1:])


if __name__ == "__main__":
    url = START_URL

    while url is not None:
        url = handle_chapter(url)

    print("Done!")
