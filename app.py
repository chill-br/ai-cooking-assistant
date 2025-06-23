import os
import json
import sqlite3
from flask import Flask, render_template, jsonify, request
import spacy
from openai import OpenAI
import httpx # Needed to explicitly control the HTTP client

# --- Flask App Setup ---
# Get the absolute path to the directory where app.py is currently located.
# On Render, this is typically /opt/render/project/src/
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__,
            # Adjust template_folder and static_folder paths relative to CURRENT_FILE_DIR
            # Assuming 'frontend' and 'frontend/static' are directly within the 'src' directory
            template_folder=os.path.join(CURRENT_FILE_DIR, 'frontend'),
            static_folder=os.path.join(CURRENT_FILE_DIR, 'frontend', 'static'))

# --- Database Setup (SQLite) ---
DATABASE = 'recipes.db'

def get_db():
    """Establishes a database connection and sets row factory to access columns by name."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # This makes rows behave like dictionaries/objects
    return conn

def init_db():
    """Initializes the database schema and populates with sample recipes if empty or not existing."""
    conn = get_db()
    cursor = conn.cursor()

    # Create recipes table with new 'category' and 'image_url' fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            cuisine TEXT,
            category TEXT,       -- New field for categorization (e.g., "Vegetarian", "Non-Vegetarian", "Sweet")
            prep_time INTEGER,
            cook_time INTEGER,
            servings INTEGER,
            instructions TEXT,   -- Stored as JSON string
            ingredients TEXT,    -- Stored as JSON string
            image_url TEXT       -- New field for recipe image URL
        )
    ''')

    # Define all recipes to be added (totaling 30) with category and image_url
    all_recipes = [
        {
            "name": "Scrambled Eggs",
            "cuisine": "Continental",
            "category": "Non-Vegetarian",
            "prep_time": 2,
            "cook_time": 5,
            "servings": 1,
            "instructions": [
                "Crack 2 large eggs into a bowl.",
                "Add a pinch of salt and pepper.",
                "Whisk well until yolks and whites are combined.",
                "Melt 1 teaspoon of butter in a non-stick pan over medium heat.",
                "Pour the egg mixture into the hot pan.",
                "Let sit for a few seconds until edges begin to set.",
                "Gently push cooked portions towards the center, tilting the pan to allow uncooked egg to flow underneath.",
                "Cook until eggs are set but still moist. Do not overcook.",
                "Remove from heat and serve immediately."
            ],
            "ingredients": [
                {"name": "eggs", "quantity": 2, "unit": "large"},
                {"name": "salt", "quantity": 1, "unit": "pinch"},
                {"name": "pepper", "quantity": 1, "unit": "pinch"},
                {"name": "butter", "quantity": 1, "unit": "tsp"}
            ],
            "image_url": "https://placehold.co/400x300/e0f2f7/263238?text=Scrambled+Eggs"
        },
        {
            "name": "Indian Chicken Curry",
            "cuisine": "Indian",
            "category": "Non-Vegetarian",
            "prep_time": 20,
            "cook_time": 45,
            "servings": 4,
            "instructions": [
                "Heat 2 tablespoons of oil in a large pot over medium heat.",
                "Add 1 chopped onion and cook until softened, about 5 minutes.",
                "Stir in 2 teaspoons of ginger-garlic paste and cook for 1 minute.",
                "Add 1 teaspoon of turmeric, 2 teaspoons of cumin, 2 teaspoons of coriander, and 1 teaspoon of garam masala. Cook for 30 seconds until fragrant.",
                "Add 500g boneless chicken pieces and cook until lightly browned on all sides.",
                "Pour in 1 cup of chopped tomatoes (or crushed tomatoes) and 1/2 cup of water. Bring to a simmer.",
                "Cover and cook for 20-25 minutes, or until chicken is cooked through.",
                "Stir in 1/4 cup of plain yogurt (optional, for creaminess) and cook for another 5 minutes, uncovered, until sauce thickens.",
                "Garnish with fresh cilantro and serve hot with rice or naan."
            ],
            "ingredients": [
                {"name": "vegetable oil", "quantity": 2, "unit": "tbsp"},
                {"name": "onion", "quantity": 1, "unit": "chopped"},
                {"name": "ginger-garlic paste", "quantity": 2, "unit": "tsp"},
                {"name": "turmeric powder", "quantity": 1, "unit": "tsp"},
                {"name": "cumin powder", "quantity": 2, "unit": "tsp"},
                {"name": "coriander powder", "quantity": 2, "unit": "tsp"},
                {"name": "garam masala", "quantity": 1, "unit": "tsp"},
                {"name": "boneless chicken", "quantity": 500, "unit": "g"},
                {"name": "chopped tomatoes", "quantity": 1, "unit": "cup"},
                {"name": "water", "quantity": 0.5, "unit": "cup"},
                {"name": "plain yogurt", "quantity": 0.25, "unit": "cup"},
                {"name": "fresh cilantro", "quantity": 0.25, "unit": "cup, chopped"}
            ],
            "image_url": "https://placehold.co/400x300/ffe0b2/3e2723?text=Chicken+Curry"
        },
        {
            "name": "Vegetable Pulao",
            "cuisine": "Indian",
            "category": "Vegetarian",
            "prep_time": 15,
            "cook_time": 25,
            "servings": 3,
            "instructions": [
                "Wash 1.5 cups of Basmati rice and soak for 20 minutes. Drain well.",
                "Heat 2 tablespoons of ghee or oil in a pressure cooker or heavy-bottomed pan.",
                "Add 1 bay leaf, 2-3 green cardamom pods, 1 cinnamon stick, and 4-5 cloves. Sauté for 30 seconds.",
                "Add 1 chopped onion and cooking until golden brown.",
                "Stir in 1/2 cup chopped carrots, 1/2 cup green peas, and 1/4 cup chopped green beans. Sauté for 3-4 minutes.",
                "Add the drained rice and gently mix for 1 minute.",
                "Pour in 3 cups of water and add 1 teaspoon of salt. Stir gently.",
                "If using a pressure cooker, close the lid and cook for 2 whistles. If using a pan, cover and cook on low heat until water is absorbed and rice is tender, about 15-20 minutes.",
                "Let it rest for 5 minutes before opening the lid (pressure cooker) or fluffing with a fork (pan).",
                "Garnish with fresh cilantro and serve hot with raita."
            ],
            "ingredients": [
                {"name": "Basmati rice", "quantity": 1.5, "unit": "cups"},
                {"name": "ghee or oil", "quantity": 2, "unit": "tbsp"},
                {"name": "bay leaf", "quantity": 1, "unit": "medium"},
                {"name": "green cardamom pods", "quantity": 3, "unit": ""},
                {"name": "cinnamon stick", "quantity": 1, "unit": "inch"},
                {"name": "cloves", "quantity": 5, "unit": ""},
                {"name": "onion", "quantity": 1, "unit": "medium, chopped"},
                {"name": "carrots", "quantity": 0.5, "unit": "cup, chopped"},
                {"name": "green peas", "quantity": 0.5, "unit": "cup"},
                {"name": "green beans", "quantity": 0.25, "unit": "cup, chopped"},
                {"name": "water", "quantity": 3, "unit": "cups"},
                {"name": "salt", "quantity": 1, "unit": "tsp"},
                {"name": "fresh cilantro", "quantity": 0.25, "unit": "cup, chopped"}
            ],
            "image_url": "https://placehold.co/400x300/e8f5e9/2e7d32?text=Veg+Pulao"
        },
        {
            "name": "Quick Pasta Primavera",
            "cuisine": "Italian",
            "category": "Vegetarian",
            "prep_time": 10,
            "cook_time": 20,
            "servings": 2,
            "instructions": [
                "Cook 200g of pasta (e.g., penne or fusilli) according to package directions.",
                "While pasta cooks, heat 1 tablespoon of olive oil in a large skillet over medium heat.",
                "Add 1 clove minced garlic and 30 seconds until fragrant.",
                "Add 1 cup chopped bell peppers (any color), 1/2 cup chopped zucchini, and 1/2 cup broccoli florets. Sauté for 5-7 minutes until vegetables are tender-crisp.",
                "Stir in 1/4 cup cherry tomatoes (halved) and 2 tablespoons of pesto. Cook for 2 minutes.",
                "Drain the cooked pasta and add it to the skillet with the vegetables.",
                "Toss everything together until well combined. Add a splash of pasta water if needed for consistency.",
                "Season with salt and black pepper to taste. Serve immediately, optionally with grated Parmesan cheese."
            ],
            "ingredients": [
                {"name": "pasta", "quantity": 200, "unit": "g"},
                {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                {"name": "garlic", "quantity": 1, "unit": "clove, minced"},
                {"name": "bell peppers", "quantity": 1, "unit": "cup, chopped"},
                {"name": "zucchini", "quantity": 0.5, "unit": "cup, chopped"},
                {"name": "broccoli florets", "quantity": 0.5, "unit": "cup"},
                {"name": "cherry tomatoes", "quantity": 0.25, "unit": "cup, halved"},
                {"name": "pesto", "quantity": 2, "unit": "tbsp"},
                {"name": "salt", "quantity": 1, "unit": "to taste"},
                {"name": "black pepper", "quantity": 1, "unit": "to taste"},
                {"name": "Parmesan cheese", "quantity": 1, "unit": "optional, grated"}
            ],
            "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Pasta+Primavera"
        },
        # --- 26 NEW RECIPES START HERE WITH CATEGORIES AND IMAGE_URLS ---
        {
            "name": "Classic Tomato Soup",
            "cuisine": "American",
            "category": "Vegetarian",
            "prep_time": 10,
            "cook_time": 25,
            "servings": 4,
            "instructions": [
                "Melt 2 tbsp butter in a large pot. Add 1 chopped onion and cook until softened.",
                "Stir in 1 minced garlic clove and cook for 1 minute.",
                "Add 28 oz can crushed tomatoes, 4 cups vegetable broth, 1 tsp sugar, and 1/2 tsp dried basil.",
                "Bring to a simmer, then reduce heat and cook for 15-20 minutes.",
                "Blend with an immersion blender until smooth (or transfer to a regular blender).",
                "Stir in 1/2 cup heavy cream (optional). Season with salt and pepper to taste. Serve hot."
            ],
            "ingredients": [
                {"name": "butter", "quantity": 2, "unit": "tbsp"},
                {"name": "onion", "quantity": 1, "unit": "chopped"},
                {"name": "garlic", "quantity": 1, "unit": "clove, minced"},
                {"name": "crushed tomatoes", "quantity": 28, "unit": "oz can"},
                {"name": "vegetable broth", "quantity": 4, "unit": "cups"},
                {"name": "sugar", "quantity": 1, "unit": "tsp"},
                {"name": "dried basil", "quantity": 0.5, "unit": "tsp"},
                {"name": "heavy cream", "quantity": 0.5, "unit": "cup", "optional": True},
                {"name": "salt", "quantity": 1, "unit": "to taste"},
                {"name": "pepper", "quantity": 1, "unit": "to taste"}
            ],
            "image_url": "https://placehold.co/400x300/fff3e0/e65100?text=Tomato+Soup"
        },
        {
            "name": "Simple Guacamole",
            "cuisine": "Mexican",
            "category": "Vegetarian",
            "prep_time": 10,
            "cook_time": 0,
            "servings": 2,
            "instructions": [
                "Mash 2 ripe avocados in a bowl.",
                "Stir in 1/4 cup finely chopped red onion, 2 tbsp chopped cilantro, and 1-2 tbsp lime juice.",
                "Add salt and pepper to taste. Mix well.",
                "Serve immediately with tortilla chips or as a topping."
            ],
            "ingredients": [
                {"name": "avocados", "quantity": 2, "unit": "ripe"},
                {"name": "red onion", "quantity": 0.25, "unit": "cup, chopped"},
                {"name": "cilantro", "quantity": 2, "unit": "tbsp, chopped"},
                {"name": "lime juice", "quantity": 1, "unit": "tbsp"},
                {"name": "salt", "quantity": 1, "unit": "to taste"},
                {"name": "pepper", "quantity": 1, "unit": "to taste"}
            ],
            "image_url": "https://placehold.co/400x300/f1f8e9/33691e?text=Guacamole"
        },
        {
            "name": "Chicken Stir-fry",
            "cuisine": "Asian",
            "category": "Non-Vegetarian",
            "prep_time": 15,
            "cook_time": 20,
            "servings": 3,
            "instructions": [
                "Slice 1 lb boneless, skinless chicken breast into thin strips.",
                "Heat 1 tbsp sesame oil in a large skillet or wok over medium-high heat.",
                "Add chicken and cook until browned and cooked through. Remove and set aside.",
                "Add 1 tbsp more oil to the pan. Add 1 chopped bell pepper, 1 cup broccoli florets, and 1 cup snap peas.",
                "Stir-fry for 5-7 minutes until vegetables are tender-crisp.",
                "Return chicken to the pan. Add 1/4 cup soy sauce, 1 tbsp honey, and 1 tsp grated ginger.",
                "Toss to coat and cook for 2 minutes. Serve hot over rice."
            ],
            "ingredients": [
                {"name": "boneless, skinless chicken breast", "quantity": 1, "unit": "lb"},
                {"name": "sesame oil", "quantity": 2, "unit": "tbsp"},
                {"name": "bell pepper", "quantity": 1, "unit": "chopped"},
                {"name": "broccoli florets", "quantity": 1, "unit": "cup"},
                {"name": "snap peas", "quantity": 1, "unit": "cup"},
                {"name": "soy sauce", "quantity": 0.25, "unit": "cup"},
                {"name": "honey", "quantity": 1, "unit": "tbsp"},
                {"name": "grated ginger", "quantity": 1, "unit": "tsp"}
            ],
            "image_url": "https://placehold.co/400x300/fffde7/f57f17?text=Chicken+Stir-fry"
        },
        {
            "name": "Lentil Soup",
            "cuisine": "Mediterranean",
            "category": "Vegetarian",
            "prep_time": 15,
            "cook_time": 40,
            "servings": 6,
            "instructions": [
                "Rinse 1 cup brown or green lentils.",
                "Heat 2 tbsp olive oil in a large pot. Add 1 chopped onion, 2 chopped carrots, and 2 chopped celery stalks. Sauté for 8-10 minutes.",
                "Stir in 2 minced garlic cloves, 1 tsp cumin, and 1/2 tsp coriander. Cook for 1 minute.",
                "Add rinsed lentils, 6 cups vegetable broth, and 1 (14.5 oz) can diced tomatoes.",
                "Bring to a boil, then reduce heat, cover, and simmer for 30-35 minutes, or until lentils are tender.",
                "Season with salt, pepper, and a squeeze of lemon juice. Garnish with fresh parsley."
            ],
            "ingredients": [
                {"name": "brown or green lentils", "quantity": 1, "unit": "cup"},
                {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
                {"name": "onion", "quantity": 1, "unit": "chopped"},
                {"name": "carrots", "quantity": 2, "unit": "chopped"},
                {"name": "celery stalks", "quantity": 2, "unit": "chopped"},
                {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                {"name": "cumin", "quantity": 1, "unit": "tsp"},
                {"name": "coriander", "quantity": 0.5, "unit": "tsp"},
                {"name": "vegetable broth", "quantity": 6, "unit": "cups"},
                {"name": "diced tomatoes", "quantity": 14.5, "unit": "oz can"},
                {"name": "lemon juice", "quantity": 1, "unit": "squeeze"},
                {"name": "salt", "quantity": 1, "unit": "to taste"},
                {"name": "pepper", "quantity": 1, "unit": "to taste"},
                {"name": "fresh parsley", "quantity": 1, "unit": "garnish"}
            ],
            "image_url": "https://placehold.co/400x300/ede7f6/512da8?text=Lentil+Soup"
        },
        {
            "name": "Baked Salmon with Asparagus",
            "cuisine": "Healthy",
            "category": "Non-Vegetarian",
            "prep_time": 10,
            "cook_time": 15,
            "servings": 2,
            "instructions": [
                "Preheat oven to 400°F (200°C).",
                "Place 2 salmon fillets on a baking sheet. Drizzle with olive oil and season with salt, pepper, and garlic powder.",
                "Toss 1 bunch of asparagus (ends trimmed) with olive oil, salt, and pepper. Arrange around salmon.",
                "Bake for 12-15 minutes, or until salmon is cooked through and flakes easily with a fork."
            ],
            "ingredients": [
                {"name": "salmon fillets", "quantity": 2, "unit": ""},
                {"name": "asparagus", "quantity": 1, "unit": "bunch"},
                {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
                {"name": "salt", "quantity": 1, "unit": "to taste"},
                {"name": "pepper", "quantity": 1, "unit": "to taste"},
                {"name": "garlic powder", "quantity": 0.5, "unit": "tsp"}
            ],
            "image_url": "https://placehold.co/400x300/e8f5e9/2e7d32?text=Baked+Salmon"
        },
        {
            "name": "Banana Pancakes",
            "cuisine": "American",
            "category": "Sweet",
            "prep_time": 5,
            "cook_time": 15,
            "servings": 2,
            "instructions": [
                "Mash 1 ripe banana in a bowl.",
                "Whisk in 1 large egg and 1/2 cup milk.",
                "Stir in 1/2 cup all-purpose flour, 1 tsp baking powder, and a pinch of salt until just combined (lumps are okay).",
                "Heat a lightly oiled griddle or non-stick pan over medium heat.",
                "Pour 1/4 cup batter per pancake. Cook for 2-3 minutes per side, until golden brown and cooked through.",
                "Serve with maple syrup and fresh fruit."
            ],
            "ingredients": [
                {"name": "ripe banana", "quantity": 1, "unit": ""},
                {"name": "large egg", "quantity": 1, "unit": ""},
                {"name": "milk", "quantity": 0.5, "unit": "cup"},
                {"name": "all-purpose flour", "quantity": 0.5, "unit": "cup"},
                {"name": "baking powder", "quantity": 1, "unit": "tsp"},
                {"name": "salt", "quantity": 1, "unit": "pinch"},
                {"name": "maple syrup", "quantity": 1, "unit": "to serve"},
                {"name": "fresh fruit", "quantity": 1, "unit": "to serve"}
            ],
            "image_url": "https://placehold.co/400x300/fff3e0/e65100?text=Banana+Pancakes"
        },
        {
            "name": "Vegetarian Chili",
            "cuisine": "American",
            "category": "Vegetarian",
            "prep_time": 20,
            "cook_time": 45,
            "servings": 6,
            "instructions": [
                "Heat 1 tbsp olive oil in a large pot. Add 1 chopped onion, 1 chopped bell pepper, and 2 minced garlic cloves. Sauté for 5 minutes.",
                "Stir in 1 tbsp chili powder, 1 tsp cumin, and 1/2 tsp smoked paprika. Cook for 1 minute.",
                "Add 1 (28 oz) can crushed tomatoes, 1 (15 oz) can kidney beans (rinsed), 1 (15 oz) can black beans (rinsed), and 1 cup vegetable broth.",
                "Bring to a simmer, then reduce heat, uncovered, for 30-40 minutes, stirring occasionally, until thickened.",
                "Season with salt and pepper. Serve with desired toppings like shredded cheese or sour cream."
            ],
            "ingredients": [
                {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                {"name": "onion", "quantity": 1, "unit": "chopped"},
                {"name": "bell pepper", "quantity": 1, "unit": "chopped"},
                {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                {"name": "chili powder", "quantity": 1, "unit": "tbsp"},
                {"name": "cumin", "quantity": 1, "unit": "tsp"},
                {"name": "smoked paprika", "quantity": 0.5, "unit": "tsp"},
                {"name": "crushed tomatoes", "quantity": 28, "unit": "oz can"},
                {"name": "kidney beans", "quantity": 15, "unit": "oz can, rinsed"},
                {"name": "black beans", "quantity": 15, "unit": "oz can, rinsed"},
                {"name": "vegetable broth", "quantity": 1, "unit": "cup"},
                {"name": "salt", "quantity": 1, "unit": "to taste"},
                {"name": "pepper", "quantity": 1, "unit": "to taste"},
                {"name": "shredded cheese", "quantity": 1, "unit": "optional"},
                {"name": "sour cream", "quantity": 1, "unit": "optional"}
            ],
            "image_url": "https://placehold.co/400x300/e8f5e9/33691e?text=Vegetarian+Chili"
        },
        {
            "name": "Caprese Salad",
            "cuisine": "Italian",
            "category": "Vegetarian",
            "prep_time": 10,
            "cook_time": 0,
            "servings": 2,
            "instructions": [
                "Slice 2 ripe tomatoes and 8 oz fresh mozzarella into 1/4-inch thick rounds.",
                "Arrange tomato and mozzarella slices on a platter, alternating them.",
                "Tuck fresh basil leaves between the slices.",
                "Drizzle generously with balsamic glaze.",
                "Season lightly with salt and freshly ground black pepper. Serve immediately."
            ],
            "ingredients": [
                {"name": "ripe tomatoes", "quantity": 2, "unit": ""},
                {"name": "fresh mozzarella", "quantity": 8, "unit": "oz"},
                {"name": "fresh basil leaves", "quantity": 0.5, "unit": "cup"},
                {"name": "balsamic glaze", "quantity": 2, "unit": "tbsp"},
                {"name": "salt", "quantity": 1, "unit": "to taste"},
                {"name": "black pepper", "quantity": 1, "unit": "to taste"}
            ],
            "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Caprese+Salad"
        },
        {
            "name": "Garlic Butter Shrimp",
            "cuisine": "Seafood",
            "category": "Non-Vegetarian",
            "prep_time": 10,
            "cook_time": 10,
            "servings": 2,
            "instructions": [
                "Pat 1 lb shrimp (peeled and deveined) dry with paper towels.",
                "Melt 2 tbsp butter in a large skillet over medium-high heat. Add 4 minced garlic cloves and cook for 1 minute until fragrant.",
                "Add shrimp to the skillet in a single layer. Cook for 2-3 minutes per side, until pink and cooked through.",
                "Stir in 1 tbsp lemon juice and 2 tbsp chopped fresh parsley.",
                "Season with salt and pepper to taste. Serve immediately, perhaps with rice or pasta."
            ],
            "ingredients": [
                {"name": "shrimp", "quantity": 1, "unit": "lb, peeled and deveined"},
                {"name": "butter", "quantity": 2, "unit": "tbsp"},
                {"name": "garlic", "quantity": 4, "unit": "cloves, minced"},
                {"name": "lemon juice", "quantity": 1, "unit": "tbsp"},
                {"name": "fresh parsley", "quantity": 2, "unit": "tbsp, chopped"},
                {"name": "salt", "quantity": 1, "unit": "to taste"},
                {"name": "pepper", "quantity": 1, "unit": "to taste"}
            ],
            "image_url": "https://placehold.co/400x300/e0f2f7/263238?text=Garlic+Shrimp"
        },
        {
            "name": "Quinoa Salad with Chickpeas",
            "cuisine": "Mediterranean",
            "category": "Vegetarian",
            "prep_time": 15,
            "cook_time": 15,
            "servings": 4,
            "instructions": [
                "Rinse 1 cup quinoa thoroughly. Cook according to package directions (typically 2 cups water, simmer 15 mins). Fluff with a fork.",
                "In a large bowl, combine cooked quinoa, 1 can (15oz) chickpeas (rinsed and drained), 1 cup chopped cucumber, 1 cup chopped cherry tomatoes, and 1/2 cup chopped red onion.",
                "For the dressing, whisk together 3 tbsp olive oil, 2 tbsp lemon juice, 1 tsp dried oregano, salt, and pepper.",
                "Pour dressing over salad and toss to combine. Chill for at least 15 minutes before serving."
            ],
            "ingredients": [
                {"name": "quinoa", "quantity": 1, "unit": "cup"},
                {"name": "chickpeas", "quantity": 15, "unit": "oz can, rinsed"},
                {"name": "cucumber", "quantity": 1, "unit": "cup, chopped"},
                {"name": "cherry tomatoes", "quantity": 1, "unit": "cup, chopped"},
                {"name": "red onion", "quantity": 0.5, "unit": "cup, chopped"},
                {"name": "olive oil", "quantity": 3, "unit": "tbsp"},
                {"name": "lemon juice", "quantity": 2, "unit": "tbsp"},
                {"name": "dried oregano", "quantity": 1, "unit": "tsp"},
                {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/f0f4c3/689f38?text=Quinoa+Salad"
            },
            {
                "name": "Chocolate Chip Cookies",
                "cuisine": "American",
                "category": "Sweet",
                "prep_time": 15,
                "cook_time": 12,
                "servings": 24,
                "instructions": [
                    "Preheat oven to 375°F (190°C). Line baking sheets with parchment paper.",
                    "In a large bowl, cream together 1/2 cup (1 stick) softened unsalted butter, 1/2 cup granulated sugar, and 1/2 cup packed light brown sugar until light and fluffy.",
                    "Beat in 1 large egg and 1 tsp vanilla extract.",
                    "In a separate bowl, whisk together 1 1/4 cups all-purpose flour, 1/2 tsp baking soda, and 1/4 tsp salt.",
                    "Gradually add dry ingredients to wet ingredients, mixing until just combined.",
                    "Fold in 1 cup chocolate chips.",
                    "Drop rounded tablespoons of dough onto prepared baking sheets.",
                    "Bake for 10-12 minutes, or until edges are golden brown and centers are still soft. Let cool on baking sheets for a few minutes before transferring to a wire rack."
                ],
                "ingredients": [
                    {"name": "unsalted butter", "quantity": 0.5, "unit": "cup, softened"},
                    {"name": "granulated sugar", "quantity": 0.5, "unit": "cup"},
                    {"name": "light brown sugar", "quantity": 0.5, "unit": "cup, packed"},
                    {"name": "large egg", "quantity": 1, "unit": ""},
                    {"name": "vanilla extract", "quantity": 1, "unit": "tsp"},
                    {"name": "all-purpose flour", "quantity": 1.25, "unit": "cups"},
                    {"name": "baking soda", "quantity": 0.5, "unit": "tsp"},
                    {"name": "salt", "quantity": 0.25, "unit": "tsp"},
                    {"name": "chocolate chips", "quantity": 1, "unit": "cup"}
                ],
                "image_url": "https://placehold.co/400x300/ffe0b2/3e2723?text=Choc+Chip+Cookies"
            },
            {
                "name": "Beef Tacos",
                "cuisine": "Mexican",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 20,
                "servings": 4,
                "instructions": [
                    "Brown 1 lb ground beef in a skillet over medium-high heat. Drain excess fat.",
                    "Stir in 1 packet (1 oz) taco seasoning and 1/2 cup water. Bring to a simmer and cook for 5-7 minutes, until sauce thickens.",
                    "Warm 12 taco shells or tortillas according to package directions.",
                    "Fill taco shells with seasoned beef. Top with shredded lettuce, diced tomatoes, shredded cheese, and salsa."
                ],
                "ingredients": [
                    {"name": "ground beef", "quantity": 1, "unit": "lb"},
                    {"name": "taco seasoning", "quantity": 1, "unit": "packet (1 oz)"},
                    {"name": "water", "quantity": 0.5, "unit": "cup"},
                    {"name": "taco shells or tortillas", "quantity": 12, "unit": ""},
                    {"name": "shredded lettuce", "quantity": 2, "unit": "cups"},
                    {"name": "diced tomatoes", "quantity": 1, "unit": "cup"},
                    {"name": "shredded cheese", "quantity": 1, "unit": "cup"},
                    {"name": "salsa", "quantity": 1, "unit": "cup"}
                ],
                "image_url": "https://placehold.co/400x300/ffccbc/bf360c?text=Beef+Tacos"
            },
            {
                "name": "Mushroom Risotto",
                "cuisine": "Italian",
                "category": "Vegetarian",
                "prep_time": 15,
                "cook_time": 30,
                "servings": 4,
                "instructions": [
                    "Heat 6 cups vegetable or chicken broth in a saucepan; keep warm over low heat.",
                    "In a large, heavy-bottomed pot, melt 2 tbsp butter with 1 tbsp olive oil over medium heat. Add 1 chopped onion and cook until softened, about 5 minutes.",
                    "Add 8 oz sliced mushrooms and cook until browned, about 5-7 minutes.",
                    "Stir in 2 minced garlic cloves and 1.5 cups Arborio rice. Cook for 1-2 minutes until edges are translucent.",
                    "Pour in 1/2 cup dry white wine and stir until absorbed.",
                    "Add warm broth, 1 ladle at a time, stirring constantly until each addition is absorbed before adding more. This will take about 20-25 minutes.",
                    "Once all broth is absorbed and rice is creamy but still al dente, stir in 1/2 cup grated Parmesan cheese and 2 tbsp butter.",
                    "Season with salt and pepper. Serve immediately."
                ],
                "ingredients": [
                    {"name": "vegetable or chicken broth", "quantity": 6, "unit": "cups"},
                    {"name": "butter", "quantity": 4, "unit": "tbsp"},
                    {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "onion", "quantity": 1, "unit": "chopped"},
                    {"name": "mushrooms", "quantity": 8, "unit": "oz, sliced"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "Arborio rice", "quantity": 1.5, "unit": "cups"},
                    {"name": "dry white wine", "quantity": 0.5, "unit": "cup"},
                    {"name": "Parmesan cheese", "quantity": 0.5, "unit": "cup, grated"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Mushroom+Risotto"
            },
            {
                "name": "French Toast",
                "cuisine": "American",
                "category": "Sweet",
                "prep_time": 5,
                "cook_time": 10,
                "servings": 2,
                "instructions": [
                    "In a shallow dish, whisk together 2 large eggs, 1/2 cup milk, 1 tbsp sugar, and 1/2 tsp vanilla extract.",
                    "Dip each slice of bread into the egg mixture, coating both sides.",
                    "Heat a lightly oiled griddle or non-stick pan over medium heat.",
                    "Cook bread slices for 2-3 minutes per side, until golden brown and cooked through.",
                    "Serve immediately with maple syrup and powdered sugar."
                ],
                "ingredients": [
                    {"name": "large eggs", "quantity": 2, "unit": ""},
                    {"name": "milk", "quantity": 0.5, "unit": "cup"},
                    {"name": "sugar", "quantity": 1, "unit": "tbsp"},
                    {"name": "vanilla extract", "quantity": 0.5, "unit": "tsp"},
                    {"name": "bread slices", "quantity": 4, "unit": ""},
                    {"name": "maple syrup", "quantity": 1, "unit": "to serve"},
                    {"name": "powdered sugar", "quantity": 1, "unit": "to serve"}
                ],
                "image_url": "https://placehold.co/400x300/fff3e0/e65100?text=French+Toast"
            },
            {
                "name": "Chicken Noodle Soup",
                "cuisine": "American",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 30,
                "servings": 6,
                "instructions": [
                    "Heat 1 tbsp olive oil in a large pot over medium heat. Add 1 chopped onion, 2 chopped carrots, and 2 chopped celery stalks. Sauté for 5-7 minutes until softened.",
                    "Add 2 minced garlic cloves and cook for 1 minute.",
                    "Pour in 8 cups chicken broth and add 1 cup cooked shredded chicken.",
                    "Bring to a simmer. Add 2 cups egg noodles and cook according to package directions, about 7-10 minutes.",
                    "Season with salt, pepper, and fresh parsley to taste. Serve hot."
                ],
                "ingredients": [
                    {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "onion", "quantity": 1, "unit": "chopped"},
                    {"name": "carrots", "quantity": 2, "unit": "chopped"},
                    {"name": "celery stalks", "quantity": 2, "unit": "chopped"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "chicken broth", "quantity": 8, "unit": "cups"},
                    {"name": "cooked shredded chicken", "quantity": 1, "unit": "cup"},
                    {"name": "egg noodles", "quantity": 2, "unit": "cups"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "fresh parsley", "quantity": 1, "unit": "to garnish"}
                ],
                "image_url": "https://placehold.co/400x300/e0f2f7/263238?text=Chicken+Noodle+Soup"
            },
            {
                "name": "Spaghetti Carbonara",
                "cuisine": "Italian",
                "category": "Non-Vegetarian",
                "prep_time": 10,
                "cook_time": 15,
                "servings": 2,
                "instructions": [
                    "Cook 200g spaghetti according to package directions until al dente. Reserve 1 cup pasta water.",
                    "While pasta cooks, cook 4 oz pancetta or bacon (diced) in a large skillet over medium heat until crispy. Remove pancetta to a plate, leaving rendered fat in the skillet.",
                    "In a bowl, whisk together 2 large eggs, 1/2 cup grated Pecorino Romano cheese, and plenty of black pepper.",
                    "Add drained spaghetti to the skillet with the fat. Toss to coat.",
                    "Pour egg mixture over pasta, stirring vigorously to coat. Add a few tablespoons of reserved pasta water as needed to create a creamy sauce.",
                    "Stir in crispy pancetta. Serve immediately with extra cheese and pepper."
                ],
                "ingredients": [
                    {"name": "spaghetti", "quantity": 200, "unit": "g"},
                    {"name": "pancetta or bacon", "quantity": 4, "unit": "oz, diced"},
                    {"name": "large eggs", "quantity": 2, "unit": ""},
                    {"name": "Pecorino Romano cheese", "quantity": 0.5, "unit": "cup, grated"},
                    {"name": "black pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Spaghetti+Carbonara"
            },
            {
                "name": "Oatmeal",
                "cuisine": "Breakfast",
                "category": "Vegetarian",
                "prep_time": 1,
                "cook_time": 5,
                "servings": 1,
                "instructions": [
                    "Combine 1/2 cup rolled oats and 1 cup water (or milk) in a small saucepan.",
                    "Bring to a boil, then reduce heat to low and simmer, stirring occasionally, for 3-5 minutes, until oats are tender and liquid is absorbed.",
                    "Remove from heat. Stir in a pinch of salt and any desired toppings like fruit, nuts, or honey.",
                    "Serve warm."
                ],
                "ingredients": [
                    {"name": "rolled oats", "quantity": 0.5, "unit": "cup"},
                    {"name": "water or milk", "quantity": 1, "unit": "cup"},
                    {"name": "salt", "quantity": 1, "unit": "pinch"},
                    {"name": "fruit", "quantity": 1, "unit": "optional, for topping"},
                    {"name": "nuts", "quantity": 1, "unit": "optional, for topping"},
                    {"name": "honey", "quantity": 1, "unit": "optional, for topping"}
                ],
                "image_url": "https://placehold.co/400x300/e8f5e9/33691e?text=Oatmeal"
            },
            {
                "name": "Homemade Pizza",
                "cuisine": "Italian",
                "category": "Vegetarian",
                "prep_time": 20,
                "cook_time": 15,
                "servings": 4,
                "instructions": [
                    "Preheat oven to 450°F (230°C) with a pizza stone or baking steel if you have one.",
                    "On a lightly floured surface, stretch or roll out 1 lb pizza dough into a 12-inch round.",
                    "Transfer dough to a parchment-lined baking sheet or a pizza peel dusted with cornmeal.",
                    "Spread 1/2 cup pizza sauce evenly over the dough, leaving a 1-inch border.",
                    "Sprinkle with 1 cup shredded mozzarella cheese and desired toppings.",
                    "Bake for 12-15 minutes, or until crust is golden brown and cheese is bubbly and lightly browned."
                ],
                "ingredients": [
                    {"name": "pizza dough", "quantity": 1, "unit": "lb"},
                    {"name": "pizza sauce", "quantity": 0.5, "unit": "cup"},
                    {"name": "shredded mozzarella cheese", "quantity": 1, "unit": "cup"},
                    {"name": "desired toppings", "quantity": 1, "unit": "to taste"},
                    {"name": "cornmeal", "quantity": 1, "unit": "for dusting"}
                ],
                "image_url": "https://placehold.co/400x300/fff8e1/ff8f00?text=Homemade+Pizza"
            },
            {
                "name": "Lemon Herb Roasted Chicken",
                "cuisine": "European",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 60,
                "servings": 4,
                "instructions": [
                    "Preheat oven to 400°F (200°C).",
                    "Pat 1 (3-4 lb) whole chicken dry with paper towels.",
                    "In a small bowl, combine 2 tbsp olive oil, 2 tbsp chopped fresh rosemary, 2 tbsp chopped fresh thyme, 1 tbsp lemon zest, 2 minced garlic cloves, salt, and pepper.",
                    "Rub the herb mixture all over the chicken, including under the skin.",
                    "Stuff the cavity with lemon halves and extra herb sprigs if desired.",
                    "Roast for 60-75 minutes, or until internal temperature reaches 165°F (74°C) in the thickest part of the thigh."
                ],
                "ingredients": [
                    {"name": "whole chicken", "quantity": 1, "unit": "3-4 lb"},
                    {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
                    {"name": "fresh rosemary", "quantity": 2, "unit": "tbsp, chopped"},
                    {"name": "fresh thyme", "quantity": 2, "unit": "tbsp, chopped"},
                    {"name": "lemon zest", "quantity": 1, "unit": "tbsp"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "lemon", "quantity": 1, "unit": "halved, for cavity"}
                ],
                "image_url": "https://placehold.co/400x300/e0f7fa/006064?text=Roasted+Chicken"
            },
            {
                "name": "Black Bean Burgers",
                "cuisine": "Vegetarian",
                "category": "Vegetarian",
                "prep_time": 20,
                "cook_time": 15,
                "servings": 4,
                "instructions": [
                    "Preheat oven to 375°F (190°C) or prepare grill/skillet.",
                    "In a large bowl, mash 1 (15 oz) can black beans (drained and rinsed) with a fork, leaving some whole.",
                    "Stir in 1/2 cup cooked brown rice, 1/4 cup finely chopped red onion, 2 tbsp breadcrumbs, 1 large egg, 1 tsp chili powder, 1/2 tsp cumin, and salt/pepper.",
                    "Form into 4 patties.",
                    "Bake for 10-12 minutes per side, or cook in a lightly oiled skillet/grill until browned and heated through.",
                    "Serve on buns with desired toppings."
                ],
                "ingredients": [
                    {"name": "black beans", "quantity": 15, "unit": "oz can, rinsed"},
                    {"name": "cooked brown rice", "quantity": 0.5, "unit": "cup"},
                    {"name": "red onion", "quantity": 0.25, "unit": "cup, chopped"},
                    {"name": "breadcrumbs", "quantity": 2, "unit": "tbsp"},
                    {"name": "large egg", "quantity": 1, "unit": ""},
                    {"name": "chili powder", "quantity": 1, "unit": "tsp"},
                    {"name": "cumin", "quantity": 0.5, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "burger buns", "quantity": 4, "unit": ""}
                ],
                "image_url": "https://placehold.co/400x300/c8e6c9/2e7d32?text=Black+Bean+Burger"
            },
            {
                "name": "Greek Salad",
                "cuisine": "Mediterranean",
                "category": "Vegetarian",
                "prep_time": 10,
                "cook_time": 0,
                "servings": 2,
                "instructions": [
                    "In a large bowl, combine 4 cups chopped romaine lettuce, 1/2 cup sliced cucumber, 1/2 cup chopped tomatoes, 1/4 cup sliced red onion, 1/4 cup Kalamata olives, and 1/4 cup crumbled feta cheese.",
                    "For the dressing, whisk together 3 tbsp olive oil, 1 tbsp red wine vinegar, 1/2 tsp dried oregano, salt, and pepper.",
                    "Pour dressing over salad and toss gently to combine. Serve immediately."
                ],
                "ingredients": [
                    {"name": "romaine lettuce", "quantity": 4, "unit": "cups, chopped"},
                    {"name": "cucumber", "quantity": 0.5, "unit": "cup, sliced"},
                    {"name": "tomatoes", "quantity": 0.5, "unit": "cup, chopped"},
                    {"name": "red onion", "quantity": 0.25, "unit": "cup, sliced"},
                    {"name": "Kalamata olives", "quantity": 0.25, "unit": "cup"},
                    {"name": "feta cheese", "quantity": 0.25, "unit": "cup, crumbled"},
                    {"name": "olive oil", "quantity": 3, "unit": "tbsp"},
                    {"name": "red wine vinegar", "quantity": 1, "unit": "tbsp"},
                    {"name": "dried oregano", "quantity": 0.5, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/ede7f6/512da8?text=Greek+Salad"
            },
            {
                "name": "Beef and Broccoli",
                "cuisine": "Asian",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 15,
                "servings": 4,
                "instructions": [
                    "Slice 1 lb flank steak thinly against the grain. Marinate in 2 tbsp soy sauce, 1 tbsp cornstarch, and 1 tbsp sesame oil for 15 minutes.",
                    "Steam or blanch 4 cups broccoli florets until tender-crisp.",
                    "Heat 1 tbsp vegetable oil in a large skillet or wok over high heat. Add beef in batches and cook until browned. Remove beef.",
                    "In the same skillet, add 1 tbsp more oil to the pan. Add 2 minced garlic cloves and 1 tsp grated ginger. Cook for 30 seconds.",
                    "Whisk together 1/4 cup beef broth, 2 tbsp soy sauce, 1 tbsp oyster sauce, 1 tbsp brown sugar, and 1 tsp cornstarch. Pour into skillet and bring to a simmer until slightly thickened.",
                    "Return beef and broccoli to the skillet. Toss to coat in sauce. Serve hot over rice."
                ],
                "ingredients": [
                    {"name": "flank steak", "quantity": 1, "unit": "lb"},
                    {"name": "soy sauce", "quantity": 4, "unit": "tbsp"},
                    {"name": "cornstarch", "quantity": 2, "unit": "tbsp"},
                    {"name": "sesame oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "broccoli florets", "quantity": 4, "unit": "cups"},
                    {"name": "vegetable oil", "quantity": 2, "unit": "tbsp"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "grated ginger", "quantity": 1, "unit": "tsp"},
                    {"name": "beef broth", "quantity": 0.25, "unit": "cup"},
                    {"name": "oyster sauce", "quantity": 1, "unit": "tbsp"},
                    {"name": "brown sugar", "quantity": 1, "unit": "tbsp"}
                ],
                "image_url": "https://placehold.co/400x300/fffde7/f57f17?text=Beef+Broccoli"
            },
            {
                "name": "Minestrone Soup",
                "cuisine": "Italian",
                "category": "Vegetarian",
                "prep_time": 20,
                "cook_time": 40,
                "servings": 6,
                "instructions": [
                    "Heat 2 tbsp olive oil in a large pot. Add 1 chopped onion, 2 chopped carrots, and 2 chopped celery stalks. Sauté for 8-10 minutes.",
                    "Add 3 minced garlic cloves, 1 tsp dried oregano, and 1/2 tsp dried basil. Cook for 1 minute.",
                    "Stir in 1 (28 oz) can crushed tomatoes, 6 cups vegetable broth, 1 (15 oz) can cannellini beans (rinsed), 1 cup small pasta (e.g., ditalini), and 1 cup chopped zucchini.",
                    "Bring to a simmer. Cook for 15-20 minutes, or until pasta is al dente and vegetables are tender.",
                    "Stir in 2 cups baby spinach until wilted. Season with salt and pepper. Serve with grated Parmesan."
                ],
                "ingredients": [
                    {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
                    {"name": "onion", "quantity": 1, "unit": "chopped"},
                    {"name": "carrots", "quantity": 2, "unit": "chopped"},
                    {"name": "celery stalks", "quantity": 2, "unit": "chopped"},
                    {"name": "garlic", "quantity": 3, "unit": "cloves, minced"},
                    {"name": "dried oregano", "quantity": 1, "unit": "tsp"},
                    {"name": "dried basil", "quantity": 0.5, "unit": "tsp"},
                    {"name": "crushed tomatoes", "quantity": 28, "unit": "oz can"},
                    {"name": "vegetable broth", "quantity": 6, "unit": "cups"},
                    {"name": "cannellini beans", "quantity": 15, "unit": "oz can, rinsed"},
                    {"name": "small pasta", "quantity": 1, "unit": "cup"},
                    {"name": "zucchini", "quantity": 1, "unit": "cup, chopped"},
                    {"name": "baby spinach", "quantity": 2, "unit": "cups"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "Parmesan cheese", "quantity": 1, "unit": "garnish"}
                ],
                "image_url": "https://placehold.co/400x300/ede7f6/512da8?text=Minestrone+Soup"
            },
            {
                "name": "Crispy Baked Chicken Thighs",
                "cuisine": "American",
                "category": "Non-Vegetarian",
                "prep_time": 10,
                "cook_time": 35,
                "servings": 4,
                "instructions": [
                    "Preheat oven to 400°F (200°C).",
                    "Pat 4 bone-in, skin-on chicken thighs dry with paper towels.",
                    "In a small bowl, combine 1 tbsp olive oil, 1 tsp garlic powder, 1 tsp paprika, 1/2 tsp dried thyme, salt, and pepper.",
                    "Rub seasoning mix all over chicken thighs.",
                    "Place chicken thighs skin-side up on a baking sheet. Bake for 30-35 minutes, or until skin is crispy and internal temperature reaches 165°F (74°C)."
                ],
                "ingredients": [
                    {"name": "bone-in, skin-on chicken thighs", "quantity": 4, "unit": ""},
                    {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "garlic powder", "quantity": 1, "unit": "tsp"},
                    {"name": "paprika", "quantity": 1, "unit": "tsp"},
                    {"name": "dried thyme", "quantity": 0.5, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/e0f2f7/263238?text=Crispy+Chicken"
            },
            {
                "name": "Pesto Chicken Sandwich",
                "cuisine": "Italian",
                "category": "Non-Vegetarian",
                "prep_time": 5,
                "cook_time": 10,
                "servings": 1,
                "instructions": [
                    "Toast 2 slices of your favorite bread.",
                    "Spread 1-2 tbsp pesto on one side of each toasted bread slice.",
                    "Layer 4 oz cooked chicken breast (sliced or shredded) on one slice of bread.",
                    "Top with 2 slices of fresh mozzarella and a few slices of roasted red bell pepper (from a jar).",
                    "Place the other slice of bread on top. Serve immediately."
                ],
                "ingredients": [
                    {"name": "bread slices", "quantity": 2, "unit": ""},
                    {"name": "pesto", "quantity": 2, "unit": "tbsp"},
                    {"name": "cooked chicken breast", "quantity": 4, "unit": "oz, sliced or shredded"},
                    {"name": "fresh mozzarella", "quantity": 2, "unit": "slices"},
                    {"name": "roasted red bell pepper", "quantity": 2, "unit": "slices (from jar)"}
                ],
                "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Pesto+Chicken+Sandwich"
            },
            {
                "name": "Avocado Toast",
                "cuisine": "Breakfast",
                "category": "Vegetarian",
                "prep_time": 5,
                "cook_time": 2,
                "servings": 1,
                "instructions": [
                    "Toast 1 slice of your favorite bread until golden.",
                    "In a small bowl, mash 1/2 ripe avocado with a fork.",
                    "Spread mashed avocado evenly over the toasted bread.",
                    "Season with a pinch of flaky sea salt, red pepper flakes (optional), and a squeeze of lemon juice (optional).",
                    "Serve immediately."
                ],
                "ingredients": [
                    {"name": "bread slice", "quantity": 1, "unit": ""},
                    {"name": "ripe avocado", "quantity": 0.5, "unit": ""},
                    {"name": "flaky sea salt", "quantity": 1, "unit": "pinch"},
                    {"name": "red pepper flakes", "quantity": 1, "unit": "pinch", "optional": True},
                    {"name": "lemon juice", "quantity": 1, "unit": "squeeze", "optional": True}
                ],
                "image_url": "https://placehold.co/400x300/e8f5e9/33691e?text=Avocado+Toast"
            },
            {
                "name": "Beef Stew",
                "cuisine": "European",
                "category": "Non-Vegetarian",
                "prep_time": 25,
                "cook_time": 120,
                "servings": 6,
                "instructions": [
                    "Pat 1.5 lb beef chuck (cut into 1-inch cubes) dry. Season with salt and pepper.",
                    "Heat 2 tbsp olive oil in a large Dutch oven or pot over medium-high heat. Brown beef in batches, then remove.",
                    "Add 1 more tbsp oil. Add 1 chopped onion, 2 chopped carrots, and 2 chopped celery stalks. Sauté for 7-10 minutes until softened.",
                    "Stir in 3 minced garlic cloves, 1 tsp dried thyme, and 1 bay leaf. Cook for 1 minute.",
                    "Pour in 4 cups beef broth and 1 cup red wine (optional). Scrape up any browned bits from the bottom of the pot.",
                    "Return roast to the pot. Add 1 lb small potatoes (halved) and 1 cup chopped mushrooms.",
                    "Bring to a simmer, then cover and transfer to a preheated oven at 325°F (160°C). Cook for 2.5 - 3 hours, or until beef is very tender.",
                    "Add 2 chopped potatoes (peeled) and 1 cup frozen peas. Cook for another 20-30 minutes until potatoes are tender.",
                    "Remove bay leaf. Season with salt and pepper. Serve hot."
                ],
                "ingredients": [
                    {"name": "beef chuck", "quantity": 1.5, "unit": "lb, cubed"},
                    {"name": "olive oil", "quantity": 3, "unit": "tbsp"},
                    {"name": "onion", "quantity": 1, "unit": "chopped"},
                    {"name": "carrots", "quantity": 2, "unit": "chopped"},
                    {"name": "celery stalks", "quantity": 2, "unit": "chopped"},
                    {"name": "garlic", "quantity": 3, "unit": "cloves, minced"},
                    {"name": "dried thyme", "quantity": 1, "unit": "tsp"},
                    {"name": "bay leaf", "quantity": 1, "unit": ""},
                    {"name": "beef broth", "quantity": 4, "unit": "cups"},
                    {"name": "red wine", "quantity": 1, "unit": "cup", "optional": True},
                    {"name": "tomato paste", "quantity": 1, "unit": "tbsp"},
                    {"name": "potatoes", "quantity": 2, "unit": "chopped, peeled"},
                    {"name": "frozen peas", "quantity": 1, "unit": "cup"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/e0f7fa/006064?text=Beef+Stew"
            },
            {
                "name": "Chicken Quesadillas",
                "cuisine": "Mexican",
                "category": "Non-Vegetarian",
                "prep_time": 10,
                "cook_time": 15,
                "servings": 2,
                "instructions": [
                    "Shred 1 cup cooked chicken breast.",
                    "Heat a large non-stick skillet over medium heat. Place 1 tortilla in the skillet.",
                    "Sprinkle half of 1 cup shredded cheddar cheese over one half of the tortilla.",
                    "Top with half of the shredded chicken and 2 tbsp salsa.",
                    "Fold the other half of the tortilla over the filling. Cook for 3-4 minutes per side, until golden brown and cheese is melted.",
                    "Repeat with remaining ingredients for the second quesadilla. Slice and serve with sour cream or guacamole."
                ],
                "ingredients": [
                    {"name": "cooked chicken breast", "quantity": 1, "unit": "cup, shredded"},
                    {"name": "flour tortillas", "quantity": 2, "unit": "large"},
                    {"name": "shredded cheddar cheese", "quantity": 1, "unit": "cup"},
                    {"name": "salsa", "quantity": 4, "unit": "tbsp"},
                    {"name": "sour cream", "quantity": 1, "unit": "optional"},
                    {"name": "guacamole", "quantity": 1, "unit": "optional"}
                ],
                "image_url": "https://placehold.co/400x300/ffccbc/bf360c?text=Chicken+Quesadilla"
            },
            {
                "name": "Vegetable Frittata",
                "cuisine": "Italian",
                "category": "Vegetarian",
                "prep_time": 15,
                "cook_time": 25,
                "servings": 4,
                "instructions": [
                    "Preheat oven to 375°F (190°C).",
                    "Heat 1 tbsp olive oil in an oven-safe, non-stick skillet over medium heat.",
                    "Add 1/2 cup chopped onion and 1 cup chopped bell peppers. Sauté for 5 minutes until softened.",
                    "Add 1 cup chopped spinach and cook until wilted. Remove vegetables from skillet and set aside.",
                    "In a bowl, whisk together 6 large eggs, 1/4 cup milk, 1/4 cup grated Parmesan cheese, salt, and pepper.",
                    "Return skillet to low heat. Pour egg mixture into the skillet. Sprinkle cooked vegetables evenly over the eggs.",
                    "Cook on stovetop for 5 minutes until edges begin to set.",
                    "Transfer skillet to preheated oven and bake for 15-20 minutes, or until frittata is set and lightly golden."
                ],
                "ingredients": [
                    {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "onion", "quantity": 0.5, "unit": "cup, chopped"},
                    {"name": "bell peppers", "quantity": 1, "unit": "cup, chopped"},
                    {"name": "spinach", "quantity": 1, "unit": "cup, chopped"},
                    {"name": "large eggs", "quantity": 6, "unit": ""},
                    {"name": "milk", "quantity": 0.25, "unit": "cup"},
                    {"name": "Parmesan cheese", "quantity": 0.25, "unit": "cup, grated"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Veg+Frittata"
            },
            {
                "name": "Simple Garden Salad",
                "cuisine": "American",
                "category": "Vegetarian",
                "prep_time": 10,
                "cook_time": 0,
                "servings": 2,
                "instructions": [
                    "In a large bowl, combine 4 cups mixed greens, 1/2 cup sliced cucumber, 1/2 cup cherry tomatoes (halved), and 1/4 cup shredded carrots.",
                    "For the dressing, whisk together 2 tbsp olive oil, 1 tbsp apple cider vinegar, 1 tsp Dijon mustard, salt, and pepper.",
                    "Pour dressing over salad and toss to coat. Serve immediately."
                ],
                "ingredients": [
                    {"name": "mixed greens", "quantity": 4, "unit": "cups"},
                    {"name": "cucumber", "quantity": 0.5, "unit": "cup, sliced"},
                    {"name": "cherry tomatoes", "quantity": 0.5, "unit": "cup, halved"},
                    {"name": "shredded carrots", "quantity": 0.25, "unit": "cup"},
                    {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
                    {"name": "apple cider vinegar", "quantity": 1, "unit": "tbsp"},
                    {"name": "Dijon mustard", "quantity": 1, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/e8f5e9/33691e?text=Garden+Salad"
            },
            {
                "name": "Grilled Cheese Sandwich",
                "cuisine": "American",
                "category": "Vegetarian",
                "prep_time": 2,
                "cook_time": 8,
                "servings": 1,
                "instructions": [
                    "Butter one side of each of 2 slices of bread.",
                    "Place one slice of bread, butter-side down, in a non-stick skillet over medium heat.",
                    "Layer 2 slices of cheddar cheese (or other favorite cheese) on the bread.",
                    "Place the second slice of bread, butter-side up, on top.",
                    "Cook for 3-4 minutes per side, or until bread is golden brown and cheese is melted and bubbly."
                ],
                "ingredients": [
                    {"name": "bread slices", "quantity": 2, "unit": ""},
                    {"name": "butter", "quantity": 1, "unit": "tbsp"},
                    {"name": "cheddar cheese slices", "quantity": 2, "unit": ""}
                ],
                "image_url": "https://placehold.co/400x300/fff8e1/ff8f00?text=Grilled+Cheese"
            },
            {
                "name": "Hummus and Veggie Wraps",
                "cuisine": "Mediterranean",
                "category": "Vegetarian",
                "prep_time": 10,
                "cook_time": 0,
                "servings": 2,
                "instructions": [
                    "Lay out 2 large whole wheat tortillas.",
                    "Spread 2-3 tbsp hummus evenly over each tortilla.",
                    "Layer with 1/2 cup shredded carrots, 1/2 cup chopped cucumber, 1/4 cup chopped bell pepper, and a handful of spinach leaves.",
                    "Roll up tortillas tightly. Slice in half and serve."
                ],
                "ingredients": [
                    {"name": "whole wheat tortillas", "quantity": 2, "unit": "large"},
                    {"name": "hummus", "quantity": 6, "unit": "tbsp"},
                    {"name": "shredded carrots", "quantity": 0.5, "unit": "cup"},
                    {"name": "chopped cucumber", "quantity": 0.5, "unit": "cup"},
                    {"name": "chopped bell pepper", "quantity": 0.25, "unit": "cup"},
                    {"name": "spinach leaves", "quantity": 1, "unit": "handful"}
                ],
                "image_url": "https://placehold.co/400x300/ede7f6/512da8?text=Veggie+Wraps"
            },
            {
                "name": "Tuna Salad Sandwich",
                "cuisine": "American",
                "category": "Non-Vegetarian",
                "prep_time": 5,
                "cook_time": 0,
                "servings": 1,
                "instructions": [
                    "Drain 1 (5 oz) can tuna.",
                    "In a small bowl, combine drained tuna with 2 tbsp mayonnaise, 1 tbsp finely chopped celery, and 1 tsp relish (optional).",
                    "Season with salt and pepper to taste. Mix well.",
                    "Spread tuna salad onto 2 slices of bread. Serve immediately, optionally with lettuce and tomato."
                ],
                "ingredients": [
                    {"name": "tuna", "quantity": 5, "unit": "oz can, drained"},
                    {"name": "mayonnaise", "quantity": 2, "unit": "tbsp"},
                    {"name": "celery", "quantity": 1, "unit": "tbsp, finely chopped"},
                    {"name": "relish", "quantity": 1, "unit": "tsp", "optional": True},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "bread slices", "quantity": 2, "unit": ""}
                ],
                "image_url": "https://placehold.co/400x300/e0f2f7/263238?text=Tuna+Sandwich"
            },
            {
                "name": "Chicken and Vegetable Skewers",
                "cuisine": "Grill/BBQ",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 15,
                "servings": 4,
                "instructions": [
                    "Cut 1 lb boneless, skinless chicken breast into 1-inch cubes.",
                    "Cut 1 bell pepper, 1 zucchini, and 1 red onion into 1-inch pieces.",
                    "Thread chicken and vegetables onto skewers, alternating them.",
                    "In a bowl, whisk together 3 tbsp olive oil, 2 minced garlic cloves, 1 tbsp lemon juice, 1 tsp dried oregano, salt, and pepper.",
                    "Brush skewers generously with the marinade.",
                    "Preheat grill to medium-high heat. Grill skewers for 10-15 minutes, turning occasionally, until chicken is cooked through and vegetables are tender-crisp."
                ],
                "ingredients": [
                    {"name": "boneless, skinless chicken breast", "quantity": 1, "unit": "lb, cubed"},
                    {"name": "bell pepper", "quantity": 1, "unit": ""},
                    {"name": "zucchini", "quantity": 1, "unit": ""},
                    {"name": "red onion", "quantity": 1, "unit": ""},
                    {"name": "wooden or metal skewers", "quantity": 8, "unit": ""},
                    {"name": "olive oil", "quantity": 3, "unit": "tbsp"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "lemon juice", "quantity": 1, "unit": "tbsp"},
                    {"name": "dried oregano", "quantity": 1, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/fffde7/f57f17?text=Chicken+Skewers"
            },
            {
                "name": "Quick Black Bean Soup",
                "cuisine": "Mexican",
                "category": "Vegetarian",
                "prep_time": 5,
                "cook_time": 15,
                "servings": 2,
                "instructions": [
                    "In a medium saucepan, combine 1 (15 oz) can black beans (undrained), 1 cup vegetable broth, 1/4 cup salsa, and 1/2 tsp cumin.",
                    "Bring to a simmer over medium heat. Cook for 10-12 minutes, stirring occasionally, until heated through and slightly thickened.",
                    "Use an immersion blender to blend about half of the soup for a creamier texture (optional).",
                    "Season with salt and pepper. Serve with a dollop of sour cream or chopped avocado."
                ],
                "ingredients": [
                    {"name": "black beans", "quantity": 15, "unit": "oz can, undrained"},
                    {"name": "vegetable broth", "quantity": 1, "unit": "cup"},
                    {"name": "salsa", "quantity": 0.25, "unit": "cup"},
                    {"name": "cumin", "quantity": 0.5, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "sour cream or avocado", "quantity": 1, "unit": "optional, for topping"}
                ],
                "image_url": "https://placehold.co/400x300/e8f5e9/33691e?text=Black+Bean+Soup"
            },
            {
                "name": "Spinach and Feta Omelette",
                "cuisine": "Mediterranean",
                "category": "Vegetarian",
                "prep_time": 5,
                "cook_time": 10,
                "servings": 1,
                "instructions": [
                    "Whisk 2 large eggs with 1 tbsp milk (optional), salt, and pepper in a small bowl.",
                    "Heat 1 tsp olive oil or butter in a small non-stick skillet over medium heat.",
                    "Add 1 cup fresh spinach and cook until wilted, about 1-2 minutes. Remove spinach and set aside.",
                    "Pour egg mixture into the skillet. As eggs set, gently push cooked portions to the center, tilting pan to allow uncooked egg to flow underneath.",
                    "When eggs are mostly set but still slightly wet on top, sprinkle cooked spinach and 2 tbsp crumbled feta cheese over one half.",
                    "Fold the other half over. Cook for another minute until cheese is melted. Serve immediately."
                ],
                "ingredients": [
                    {"name": "large eggs", "quantity": 2, "unit": ""},
                    {"name": "milk", "quantity": 1, "unit": "tbsp", "optional": True},
                    {"name": "salt", "quantity": 1, "unit": "pinch"},
                    {"name": "pepper", "quantity": 1, "unit": "pinch"},
                    {"name": "olive oil or butter", "quantity": 1, "unit": "tsp"},
                    {"name": "fresh spinach", "quantity": 1, "unit": "cup"},
                    {"name": "feta cheese", "quantity": 2, "unit": "tbsp, crumbled"}
                ],
                "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Spinach+Omelette"
            },
            {
                "name": "Teriyaki Chicken",
                "cuisine": "Asian",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 20,
                "servings": 4,
                "instructions": [
                    "Cut 1 lb boneless, skinless chicken thighs or breasts into 1-inch pieces.",
                    "In a bowl, whisk together 1/2 cup soy sauce, 2 tbsp honey or brown sugar, 1 tbsp rice vinegar, 1 tsp grated ginger, 1 minced garlic clove, and 1 tsp sesame oil.",
                    "Add chicken to marinade and toss to coat. Marinate for at least 15 minutes (or up to 30 mins).",
                    "Heat 1 tbsp vegetable oil in a large skillet over medium-high heat. Add chicken and cook until browned on all sides and cooked through. Pour remaining marinade over chicken and bring to a simmer.",
                    "Cook for 2-3 minutes, stirring, until sauce thickens and coats the chicken. Garnish with sesame seeds and chopped green onions. Serve with rice."
                ],
                "ingredients": [
                    {"name": "boneless, skinless chicken thighs or breasts", "quantity": 1, "unit": "lb"},
                    {"name": "soy sauce", "quantity": 0.5, "unit": "cup"},
                    {"name": "honey or brown sugar", "quantity": 2, "unit": "tbsp"},
                    {"name": "rice vinegar", "quantity": 1, "unit": "tbsp"},
                    {"name": "grated ginger", "quantity": 1, "unit": "tsp"},
                    {"name": "garlic", "quantity": 1, "unit": "clove, minced"},
                    {"name": "sesame oil", "quantity": 1, "unit": "tsp"},
                    {"name": "vegetable oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "sesame seeds", "quantity": 1, "unit": "optional, for garnish"},
                    {"name": "green onions", "quantity": 1, "unit": "optional, chopped, for garnish"}
                ],
                "image_url": "https://placehold.co/400x300/fffde7/f57f17?text=Teriyaki+Chicken"
            },
            {
                "name": "Vegetarian Lentil Shepherd's Pie",
                "cuisine": "British",
                "category": "Vegetarian",
                "prep_time": 25,
                "cook_time": 45,
                "servings": 6,
                "instructions": [
                    "Preheat oven to 375°F (190°C).",
                    "For filling: Heat 1 tbsp olive oil in a large pot. Add 1 chopped onion, 2 chopped carrots, and 2 chopped celery stalks. Sauté for 7-10 minutes.",
                    "Add 2 minced garlic cloves, 1 cup cooked green lentils, 1 (14.5 oz) can diced tomatoes, 1 cup vegetable broth, 1 tbsp tomato paste, 1 tsp dried thyme, and 1/2 tsp dried rosemary.",
                    "Bring to a simmer, reduce heat, and cook for 15 minutes, stirring occasionally, until thickened.",
                    "For topping: Boil 2 lbs potatoes (peeled and chopped) until very tender. Drain and mash with 1/4 cup milk, 2 tbsp butter, salt, and pepper.",
                    "Pour lentil filling into a 9x13 inch baking dish. Spread mashed potatoes evenly over the top.",
                    "Bake for 25-30 minutes, or until topping is golden and filling is bubbly."
                ],
                "ingredients": [
                    {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "onion", "quantity": 1, "unit": "chopped"},
                    {"name": "carrots", "quantity": 2, "unit": "chopped"},
                    {"name": "celery stalks", "quantity": 2, "unit": "chopped"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "cooked green lentils", "quantity": 1, "unit": "cup"},
                    {"name": "diced tomatoes", "quantity": 14.5, "unit": "oz can"},
                    {"name": "vegetable broth", "quantity": 1, "unit": "cup"},
                    {"name": "tomato paste", "quantity": 1, "unit": "tbsp"},
                    {"name": "dried thyme", "quantity": 1, "unit": "tsp"},
                    {"name": "dried rosemary", "quantity": 0.5, "unit": "tsp"},
                    {"name": "potatoes", "quantity": 2, "unit": "lbs, peeled and chopped"},
                    {"name": "milk", "quantity": 0.25, "unit": "cup"},
                    {"name": "butter", "quantity": 2, "unit": "tbsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/e8f5e9/33691e?text=Lentil+Shepherd's+Pie"
            },
            {
                "name": "Chicken Caesar Salad",
                "cuisine": "American",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 10,
                "servings": 2,
                "instructions": [
                    "Cook 8 oz chicken breast (grilled or pan-fried) until cooked through. Slice into strips.",
                    "In a large bowl, combine 4 cups chopped romaine lettuce, 1/2 cup croutons, and 1/4 cup grated Parmesan cheese.",
                    "Add Caesar dressing and toss to coat.",
                    "Top with sliced chicken breast. Serve immediately."
                ],
                "ingredients": [
                    {"name": "chicken breast", "quantity": 8, "unit": "oz, cooked"},
                    {"name": "romaine lettuce", "quantity": 4, "unit": "cups, chopped"},
                    {"name": "croutons", "quantity": 0.5, "unit": "cup"},
                    {"name": "Parmesan cheese", "quantity": 0.25, "unit": "cup, grated"},
                    {"name": "Caesar dressing", "quantity": 0.5, "unit": "cup"}
                ],
                "image_url": "https://placehold.co/400x300/e0f2f7/263238?text=Chicken+Caesar+Salad"
            },
            {
                "name": "Thai Green Curry",
                "cuisine": "Thai",
                "category": "Non-Vegetarian",
                "prep_time": 20,
                "cook_time": 30,
                "servings": 4,
                "instructions": [
                    "Heat 1 tbsp vegetable oil in a large pot or wok. Add 2 tbsp green curry paste and cook for 1 minute until fragrant.",
                    "Stir in 1 (13.5 oz) can full-fat coconut milk and 1/2 cup chicken or vegetable broth. Bring to a simmer.",
                    "Add 1 lb boneless, skinless chicken thighs (cut into bite-sized pieces) or firm tofu cubes. Cook for 10-12 minutes until cooked through.",
                    "Add 1 cup chopped bell peppers, 1 cup bamboo shoots (sliced), and 1 cup snap peas. Cook for 5-7 minutes until vegetables are tender-crisp.",
                    "Stir in 1 tbsp fish sauce (or soy sauce for vegetarian), 1 tsp brown sugar, and juice of 1 lime.",
                    "Garnish with fresh basil leaves and serve hot over jasmine rice."
                ],
                "ingredients": [
                    {"name": "vegetable oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "green curry paste", "quantity": 2, "unit": "tbsp"},
                    {"name": "full-fat coconut milk", "quantity": 13.5, "unit": "oz can"},
                    {"name": "chicken or vegetable broth", "quantity": 0.5, "unit": "cup"},
                    {"name": "boneless, skinless chicken thighs or firm tofu", "quantity": 1, "unit": "lb"},
                    {"name": "bell peppers", "quantity": 1, "unit": "cup, chopped"},
                    {"name": "bamboo shoots", "quantity": 1, "unit": "cup, sliced"},
                    {"name": "snap peas", "quantity": 1, "unit": "cup"},
                    {"name": "fish sauce", "quantity": 1, "unit": "tbsp"},
                    {"name": "brown sugar", "quantity": 1, "unit": "tsp"},
                    {"name": "lime juice", "quantity": 1, "unit": "from 1 lime"},
                    {"name": "fresh basil leaves", "quantity": 1, "unit": "for garnish"},
                    {"name": "jasmine rice", "quantity": 1, "unit": "to serve"}
                ],
                "image_url": "https://placehold.co/400x300/fffde7/f57f17?text=Thai+Green+Curry"
            },
            {
                "name": "Classic Macaroni and Cheese",
                "cuisine": "American",
                "category": "Vegetarian",
                "prep_time": 10,
                "cook_time": 25,
                "servings": 4,
                "instructions": [
                    "Cook 8 oz elbow macaroni according to package directions. Drain.",
                    "In a large saucepan, melt 3 tbsp butter over medium heat. Whisk in 3 tbsp all-purpose flour and cook for 1 minute.",
                    "Gradually whisk in 2 cups milk until smooth. Bring to a simmer, whisking constantly, until sauce thickens, about 5 minutes.",
                    "Remove from heat. Stir in 2 cups shredded cheddar cheese and 1/2 cup grated Gruyère or Parmesan cheese until melted and smooth.",
                    "Add cooked macaroni to the cheese sauce and stir to combine. Season with salt and pepper to taste.",
                    "Serve immediately, or transfer to a baking dish, top with breadcrumbs, and bake at 375°F (190°C) for 15 minutes for a baked mac and cheese."
                ],
                "ingredients": [
                    {"name": "elbow macaroni", "quantity": 8, "unit": "oz"},
                    {"name": "butter", "quantity": 3, "unit": "tbsp"},
                    {"name": "all-purpose flour", "quantity": 3, "unit": "tbsp"},
                    {"name": "milk", "quantity": 2, "unit": "cups"},
                    {"name": "shredded cheddar cheese", "quantity": 2, "unit": "cups"},
                    {"name": "Gruyère or Parmesan cheese", "quantity": 0.5, "unit": "cup, grated"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "breadcrumbs", "quantity": 1, "unit": "optional, for topping"}
                ],
                "image_url": "https://placehold.co/400x300/fff8e1/ff8f00?text=Mac+Cheese"
            },
            {
                "name": "Chicken Fajitas",
                "cuisine": "Mexican",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 20,
                "servings": 4,
                "instructions": [
                    "Slice 1.5 lbs chicken breast into thin strips.",
                    "Slice 2 bell peppers (different colors) and 1 onion into thin strips.",
                    "In a large bowl, toss chicken and vegetables with 2 tbsp olive oil and 1 packet (1 oz) fajita seasoning.",
                    "Heat a large cast-iron skillet or heavy-bottomed pan over medium-high heat until very hot.",
                    "Add chicken and vegetables to the hot skillet in a single layer. Cook for 5-7 minutes, stirring occasionally, until chicken is cooked through and vegetables are tender-crisp and slightly charred.",
                    "Serve immediately with warm tortillas and desired toppings like salsa, guacamole, and sour cream."
                ],
                "ingredients": [
                    {"name": "chicken breast", "quantity": 1.5, "unit": "lbs, sliced"},
                    {"name": "bell peppers", "quantity": 2, "unit": "sliced"},
                    {"name": "onion", "quantity": 1, "unit": "sliced"},
                    {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
                    {"name": "fajita seasoning", "quantity": 1, "unit": "packet (1 oz)"},
                    {"name": "tortillas", "quantity": 8, "unit": "warm"},
                    {"name": "salsa", "quantity": 1, "unit": "optional"},
                    {"name": "guacamole", "quantity": 1, "unit": "optional"},
                    {"name": "sour cream", "quantity": 1, "unit": "optional"}
                ],
                "image_url": "https://placehold.co/400x300/ffccbc/bf360c?text=Chicken+Fajitas"
            },
            {
                "name": "Simple Tomato Pasta",
                "cuisine": "Italian",
                "category": "Vegetarian",
                "prep_time": 5,
                "cook_time": 20,
                "servings": 2,
                "instructions": [
                    "Cook 8 oz spaghetti or preferred pasta according to package directions. Reserve 1/2 cup pasta water. Drain.",
                    "While pasta cooks, heat 1 tbsp olive oil in a large skillet over medium heat. Add 3 minced garlic cloves and cook for 1 minute until fragrant.",
                    "Stir in 1 (14.5 oz) can crushed tomatoes and 1/2 tsp dried oregano. Bring to a simmer.",
                    "Reduce heat and cook for 10-15 minutes, stirring occasionally, until sauce is slightly thickened.",
                    "Add drained pasta to the skillet. Toss to coat, adding reserved pasta water as needed to reach desired consistency.",
                    "Stir in 1/4 cup fresh basil leaves (chopped). Season with salt and pepper. Serve with grated Parmesan cheese."
                ],
                "ingredients": [
                    {"name": "spaghetti or pasta", "quantity": 8, "unit": "oz"},
                    {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "garlic", "quantity": 3, "unit": "cloves, minced"},
                    {"name": "crushed tomatoes", "quantity": 14.5, "unit": "oz can"},
                    {"name": "dried oregano", "quantity": 0.5, "unit": "tsp"},
                    {"name": "fresh basil leaves", "quantity": 0.25, "unit": "cup, chopped"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "Parmesan cheese", "quantity": 1, "unit": "optional, for serving"}
                ],
                "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Tomato+Pasta"
            },
            {
                "name": "Chicken and Rice Soup",
                "cuisine": "Comfort Food",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 35,
                "servings": 6,
                "instructions": [
                    "Heat 1 tbsp olive oil in a large pot. Add 1 chopped onion, 2 chopped carrots, and 2 chopped celery stalks. Sauté for 5-7 minutes.",
                    "Add 2 minced garlic cloves and cook for 1 minute.",
                    "Pour in 8 cups chicken broth and 1 cup cooked shredded chicken. Bring to a simmer.",
                    "Add 1 cup chopped potatoes (peeled) and 1/2 cup uncooked white rice.",
                    "Cook for 20-25 minutes, or until rice is tender.",
                    "Season with salt, pepper, and fresh parsley. Serve hot."
                ],
                "ingredients": [
                    {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "onion", "quantity": 1, "unit": "chopped"},
                    {"name": "carrots", "quantity": 2, "unit": "chopped"},
                    {"name": "celery stalks", "quantity": 2, "unit": "chopped"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "chicken broth", "quantity": 8, "unit": "cups"},
                    {"name": "cooked shredded chicken", "quantity": 1, "unit": "cup"},
                    {"name": "uncooked white rice", "quantity": 0.5, "unit": "cup"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "fresh parsley", "quantity": 1, "unit": "for garnish"}
                ],
                "image_url": "https://placehold.co/400x300/e0f2f7/263238?text=Chicken+Rice+Soup"
            },
            {
                "name": "Classic Pot Roast",
                "cuisine": "American",
                "category": "Non-Vegetarian",
                "prep_time": 20,
                "cook_time": 180,
                "servings": 6,
                "instructions": [
                    "Pat 3 lbs beef chuck roast dry. Season generously with salt and pepper.",
                    "Heat 2 tbsp olive oil in a large Dutch oven over medium-high heat. Brown roast on all sides.",
                    "Remove roast. Add 1 chopped onion, 2 chopped carrots, and 2 chopped celery stalks to the pot. Sauté for 5 minutes.",
                    "Stir in 3 minced garlic cloves, 1 tbsp tomato paste, and 1 tsp dried thyme. Cook for 1 minute.",
                    "Pour in 2 cups beef broth and 1 cup red wine (optional). Scrape up any browned bits from the bottom of the pot.",
                    "Return roast to the pot. Add 1 lb small potatoes (halved) and 1 cup chopped mushrooms.",
                    "Bring to a simmer, then cover and transfer to a preheated oven at 325°F (160°C). Cook for 2.5 - 3 hours, or until beef is fork-tender.",
                    "Add 2 chopped potatoes (peeled) and 1 cup frozen peas. Cook for another 20-30 minutes until potatoes are tender.",
                    "Remove bay leaf. Season with salt and pepper. Serve hot."
                ],
                "ingredients": [
                    {"name": "beef chuck roast", "quantity": 3, "unit": "lbs"},
                    {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
                    {"name": "onion", "quantity": 1, "unit": "chopped"},
                    {"name": "carrots", "quantity": 2, "unit": "chopped"},
                    {"name": "celery stalks", "quantity": 2, "unit": "chopped"},
                    {"name": "garlic", "quantity": 3, "unit": "cloves, minced"},
                    {"name": "tomato paste", "quantity": 1, "unit": "tbsp"},
                    {"name": "dried thyme", "quantity": 1, "unit": "tsp"},
                    {"name": "beef broth", "quantity": 2, "unit": "cups"},
                    {"name": "red wine", "quantity": 1, "unit": "cup", "optional": True},
                    {"name": "small potatoes", "quantity": 1, "unit": "lb, halved"},
                    {"name": "mushrooms", "quantity": 1, "unit": "cup, chopped"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "cornstarch", "quantity": 1, "unit": "optional, for thickening"}
                ],
                "image_url": "https://placehold.co/400x300/c8e6c9/2e7d32?text=Pot+Roast"
            },
            {
                "name": "Chicken Pad Thai",
                "cuisine": "Thai",
                "category": "Non-Vegetarian",
                "prep_time": 25,
                "cook_time": 20,
                "servings": 2,
                "instructions": [
                    "Soak 6 oz dried flat rice noodles in hot water for 15-20 minutes until tender but still firm. Drain.",
                    "Slice 8 oz chicken breast into thin strips.",
                    "In a bowl, whisk together 2 tbsp fish sauce, 2 tbsp brown sugar, 1 tbsp rice vinegar, 1 tbsp lime juice, and 1 tsp sriracha (optional).",
                    "Add chicken to marinade and toss to coat. Marinate for at least 15 minutes (or up to 30 mins).",
                    "Heat 1 tbsp vegetable oil in a large wok or skillet over high heat. Add chicken and cook until browned and cooked through. Push chicken to one side.",
                    "Add 2 minced garlic cloves and 1/4 cup chopped shallots (or red onion) to the empty side and cook for 1 minute.",
                    "Push everything to one side. Crack 1 large egg into the empty side and scramble until cooked. Mix with other ingredients.",
                    "Add drained noodles to the wok. Pour sauce over noodles. Toss constantly for 2-3 minutes until noodles are coated.",
                    "Stir in 1 cup bean sprouts and 1/4 cup chopped peanuts. Serve immediately with extra lime wedges and cilantro."
                ],
                "ingredients": [
                    {"name": "dried flat rice noodles", "quantity": 6, "unit": "oz"},
                    {"name": "chicken breast", "quantity": 8, "unit": "oz, sliced"},
                    {"name": "fish sauce", "quantity": 2, "unit": "tbsp"},
                    {"name": "brown sugar", "quantity": 2, "unit": "tbsp"},
                    {"name": "rice vinegar", "quantity": 1, "unit": "tbsp"},
                    {"name": "lime juice", "quantity": 1, "unit": "tbsp"},
                    {"name": "sriracha", "quantity": 1, "unit": "tsp", "optional": True},
                    {"name": "vegetable oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "chopped shallots or red onion", "quantity": 0.25, "unit": "cup"},
                    {"name": "large egg", "quantity": 1, "unit": ""},
                    {"name": "bean sprouts", "quantity": 1, "unit": "cup"},
                    {"name": "chopped peanuts", "quantity": 0.25, "unit": "cup"},
                    {"name": "lime wedges", "quantity": 1, "unit": "for serving"},
                    {"name": "cilantro", "quantity": 1, "unit": "for garnish"}
                ],
                "image_url": "https://placehold.co/400x300/fffde7/f57f17?text=Chicken+Pad+Thai"
            },
            {
                "name": "Veggie Burgers",
                "cuisine": "Vegetarian",
                "category": "Vegetarian",
                "prep_time": 20,
                "cook_time": 15,
                "servings": 4,
                "instructions": [
                    "Preheat oven to 375°F (190°C) or prepare grill/skillet.",
                    "In a large bowl, combine 1 can (15oz) black beans (mashed), 1 cup cooked quinoa, 1/2 cup breadcrumbs, 1/4 cup finely chopped onion, 1 large egg, 1 tbsp soy sauce, 1 tsp smoked paprika, and 1/2 tsp garlic powder.",
                    "Mix well until combined. Form into 4 patties.",
                    "Bake for 10-12 minutes per side, or cook in a lightly oiled skillet/grill until browned and heated through.",
                    "Serve on buns with desired toppings."
                ],
                "ingredients": [
                    {"name": "black beans", "quantity": 15, "unit": "oz can, rinsed and mashed"},
                    {"name": "cooked quinoa", "quantity": 1, "unit": "cup"},
                    {"name": "breadcrumbs", "quantity": 0.5, "unit": "cup"},
                    {"name": "onion", "quantity": 0.25, "unit": "cup, finely chopped"},
                    {"name": "large egg", "quantity": 1, "unit": ""},
                    {"name": "soy sauce", "quantity": 1, "unit": "tbsp"},
                    {"name": "smoked paprika", "quantity": 1, "unit": "tsp"},
                    {"name": "garlic powder", "quantity": 0.5, "unit": "tsp"},
                    {"name": "burger buns", "quantity": 4, "unit": ""}
                ],
                "image_url": "https://placehold.co/400x300/c8e6c9/2e7d32?text=Veggie+Burger"
            },
            {
                "name": "Chicken Lettuce Wraps",
                "cuisine": "Asian",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 15,
                "servings": 4,
                "instructions": [
                    "Heat 1 tbsp sesame oil in a large skillet or wok over medium-high heat. Add 1 lb ground chicken and cook until browned. Drain excess fat.",
                    "Stir in 1/4 cup hoisin sauce, 2 tbsp soy sauce, 1 tbsp rice vinegar, 1 tbsp grated ginger, and 2 minced garlic cloves. Cook for 2-3 minutes.",
                    "Add 1/2 cup finely chopped water chestnuts and 1/2 cup shredded carrots. Cook for 3-5 minutes until heated through.",
                    "Serve warm mixture in large lettuce cups (e.g., butter lettuce or iceberg). Garnish with chopped green onions and sesame seeds."
                ],
                "ingredients": [
                    {"name": "sesame oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "ground chicken", "quantity": 1, "unit": "lb"},
                    {"name": "hoisin sauce", "quantity": 0.25, "unit": "cup"},
                    {"name": "soy sauce", "quantity": 2, "unit": "tbsp"},
                    {"name": "rice vinegar", "quantity": 1, "unit": "tbsp"},
                    {"name": "grated ginger", "quantity": 1, "unit": "tbsp"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "water chestnuts", "quantity": 0.5, "unit": "cup, finely chopped"},
                    {"name": "shredded carrots", "quantity": 0.5, "unit": "cup"},
                    {"name": "lettuce cups", "quantity": 1, "unit": "large head"},
                    {"name": "green onions", "quantity": 1, "unit": "for garnish"},
                    {"name": "sesame seeds", "quantity": 1, "unit": "for garnish"}
                ],
                "image_url": "https://placehold.co/400x300/fffde7/f57f17?text=Chicken+Lettuce+Wraps"
            },
            {
                "name": "Creamy Tomato Soup",
                "cuisine": "European",
                "category": "Vegetarian",
                "prep_time": 10,
                "cook_time": 25,
                "servings": 4,
                "instructions": [
                    "Melt 2 tbsp butter in a large pot. Add 1 chopped onion and cook until softened.",
                    "Stir in 1 minced garlic clove and cook for 1 minute.",
                    "Add 28 oz can crushed tomatoes, 4 cups vegetable broth, 1 tsp sugar, and 1/2 tsp dried basil.",
                    "Bring to a simmer, then reduce heat and cook for 15-20 minutes.",
                    "Blend with an immersion blender until smooth (or transfer to a regular blender).",
                    "Stir in 1/2 cup heavy cream. Season with salt and pepper to taste. Serve hot."
                ],
                "ingredients": [
                    {"name": "butter", "quantity": 2, "unit": "tbsp"},
                    {"name": "onion", "quantity": 1, "unit": "chopped"},
                    {"name": "garlic", "quantity": 1, "unit": "clove, minced"},
                    {"name": "crushed tomatoes", "quantity": 28, "unit": "oz can"},
                    {"name": "vegetable broth", "quantity": 4, "unit": "cups"},
                    {"name": "sugar", "quantity": 1, "unit": "tsp"},
                    {"name": "dried basil", "quantity": 0.5, "unit": "tsp"},
                    {"name": "heavy cream", "quantity": 0.5, "unit": "cup"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/fff3e0/e65100?text=Creamy+Tomato+Soup"
            },
            {
                "name": "Chicken Enchiladas",
                "cuisine": "Mexican",
                "category": "Non-Vegetarian",
                "prep_time": 20,
                "cook_time": 25,
                "servings": 6,
                "instructions": [
                    "Preheat oven to 375°F (190°C).",
                    "In a bowl, combine 2 cups cooked shredded chicken, 1 cup shredded Monterey Jack cheese, and 1/2 cup green chilies (canned, diced).",
                    "Spread 1/2 cup enchilada sauce in the bottom of a 9x13 inch baking dish.",
                    "Warm 12 corn tortillas slightly to make them pliable. Fill each tortilla with chicken mixture and roll up tightly.",
                    "Place seam-side down in the baking dish. Pour remaining enchilada sauce over enchiladas and sprinkle with 1 cup shredded cheddar cheese.",
                    "Bake for 20-25 minutes, or until cheese is bubbly and lightly browned. Garnish with fresh cilantro and serve."
                ],
                "ingredients": [
                    {"name": "cooked shredded chicken", "quantity": 2, "unit": "cups"},
                    {"name": "shredded Monterey Jack cheese", "quantity": 1, "unit": "cup"},
                    {"name": "green chilies", "quantity": 0.5, "unit": "cup, canned, diced"},
                    {"name": "enchilada sauce", "quantity": 1, "unit": "can (19 oz)"},
                    {"name": "corn tortillas", "quantity": 12, "unit": ""},
                    {"name": "shredded cheddar cheese", "quantity": 1, "unit": "cup"},
                    {"name": "fresh cilantro", "quantity": 1, "unit": "for garnish"}
                ],
                "image_url": "https://placehold.co/400x300/ffccbc/bf360c?text=Chicken+Enchiladas"
            },
            {
                "name": "Spinach Salad with Poppy Seed Dressing",
                "cuisine": "American",
                "category": "Vegetarian",
                "prep_time": 15,
                "cook_time": 0,
                "servings": 4,
                "instructions": [
                    "In a large bowl, combine 6 cups fresh spinach, 1/2 cup sliced strawberries, 1/4 cup sliced red onion, and 1/4 cup crumbled feta cheese (optional).",
                    "For the dressing: In a small jar or bowl, whisk together 1/4 cup olive oil, 2 tbsp apple cider vinegar, 1 tbsp honey, 1 tsp Dijon mustard, 1 tsp poppy seeds, salt, and pepper.",
                    "Pour dressing over salad and toss gently to coat. Serve immediately."
                ],
                "ingredients": [
                    {"name": "fresh spinach", "quantity": 6, "unit": "cups"},
                    {"name": "sliced strawberries", "quantity": 0.5, "unit": "cup"},
                    {"name": "sliced red onion", "quantity": 0.25, "unit": "cup"},
                    {"name": "feta cheese", "quantity": 0.25, "unit": "cup, crumbled", "optional": True},
                    {"name": "olive oil", "quantity": 0.25, "unit": "cup"},
                    {"name": "apple cider vinegar", "quantity": 2, "unit": "tbsp"},
                    {"name": "honey", "quantity": 1, "unit": "tbsp"},
                    {"name": "Dijon mustard", "quantity": 1, "unit": "tsp"},
                    {"name": "poppy seeds", "quantity": 1, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/e8f5e9/33691e?text=Spinach+Salad"
            },
            {
                "name": "Stuffed Bell Peppers",
                "cuisine": "Mediterranean",
                "category": "Non-Vegetarian", # Can also be vegetarian if using plant-based mince
                "prep_time": 20,
                "cook_time": 40,
                "servings": 4,
                "instructions": [
                    "Preheat oven to 375°F (190°C).",
                    "Halve 4 bell peppers lengthwise and remove seeds. Place cut-side up in a baking dish.",
                    "In a bowl, combine 1 lb cooked ground beef or turkey, 1 cup cooked rice, 1/2 cup chopped onion, 1/2 cup chopped tomatoes, 1/4 cup tomato sauce, 1 tsp Italian seasoning, salt, and pepper.",
                    "Spoon mixture evenly into bell pepper halves.",
                    "Pour 1/2 inch water into the bottom of the baking dish.",
                    "Bake for 30-35 minutes, or until peppers are tender and filling is heated through. Optionally top with cheese for last 5 minutes."
                ],
                "ingredients": [
                    {"name": "bell peppers", "quantity": 4, "unit": ""},
                    {"name": "cooked ground beef or turkey", "quantity": 1, "unit": "lb"},
                    {"name": "cooked rice", "quantity": 1, "unit": "cup"},
                    {"name": "chopped onion", "quantity": 0.5, "unit": "cup"},
                    {"name": "chopped tomatoes", "quantity": 0.5, "unit": "cup"},
                    {"name": "tomato sauce", "quantity": 0.25, "unit": "cup"},
                    {"name": "Italian seasoning", "quantity": 1, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "shredded cheese", "quantity": 1, "unit": "optional"}
                ],
                "image_url": "https://placehold.co/400x300/c8e6c9/2e7d32?text=Stuffed+Peppers"
            },
            {
                "name": "Baked Ziti",
                "cuisine": "Italian",
                "category": "Vegetarian",
                "prep_time": 20,
                "cook_time": 30,
                "servings": 6,
                "instructions": [
                    "Preheat oven to 375°F (190°C).",
                    "Cook 12 oz ziti pasta according to package directions until al dente. Drain.",
                    "In a large bowl, combine cooked ziti, 1 (24 oz) jar marinara sauce, 15 oz ricotta cheese, 1 large egg, 1/2 cup grated Parmesan cheese, and 1/4 cup chopped fresh parsley.",
                    "Stir well to combine all ingredients.",
                    "Pour half of the ziti mixture into a 9x13 inch baking dish. Top with 1 cup shredded mozzarella cheese.",
                    "Add remaining ziti mixture and top with another 1 cup shredded mozzarella cheese.",
                    "Bake for 25-30 minutes, or until bubbly and cheese is melted and lightly golden. Let stand 5 minutes before serving."
                ],
                "ingredients": [
                    {"name": "ziti pasta", "quantity": 12, "unit": "oz"},
                    {"name": "marinara sauce", "quantity": 24, "unit": "oz jar"},
                    {"name": "ricotta cheese", "quantity": 15, "unit": "oz"},
                    {"name": "large egg", "quantity": 1, "unit": ""},
                    {"name": "Parmesan cheese", "quantity": 0.5, "unit": "cup, grated"},
                    {"name": "fresh parsley", "quantity": 0.25, "unit": "cup, chopped"},
                    {"name": "shredded mozzarella cheese", "quantity": 2, "unit": "cups"}
                ],
                "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Baked+Ziti"
            },
            {
                "name": "Chicken Tenders",
                "cuisine": "American",
                "category": "Non-Vegetarian",
                "prep_time": 10,
                "cook_time": 15,
                "servings": 2,
                "instructions": [
                    "Preheat oven to 400°F (200°C).",
                    "Pat 1 lb chicken tenderloins dry.",
                    "In a shallow dish, whisk 1 large egg. In another shallow dish, combine 1 cup breadcrumbs, 1/2 tsp garlic powder, 1/2 tsp paprika, salt, and pepper.",
                    "Dip each chicken tenderloin in egg, then dredge in breadcrumb mixture, pressing to coat.",
                    "Place coated chicken on a baking sheet. Spray lightly with cooking spray or drizzle with oil.",
                    "Bake for 12-15 minutes, flipping halfway, until golden brown and cooked through."
                ],
                "ingredients": [
                    {"name": "chicken tenderloins", "quantity": 1, "unit": "lb"},
                    {"name": "large egg", "quantity": 1, "unit": ""},
                    {"name": "breadcrumbs", "quantity": 1, "unit": "cup"},
                    {"name": "garlic powder", "quantity": 0.5, "unit": "tsp"},
                    {"name": "paprika", "quantity": 0.5, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "cooking spray or oil", "quantity": 1, "unit": "for baking"}
                ],
                "image_url": "https://placehold.co/400x300/e0f2f7/263238?text=Chicken+Tenders"
            },
            {
                "name": "Shrimp Scampi",
                "cuisine": "Italian",
                "category": "Non-Vegetarian",
                "prep_time": 10,
                "cook_time": 15,
                "servings": 2,
                "instructions": [
                    "Cook 8 oz linguine or spaghetti according to package directions. Reserve 1/2 cup pasta water. Drain.",
                    "Pat 1 lb shrimp (peeled and deveined) dry. Season with salt and pepper.",
                    "Heat 2 tbsp olive oil and 2 tbsp butter in a large skillet over medium heat. Add 4 minced garlic cloves and 1 minute until fragrant.",
                    "Add shrimp and cook for 2-3 minutes per side until pink and opaque. Remove shrimp.",
                    "Add 1/4 cup dry white wine or chicken broth to the skillet. Bring to a simmer and scrape up any browned bits.",
                    "Stir in 2 tbsp lemon juice and 2 tbsp chopped fresh parsley. Return shrimp to skillet. Add drained pasta.",
                    "Toss everything together, adding reserved pasta water as needed to create a light sauce. Serve immediately."
                ],
                "ingredients": [
                    {"name": "linguine or spaghetti", "quantity": 8, "unit": "oz"},
                    {"name": "shrimp", "quantity": 1, "unit": "lb, peeled and deveined"},
                    {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
                    {"name": "butter", "quantity": 2, "unit": "tbsp"},
                    {"name": "garlic", "quantity": 4, "unit": "cloves, minced"},
                    {"name": "dry white wine or chicken broth", "quantity": 0.25, "unit": "cup"},
                    {"name": "lemon juice", "quantity": 2, "unit": "tbsp"},
                    {"name": "fresh parsley", "quantity": 2, "unit": "tbsp, chopped"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Shrimp+Scampi"
            },
            {
                "name": "Simple Tomato Cucumber Salad",
                "cuisine": "Mediterranean",
                "category": "Vegetarian",
                "prep_time": 10,
                "cook_time": 0,
                "servings": 2,
                "instructions": [
                    "Dice 2 medium tomatoes and 1 large cucumber.",
                    "In a bowl, combine diced tomatoes and cucumber with 1/4 cup finely chopped red onion and 1/4 cup chopped fresh parsley.",
                    "For the dressing, whisk together 2 tbsp olive oil, 1 tbsp lemon juice, and a pinch of salt and pepper.",
                    "Pour dressing over vegetables and toss gently to combine. Serve immediately as a side dish."
                ],
                "ingredients": [
                    {"name": "medium tomatoes", "quantity": 2, "unit": ""},
                    {"name": "large cucumber", "quantity": 1, "unit": ""},
                    {"name": "red onion", "quantity": 0.25, "unit": "cup, finely chopped"},
                    {"name": "fresh parsley", "quantity": 0.25, "unit": "cup, chopped"},
                    {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
                    {"name": "lemon juice", "quantity": 1, "unit": "tbsp"},
                    {"name": "salt", "quantity": 1, "unit": "pinch"},
                    {"name": "pepper", "quantity": 1, "unit": "pinch"}
                ],
                "image_url": "https://placehold.co/400x300/e8f5e9/33691e?text=Tomato+Cucumber+Salad"
            },
            {
                "name": "Breakfast Burritos",
                "cuisine": "Mexican",
                "category": "Vegetarian",
                "prep_time": 10,
                "cook_time": 15,
                "servings": 2,
                "instructions": [
                    "Scramble 4 large eggs in a bowl with a pinch of salt and pepper. Cook in a lightly oiled skillet until set. Remove.",
                    "In the same skillet, cook 1/2 cup diced cooked potatoes or frozen hash browns until browned and crispy.",
                    "Warm 2 large flour tortillas.",
                    "On each tortilla, layer scrambled eggs, cooked potatoes, 1/4 cup shredded cheddar cheese, and 2 tbsp salsa.",
                    "Fold in the sides of the tortilla, then roll up tightly. Serve immediately."
                ],
                "ingredients": [
                    {"name": "large eggs", "quantity": 4, "unit": ""},
                    {"name": "salt", "quantity": 1, "unit": "pinch"},
                    {"name": "pepper", "quantity": 1, "unit": "pinch"},
                    {"name": "cooked diced potatoes or hash browns", "quantity": 0.5, "unit": "cup"},
                    {"name": "large flour tortillas", "quantity": 2, "unit": ""},
                    {"name": "shredded cheddar cheese", "quantity": 0.5, "unit": "cup"},
                    {"name": "salsa", "quantity": 4, "unit": "tbsp"}
                ],
                "image_url": "https://placehold.co/400x300/ffccbc/bf360c?text=Breakfast+Burrito"
            },
            {
                "name": "Vegetable Fried Rice",
                "cuisine": "Asian",
                "category": "Vegetarian",
                "prep_time": 15,
                "cook_time": 15,
                "servings": 2,
                "instructions": [
                    "Heat 1 tbsp vegetable oil in a large wok or skillet over high heat.",
                    "Add 1/2 cup diced carrots and 1/2 cup frozen peas. Stir-fry for 3-4 minutes until tender-crisp.",
                    "Push vegetables to one side. Add 1 tbsp oil to the empty side. Crack 1 large egg into the empty side and scramble until cooked. Mix with vegetables.",
                    "Add 2 cups cooked day-old rice to the wok. Break up any clumps.",
                    "Pour 2 tbsp soy sauce and 1 tsp sesame oil over the rice. Stir-fry for 5-7 minutes, breaking up rice and tossing, until heated through and slightly browned.",
                    "Stir in 2 chopped green onions. Serve hot."
                ],
                "ingredients": [
                    {"name": "vegetable oil", "quantity": 2, "unit": "tbsp"},
                    {"name": "diced carrots", "quantity": 0.5, "unit": "cup"},
                    {"name": "frozen peas", "quantity": 0.5, "unit": "cup"},
                    {"name": "large egg", "quantity": 1, "unit": ""},
                    {"name": "cooked day-old rice", "quantity": 2, "unit": "cups"},
                    {"name": "soy sauce", "quantity": 2, "unit": "tbsp"},
                    {"name": "sesame oil", "quantity": 1, "unit": "tsp"},
                    {"name": "green onions", "quantity": 2, "unit": "chopped"}
                ],
                "image_url": "https://placehold.co/400x300/fffde7/f57f17?text=Veg+Fried+Rice"
            },
            {
                "name": "Cream of Mushroom Soup",
                "cuisine": "European",
                "category": "Vegetarian",
                "prep_time": 15,
                "cook_time": 30,
                "servings": 4,
                "instructions": [
                    "Melt 2 tbsp butter in a large pot over medium heat. Add 1 lb sliced mushrooms and cook until browned and tender, about 8-10 minutes. Remove half of the mushrooms and set aside.",
                    "Add 1 chopped onion to the pot and cook until softened, about 5 minutes.",
                    "Stir in 2 minced garlic cloves and cook for 1 minute.",
                    "Whisk in 1/4 cup all-purpose flour and cook for 1 minute.",
                    "Gradually whisk in 4 cups vegetable or chicken broth and 1 cup milk (or cream). Bring to a simmer, whisking constantly, until thickened.",
                    "Season with salt, pepper, and 1/2 tsp dried thyme. If desired, blend half of the soup with an immersion blender for a creamier texture.",
                    "Return reserved mushrooms to the pot. Heat through and serve hot."
                ],
                "ingredients": [
                    {"name": "butter", "quantity": 2, "unit": "tbsp"},
                    {"name": "sliced mushrooms", "quantity": 1, "unit": "lb"},
                    {"name": "onion", "quantity": 1, "unit": "chopped"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "all-purpose flour", "quantity": 0.25, "unit": "cup"},
                    {"name": "vegetable or chicken broth", "quantity": 4, "unit": "cups"},
                    {"name": "milk or cream", "quantity": 1, "unit": "cup"},
                    {"name": "dried thyme", "quantity": 0.5, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/ede7f6/512da8?text=Mushroom+Soup"
            },
            {
                "name": "Chicken BLT Sandwich",
                "cuisine": "American",
                "category": "Non-Vegetarian",
                "prep_time": 10,
                "cook_time": 10,
                "servings": 1,
                "instructions": [
                    "Cook 3-4 slices of bacon until crispy. Drain on paper towels.",
                    "Toast 2 slices of your favorite bread.",
                    "Spread 1 tbsp mayonnaise on one side of each toasted bread slice.",
                    "Layer 4 oz cooked chicken breast (sliced), crispy bacon, 2 lettuce leaves, and 2 tomato slices on one slice of bread.",
                    "Place the other slice of bread on top. Slice in half and serve."
                ],
                "ingredients": [
                    {"name": "bacon slices", "quantity": 3, "unit": ""},
                    {"name": "bread slices", "quantity": 2, "unit": ""},
                    {"name": "mayonnaise", "quantity": 1, "unit": "tbsp"},
                    {"name": "cooked chicken breast", "quantity": 4, "unit": "oz, sliced"},
                    {"name": "lettuce leaves", "quantity": 2, "unit": ""},
                    {"name": "tomato slices", "quantity": 2, "unit": ""}
                ],
                "image_url": "https://placehold.co/400x300/e0f2f7/263238?text=Chicken+BLT"
            },
            {
                "name": "Roasted Vegetable Medley",
                "cuisine": "Side Dish",
                "category": "Vegetarian",
                "prep_time": 15,
                "cook_time": 25,
                "servings": 4,
                "instructions": [
                    "Preheat oven to 400°F (200°C).",
                    "Chop 1 zucchini, 1 yellow squash, 1 bell pepper, 1 red onion, and 1 cup broccoli florets into bite-sized pieces.",
                    "Toss vegetables with 2 tbsp olive oil, 1 tsp dried Italian seasoning, 1/2 tsp garlic powder, salt, and pepper on a large baking sheet.",
                    "Spread vegetables in a single layer. Roast for 20-25 minutes, stirring halfway, until tender and lightly browned."
                ],
                "ingredients": [
                    {"name": "zucchini", "quantity": 1, "unit": ""},
                    {"name": "yellow squash", "quantity": 1, "unit": ""},
                    {"name": "bell pepper", "quantity": 1, "unit": ""},
                    {"name": "red onion", "quantity": 1, "unit": ""},
                    {"name": "broccoli florets", "quantity": 1, "unit": "cup"},
                    {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
                    {"name": "dried Italian seasoning", "quantity": 1, "unit": "tsp"},
                    {"name": "garlic powder", "quantity": 0.5, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/c8e6c9/2e7d32?text=Roasted+Veg"
            },
            {
                "name": "Homemade Coleslaw",
                "cuisine": "American",
                "category": "Vegetarian",
                "prep_time": 15,
                "cook_time": 0,
                "servings": 6,
                "instructions": [
                    "In a large bowl, combine 4 cups shredded green cabbage, 1 cup shredded red cabbage, and 1 large shredded carrot.",
                    "For the dressing: In a separate bowl, whisk together 1/2 cup mayonnaise, 2 tbsp apple cider vinegar, 1 tbsp sugar, 1 tsp Dijon mustard, 1/2 tsp celery salt, salt, and pepper.",
                    "Pour dressing over cabbage mixture and toss well to coat.",
                    "Cover and refrigerate for at least 30 minutes before serving to allow flavors to meld."
                ],
                "ingredients": [
                    {"name": "shredded green cabbage", "quantity": 4, "unit": "cups"},
                    {"name": "shredded red cabbage", "quantity": 1, "unit": "cup"},
                    {"name": "large carrot", "quantity": 1, "unit": "shredded"},
                    {"name": "mayonnaise", "quantity": 0.5, "unit": "cup"},
                    {"name": "apple cider vinegar", "quantity": 2, "unit": "tbsp"},
                    {"name": "sugar", "quantity": 1, "unit": "tbsp"},
                    {"name": "Dijon mustard", "quantity": 1, "unit": "tsp"},
                    {"name": "celery salt", "quantity": 0.5, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/ede7f6/512da8?text=Coleslaw"
            },
            {
                "name": "Chicken Alfredo",
                "cuisine": "Italian",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 25,
                "servings": 4,
                "instructions": [
                    "Cook 8 oz fettuccine or preferred pasta according to package directions. Reserve 1 cup pasta water. Drain.",
                    "While pasta cooks, cook 1 lb boneless, skinless chicken breast (sliced) in 1 tbsp olive oil in a large skillet over medium-high heat until cooked through. Remove chicken.",
                    "In the same skillet, melt 4 tbsp butter over medium heat. Add 2 minced garlic cloves and cook for 1 minute.",
                    "Stir in 1.5 cups heavy cream and bring to a gentle simmer. Cook for 5 minutes, stirring, until slightly thickened.",
                    "Remove from heat. Stir in 1 cup grated Parmesan cheese until melted and smooth. Season with salt and pepper.",
                    "Add cooked pasta and chicken to the sauce. Toss to coat, adding reserved pasta water as needed to reach desired consistency.",
                    "Garnish with fresh parsley and serve hot."
                ],
                "ingredients": [
                    {"name": "fettuccine or pasta", "quantity": 8, "unit": "oz"},
                    {"name": "boneless, skinless chicken breast", "quantity": 1, "unit": "lb, sliced"},
                    {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "butter", "quantity": 4, "unit": "tbsp"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "heavy cream", "quantity": 1.5, "unit": "cups"},
                    {"name": "Parmesan cheese", "quantity": 1, "unit": "cup, grated"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "fresh parsley", "quantity": 1, "unit": "for garnish"}
                ],
                "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Chicken+Alfredo"
            },
            {
                "name": "Spicy Black Bean Tacos",
                "cuisine": "Mexican",
                "category": "Vegetarian",
                "prep_time": 15,
                "cook_time": 15,
                "servings": 3,
                "instructions": [
                    "Heat 1 tbsp olive oil in a skillet over medium heat. Add 1/2 chopped onion and 2 minced garlic cloves. Sauté for 3 minutes.",
                    "Add 1 (15 oz) can black beans (rinsed and drained), 1/2 cup corn (frozen or fresh), 1/2 tsp chili powder, and 1/4 tsp cayenne pepper (optional).",
                    "Cook for 5-7 minutes, mashing some of the beans with a fork, until heated through and slightly thickened.",
                    "Warm 6 small tortillas. Fill with black bean mixture. Top with desired toppings like avocado, salsa, or hot sauce."
                ],
                "ingredients": [
                    {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "onion", "quantity": 0.5, "unit": "chopped"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "black beans", "quantity": 15, "unit": "oz can, rinsed"},
                    {"name": "corn", "quantity": 0.5, "unit": "cup"},
                    {"name": "chili powder", "quantity": 0.5, "unit": "tsp"},
                    {"name": "cayenne pepper", "quantity": 0.25, "unit": "tsp", "optional": True},
                    {"name": "small tortillas", "quantity": 6, "unit": ""},
                    {"name": "avocado", "quantity": 1, "unit": "optional"},
                    {"name": "salsa", "quantity": 1, "unit": "optional"},
                    {"name": "hot sauce", "quantity": 1, "unit": "optional"}
                ],
                "image_url": "https://placehold.co/400x300/ffccbc/bf360c?text=Black+Bean+Tacos"
            },
            {
                "name": "Breakfast Smoothie",
                "cuisine": "Healthy",
                "category": "Sweet",
                "prep_time": 5,
                "cook_time": 0,
                "servings": 1,
                "instructions": [
                    "Combine 1 ripe banana, 1/2 cup berries (fresh or frozen), 1/2 cup milk (dairy or non-dairy), 1/4 cup plain yogurt, and 1 tbsp honey or maple syrup (optional) in a blender.",
                    "Blend until smooth and creamy. If too thick, add a little more milk. If too thin, add a few ice cubes.",
                    "Pour into a glass and serve immediately."
                ],
                "ingredients": [
                    {"name": "ripe banana", "quantity": 1, "unit": ""},
                    {"name": "berries", "quantity": 0.5, "unit": "cup, fresh or frozen"},
                    {"name": "milk", "quantity": 0.5, "unit": "cup"},
                    {"name": "plain yogurt", "quantity": 0.25, "unit": "cup"},
                    {"name": "honey or maple syrup", "quantity": 1, "unit": "tbsp", "optional": True},
                    {"name": "ice cubes", "quantity": 1, "unit": "optional"}
                ],
                "image_url": "https://placehold.co/400x300/fff3e0/e65100?text=Breakfast+Smoothie"
            },
            {
                "name": "Tomato Basil Bruschetta",
                "cuisine": "Italian",
                "category": "Vegetarian",
                "prep_time": 15,
                "cook_time": 10,
                "servings": 4,
                "instructions": [
                    "Preheat oven to 375°F (190°C).",
                    "Slice 1 baguette diagonally into 1/2-inch thick slices.",
                    "Arrange bread slices on a baking sheet. Drizzle lightly with olive oil.",
                    "Bake for 8-10 minutes, or until lightly golden and crisp.",
                    "While bread toasts, dice 3 ripe tomatoes. In a bowl, combine diced tomatoes with 2 minced garlic cloves, 1/4 cup chopped fresh basil, 1 tbsp olive oil, 1 tsp balsamic glaze, salt, and pepper.",
                    "Spoon tomato mixture over toasted baguette slices. Serve immediately."
                ],
                "ingredients": [
                    {"name": "baguette", "quantity": 1, "unit": ""},
                    {"name": "olive oil", "quantity": 3, "unit": "tbsp"},
                    {"name": "ripe tomatoes", "quantity": 3, "unit": "diced"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "fresh basil", "quantity": 0.25, "unit": "cup, chopped"},
                    {"name": "balsamic glaze", "quantity": 1, "unit": "tsp"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"}
                ],
                "image_url": "https://placehold.co/400x300/f3e5f5/4a148c?text=Bruschetta"
            },
            {
                "name": "Chicken Soup with Vegetables",
                "cuisine": "Comfort Food",
                "category": "Non-Vegetarian",
                "prep_time": 15,
                "cook_time": 40,
                "servings": 6,
                "instructions": [
                    "Heat 1 tbsp olive oil in a large pot. Add 1 chopped onion, 2 chopped carrots, and 2 chopped celery stalks. Sauté for 5-7 minutes.",
                    "Add 2 minced garlic cloves and cook for 1 minute.",
                    "Pour in 8 cups chicken broth and 1 cup cooked shredded chicken. Bring to a simmer.",
                    "Add 1 cup chopped potatoes (peeled) and 1/2 cup frozen peas. Cook for 20-25 minutes, or until potatoes are tender.",
                    "Season with salt, pepper, and fresh dill (optional). Serve hot."
                ],
                "ingredients": [
                    {"name": "olive oil", "quantity": 1, "unit": "tbsp"},
                    {"name": "onion", "quantity": 1, "unit": "chopped"},
                    {"name": "carrots", "quantity": 2, "unit": "chopped"},
                    {"name": "celery stalks", "quantity": 2, "unit": "chopped"},
                    {"name": "garlic", "quantity": 2, "unit": "cloves, minced"},
                    {"name": "chicken broth", "quantity": 8, "unit": "cups"},
                    {"name": "cooked shredded chicken", "quantity": 1, "unit": "cup"},
                    {"name": "potatoes", "quantity": 1, "unit": "cup, chopped, peeled"},
                    {"name": "frozen peas", "quantity": 0.5, "unit": "cup"},
                    {"name": "salt", "quantity": 1, "unit": "to taste"},
                    {"name": "pepper", "quantity": 1, "unit": "to taste"},
                    {"name": "fresh dill", "quantity": 1, "unit": "optional, for garnish"}
                ],
                "image_url": "https://placehold.co/400x300/e0f2f7/263238?text=Chicken+Veg+Soup"
            }
    ]

    for recipe_data in all_recipes:
        try:
            # Use INSERT OR IGNORE into recipes to prevent duplicates based on unique 'name'
            cursor.execute(
                "INSERT OR IGNORE INTO recipes (name, cuisine, category, prep_time, cook_time, servings, instructions, ingredients, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (recipe_data['name'], recipe_data['cuisine'], recipe_data['category'], recipe_data['prep_time'],
                 recipe_data['cook_time'], recipe_data['servings'],
                 json.dumps(recipe_data['instructions']), json.dumps(recipe_data['ingredients']), recipe_data['image_url'])
            )
            if cursor.rowcount > 0:
                print(f"Added recipe '{recipe_data['name']}' to the database.")
            else:
                print(f"Recipe '{recipe_data['name']}' already exists, skipped insertion.")
        except Exception as e:
            print(f"Error adding recipe '{recipe_data['name']}': {e}")

    conn.commit()
    conn.close()

# --- AI Model Loading ---
try:
    nlp = spacy.load("en_core_web_sm")
    print("SpaCy model 'en_core_web_sm' loaded successfully.")
except OSError:
    print("SpaCy model 'en_core_web_sm' not found. Attempting to download...")
    try:
        import subprocess
        subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
        nlp = spacy.load("en_core_web_sm")
        print("SpaCy model downloaded and loaded.")
    except Exception as e:
        print(f"Failed to download SpaCy model: {e}")
        print("Some NLU functionalities might be limited. Please ensure 'en_core_web_sm' is installed.")
        nlp = None

# Initialize OpenAI client. API key should be set as an environment variable.
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    print("WARNING: OPENAI_API_KEY environment variable not set. OpenAI API calls will fail.")
    print("Please set it in your terminal before running app.py:")
    print('Windows (PowerShell): $env:OPENAI_API_KEY="sk-YOUR_KEY_HERE"')
    print('macOS/Linux: export OPENAI_API_KEY="sk-YOUR_KEY_HERE"')

# CRITICAL FIX: Explicitly create httpx.Client to disable environment proxy detection.
# This prevents the 'proxies' unexpected keyword argument TypeError.
try:
    # Create a custom httpx client that does not trust environment variables for proxies.
    # This prevents 'proxies' from being implicitly passed, which was causing the TypeError.
    custom_httpx_client = httpx.Client(trust_env=False)
    client = OpenAI(api_key=openai_api_key, http_client=custom_httpx_client)
except Exception as e:
    # This fallback is a last resort; ideally, the above 'trust_env=False' fixes it.
    print(f"CRITICAL ERROR: Failed to initialize OpenAI client with custom httpx.Client: {e}")
    # Attempt a basic initialization as a last resort, though it's likely to fail again if the root cause persists.
    client = OpenAI(api_key=openai_api_key)


# --- NLU/NER Function (SpaCy based) ---
def process_with_nlu(command_text, current_step_index, recipe):
    if nlp is None:
        return {"response": "My NLU capabilities are offline. Please ensure SpaCy model is installed.", "action": None}

    doc = nlp(command_text)
    intent = "unknown"
    action = None
    response_text = "I'm sorry, I don't understand that command. Could you please rephrase?"

    if "next step" in command_text or "what's next" in command_text or "move on" in command_text:
        intent = "next_step"
    elif "repeat" in command_text or "say again" in command_text or "what was that" in command_text:
        intent = "repeat_step"
    elif "ingredients" in command_text or "what do i need" in command_text or "list ingredients" in command_text:
        intent = "list_ingredients"
    elif "hello" in command_text or "hi" in command_text:
        intent = "greeting"
    elif "how much" in command_text or "how many" in command_text:
        intent = "get_quantity"
    elif "set timer" in command_text or "start timer" in command_text:
        intent = "set_timer"
    elif "recipe" in command_text and ("load" in command_text or "switch to" in command_text):
        intent = "load_recipe"
    elif "go back" in command_text or "back to recipes" in command_text:
        intent = "back_to_list"
    elif "show all" in command_text or "show all recipes" in command_text or "all recipes" in command_text:
        intent = "show_all_recipes"
    elif "show vegetarian" in command_text or "vegetarian recipes" in command_text:
        intent = "show_vegetarian"
    elif "show non-vegetarian" in command_text or "non-vegetarian recipes" in command_text:
        intent = "show_non_vegetarian"
    elif "show sweet" in command_text or "sweet recipes" in command_text or "dessert recipes" in command_text:
        intent = "show_sweet"


    if intent == "next_step":
        if recipe and current_step_index < len(recipe['instructions']) - 1:
            action = 'next_step'
            response_text = recipe['instructions'][current_step_index + 1]
        elif recipe:
            response_text = "You are at the last step of the recipe!"
        else:
            response_text = "No recipe is currently loaded."
    elif intent == "repeat_step":
        if recipe and recipe['instructions'] and 0 <= current_step_index < len(recipe['instructions']):
            action = 'repeat_step'
            response_text = recipe['instructions'][current_step_index]
        else:
            response_text = "No step to repeat, or no recipe loaded."
    elif intent == "list_ingredients":
        if recipe and recipe['ingredients']:
            ingredients_str = ", ".join([f"{ing['quantity']} {ing['unit'] or ''} {ing['name']}" for ing in recipe['ingredients']])
            response_text = f"The ingredients for {recipe['name']} are: {ingredients_str}."
        else:
            response_text = "No ingredients loaded for this recipe."
    elif intent == "greeting":
        response_text = "Hello there! How can I help you with your cooking today?"
    elif intent == "get_quantity":
        ingredient_name = ""
        for token in doc:
            if token.pos_ == "NOUN" and (token.text.lower() in command_text or any(char.isalpha() for char in token.text)):
                ingredient_name = token.text.lower()
                break

        for ent in doc.ents:
            if ent.label_ in ["PRODUCT", "FOOD", "GPE", "ORG"] or any(term in ent.text.lower() for term in ['sugar', 'salt', 'flour', 'milk', 'water', 'butter', 'eggs', 'chicken', 'rice', 'carrots', 'peas', 'beans', 'pasta', 'peppers', 'zucchini', 'broccoli', 'tomatoes', 'pesto']):
                ingredient_name = ent.text.lower()
                break

        if ingredient_name and recipe and recipe['ingredients']:
            found_ingredient = next((ing for ing in recipe['ingredients'] if ingredient_name in ing['name'].lower()), None)
            if found_ingredient:
                response_text = f"You need {found_ingredient['quantity']} {found_ingredient['unit'] or ''} of {found_ingredient['name']} for {recipe['name']}."
            else:
                response_text = f"I don't see {ingredient_name} listed in this recipe."
        else:
            response_text = "Which ingredient are you asking about?"
    elif intent == "set_timer":
        time_value = None
        time_unit = ""
        for token in doc:
            if token.like_num:
                time_value = int(token.text)
            if "minute" in token.text.lower():
                time_unit = "minutes"
            elif "second" in token.text.lower():
                time_unit = "seconds"
        
        if time_value and time_unit:
            response_text = f"Okay, setting a timer for {time_value} {time_unit}. I'll let you know when it's done!"
        elif time_value:
            response_text = f"For how long should I set the timer for {time_value}? (minutes or seconds?)"
        else:
            response_text = "For how long should I set the timer?"
    elif intent == "load_recipe":
        recipe_name_found = None
        # Extract full recipe name from command if possible
        for token in doc:
            if token.text.lower() == "recipe" and token.head.text.lower() == "load":
                # Look for named entities or subsequent words as recipe name
                start_index = token.i + 1
                if start_index < len(doc):
                    recipe_name_found = " ".join([t.text for t in doc[start_index:] if not t.is_punct and t.text.lower() not in ["please", "assistant", "for", "me"]]).strip()
                    if recipe_name_found:
                        break
        if not recipe_name_found:
            for ent in doc.ents:
                # Try to capture more general entities or common recipe names
                if ent.label_ in ["PRODUCT", "FOOD", "WORK_OF_ART", "EVENT"] or any(name.lower() in ent.text.lower() for name in ["scrambled eggs", "chicken curry", "vegetable pulao", "pasta primavera", "tomato soup", "guacamole", "stir fry", "lentil soup", "baked salmon", "pancakes", "vegetarian chili", "caprese salad", "garlic shrimp", "quinoa salad", "chocolate chip cookies", "beef tacos", "mushroom risotto", "french toast", "chicken noodle soup", "spaghetti carbonara", "oatmeal", "homemade pizza", "roasted chicken", "black bean burgers", "greek salad", "beef and broccoli", "minestrone soup", "crispy chicken thighs", "pesto chicken sandwich", "avocado toast", "beef stew", "chicken quesadillas", "vegetable frittata", "garden salad", "grilled cheese", "hummus wraps", "tuna sandwich", "chicken skewers", "black bean soup", "spinach omelette", "teriyaki chicken", "lentil pie", "chicken caesar salad", "green curry", "mac and cheese", "chicken fajitas", "tomato pasta", "chicken and rice soup", "pot roast", "chicken pad thai", "veggie burgers", "chicken lettuce wraps", "creamy tomato soup", "chicken enchiladas", "spinach salad", "stuffed bell peppers", "baked ziti", "chicken tenders", "shrimp scampi", "tomato cucumber salad", "breakfast burritos", "fried rice", "cream of mushroom soup", "chicken blt", "roasted vegetable medley", "coleslaw", "chicken alfredo", "spicy black bean tacos", "breakfast smoothie", "bruschetta", "chicken soup with vegetables"]):
                    recipe_name_found = ent.text.lower()
                    break

        if recipe_name_found:
            conn = get_db()
            cursor = conn.cursor()
            # Use LIKE for partial matching
            found_db_recipe = cursor.execute("SELECT id, name FROM recipes WHERE LOWER(name) LIKE ?", (f"%{recipe_name_found}%",)).fetchone()
            conn.close()
            
            if found_db_recipe:
                action = "load_recipe_id"
                response_text = f"Switching to {found_db_recipe['name']} recipe."
                return {"response": response_text, "action": action, "recipe_id": found_db_recipe['id']}
            else:
                response_text = f"I can't find a recipe called {recipe_name_found}. Please try a different recipe name."
        else:
            response_text = "Which recipe would you like to load? Say 'Load recipe [name]'."
    elif intent == "back_to_list":
        action = "show_recipe_list"
        response_text = "Going back to the recipe list."
        return {"response": response_text, "action": action}
    elif intent == "show_all_recipes":
        action = "filter_recipes"
        response_text = "Showing all recipes."
        return {"response": response_text, "action": action, "category": "All"}
    elif intent == "show_vegetarian":
        action = "filter_recipes"
        response_text = "Showing vegetarian recipes."
        return {"response": response_text, "action": action, "category": "Vegetarian"}
    elif intent == "show non-vegetarian" in command_text or "non-vegetarian recipes" in command_text:
        action = "filter_recipes"
        response_text = "Showing non-vegetarian recipes."
        return {"response": response_text, "action": action, "category": "Non-Vegetarian"}
    elif intent == "show_sweet":
        action = "filter_recipes"
        response_text = "Showing sweet recipes."
        return {"response": response_text, "action": action, "category": "Sweet"}

    return {"response": response_text, "action": action, "intent": intent}

# --- LLM Response Function (OpenAI API based) ---
def get_ai_response_llm(command_text, current_step_index, recipe):
    if not openai_api_key:
        return {"response": "My advanced AI brain is offline due to missing API key.", "action": None}

    context_messages = [
        {"role": "system", "content": "You are a helpful and friendly voice-controlled cooking assistant. Provide concise, helpful answers. Keep cooking safety in mind. If the user asks about a step or ingredient, refer to the current recipe details provided. Do not invent recipe steps or ingredients."},
    ]

    if recipe:
        recipe_details = f"Current Recipe: {recipe['name']}.\n"
        if recipe['ingredients']:
            ingredients_list = "\n".join([f"- {ing['quantity']} {ing['unit'] or ''} {ing['name']}" for ing in recipe['ingredients']])
            recipe_details += f"Ingredients:\n{ingredients_list}\n"
        if recipe['instructions'] and 0 <= current_step_index < len(recipe['instructions']):
            recipe_details += f"Current Step ({current_step_index + 1} of {len(recipe['instructions'])}): {recipe['instructions'][current_step_index]}\n"
        context_messages.append({"role": "system", "content": f"Here's the context about the recipe you are working on:\n{recipe_details}"})
    else:
        context_messages.append({"role": "system", "content": "No specific recipe is currently loaded. You can ask general cooking questions or ask to 'load recipe [name]'."})


    context_messages.append({"role": "user", "content": command_text})

    try:
        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=context_messages,
            temperature=0.7,
            max_tokens=150
        )
        response_content = chat_completion.choices[0].message.content.strip()
        return {"response": response_content, "action": None}
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return {"response": "I'm sorry, I'm having trouble thinking right now. Please try again or rephrase your question.", "action": None}

# --- Flask Routes ---
@app.route('/')
def index():
    """Serves the main HTML page of the cooking assistant."""
    return render_template('index.html')

@app.route('/api/recipe/<int:recipe_id>')
def get_recipe(recipe_id):
    """Fetches a specific recipe from the database by ID."""
    conn = get_db()
    cursor = conn.cursor()
    recipe = cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    conn.close()

    if recipe:
        recipe_dict = dict(recipe)
        if recipe_dict.get('instructions'):
            recipe_dict['instructions'] = json.loads(recipe_dict['instructions'])
        if recipe_dict.get('ingredients'):
            recipe_dict['ingredients'] = json.loads(recipe_dict['ingredients'])
        return jsonify(recipe_dict)
    return jsonify({"error": "Recipe not found"}), 404

@app.route('/api/recipes')
def get_all_recipes():
    """Fetches a list of all recipe names and their IDs."""
    conn = get_db()
    cursor = conn.cursor()
    # Select all fields needed for listing and filtering
    recipes = cursor.execute("SELECT id, name, cuisine, category, prep_time, cook_time, servings, image_url FROM recipes ORDER BY name ASC").fetchall()
    conn.close()
    
    recipe_list = [dict(r) for r in recipes]
    return jsonify(recipe_list)

@app.route('/api/recipes_by_category')
def get_recipes_by_category():
    """Fetches recipes filtered by category."""
    category = request.args.get('category') # Get category from query parameter
    conn = get_db()
    cursor = conn.cursor()

    if category and category.lower() != 'all':
        recipes = cursor.execute("SELECT id, name, cuisine, category, prep_time, cook_time, servings, image_url FROM recipes WHERE LOWER(category) = ? ORDER BY name ASC", (category.lower(),)).fetchall()
    else:
        # If no category or "All", return all recipes
        recipes = cursor.execute("SELECT id, name, cuisine, category, prep_time, cook_time, servings, image_url FROM recipes ORDER BY name ASC").fetchall()
    
    conn.close()
    recipe_list = [dict(r) for r in recipes]
    return jsonify(recipe_list)


@app.route('/api/process_command', methods=['POST'])
def process_command_route():
    data = request.get_json()
    command = data.get('command', '').lower()
    current_step_index = data.get('current_step', 0)
    recipe_id = data.get('recipe_id')

    recipe = None
    if recipe_id:
        conn = get_db()
        cursor = conn.cursor()
        fetched_recipe = cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
        conn.close()
        if fetched_recipe:
            recipe = dict(fetched_recipe)
            if recipe.get('instructions'):
                recipe['instructions'] = json.loads(recipe['instructions'])
            if recipe.get('ingredients'):
                recipe['ingredients'] = json.loads(recipe['ingredients'])

    nlu_result = process_with_nlu(command, current_step_index, recipe)

    if nlu_result.get("action") or nlu_result.get("intent") != "unknown":
        return jsonify(nlu_result)
    else:
        llm_result = get_ai_response_llm(command, current_step_index, recipe)
        return jsonify(llm_result)

# --- Application Entry Point ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
