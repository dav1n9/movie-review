from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, g
import os
from flask_sqlalchemy import SQLAlchemy

import urllib.request as req

import requests
from bs4 import BeautifulSoup
from werkzeug.security import generate_password_hash, check_password_hash


basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')
app.secret_key = 's3cr3t_k3y_1234567890'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'{self.userid} : {self.email}'

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_cd = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User', backref=db.backref('review_set')) 
    content = db.Column(db.String, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'{self.movie_cd} : {self.content} by {self.username}, rating: {self.rating}'

with app.app_context():
    db.create_all()



#== 로그인된 사용자 전역변수로 관리==#
@app.before_request
def load_logged_in_user():
    user_id = session.get('userid')
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.filter_by(userid=user_id).first()

# 마이페이지
@app.route('/mypage')
def mypage():

    review_list = Review.query.filter_by(user = g.user).all()

    reviews = {
        'review_list': review_list,
        'len' : len(review_list),
    }

    return render_template('mypage.html', data=reviews)



# 영화 정보 크롤링
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

# 메인 페이지
@app.route('/movie')
def movie():
    movies = get_box_office()

    query = request.args.get('query')

    res = requests.get(
        f"http://kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieList.json?key=f5eef3421c602c6cb7ea224104795888&movieNm={query}"
    )
    rjson = res.json()
    movieNm = rjson["movieListResult"]["movieList"][0]['movieNm']

    return render_template('movie.html', movies=movies, movie_Name=movieNm)

# 회원가입
@app.route('/signup', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # id_receive = request.form.get('id')
        userid_receive = request.form.get('userid')
        username_receive = request.form.get('username')
        email_receive = request.form.get('email')
        password_receive = request.form.get('password')

        hashed_password = generate_password_hash(password_receive)

        user = User(userid=userid_receive, username=username_receive, email=email_receive, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('movie'))
    
    return render_template('signup.html')

# 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form.get('userid')
        password = request.form.get('password')

        user = User.query.filter_by(userid=userid).first()

        if user is None or not check_password_hash(user.password, password):
            return jsonify({'msg': 'Invalid username or password'}), 401

        session['logged_in'] = True
        session['userid'] = user.userid

        return redirect(url_for('movie'))
    
    return render_template('login.html')

# 로그인 상태 확인
@app.route('/logged_in', methods=['GET'])
def logged_in():
    if 'logged_in' in session:
        return jsonify({'msg': 'User is logged in'}), 200
    else:
        return jsonify({'msg': 'User is not logged in'}), 401

# 로그인 사용자 이름 가져오기
@app.route('/username', methods=['GET'])
def get_username():
    if 'logged_in' in session:
        userid = session['userid']
        user = User.query.filter_by(userid=userid).first()
        if user:
            return jsonify({'username': user.username}), 200
        else:
            return jsonify({'msg': 'User not found'}), 404
    else:
        return jsonify({'msg': 'User is not logged in'}), 401

# 로그아웃
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    session.pop('userid', None)
    return jsonify({'msg': 'Logout successful'}), 200


#=== 영화검색 결과 및 리뷰 보여주기 ===#
@app.route('/review/<movie_nm>')
def review_with_movienm(movie_nm):
    res = requests.get(f"http://kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieList.json?key=f5eef3421c602c6cb7ea224104795888&movieNm={movie_nm}")
    rjson = res.json()

    # movieList에서 movie_nm 필드가 query 변수와 동일한 영화 정보 찾기
    for movie in rjson["movieListResult"]["movieList"]:
        if movie['movieNm'] == movie_nm:
            movie_info = movie
            break

    # movie_nm 필드가 없거나 찾지 못한 경우, 0번 인덱스의 영화 정보 선택
    if movie_info is None:
        movie_info = rjson["movieListResult"]["movieList"][0]

    movie_cd = movie_info['movieCd']

    review_list = Review.query.filter_by(movie_cd=movie_cd)

    movie = {
        'movie_info': movie_info,
        'reviews': review_list,
    }
    
    return render_template("review.html", data = movie)


@app.route('/review')
def review():
    query = request.args.get('query')
    res = requests.get(f"http://kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieList.json?key=f5eef3421c602c6cb7ea224104795888&movieNm={query}")

    rjson = res.json()

    # movieList에서 movie_nm 필드가 query 변수와 동일한 영화 정보 찾기
    for movie in rjson["movieListResult"]["movieList"]:
        if movie['movieNm'] == query:
            movie_info = movie
            break

    # movie_nm 필드가 없거나 찾지 못한 경우, 0번 인덱스의 영화 정보 선택
    if movie_info is None:
        movie_info = rjson["movieListResult"]["movieList"][0]

    movie_cd = movie_info['movieCd']

    review_list = Review.query.filter_by(movie_cd=movie_cd)
    
    movie = {
        'movie_info': movie_info,
        'reviews': review_list,
    }
    return render_template("review.html", data = movie)

# 리뷰 생성
@app.route('/review', methods=['POST'])
def review_create():
    content_receive = request.form.get("content")
    rating_receive = request.form.get("rating")
    movie_receive = request.form.get("movie_cd")

    movienm_receive = request.form.get("movie_nm")

    # 데이터 DB에 저장
    review = Review(movie_cd = movie_receive, user = g.user, content = content_receive, rating = rating_receive)
    db.session.add(review)
    db.session.commit()

    return redirect(url_for('review_with_movienm', movie_nm=movienm_receive))

# 리뷰 삭제
@app.route('/review/<review_id>', methods=['POST'])
def review_delete(review_id):
    delete_data = Review.query.filter_by(id=review_id).first()
    db.session.delete(delete_data)
    db.session.commit()

    return redirect(url_for('movie'))

# 리뷰 수정
@app.route('/review/update', methods=['POST'])
def review_update():
    review_id = int(request.form.get('review_id'))

    update_data = Review.query.filter_by(id=review_id).first()
    update_data.content = request.form.get("content")
    update_data.rating = request.form.get("rating")
    update_data.movie_cd = request.form.get("movie_cd")

    movienm_receive = request.form.get("movie_nm")

    db.session.add(update_data)
    db.session.commit()

    return redirect(url_for('review_with_movienm', movie_nm=movienm_receive))

if __name__ == "__main__":
    app.run(debug=True)