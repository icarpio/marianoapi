document.addEventListener("DOMContentLoaded", function () {
    var petId = document.getElementById("game-container").getAttribute("data-pet-id");
    var petImageUrl = document.getElementById("game-container").getAttribute("data-pet-image");
    //var petName = document.getElementById("game-container").getAttribute("data-pet-name");
    var hunger = parseInt(document.getElementById("game-container").getAttribute("data-hunger"));
    var energy = parseInt(document.getElementById("game-container").getAttribute("data-energy"));
    var happiness = parseInt(document.getElementById("game-container").getAttribute("data-happiness"));
    var csrfToken = document.getElementById("game-container").getAttribute("data-csrf");

    var config = {
        type: Phaser.AUTO,
        width: 800,
        height: 600,
        parent: 'game-container',
        scene: { preload, create, update }
    };

    var petImage, hungerText, energyText, happinessText, flipXEvent;
    var game = new Phaser.Game(config);

    function preload() {
        if (!petImageUrl) {
            console.error('La URL de la imagen es inválida');
        } else {
            this.load.image('background', '/static/images/part3.png');
            // Si la imagen estática es de "static/", la cargamos directamente
            if (petImageUrl.startsWith('/static/')) {
                this.load.image('pet', petImageUrl);
            } else {
                // Si es una URL externa, la pasamos por el proxy
                var proxyUrl = "/pets/image-proxy/" + encodeURIComponent(petImageUrl);
                this.load.image('pet', proxyUrl);
            }
        }
        this.load.image('sleepButton', '/static/images/sleeping2.png');
        this.load.image('hungerButton', '/static/images/b1.png');  
        this.load.image('energyButton', '/static/images/b2.png');
        this.load.image('happinessButton', '/static/images/b3.png');
        this.load.image('wakeupButton', '/static/images/alarm.png');

        this.load.image('hungerIcon', '/static/images/food.png');  
        this.load.image('energyIcon', '/static/images/ray.png');
        this.load.image('happinessIcon', '/static/images/smile.png');
    }

    function create() {
        this.add.image(400, 300, 'background').setScale(1.5);
        this.load.once('complete', () => {
            // Agrega la imagen a la escena después de que Phaser la cargue
            petImage = this.add.image(430, 240, 'pet');
        
            // Si la imagen es estática (durmiendo), aplica una escala diferente
            if (petImageUrl.startsWith('/static/')) {
                petImage.setScale(1.8);  // Escala más grande para imágenes estáticas
            } else {
                petImage.setScale(1.7);  // Escala normal para imágenes dinámicas
                // Volteo continuo de la imagen de la mascota
            }
            this.time.addEvent({
                delay: 1000, // 500ms para alternar
                callback: () => {
                    petImage.toggleFlipX(); // Alterna el flipX
                },
                loop: true // Hace que el evento sea continuo
            });
        });
        
        // Inicia la carga de imágenes
        this.load.start();
        
        this.add.image(50, 40, 'hungerIcon').setScale(0.3);
        this.add.image(300, 40, 'energyIcon').setScale(0.3);
        this.add.image(600, 40, 'happinessIcon').setScale(0.3);
        
        //this.add.text(35, 40, "Mascota: " + petName, { font: "24px Arial", fill: "#ffffff" });
        var sleepButton = this.add.image(80, 520, 'sleepButton').setInteractive().on('pointerdown', () => sleepPet());
        var hungerButton = this.add.image(240, 520, 'hungerButton').setInteractive().on('pointerdown', () => increaseParameter('hunger'));
        var energyButton = this.add.image(400, 520, 'energyButton').setInteractive().on('pointerdown', () => increaseParameter('energy'));
        var happinessButton = this.add.image(570, 520, 'happinessButton').setInteractive().on('pointerdown', () => increaseParameter('happiness'));
        var wakeupButton = this.add.image(720, 520, 'wakeupButton').setInteractive().on('pointerdown', () => wake_up());

        hungerText = this.add.text(90, 30, 'Hambre: ' + hunger, { font: '20px Arial', fill: '#ffffff' });
        energyText = this.add.text(340, 30, 'Energía: ' + energy, { font: '20px Arial', fill: '#ffffff' });
        happinessText = this.add.text(640, 30, 'Felicidad: ' + happiness, { font: '20px Arial', fill: '#ffffff' });

        hungerButton.setScale(0.60);
        energyButton.setScale(0.90);
        happinessButton.setScale(0.60);
        wakeupButton.setScale(0.62);
        sleepButton.setScale(0.62);

        
         
    }

    function update() {
        hungerText.setText('Hambre: ' + hunger);
        energyText.setText('Energía: ' + energy);
        happinessText.setText('Felicidad: ' + happiness);
    }
    
    
    function increaseParameter(param) {
        let urlMap = {
            'hunger': `/pets/increase_hunger/${petId}/`,
            'energy': `/pets/increase_energy/${petId}/`,
            'happiness': `/pets/increase_happiness/${petId}/`
        };

        fetch(urlMap[param], {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (param === 'hunger') hunger = data.hunger;
            else if (param === 'energy') energy = data.energy;
            else if (param === 'happiness') happiness = data.happiness;
        })
        .catch(error => console.error('Error:', error));
    }


    function updatePetImage(imageUrl) {
        if (!imageUrl) {
            console.error('La URL de la imagen es inválida');
            return;
        }
        
        // Generar un key único con timestamp para evitar cacheo
        const textureKey = 'pet_' + new Date().getTime();
        
        // Obtener la escena actual
        const game = petImage.scene;
        
        // Determinar la URL correcta según su origen
        let urlToLoad;
        if (imageUrl.startsWith('/static/')) {
            urlToLoad = imageUrl;
        } else {
            // Usar el mismo proxy que en preload()
            urlToLoad = "/pets/image-proxy/" + encodeURIComponent(imageUrl);
        }
        
        // Añadir parámetro para evitar caché
        urlToLoad = urlToLoad + (urlToLoad.includes('?') ? '&' : '?') + 'nocache=' + new Date().getTime();
        
        // Destruir la textura anterior si existe con ese key
        if (game.textures.exists(textureKey)) {
            game.textures.remove(textureKey);
        }
        
        // Cargar la nueva imagen
        game.load.image(textureKey, urlToLoad);
        
        game.load.once('complete', function() {
            // Actualizar el sprite con la nueva textura
            petImage.setTexture(textureKey);
            
            // Ajustar la escala según el origen
            if (imageUrl.startsWith('/static/')) {
                petImage.setScale(1.8);  // Escala para imágenes estáticas
            } else {
                petImage.setScale(1.7);  // Escala normal para imágenes dinámicas
                
            }       
            console.log('Imagen de mascota actualizada:', imageUrl);
        });
        
        // Manejar errores de carga
        game.load.on('loaderror', function(fileObj) {
            if (fileObj.key === textureKey) {
                console.error('Error al cargar la imagen:', imageUrl);
                // Volver a la textura predeterminada en caso de error
                petImage.setTexture('pet');
            }
        });
        
        // Iniciar la carga
        game.load.start();
    }
// Función para poner a dormir a la mascota
function sleepPet() {
    fetch( `/pets/sleep/${petId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ pet_id: petId })
    })
    .then(response => response.json())
    .then(data => {
        updatePetImage(data.new_pet_image_url); 

    })
    .catch(error => console.error('Error al dormir la mascota:', error));
}

// Función para despertar a la mascota
function wake_up() {
    fetch(`/pets/wake_up/${petId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ pet_id: petId })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.message);
        // Actualizar la imagen de la mascota a despierta
        updatePetImage(data.new_pet_image_url);  // Usa la URL recibida en la respuesta
        
    })
    .catch(error => console.error('Error al despertar la mascota:', error));
}
});



function toggleSleepWake(action) {
    // Determina la URL de la API según la acción
    const url = action === 'sleep' ? `/pets/sleep/${petId}/` : `/pets/wake_up/${petId}/`;

    // Realiza la solicitud fetch
    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ pet_id: petId })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.message);
        // Actualiza la imagen de la mascota según la acción
        updatePetImage(data.new_pet_image_url);  // Usa la URL recibida en la respuesta

        // Si la acción es 'sleep', detenemos el evento de flipX
        if (action === 'sleep') {
            if (this.flipXEvent) {
                this.flipEvent.remove()
            }
        }
        // Si la acción es 'wake', reiniciamos el evento de flipX
        else if (action === 'wake_up') {
            this.flipEvent = this.time.addEvent({
                delay: 1000, 
                callback: () => {
                    petImage.toggleFlipX();
                },
                loop: true
            });
        }
    })
    .catch(error => console.error(`Error al ${action} la mascota:`, error));
}



