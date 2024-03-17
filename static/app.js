
$(document).ready(function() {
    $('#recipeForm').on('submit', function(e) {
        e.preventDefault();
        let ingredients = $('#ingredients').val();
        let allergies = $('#allergies').val();
        let diets = $('#diets').val();
        $('#loadingIcon').show();
        updateLoadingText('Loading recommendations...');
        $.ajax({
            url: '/recommendations',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({         
            ingredients: $('#ingredients').val().split(','),
            allergies: $('#allergies').val(),
            diets: $('#diets').val()
        }),
        success: function(data) {
            $('#loadingIcon').hide();
            updateLoadingText('');
            displayRecommendations(data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            let errorMessage = jqXHR.status === 429 ? "Too many requests. Please try again later." : `An error occurred: ${textStatus}, ${errorThrown}`;
            $('#results').html(`<p>${errorMessage}</p>`);
            $('#loadingIcon').hide();
            updateLoadingText('');
            }
        });
    });
    $('#imageUpload').on('change', function(e) {
        if (this.files && this.files[0]) {
            let formData = new FormData();
            formData.append('file', this.files[0]);
            $('#loadingIcon').show();
            updateLoadingText('Identifying Ingredients...')
            $.ajax({
                url: '/upload-image',
                type: 'POST',
                processData: false,
                contentType: false,
                data: formData,
                success: function(data) {
                    console.log('Image uploaded:', data);
                    $('#loadingIcon').hide();
                    updateLoadingText('');
                    // Automatically fill the identified ingredients into the ingredients input
                    $('#ingredients').val(data.ingredients);
                },
                error: function(jqXHR, textStatus, errorThrown) {
                    console.error(`An error occurred: ${textStatus}, ${errorThrown}`);
                    $('#loadingIcon').hide();
                    updateLoadingText('');
                }
            });
        }
    });
    $('#loadingIcon').hide();
    updateLoadingText('');


});
$(document).on('click', '.thumbs-up, .thumbs-down', function() {
    if (!isLoggedIn) 
        return  alert('Please log in to submit feedback.');

    const recipeId = $(this).data('recipe-id');
    const feedback = $(this).hasClass('thumbs-up') ? 'like' : 'dislike';
    submitFeedback(recipeId, feedback);
});

function updateLoadingText(text) {
    $('#loadingText').text(text);
}
function submitFeedback(recipeId, feedback) {
    const thumbsUpButton = $(`button.thumbs-up[data-recipe-id="${recipeId}"]`);
    const thumbsDownButton = $(`button.thumbs-down[data-recipe-id="${recipeId}"]`);
    const originalUpText = thumbsUpButton.text(); // Store the original button text
    const originalDownText = thumbsDownButton.text(); // Store the original button text
    const feedbackMessage = feedback === 'like' ? 'Liked 👍' : 'Disliked 👎';

    $.ajax({
        url: '/feedback',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            recipe_id: recipeId,
            feedback: feedback
        }),
        beforeSend: function() {
            thumbsUpButton.prop('disabled', true);
            thumbsDownButton.prop('disabled', true);
        },
        success: function(response) {
            if (feedback === 'like') {
                thumbsUpButton.addClass('liked').removeClass('disliked').prop('disabled', false).html(feedbackMessage);
                setTimeout(function() { // Revert the button after 2 seconds
                    thumbsUpButton.html(originalUpText).removeClass('liked');
                }, 2000); // 2000 milliseconds = 2 seconds
            } else {
                thumbsDownButton.addClass('disliked').removeClass('liked').prop('disabled', false).html(feedbackMessage);
                setTimeout(function() { // Revert the button after 2 seconds
                    thumbsDownButton.html(originalDownText).removeClass('disliked');
                }, 2000);
            }
        },
        error: function(error) {
            console.error('Error submitting feedback', error);
            // Re-enable buttons and revert text without timeout if there was an error
            thumbsUpButton.prop('disabled', false).html(originalUpText);
            thumbsDownButton.prop('disabled', false).html(originalDownText);
        }
    });
}

