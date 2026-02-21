// Importar escenas correctamente
import PetScene from './pet_scene.js';
import MinigameScene from './minigame_scene.js';

document.addEventListener("DOMContentLoaded", function () {
    const gameContainer = document.getElementById("game-container");
    const petId = gameContainer.getAttribute("data-pet-id");
    const petImageUrl = gameContainer.getAttribute("data-pet-image");
    const hunger = parseInt(gameContainer.getAttribute("data-hunger"));
    const energy = parseInt(gameContainer.getAttribute("data-energy"));
    const happiness = parseInt(gameContainer.getAttribute("data-happiness"));
    const csrfToken = gameContainer.getAttribute("data-csrf");

    // Configuración del juego de Phaser
    const config = {
        type: Phaser.AUTO,
        width: 800,
        height: 600,
        parent: 'game-container',
        scene: [PetScene, MinigameScene],  // Las dos escenas a cargar
    };

    const game = new Phaser.Game(config);

    game.scene.start('PetScene', {
        petId,
        petImageUrl,
        hunger,
        energy,
        happiness,
        csrfToken
    });
});


