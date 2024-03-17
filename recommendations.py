from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from models import RecipeImage, db
from flask import current_app
import pandas as pd
import openai
import os
import requests
import io
from io import BytesIO
import base64
from PIL import Image
from flask import current_app
import logging 


def process_image_to_base64(url):
    response = requests.get(url)
    image_bytes = io.BytesIO(response.content)
    img = Image.open(image_bytes)
    jpeg_image = io.BytesIO()
    img.save(jpeg_image, format='JPEG')
    jpeg_image.seek(0)
    base64_string = base64.b64encode(jpeg_image.read()).decode('utf-8')
    return "data:image/jpeg;base64," + base64_string

def generate_and_save_image(recipe_id, recipe_name, api_key):
    logging.debug(f"Attempting to generate image for recipe: {recipe_name} with ID: {recipe_id}")
    
    
    prompt = f"Create a photorealistic image of a dish called {recipe_name}. The image should be vivid and display the ingredients as if they are freshly prepared and ready to be served.Editorial Photography, Photography, Shot on 70mm lens, Depth of Field, Bokeh, DOF, Tilt Blur, Shutter Speed 1/1000, F/22, White Balance, 32k, Super-Resolution, white background"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    body = {
        "model": "dall-e-3",
        "prompt": prompt,
        'n': 1,
        "size": "1024x1024",
        "response_format": 'url',
        "quality": "hd",
        "style": "vivid"
    }
    try:
        response = requests.post('https://api.openai.com/v1/images/generations', headers=headers, json=body)
        if response.status_code == 200:
            logging.debug(f"Successfully generated and saved image for {recipe_name} with ID: {recipe_id}")
            image_data = response.json().get('data', [{}])[0]
            image_url = image_data['url']
            
            base64_image = process_image_to_base64(image_data['url'])
            new_image = RecipeImage(recipe_id=recipe_id, image_url=base64_image)  # or base64_image
            db.session.add(new_image)
            db.session.commit()
            return image_url
        else:
            logging.error(f"Failed to generate image for {recipe_name}. Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logging.exception("Request exception: %s", e)
        return None   

# Function to load the dataset and create TF-IDF matrix
def load_and_vectorize_data(filepath):
    recipes_df = pd.read_csv(filepath)
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf_vectorizer.fit_transform(recipes_df['combined_features'])
    return recipes_df, tfidf_matrix, tfidf_vectorizer

# Function to recommend recipes based on user input
def recommend_recipes(user_diet_preferences, allergies, recipes_df, tfidf_matrix, tfidf_vectorizer,user_input,liked_recipes=None, disliked_recipes=None):
    if isinstance(user_input, list):
        user_input_str = " ".join(user_input)
    else:
        user_input_str = user_input
    
    user_input_vector = tfidf_vectorizer.transform([user_input_str])
    cosine_sim = cosine_similarity(user_input_vector, tfidf_matrix)
    if liked_recipes:
        for liked_recipe_id in liked_recipes:
            idx = recipes_df.index[recipes_df['recipeID'] == liked_recipe_id].tolist()
            if idx:
                cosine_sim[0][idx[0]] *= 1.1  # Boosting the score

    if disliked_recipes:
        for disliked_recipe_id in disliked_recipes:
            idx = recipes_df.index[recipes_df['recipeID'] == disliked_recipe_id].tolist()
            if idx:
                cosine_sim[0][idx[0]] = 0  # Reducing the score or setting it to 0

    sorted_indices = cosine_sim[0].argsort()[::-1]
    print(f"Top 5 indices: {sorted_indices[:5]}")
    recommended_recipes = []

    for idx in sorted_indices:
        recipe = recipes_df.iloc[idx]
        print(f"Considering recipe: {recipe['name']} with similarity score {cosine_sim[0][idx]}")
        if (meets_dietary_restrictions(recipe['tags'], user_diet_preferences) and
            not contains_allergens(recipe['ingredients'], allergies)):
            recommended_recipes.append(recipe)
            if len(recommended_recipes) >= 5:  # Limiting to top 5 recommendations for simplicity
                break

    return pd.DataFrame(recommended_recipes)

# Check dietary restrictions
def meets_dietary_restrictions(tags, user_diet_preferences):
    recipe_tags = [tag.lower().strip() for tag in tags.split(',')]
    if not user_diet_preferences:
        return True
    
    diet_list = [diet.lower().strip() for diet in user_diet_preferences.split(',')]
    for diet in diet_list:
        print(f"User diet tag {user_diet_preferences} recipe:{recipe_tags}")
        if any (diet in tag for tag in recipe_tags):
            return True
    return False


# Check for allergens
def contains_allergens(ingredients, allergies):
    ingredient_list = [ingredient.lower().strip() for ingredient in ingredients.split(',')]
    if not allergies:
        return False 
    
    allergy_list = [allergy.lower().strip() for allergy in allergies.split(',')]
    
    for allergen in allergy_list:
        if any(allergen in ingredient for ingredient in ingredient_list):
            print(f"Excluding recipe due to allergen {allergen} in ingredients.")
            return True
    return False
    