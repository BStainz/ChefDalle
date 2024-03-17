from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class RecipeImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.String, unique=True, nullable=False)
    image_url = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f'<RecipeImage {self.recipe_id}>'
    
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))
    diet = db.Column(db.String(128))  # New field for diet preferences
    allergies = db.Column(db.String(256))  # New field for allergies
    saved_recipe_ids = db.Column(db.String, default='')
    feedbacks = db.relationship('UserFeedback', backref='user', lazy='dynamic')
    


    
class UserFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.String, nullable=False)
    feedback = db.Column(db.String, nullable=False)  # 'like' or 'dislike'
    
def init_app(app):
    db.init_app(app)