function displayRecommendations(recipes) {
    console.log("Received recipes:", recipes);
    let resultsDiv = $('#results');
    resultsDiv.empty();
    if (!recipes || recipes.length === 0) {
        resultsDiv.append('<p>No recipes found. Try different keywords.</p>');
        return;
    }
    recipes.forEach(function(recipe) {
        // Check if ingredients and steps are arrays, and convert them to strings if they are
        let ingredientsString = recipe.ingredients.replace(/^\[|\]$/g, '');
        // Split the ingredients string into an array on ', ' delimiter
        let ingredientsList = ingredientsString.split(', ').map(ingredient => ingredient.replace(/['"]+/g, ''));

        // Remove leading and trailing square brackets and split the steps string on ', ' if it's a string
        let stepsString = recipe.steps.replace(/^\[|\]$/g, '');
        // Split the steps string into an array, using regex to match text between single quotes
        let stepsList = stepsString.match(/'([^']+)'/g).map(step => step.replace(/'/g, ''));
        let recipeID = recipe.recipeID;
        let imageSrc = recipe.image ? recipe.image : 'path/to/fallback/image.jpg'; // Ensure you have a fallback image

        let calories = recipe.nutrition.calories;
        let total_fat = recipe.nutrition.total_fat;   
        let sugar = recipe.nutrition.sugar;
        let sodium = recipe.nutrition.sodium;
        let protein = recipe.nutrition.protein;
        let carbohydrates = recipe.nutrition.carbohydrates;
        let saturated_fat = recipe.nutrition.saturated_fat;

        let ingredientsHtml = ingredientsList.map(ingredient => `<li>${ingredient}</li>`).join('');

        // Construct the HTML for the preparation steps list
        let stepsHtml = stepsList.map(step => `<li>${step}</li>`).join('');

        
        let recipeHtml = `
        <div class="recipe-card">
            <img src="${imageSrc}" class="recipe-image" alt="${recipe.name}">
            <h2 class="recipe-title">${recipe.name}</h2>
            <div class="recipe-info">
                <div class="recipe-nutrition">
                    <h3>Nutrition Information</h3>
                    <p>Calories: ${calories}</p>
                    <p>Total Fat: ${total_fat}% PDV Sugar: ${sugar}% PDV Sodium: ${sodium}% PDV</p>
                    <p>Protein: ${protein}% PDV Carbohydrates: ${carbohydrates}% PDV Saturated Fat: ${saturated_fat}% PDV</p>
                </div>
                <div class="recipe-ingredients">
                    <h3>Ingredients</h3>
                    <ul>${ingredientsHtml}</ul>
                </div>
                <div class="recipe-steps">
                    <h3>Preparation Steps</h3>
                    <ol>${stepsHtml}</ol>
                </div>
                <div class="recipe-time">
                    <h3>Preparation Time</h3>
                    <p>${recipe.preparation_time} minutes</p>
                </div>
                <button class="thumbs-up" data-recipe-id="${recipe.recipe_id}">👍</button>
                <button class="thumbs-down" data-recipe-id="${recipe.recipe_id}">👎</button>
                <button class="save-recipe" data-recipe-id="${recipe.recipe_id}">Save</button>
            </div>
        </div>`;
        resultsDiv.append(recipeHtml);
    });
} 

$(document).on('click', '.save-recipe', function() {
    if (!isLoggedIn) 
        return  alert('Please log in to save recipes.');

    let recipeId = $(this).data('recipe-id');
    // AJAX request to save the recipe
    $.ajax({
        url: '/save_recipe', // Ensure this endpoint exists in your Flask app
        type: 'POST',
        data: JSON.stringify({ recipe_id: recipeId }),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json',
        success: function(response) {
            if(response.status === 'success') {
                alert(response.message);
                button.text('Saved').addClass('btn-success').removeClass('btn-primary');
                // Disable the button to prevent multiple saves
                button.prop('disabled', true);
            } else {
                alert('Error saving recipe.');
            }
        }
    });
});

const itemsPerPage = 6;
let currentPage = 1;

