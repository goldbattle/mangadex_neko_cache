
# MangaDex Neko Cache

The goal of this project is to provide a small server that people can host on their local network to cache frequently
downloaded MangaDex chapters on. The current code provide some small APIs to query the currently downloaded manga,
chapters, and image lists. Additionally, a request can be made to the server to try to download a specific manga.
The server will try to download the latest chapters for that manga if possible.


### Dependencies

This has been tested on Python 3.7 on a windows machine with PyCharm.
You will need to download the following packages and ensure you have enough space on disk to download images.

```
pip install flask
pip install cloudscraper
```




### API Endpoints

- **/** -- This will list all the current manga that have been downloaded on the server.

```
[
    "43484",
    "46051"
]
```

- **/manga/<manga_id>/** -- This will list all the current chapters for this that have been downloaded on the server.

```
[
    "0e4811ad113ff993a588a0b06e2646c7",
    "8712b21a21bab52733ec3e64b21a8d90"
]
```

- **/chapter/<chapter_hash>/** -- This will list all the current images for this that have been downloaded on the server.

```
[
    "001.jpg",
    "002.jpg",
    "003.jpg",
    "004.jpg",
    "005.jpg",
    "006.jpg",
    "007.jpg",
    "008.jpg",
    "009.jpg"
]
```

- **/download/<manga_id>/** -- This will try to download the requested manga. This can also be queried to get what the status of the current download is at.

```
{
    "mangaId": "46051",
    "message": "",
    "message_error": "MangaDex code 502 error: Expecting value: line 1 column 1 (char 0)",
    "percent": 0,
    "status": 502
}
```






