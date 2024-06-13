from flask import Flask, render_template
import os
from flask_sqlalchemy import SQLAlchemy

import urllib.request as req

import requests
from bs4 import BeautifulSoup


basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = \
    'sqlite:///' + os.path.join(basedir, 'database.db')

db = SQLAlchemy(app)

class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_cd = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    content = db.Column(db.String, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'{self.movie_cd} : {self.content} by {self.username}, rating: {self.rating}'

with app.app_context():
    db.create_all()

def get_box_office():
    code=req.urlopen("http://www.cgv.co.kr/movies/?lt=1&ft=0")
    soup=BeautifulSoup(code, "html.parser")

    movies = []
    movie_list = soup.select("li")
    for movie in movie_list:
        rank = movie.select_one("strong.rank")
        # info = movie.select_one("div.box-contents")
        title = movie.select_one("strong.title")
        img_url = movie.select_one("img")

        if title and img_url:  # title과 img_url이 모두 존재하는 경우에만 추가
            movies.append({
                'title': title.string,
                'image': img_url.get("src"),
                'rank': rank.string
            })

    return movies

@app.route('/')
def movie():
    movies = get_box_office()

    print(get_box_office())
    return render_template('movie.html', movies=movies)

if __name__ == "__main__":
    app.run(debug=True)