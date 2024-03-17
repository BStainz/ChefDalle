from flask import Flask, request, render_template, jsonify,flash, redirect, url_for, flash, request, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from recommendations import load_and_vectorize_data, recommend_recipes, generate_and_save_image
import os
import pandas as pd
import logging
import base64
import requests
import secrets
import csv
import json
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db,User,UserFeedback, init_app, RecipeImage, User
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SubmitField
from wtforms.validators import DataRequired, Email



app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/brend/source/repos/ChefDalle/instance/recipeImages.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

init_app(app)  # Initialize SQLAlchemy with the Flask app
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
app.logger.setLevel(logging.DEBUG)
migrate = Migrate(app, db)

# Load the dataset and create TF-IDF matrix
recipes_df, tfidf_matrix, tfidf_vectorizer = load_and_vectorize_data('cleaned_recipes.csv')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))  # Redirect to the main page after login
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

class ProfileForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    diet = StringField('Diet Preferences')
    allergies = StringField('Allergies')
    submit = SubmitField('Update Profile')
    
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)  # Create a form object pre-filled with current_user's data
    saved_recipes = get_saved_recipes()
    print("Profile route hit. Saved recipes fetched:", saved_recipes)  # Debug statement
    if request.method == 'POST' and form.validate_on_submit():
        form.populate_obj(current_user)
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('profile'))
        
    saved_recipes = get_saved_recipes()
    return render_template('profile.html', form=form,  saved_recipes=saved_recipes)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user is None:
            new_user = User(username=username, saved_recipe_ids='', password_hash=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)  # Log in the new user immediately after registration
            return redirect(url_for('home'))
        else:
            flash('Username already exists')
    return render_template('register.html')

@app.route('/recommendations', methods=['POST'])
def get_recommendations():
    user_input = request.json
    ingredients = user_input.get('ingredients', [])
    allergies = user_input.get('allergies', [])
    user_diet_preferences = user_input.get('diets', [])

    # Convert user input into a string format expected by recommend_recipes
    user_input_str = " ".join(ingredients)

    liked_recipes = []
    disliked_recipes = []

    if current_user.is_authenticated:
        user_feedback = UserFeedback.query.filter_by(user_id=current_user.id).all()
        liked_recipes = [fb.recipe_id for fb in user_feedback if fb.feedback == 'like']
        disliked_recipes = [fb.recipe_id for fb in user_feedback if fb.feedback == 'dislike']

    recommendations = recommend_recipes(user_diet_preferences, allergies, recipes_df, tfidf_matrix, tfidf_vectorizer, " ".join(ingredients), liked_recipes, disliked_recipes)

    # Generate detailed information for each recommended recipe

    detailed_recommendations = []
    for index, row in recommendations.iterrows():
        recipe_id = str(row['recipeID'])  # Make sure 'recipeID' matches your DataFrame column name
        recipe_name = row['name']
        preparation_time = row['minutes']
        ingredients_list = row['ingredients']  # Assuming this is stored as a list
        steps = row['steps']  # Assuming this is stored as a list
        nutrition_info = {  # Extract nutrition information if you wish to include it
            "calories": row['calories'],
            "total_fat": row['total_fat'],
            "sugar": row['sugar'],
            "sodium": row['sodium'],
            "protein": row['protein'],
            "saturated_fat": row['saturated_fat'],
            "carbohydrates": row['carbohydrates']
        }
        print(nutrition_info)
        image_record = RecipeImage.query.filter_by(recipe_id=recipe_id).first()
        if image_record:
            app.logger.debug(f"Found existing image for recipe {recipe_name} with ID: {recipe_id}")
            image_url = image_record.image_url
        else:
            app.logger.debug(f"No existing image found for recipe {recipe_name} with ID: {recipe_id}, generating new one.")
            image_url = generate_and_save_image(recipe_id, recipe_name, OPENAI_API_KEY)
   
        detailed_recommendations.append({
            "recipe_id": recipe_id,
            "name": recipe_name,
            "preparation_time": preparation_time,
            "ingredients": ingredients_list,
            "steps": steps,
            "image": image_url,
            "nutrition": nutrition_info
        })
    # Return the detailed recommendations as JSON
    return jsonify(detailed_recommendations)

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400 
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Convert the image to base64 string
    base64_image = base64.b64encode(file.read()).decode('utf-8')
    
    # Send the image to OpenAI's API
    ingredients = identify_ingredients(base64_image)
    print("Ingredients identified: ", ingredients)
    return jsonify({"ingredients": ingredients})

