import html
import json
import os
import re
import threading
import requests

from ratelimit import limits, RateLimitException  # pip install ratelimit
from backoff import on_exception, expo  # pip install backoff

# only have one thread at a time go out to mangadex
# https://stackoverflow.com/a/23524451
threadLimiter = threading.BoundedSemaphore(1)

def pad_filename(str):
    digits = re.compile('(\\d+)')
    pos = digits.search(str)
    if pos:
        return str[1:pos.start()] + pos.group(1).zfill(3) + str[pos.end():]
    else:
        return str


def float_conversion(x):
    try:
        x = float(x)
    except ValueError:  # empty string for oneshot
        x = 0
    return x


def zpad(num):
    if "." in num:
        parts = num.split('.')
        return "{}.{}".format(parts[0].zfill(3), parts[1])
    else:
        return num.zfill(3)


@on_exception(expo, RateLimitException, max_tries=3)
@limits(calls=60, period=60)
def call_mangadex_api(url):
    cookies = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/77.0'
    }
    response = requests.get(url, headers=headers, cookies=cookies)
    if response.status_code != 200:
        raise Exception('API response: {}'.format(response.status_code))
    return response


@on_exception(expo, RateLimitException, max_tries=3)
@limits(calls=200, period=60)
def call_mangadex_images(url):
    cookies = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/77.0'
    }
    response = requests.get(url, headers=headers, cookies=cookies)
    if response.status_code != 200:
        raise Exception('API response: {}'.format(response.status_code))
    return response


class Download(threading.Thread):
    total_file_count = 0
    total_processed_count = 0

    manga_id = 0
    lang_code = "gb"
    tld = "org"

    error_code = 200
    error_message = ""
    message = ""

    def __init__(self, manga_id, lang_code, tld="org"):
        threading.Thread.__init__(self)
        self.manga_id = manga_id
        self.lang_code = lang_code
        self.tld = tld

    def information(self):
        return {
            "mangaId": self.manga_id,
            "status": self.error_code,
            "message_error": self.error_message,
            "message": self.message,
            "percent": self.percent_done(),
        }

    def percent_done(self):
        if self.total_file_count == 0:
            return 0.0
        return float(self.total_processed_count) / float(self.total_file_count) * 100.0

    def run(self):
        global threadLimiter
        threadLimiter.acquire()
        try:
            self.run_self()
        except Exception as err:
            self.error_code = 500
            self.error_message += str(err)
        finally:
            threadLimiter.release()

    def run_self(self):

        # grab manga info json from api
        url = "https://api.mangadex.{}/v2/manga/{}/?include=chapters".format(self.tld, self.manga_id)
        response_code = 200
        try:
            print(url)
            r = call_mangadex_api(url)
            response_code = r.status_code
            print(r.text)
            jason = json.loads(r.text)
        except (json.decoder.JSONDecodeError, ValueError) as err:
            self.error_code = response_code
            self.error_message += ("MangaDex code {} error: {}".format(response_code, err))
            return
        except:
            self.error_code = response_code
            self.error_message += "Error with URL: {}".format(url)
            return

        try:
            title = jason["data"]["manga"]["title"]
        except:
            self.error_code = 404
            self.error_message += "Invalid ID specified"
            return
        self.message += "TITLE: {}\n".format(html.unescape(title))

        # find out which are available to dl
        chaps_to_dl = []
        chapter_num = None
        for i in jason["data"]["chapters"]:
            if i["language"] == self.lang_code:
                chaps_to_dl.append((str(chapter_num), i["id"]))
        chaps_to_dl.sort(key=lambda x: float_conversion(x[0]))

        # get chapter(s) json
        chapters = []
        chapter_images = []
        for chapter_info in chaps_to_dl:

            # download the page
            self.message += "Getting chapter API {}...\n".format(chapter_info[1])
            url = "https://api.mangadex.{}/v2/chapter/{}/".format(self.tld, chapter_info[1])
            response_code = 200
            try:
                print(url)
                r = call_mangadex_api(url)
                response_code = r.status_code
                print(r.text)
                chapter = json.loads(r.text)
            except (json.decoder.JSONDecodeError, ValueError) as err:
                self.error_code = response_code
                self.error_message += ("MangaDex code {} error: {}\n".format(response_code, err))
                continue
            except:
                self.error_code = response_code
                self.error_message += "Error with URL: {}\n".format(url)
                continue

            # get url list, might fail if no images are present
            try:
                images = []
                images_fallback = []
                server = chapter["data"]["server"]
                hashcode = chapter["data"]["hash"]
                for page in chapter["data"]["pages"]:
                    images.append("{}{}/{}".format(server, hashcode, page))
                chapters.append(chapter)
                chapter_images.append(images)
                self.total_file_count += len(images)
            except:
                pass

        # now lets loop through our images and actually download them
        for idx, chapter in enumerate(chapters):

            # get our corresponding chapter
            images = chapter_images[idx]

            # download images
            for pagenum, url in enumerate(images, 1):

                # get the save location
                filename = os.path.basename(url)
                ext = os.path.splitext(filename)[1]
                dest_folder = os.path.join(os.getcwd(), "download", str(chapter["data"]["mangaId"]),
                                           str(chapter["data"]["id"]))
                if not os.path.exists(dest_folder):
                    os.makedirs(dest_folder)
                dest_filename = pad_filename("{}{}".format(pagenum, ext))
                outfile = os.path.join(dest_folder, dest_filename)

                # if the file is already there, then skip it!
                if os.path.exists(outfile):
                    self.message += " Skipping {}.\n".format(pagenum)
                    self.total_processed_count += 1
                    continue

                # actually try to download the file
                # will silently try again if it fails
                try:
                    print(url)
                    r = call_mangadex_images(url)
                    assert r.status_code == 200
                    with open(outfile, 'wb') as f:
                        f.write(r.content)
                        self.message += " Downloaded page {}.\n".format(pagenum)
                except Exception as e:
                    self.error_code = 500
                    self.error_message += " Skipping download of page {} - {}.\n".format(pagenum, e)
                self.total_processed_count += 1

        self.message += "Done!"
