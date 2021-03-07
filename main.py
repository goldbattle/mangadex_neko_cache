import os

from flask import Flask, jsonify, abort, send_from_directory  # pip install flask

import download  # pip install cloudscraper

app = Flask(__name__)
active_downloads = []


@app.route('/')
def manga_listing():
    search_dir = os.path.join(os.getcwd(), "download")
    if not os.path.exists(search_dir):
        abort(404)
    return jsonify(os.listdir(search_dir))


@app.route('/manga/<mangaid>/', methods=['GET'])
def manga_info(mangaid):
    search_dir = os.path.join(os.getcwd(), "download", str(mangaid))
    if not os.path.exists(search_dir):
        abort(404)
    directories = []
    for dir_c in os.listdir(search_dir):
        dir_i = os.path.join(search_dir, dir_c)
        if len(os.listdir(dir_i)) != 0:
            directories.append(dir_i)
    if len(directories) == 0:
        abort(404)
    return jsonify(directories)


@app.route('/chapter/<chapterid>/', methods=['GET'])
def manga_chapter(chapterid):
    search_dir = os.path.join(os.getcwd(), "download")
    if not os.path.exists(search_dir):
        abort(404)
    found = False
    search_dir_chapter = ""
    for dir_m in os.listdir(search_dir):
        for dir_c in os.listdir(os.path.join(search_dir, dir_m)):
            if os.path.basename(dir_c) == chapterid:
                search_dir_chapter = os.path.join(search_dir, dir_m, dir_c)
                found = True
                break
        if found:
            break
    if not found or not os.path.exists(search_dir_chapter):
        abort(404)
    if len(os.listdir(search_dir_chapter)) == 0:
        abort(404)
    return jsonify(os.listdir(search_dir_chapter))


@app.route('/download/<mangaid>/', methods=['GET'])
def manga_download(mangaid):
    # debug information
    print(f"downloading {mangaid}")
    print(f"threads {len(active_downloads)}")

    # if our manga exists in our db, report the status
    thread_to_delete = -1
    for idx, thread in enumerate(active_downloads):
        if thread.manga_id == mangaid:
            if not thread.is_alive():
                thread_to_delete = idx
                break
            return jsonify(thread.information())

    # call our download utility
    thread = download.Download(mangaid, "gb")
    thread.start()
    active_downloads.append(thread)

    # if the thread has finished, then we can return the result and remove
    # this means next time we call on this, it will try to re-download if errors
    if thread_to_delete != -1:
        info = active_downloads[thread_to_delete].information()
        del active_downloads[thread_to_delete]
        return jsonify(info)

    # return the status of the thread
    return jsonify(thread.information())


@app.route('/images/<path:path>')
def image_fetch(path):
    search_dir = os.path.join(os.getcwd(), "download")
    if not os.path.exists(search_dir):
        abort(404)
    return send_from_directory(search_dir, path)


if __name__ == "__main__":
    app.run(debug=True)