def identify_ingredients(base64_image):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What ingredients are in this image? Return the list using just the ingredients. Example: butter, onion, cilantro,"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
    }
    
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    if response.ok:
        # Extracting the ingredients from the response's text
        response_data = response.json()
        try:
            ingredients_text = response_data['choices'][0]['message']['content']
            # You might need to further process ingredients_text to extract a clean list of ingredients.
            return ingredients_text
        except KeyError:
            return "Failed to extract ingredients from the response."
    else:
        return "Failed to identify ingredients."
    
@app.route('/feedback', methods=['POST'])
@login_required
def handle_feedback():
    feedback_data = request.json
    recipe_id = feedback_data.get('recipe_id')
    feedback = feedback_data.get('feedback')

    # Save feedback to the database
    user_feedback = UserFeedback(user_id=current_user.id, recipe_id=recipe_id, feedback=feedback)
    db.session.add(user_feedback)
    db.session.commit()

    return jsonify({"status": "success"})

@app.route('/save_recipe', methods=['POST'])
@login_required
def save_recipe():
    data = request.get_json()
    recipe_id = str(data.get('recipe_id')) 

    if current_user.saved_recipe_ids is None:
        current_user.saved_recipe_ids = ''

    saved_ids = current_user.saved_recipe_ids.split(',')
     
    if recipe_id not in saved_ids:
        if current_user.saved_recipe_ids:
            current_user.saved_recipe_ids += ',' + recipe_id
        else:
            current_user.saved_recipe_ids = recipe_id

        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Recipe saved successfully!'})
    else:
        return jsonify({'status': 'error', 'message': 'Recipe already saved.'})
    
    
def get_saved_recipes():
    saved_recipes = []
    if not current_user.saved_recipe_ids:
        return saved_recipes
    
    saved_ids = current_user.saved_recipe_ids.split(',')
    with open('cleaned_recipes.csv', mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        for row in csv_reader:
            if row['recipeID'] in saved_ids:
                nutrition_info = json.loads(row['nutrition'])
                image_record = RecipeImage.query.filter_by(recipe_id=row['recipeID']).first()
                image_url = image_record.image_url if image_record else 'path/to/default/image.jpg'
                
                saved_recipes.append({
                    "recipe_id": row['recipeID'],
                    "name": row['name'],
                    "preparation_time": row['minutes'],
                    "ingredients": eval(row['ingredients']),
                    "steps": eval(row['steps']),
                    "image_url": image_url,
                    "calories":row['calories'],
                    "total_fat":row['total_fat'],
                    "sugar":row['sugar'],
                    "sodium":row['sodium'],
                    "protein":row['protein'],
                    "saturated_fat":row['saturated_fat'],
                    "carbohydrates":row['carbohydrates']
                })
    return saved_recipes

@app.route('/delete_recipe', methods=['POST'])
@login_required
def delete_recipe():
    data = request.get_json()
    recipe_id = str(data.get('recipe_id'))
    print(f"Recipe ID: {recipe_id}")
    if not current_user.saved_recipe_ids:
        return jsonify({'status': 'error', 'message': 'No saved recipes to delete.'})

    saved_ids = current_user.saved_recipe_ids.split(',')
    
    if recipe_id in saved_ids:
        saved_ids.remove(recipe_id)
        current_user.saved_recipe_ids = ','.join(saved_ids)

        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Recipe deleted successfully!'})
    else:
        return jsonify({'status': 'error', 'message': 'Recipe not found in saved recipes.'})


@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
