export default class MinigameScene extends Phaser.Scene {
    constructor() {
        super({ key: 'MinigameScene' });
    }

    init(data) {
        this.petImageUrl = data.petImageUrl;
        this.petId = data.petId;
        this.csrfToken = data.csrfToken;
    }

    preload() {
        this.petKey = 'petMinigame';
        const staticImages = {
            minigameBg: '/static/images/part3.png',
            energy: '/static/images/b2.png',
            hunger: '/static/images/food.png',
            happiness: '/static/images/smile.png',
            cherry: '/static/images/cherries.png',
            diamond:'/static/images/diamond.png',
        };

        // Cargar imágenes estáticas
        Object.entries(staticImages).forEach(([key, path]) => {
            this.load.image(key, path);
        });

        // Cargar imagen de la mascota
        const petPath = this.petImageUrl.startsWith('/static/')
            ? this.petImageUrl
            : `/pets/image-proxy/${encodeURIComponent(this.petImageUrl)}`;
        this.load.image(this.petKey, petPath);
    }

    create() {
        this.add.image(400, 300, 'minigameBg').setScale(1.5);
        this.pet = this.add.image(400, 340, this.petKey).setScale(0.8);

        this.add.text(310, 80, '¡PET SLOT!', {
            font: '32px Arial',
            fill: '#ffffff'
        });

        // Botón Volver
        this.createButton('Volver', 350, 550, '#00ffcc', () => {
            // Pasar los datos actualizados al regresar a PetScene
            this.scene.start('PetScene', {
                petId: this.petId,  // valores actualizados de MinigameScene
                petImageUrl: this.petImageUrl,
                hunger: this.hunger,
                energy: this.energy,
                happiness: this.happiness,
                csrfToken: this.csrfToken
            });
        });

        // Símbolos disponibles para el minijuego
        this.symbols = ['energy', 'hunger', 'happiness', 'cherry','diamond'];

        // Crear slots iniciales
        
        this.slots = [];
        const iconSize = 0.8;  // Escala para los íconos 
        const spacing = 120;    // Espacio entre los íconos 
        
        for (let i = 0; i < 3; i++) {
            const slot = this.add.image(280 + i * spacing, 200, 'cherry').setScale(iconSize);
            this.slots.push(slot);
        }

        // Botón Girar
        this.createButton('Spin🎰', 340, 470, '#ffffff', () => this.spinSlots(), '#00cc99', 28);
         
    
        
    }

    createButton(text, x, y, fill, callback, bgColor = '#000', fontSize = 24) {
        this.add.text(x, y, text, {
            font: `${fontSize}px Arial`,
            fill,
            backgroundColor: bgColor,
            padding: { x: 15, y: 10 }
        }).setInteractive().on('pointerdown', callback);
    }
    
    spinSlots() {
        if (this.isSpinning) return;
        this.isSpinning = true;
    
        const spinDuration = 1500;
        const spinInterval = 100;
        const results = [];
        let completed = 0;
    
        // Inicia la animación de flip de la mascota
        this.flipEvent = this.time.addEvent({
            delay: 400,
            callback: () => this.pet.toggleFlipX(),
            loop: true
        });
    
        this.slots.forEach((slot, index) => {
            const spinTime = spinDuration + index * 300;
    
            this.time.addEvent({
                delay: spinInterval,
                callback: () => {
                    const randomSymbol = Phaser.Utils.Array.GetRandom(this.symbols);
                    slot.setTexture(randomSymbol);
                },
                repeat: Math.floor(spinTime / spinInterval)
            });
    
            // Finaliza el spin y selecciona el símbolo real
            this.time.delayedCall(spinTime + spinInterval, () => {
                const finalSymbol = Phaser.Utils.Array.GetRandom(this.symbols);
                slot.setTexture(finalSymbol);
                results[index] = finalSymbol;
    
                completed++;
    
                if (completed === this.slots.length) {
                    // Detener el flip de la mascota
                    this.flipEvent.remove();
    
                    this.time.delayedCall(300, () => {
                        this.evaluateResults(results);
                        this.isSpinning = false;
                    });
                }
            });
        });
    }
    
    

    async evaluateResults(results) {
        //console.log('Símbolos obtenidos:', results);
        
        const allEqual = results.every(symbol => symbol === results[0]);
    
        if (allEqual) {
            const symbol = results[0].trim().toLowerCase();
    
            if (symbol === 'cherry') {
                //console.log('Cherry detectado. Incrementando los tres parámetros');
                
                // Aumentar los tres parámetros uno por uno, esperando cada respuesta
                const params = ['energy', 'hunger', 'happiness'];
                for (const param of params) {
                    //console.log(`Intentando incrementar ${param}`);
                    await this.increaseParameter(param); // Esperar la llamada al backend
                }
    
                // Mostrar mensaje visual
                const bonusText = this.add.text(250, 470, `¡CHERRY BONUS +9+9+9`, {
                    font: '24px Arial',
                    fill: '#ff66ff',
                    backgroundColor: '#000',
                    padding: { x: 10, y: 5 }
                });
                this.time.delayedCall(2000, () => bonusText.destroy());
    
            } else if (symbol === 'diamond') {
                const params = ['energy', 'hunger', 'happiness'];
                for (const param of params) {
                    await this.increaseParameter(param);
                    await this.increaseParameter(param);
                    await this.increaseParameter(param);
                }
    
                const bonusText = this.add.text(220, 470, `¡DIAMOND BONUS x3 +27+27+27!`, {
                    font: '24px Arial',
                    fill: '#00ffff',
                    backgroundColor: '#000',
                    padding: { x: 10, y: 5 }
                });
                this.time.delayedCall(2500, () => bonusText.destroy());
    
            } 
            
            else {
                const validParams = ['energy', 'hunger', 'happiness'];
                if (validParams.includes(symbol)) {
                    await this.increaseParameter(symbol); // Solo una llamada
                    const bonusText = this.add.text(300, 470, `¡${symbol.toUpperCase()} +9!`, {
                        font: '24px Arial',
                        fill: '#ffff00',
                        backgroundColor: '#000',
                        padding: { x: 10, y: 5 }
                    });
                    this.time.delayedCall(2000, () => bonusText.destroy());
                } else {
                    //console.log(`Tres iguales de ${symbol}, sin efecto.`);
                }
            }
        } else {
            //console.log('No hay tres símbolos iguales. No se otorga bono.');
        }
    }
    
    
    async increaseParameter(param) {
        const url = `/pets/increase_${param}/${this.petId}/`;
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json'
                }
            });
            const data = await res.json();
            //console.log(`${param} actualizado:`, data[param]);
            return data;
        } catch (err) {
            console.error('Error:', err);
            throw err;
        }
    }
    
}
