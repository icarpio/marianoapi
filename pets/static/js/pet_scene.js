export default class PetScene extends Phaser.Scene {
    constructor() {
        super({ key: 'PetScene' });

        // Estado inicial
        this.petImage = null;
        this.petImageUrl = '';
        this.petId = '';
        this.csrfToken = '';
        this.hunger = 0;
        this.energy = 0;
        this.happiness = 0;
    }

    init() {
        const container = document.getElementById("game-container");
        this.petId = container.getAttribute("data-pet-id");
        this.petImageUrl = container.getAttribute("data-pet-image");
        this.hunger = parseInt(container.getAttribute("data-hunger"));
        this.energy = parseInt(container.getAttribute("data-energy"));
        this.happiness = parseInt(container.getAttribute("data-happiness"));
        this.csrfToken = container.getAttribute("data-csrf");
    }

    
    preload() {
        this.load.image('background', '/static/images/part1.png');

        let petUrl = this.petImageUrl.startsWith('/static/')
            ? this.petImageUrl
            : "/pets/image-proxy/" + encodeURIComponent(this.petImageUrl);
        this.load.image('pet', petUrl);

        this.load.image('sleepButton', '/static/images/sleeping2.png');
        this.load.image('hungerButton', '/static/images/b1.png');
        this.load.image('energyButton', '/static/images/b2.png');
        this.load.image('happinessButton', '/static/images/b3.png');
        this.load.image('wakeupButton', '/static/images/alarm.png');

        this.load.image('hungerIcon', '/static/images/food.png');
        this.load.image('energyIcon', '/static/images/ray.png');
        this.load.image('happinessIcon', '/static/images/smile.png');

        this.load.image('minigameButton', '/static/images/game.png');
    }

    create() {
        this.add.image(400, 300, 'background').setScale(1.5);
        this.petImage = this.add.image(430, 240, 'pet');

        this.petImage.setScale(this.petImageUrl.startsWith('/static/') ? 1.8 : 1.7);

        this.flipEvent = this.time.addEvent({
            delay: 1000,
            callback: () => this.petImage.toggleFlipX(),
            loop: true
        });

        this.add.image(50, 40, 'hungerIcon').setScale(0.3);
        this.add.image(300, 40, 'energyIcon').setScale(0.3);
        this.add.image(600, 40, 'happinessIcon').setScale(0.3);

        this.hungerText = this.add.text(90, 30, `Hambre: ${this.hunger}`, { font: '20px Arial', fill: '#fff' });
        this.energyText = this.add.text(340, 30, `Energía: ${this.energy}`, { font: '20px Arial', fill: '#fff' });
        this.happinessText = this.add.text(640, 30, `Felicidad: ${this.happiness}`, { font: '20px Arial', fill: '#fff' });

        var sleepButton = this.add.image(80, 520, 'sleepButton').setInteractive().on('pointerdown', () => this.sleepPet());
        var hungerButton = this.add.image(240, 520, 'hungerButton').setInteractive().on('pointerdown', () => this.increaseParam('hunger'));
        var energyButton = this.add.image(400, 520, 'energyButton').setInteractive().on('pointerdown', () => this.increaseParam('energy'));
        var happinessButton = this.add.image(570, 520, 'happinessButton').setInteractive().on('pointerdown', () => this.increaseParam('happiness'));
        var wakeupButton = this.add.image(720, 520, 'wakeupButton').setInteractive().on('pointerdown', () => this.wakePet());

        //Botón para ir al minijuego
        const minigameButton = this.add.image(720, 400, 'minigameButton').setInteractive().setScale(0.6);
        minigameButton.on('pointerdown', () => {
            this.scene.start('MinigameScene', {
                petImageUrl: this.petImageUrl,
                petId: this.petId,
                csrfToken: this.csrfToken
            });
        });
        hungerButton.setScale(0.60);
        energyButton.setScale(0.90);
        happinessButton.setScale(0.60);
        wakeupButton.setScale(0.62);
        sleepButton.setScale(0.62);
    }

    update() {
        this.hungerText.setText(`Hambre: ${this.hunger}`);
        this.energyText.setText(`Energía: ${this.energy}`);
        this.happinessText.setText(`Felicidad: ${this.happiness}`);
    }

    increaseParam(param) {
        const urlMap = {
            hunger: `/pets/increase_hunger/${this.petId}/`,
            energy: `/pets/increase_energy/${this.petId}/`,
            happiness: `/pets/increase_happiness/${this.petId}/`
        };

        fetch(urlMap[param], {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.csrfToken,
                'Content-Type': 'application/json'
            }
        })
        .then(r => r.json())
        .then(data => {
            this[param] = data[param];
        })
        .catch(err => console.error('Error:', err));
    }

    updatePetImage(newUrl) {
        const key = 'pet_' + Date.now();
        const game = this;

        let finalUrl = newUrl.startsWith('/static/')
            ? newUrl
            : "/pets/image-proxy/" + encodeURIComponent(newUrl);

        finalUrl += `?nocache=${Date.now()}`;

        this.textures.remove(key);
        this.load.image(key, finalUrl);

        this.load.once('complete', () => {
            game.petImage.setTexture(key);
            game.petImage.setScale(newUrl.startsWith('/static/') ? 1.8 : 1.7);
        });

        this.load.start();
    }

    sleepPet() {
        fetch(`/pets/sleep/${this.petId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.csrfToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ pet_id: this.petId })
        })
        .then(r => r.json())
        .then(data => this.updatePetImage(data.new_pet_image_url))
        .catch(err => console.error('Error al dormir:', err));
    }

    wakePet() {
        fetch(`/pets/wake_up/${this.petId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.csrfToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ pet_id: this.petId })
        })
        .then(r => r.json())
        .then(data => this.updatePetImage(data.new_pet_image_url))
        .catch(err => console.error('Error al despertar:', err));
    }
}


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
