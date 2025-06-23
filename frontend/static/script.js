document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element References ---
    const recipeListSection = document.getElementById('recipe-list-section');
    const recipesGrid = document.getElementById('recipes-grid');
    const recipeDisplaySection = document.getElementById('recipe-display-section');
    const backToRecipesBtn = document.getElementById('back-to-recipes-btn');
    const filterButtons = document.querySelectorAll('.filter-button'); // Get all filter buttons

    const recipeTitle = document.getElementById('recipe-title');
    const recipeCuisine = document.getElementById('recipe-cuisine');
    const recipeCategory = document.getElementById('recipe-category'); // New element for category
    const recipePrepTime = document.getElementById('recipe-prep-time');
    const recipeCookTime = document.getElementById('recipe-cook-time');
    const recipeServings = document.getElementById('recipe-servings'); 
    const ingredientsList = document.getElementById('ingredients-list');
    const instructionsList = document.getElementById('instructions-list');
    const recipeImageDisplay = document.getElementById('recipe-image-display'); // New element for image
    const statusDiv = document.getElementById('status');
    const responseDiv = document.getElementById('response');
    const startListeningBtn = document.getElementById('start-listening');

    // --- State Variables ---
    let currentStepIndex = 0;
    let currentRecipe = null;
    let recognition;
    let isSpeaking = false;
    let currentFilterCategory = 'all'; // Default filter category

    // --- Section Visibility Management ---
    function showRecipeList() {
        recipeListSection.classList.remove('hidden');
        recipeDisplaySection.classList.add('hidden');
        startListeningBtn.disabled = true; // Disable assistant when viewing list
        statusDiv.textContent = "Select a recipe to begin or filter by category.";
        responseDiv.textContent = "Assistant will speak here.";
        currentRecipe = null; // Clear current recipe state
        currentStepIndex = 0; // Reset step index
        if (speechSynthesis.speaking) {
            speechSynthesis.cancel();
        }
        fetchAllRecipes(currentFilterCategory); // Re-fetch recipes with current filter
    }

    function showRecipeDisplay() {
        recipeListSection.classList.add('hidden');
        recipeDisplaySection.classList.remove('hidden');
        startListeningBtn.disabled = false; // Enable assistant when recipe is displayed
        statusDiv.textContent = "Recipe loaded. Click 'Start Assistant' to begin.";
        speak(`The recipe for ${currentRecipe.name} is loaded. Click Start Assistant when you are ready.`);
    }

    // --- Recipe List Functions ---
    async function fetchAllRecipes(category = 'all') {
        recipesGrid.innerHTML = '<p class="text-center text-gray-600 col-span-full">Loading recipes...</p>';
        
        let url = '/api/recipes';
        if (category && category !== 'all') {
            url = `/api/recipes_by_category?category=${category}`;
        }

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const recipes = await response.json();
            displayRecipeList(recipes);
        } catch (error) {
            console.error('Error fetching all recipes:', error);
            recipesGrid.innerHTML = '<p class="text-red-600 text-center col-span-full">Failed to load recipes. Please ensure your backend is running and accessible.</p>';
            speak("Sorry, I could not fetch the list of recipes.");
        }
    }

    function displayRecipeList(recipes) {
        recipesGrid.innerHTML = ''; // Clear loading message
        if (recipes.length === 0) {
            recipesGrid.innerHTML = '<p class="text-center text-gray-600 col-span-full">No recipes available for this category.</p>';
            return;
        }

        recipes.forEach(recipe => {
            const recipeCard = document.createElement('div');
            recipeCard.className = 'bg-white rounded-lg shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all duration-300 cursor-pointer p-4 border border-gray-100 flex flex-col justify-between overflow-hidden';
            recipeCard.dataset.recipeId = recipe.id;

            // Use image_url from recipe data, with a fallback
            const imageUrl = recipe.image_url || 'https://placehold.co/400x300/cccccc/333333?text=No+Image';

            recipeCard.innerHTML = `
                <img src="${imageUrl}" alt="${recipe.name}" class="w-full h-36 object-cover rounded-md mb-4 shadow-sm" onerror="this.onerror=null;this.src='https://placehold.co/400x300/cccccc/333333?text=Image+Not+Found';">
                <div>
                    <h3 class="text-xl font-bold text-indigo-700 mb-2">${recipe.name}</h3>
                    <p class="text-gray-600 text-sm mb-1"><strong class="font-medium">Cuisine:</strong> ${recipe.cuisine || 'N/A'}</p>
                    <p class="text-gray-600 text-sm mb-1"><strong class="font-medium">Category:</strong> ${recipe.category || 'N/A'}</p>
                    <p class="text-gray-600 text-sm mb-1"><strong class="font-medium">Prep:</strong> ${recipe.prep_time || 'N/A'} mins</p>
                    <p class="text-gray-600 text-sm"><strong class="font-medium">Cook:</strong> ${recipe.cook_time || 'N/A'} mins</p>
                </div>
                <button class="mt-4 w-full bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600 transition-colors duration-200">View Recipe</button>
            `;
            
            recipeCard.querySelector('button').addEventListener('click', () => {
                fetchRecipe(recipe.id);
            });

            recipesGrid.appendChild(recipeCard);
        });
    }

    // --- Recipe Display Functions ---
    async function fetchRecipe(id) {
        statusDiv.textContent = "Fetching recipe...";
        try {
            const response = await fetch(`/api/recipe/${id}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const recipe = await response.json();
            currentRecipe = recipe;
            displayRecipe(recipe);
            currentStepIndex = 0;
            highlightCurrentStep();
            showRecipeDisplay();
        } catch (error) {
            console.error('Error fetching recipe:', error);
            recipeTitle.textContent = 'Error loading recipe.';
            statusDiv.textContent = "Failed to load recipe. Please try again.";
            ingredientsList.innerHTML = '';
            instructionsList.innerHTML = '';
            speak("Sorry, I could not load the recipe.");
            showRecipeList();
        }
    }

    function displayRecipe(recipe) {
        recipeTitle.textContent = recipe.name;
        recipeCuisine.textContent = recipe.cuisine || 'N/A';
        recipeCategory.textContent = recipe.category || 'N/A'; // Display category
        recipePrepTime.textContent = recipe.prep_time || 'N/A';
        recipeCookTime.textContent = recipe.cook_time || 'N/A';
        recipeServings.textContent = recipe.servings || 'N/A';
        
        // Set image for single recipe display
        recipeImageDisplay.src = recipe.image_url || 'https://placehold.co/400x300/cccccc/333333?text=No+Image';
        recipeImageDisplay.alt = recipe.name;

        ingredientsList.innerHTML = '';
        if (recipe.ingredients && Array.isArray(recipe.ingredients)) {
            recipe.ingredients.forEach(ing => {
                const li = document.createElement('li');
                li.textContent = `${ing.quantity} ${ing.unit || ''} ${ing.name}`;
                ingredientsList.appendChild(li);
            });
        } else {
            ingredientsList.innerHTML = '<li>No ingredients listed.</li>';
        }

        instructionsList.innerHTML = '';
        if (recipe.instructions && Array.isArray(recipe.instructions)) {
            recipe.instructions.forEach((instruction, index) => {
                const li = document.createElement('li');
                li.textContent = instruction;
                li.dataset.stepIndex = index;
                instructionsList.appendChild(li);
            });
        } else {
            instructionsList.innerHTML = '<li>No instructions listed.</li>';
        }
    }

    function highlightCurrentStep() {
        const allSteps = instructionsList.querySelectorAll('li');
        allSteps.forEach((li, index) => {
            if (index === currentStepIndex) {
                li.classList.add('current-step');
                li.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                li.classList.remove('current-step');
            }
        });
    }

    // --- Speech Synthesis (Text-to-Speech) Function ---
    function speak(text) {
        if ('speechSynthesis' in window) {
            if (speechSynthesis.speaking) {
                speechSynthesis.cancel();
            }

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'en-US';

            utterance.onstart = () => { isSpeaking = true; startListeningBtn.disabled = true; };
            utterance.onend = () => { isSpeaking = false; startListeningBtn.disabled = false; statusDiv.textContent = currentRecipe ? "Ready for your command." : "Select a recipe to begin or filter by category."; };
            utterance.onerror = (event) => {
                console.error('Speech synthesis error:', event.error);
                isSpeaking = false;
                startListeningBtn.disabled = false;
                statusDiv.textContent = currentRecipe ? "Error speaking. Ready for command." : "Select a recipe to begin or filter by category.";
            };
            speechSynthesis.speak(utterance);
        } else {
            console.warn("Speech Synthesis not supported in this browser.");
            responseDiv.textContent = text;
            statusDiv.textContent = currentRecipe ? "Speech Synthesis not available. Ready for command." : "Select a recipe to begin or filter by category.";
            startListeningBtn.disabled = false;
        }
    }

    // --- Speech Recognition (Web Speech API) Functions ---
    function startRecognition() {
        if (isSpeaking) {
            statusDiv.textContent = "Assistant is speaking. Please wait.";
            return;
        }
        if (!currentRecipe) {
            statusDiv.textContent = "Please select a recipe first.";
            speak("Please select a recipe from the list before activating the assistant.");
            return;
        }

        if (!recognition) {
            if ('webkitSpeechRecognition' in window) {
                recognition = new webkitSpeechRecognition();
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.lang = 'en-US';

                recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript.toLowerCase();
                    statusDiv.textContent = `You said: "${transcript}"`;
                    console.log('Transcript:', transcript);
                    processVoiceCommand(transcript);
                };

                recognition.onerror = (event) => {
                    console.error('Speech recognition error', event.error);
                    statusDiv.textContent = `Speech error: ${event.error}. Please try again.`;
                    speak("I didn't quite catch that. Please try again.");
                    startListeningBtn.disabled = false;
                };

                recognition.onend = () => {
                    console.log('Speech recognition ended.');
                    startListeningBtn.disabled = false;
                };

            } else {
                statusDiv.textContent = "Speech recognition not supported in this browser. Please use Chrome for full functionality.";
                startListeningBtn.disabled = true;
                return;
            }
        }

        try {
            recognition.start();
            statusDiv.textContent = "Listening...";
            startListeningBtn.disabled = true;
        } catch (error) {
            console.error("Error starting speech recognition:", error);
            statusDiv.textContent = "Could not start listening. Microphone might be in use or permissions denied.";
            startListeningBtn.disabled = false;
        }
    }

    async function processVoiceCommand(command) {
        responseDiv.textContent = `Processing command: "${command}"...`;
        speak("Processing your request.");

        try {
            const backendResponse = await fetch('/api/process_command', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    command: command,
                    current_step: currentStepIndex,
                    recipe_id: currentRecipe ? currentRecipe.id : null
                })
            });

            if (!backendResponse.ok) {
                throw new Error(`HTTP error! status: ${backendResponse.status}`);
            }
            const data = await backendResponse.json();
            console.log("Backend AI Response:", data);

            if (speechSynthesis.speaking && speechSynthesis.pending) {
                speechSynthesis.cancel();
            }

            responseDiv.textContent = `Assistant: ${data.response}`;
            speak(data.response);

            // Handle actions returned by the backend
            if (data.action === 'next_step') {
                window.nextStep();
            } else if (data.action === 'repeat_step') {
                window.repeatStep();
            } else if (data.action === 'load_recipe_id' && data.recipe_id) {
                fetchRecipe(data.recipe_id);
            } else if (data.action === 'show_recipe_list') {
                showRecipeList();
            } else if (data.action === 'filter_recipes' && data.category) {
                // Update the UI for the active filter button
                filterButtons.forEach(btn => {
                    if (btn.dataset.category === data.category.toLowerCase()) {
                        btn.classList.add('active');
                    } else {
                        btn.classList.remove('active');
                    }
                });
                currentFilterCategory = data.category.toLowerCase();
                fetchAllRecipes(currentFilterCategory); // Re-fetch based on voice command category
                showRecipeList(); // Ensure we are on the list view
            }


        } catch (error) {
            console.error('Error processing command with backend:', error);
            responseDiv.textContent = "Sorry, I couldn't process that command. Please check the console for errors.";
            speak("Sorry, I couldn't process that command due to an error.");
        } finally {
            startListeningBtn.disabled = false;
        }
    }

    // --- Global Functions (Called by Backend Actions) ---

    window.nextStep = () => {
        if (currentRecipe && currentStepIndex < currentRecipe.instructions.length - 1) {
            currentStepIndex++;
            highlightCurrentStep();
            speak(currentRecipe.instructions[currentStepIndex]); // Speak the next step automatically
            console.log(`Moved to step: ${currentStepIndex + 1}`);
        } else if (currentRecipe) {
            speak("You are at the last step of the recipe!");
            console.log("Already at the last step.");
        } else {
            speak("No recipe loaded to advance steps.");
            console.log("No step to repeat.");
        }
    };

    window.repeatStep = () => {
        if (currentRecipe && currentRecipe.instructions[currentStepIndex]) {
            highlightCurrentStep();
            speak(currentRecipe.instructions[currentStepIndex]);
            console.log(`Repeating step: ${currentStepIndex + 1}`);
        } else {
            speak("No step to repeat.");
            console.log("No step to repeat.");
        }
    };

    // --- Event Listeners and Initial Load ---
    startListeningBtn.addEventListener('click', () => {
        startRecognition();
    });

    backToRecipesBtn.addEventListener('click', () => {
        showRecipeList();
    });

    // Add event listeners for filter buttons
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove 'active' class from all buttons
            filterButtons.forEach(btn => btn.classList.remove('active'));
            // Add 'active' class to the clicked button
            button.classList.add('active');
            
            const category = button.dataset.category;
            currentFilterCategory = category; // Update current filter state
            fetchAllRecipes(category); // Fetch recipes based on the selected category
            showRecipeList(); // Ensure we are on the list view
        });
    });

    // Initial page load: Fetch and display the list of all recipes (default 'all' category)
    fetchAllRecipes(currentFilterCategory);
    showRecipeList(); // Ensure recipe list section is shown initially and buttons are set up
});