function displaySavedRecipes(recipes) {

    console.log("Displaying saved recipes:", recipes);  // Debug statement
    let resultsDiv = $('#saved-recipes');
    resultsDiv.empty();

    const start = (currentPage - 1) * itemsPerPage;
    const end = currentPage * itemsPerPage;
    const paginatedItems = recipes.slice(start, end);

    if (!paginatedItems || paginatedItems.length === 0) {
        resultsDiv.append('<p>No saved recipes to display.</p>');
        return;
    }

    paginatedItems.forEach((recipes, index) => {
    
       let recipeID = recipes.recipeID;

       let calories = recipes.calories;
       let total_fat = recipes.total_fat;   
       let sugar = recipes.sugar;
       let sodium = recipes.sodium;
       let protein = recipes.protein;
       let carbohydrates = recipes.carbohydrates;
       let saturated_fat = recipes.saturated_fat;

       let ingredientsHtml = recipes.ingredients.map(ingredient => `<li>${ingredient}</li>`).join('');

       // Construct the HTML for the preparation steps list
       let stepsHtml = recipes.steps.map(step => `<li>${step}</li>`).join('');
       
        let recipeHtml = `
        <div class="saved-recipe-card" id="recipe-${recipes.recipe_id}">
        <img src="${recipes.image_url}" class="saved-recipe-image" alt="${recipes.name}" id="recipe-image-${recipes.recipe_id}">
            <h2 class="saved-recipe-title">${recipes.name}</h2>
            <div class="saved-recipe-info" id="recipe-info-${recipes.recipe_id}" style="display: none;">
                <div class="recipe-nutrition">
                <h3>Nutrition Information</h3>
                <p>Calories: ${calories}</p>
                <p>Total Fat: ${total_fat}% PDV Sugar: ${sugar}% PDV Sodium: ${sodium}% PDV</p>
                <p>Protein: ${protein}% PDV Carbohydrates: ${carbohydrates}% PDV Saturated Fat: ${saturated_fat}% PDV</p>
                </div>
                <div class="recipe-ingredients">
                    <h3>Ingredients</h3>
                    <ul>${ingredientsHtml}</ul>
                </div>
                <div class="recipe-steps">
                    <h3>Preparation Steps</h3>
                    <ol>${stepsHtml}</ol>
                </div>
                <div class="recipe-time">
                    <h3>Preparation Time</h3>
                    <p>${recipes.preparation_time} minutes</p>
                </div>
            </div>
            <div class="button-container">
            <button class="show-details" onclick="toggleDetails('${recipes.recipe_id}')">Show/Hide Details</button>
            <button class="delete-recipe" onclick="deleteRecipe('${recipes.recipe_id}')" data-recipe-id="${recipes.recipe_id}">Delete</button>
            </div>
        </div>`;
        resultsDiv.append(recipeHtml);
        });
        
        
        $('#saved-recipes').find('.delete-recipe').last().on('click', function() {
            let recipeId = $(this).data('recipe-id');
            deleteRecipe(recipeId);
        });
    displayPaginationControls(recipes.length);
}
function showRecipes() {
    $('#recipes-container').show();
    const savedRecipes = JSON.parse(document.getElementById('saved-recipes-data').textContent || '[]');
    displaySavedRecipes(savedRecipes);
    $('#show-recipes-btn').hide(); // Optional: Hide the "Show Recipes" button after showing the recipes
}
function displayPaginationControls(totalItems) {
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    const paginationControls = $('#pagination-controls');
    paginationControls.empty();

    for (let i = 1; i <= totalPages; i++) {
        const button = $('<button></button>')
          .text(i)
          .click(function() {
            currentPage = i;
            displaySavedRecipes(savedRecipes, currentPage); // Redraw the saved recipes for the new page
          });

        if (i === currentPage) {
          button.addClass('active');
        }

        paginationControls.append(button);
    }
}


function changePage(page) {
    console.log("Changing to page: ", page);
    currentPage = page;
    displaySavedRecipes(savedRecipes); // Make sure savedRecipes is accessible
}

function toggleDetails(recipeID) {
    const infoDiv = $(`#recipe-info-${recipeID}`);
    const recipeCard = $(`#recipe-${recipeID}`);
    const isExpanded = recipeCard.hasClass('expanded-recipe-card');
    
    // Collapse any previously expanded recipe card
    $('.expanded-recipe-card').not(recipeCard).removeClass('expanded-recipe-card')
        .find('.saved-recipe-info').slideUp('fast'); // Optionally collapse details

    // Toggle the expansion of the current card
    if (isExpanded) {
        recipeCard.removeClass('expanded-recipe-card');
        infoDiv.slideUp('fast');
    } else {
        recipeCard.addClass('expanded-recipe-card');
        infoDiv.slideDown('fast', function() {
            // Scroll to the recipe card's new position after expanding
            $('html, body').animate({
                scrollTop: recipeCard.offset().top - 20
            }, 500);
        });
    }
}
function showSingleRecipeDetails(recipeId) {
    // Hide all recipe details
    $('.saved-recipe-info').slideUp('fast');
    // Remove expanded class from all cards
    $('.saved-recipe-card').removeClass('expanded-recipe-card');
    
    // Show the clicked recipe's details
    toggleDetails(recipeId);
}

// Modify displaySavedRecipes to include a "Show Details" button that calls toggleDetails.

$(document).ready(function() {
    // Ensure savedRecipes is defined globally or fetched here
    displaySavedRecipes(savedRecipes);
});

function deleteRecipe(recipeId) {
    $.ajax({
        url: '/delete_recipe', 
        type: 'POST',
        data: JSON.stringify({ recipe_id: recipeId }),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json',
        success: function(response) {
            if(response.status === 'success') {
                $(`#recipe-${recipeId}`).remove(); // Remove the recipe from the page
                alert('Recipe deleted successfully.');
            } else {
                alert(response.message);
            }
        },
        error: function() {
            alert('Error deleting recipe.');
        }
    });
}

