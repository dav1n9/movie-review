from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
import os
from flask_sqlalchemy import SQLAlchemy

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')

db = SQLAlchemy(app)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_cd = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    content = db.Column(db.String, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'{self.movie_cd} : {self.content} by {self.username}, rating: {self.rating}'

with app.app_context():
    db.create_all()

    

@app.route('/review')
def review():

    review_list = Review.query.all()
    movie = {
        'movie_cd': '12345',
        'reviews': review_list,
    }
    return render_template("review.html", data = movie)

# 리뷰 생성
@app.route('/review', methods=['POST'])
def review_create():
    username_receive = request.form.get("username")
    content_receive = request.form.get("content")
    rating_receive = request.form.get("rating")
    movie_receive = request.form.get("movie_cd")

    # 데이터 DB에 저장
    review = Review(movie_cd = movie_receive, username = username_receive, content = content_receive, rating = rating_receive)
    db.session.add(review)
    db.session.commit()

    return redirect(url_for('review'))

# 리뷰 삭제
@app.route('/review/<review_id>', methods=['POST'])
def review_delete(review_id):
    delete_data = Review.query.filter_by(id=review_id).first()
    db.session.delete(delete_data)
    db.session.commit()

    return redirect(url_for('review'))

# 리뷰 수정
@app.route('/review/update', methods=['POST'])
def review_update():
    review_id = int(request.form.get('review_id'))

    update_data = Review.query.filter_by(id=review_id).first()
    update_data.username  = request.form.get("username")
    update_data.content = request.form.get("content")
    update_data.rating = request.form.get("rating")
    update_data.movie_cd = request.form.get("movie_cd")

    db.session.add(update_data)
    db.session.commit()

    return redirect(url_for('review'))

if __name__ == "__main__":
    app.run(debug=True)