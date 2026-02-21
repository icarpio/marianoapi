export default class MiniGameBase extends Phaser.Scene {
    constructor() {
        super({ key: 'MiniGameBase' });
    }

    init(data) {
        this.petImageUrl = data.petImageUrl;
    }

    preload() {
        this.load.image('minigameBg', '/static/images/part3.png');

        this.petKey = 'petMinigame'; // ⬅ clave única
        if (this.petImageUrl.startsWith('/static/')) {
            this.load.image(this.petKey, this.petImageUrl);
        } else {
            const proxyUrl = "/pets/image-proxy/" + encodeURIComponent(this.petImageUrl);
            this.load.image(this.petKey, proxyUrl);
        }
        this.load.on('complete', () => {
        });
    }

    create() {
        this.add.image(400, 300, 'minigameBg').setScale(1.5);

        this.pet = this.add.image(400, 300, this.petKey).setScale(1);


        /*
        this.flipEvent = this.time.addEvent({
            delay: 1000,
            callback: () => this.pet.toggleFlipX(),
            loop: true
        });
        */

        this.add.text(270, 80, '¡Minijuego Activo!', {
            font: '32px Arial',
            fill: '#ffffff'
        });

        const backButton = this.add.text(350, 550, 'Volver', {
            font: '24px Arial',
            fill: '#00ffcc',
            backgroundColor: '#000',
            padding: { x: 15, y: 10 }
        }).setInteractive();

        backButton.on('pointerdown', () => {
            this.scene.start('PetScene');
        });
    }
}
