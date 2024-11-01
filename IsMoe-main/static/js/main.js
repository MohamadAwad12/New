// Price formatters
const formatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 8
});

const valueFormatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
});

const GOAL = 1000000;
let previousTotal = 0;

// Create confetti effect
function createConfetti() {
    const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff'];
    for (let i = 0; i < 100; i++) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        confetti.style.left = Math.random() * 100 + 'vw';
        confetti.style.top = -10 + 'px';
        document.body.appendChild(confetti);

        gsap.to(confetti, {
            y: '100vh',
            x: (Math.random() - 0.5) * 200,
            rotation: Math.random() * 360,
            duration: Math.random() * 2 + 1,
            ease: 'none',
            onComplete: () => confetti.remove()
        });
    }
}

// Update theme based on total value
function updateTheme(total) {
    const isMillionaire = total >= GOAL;
    document.body.className = isMillionaire ? 'text-white millionaire' : 'text-white not-millionaire';
    
    // Update main status
    const mainStatus = document.getElementById('main-status');
    mainStatus.textContent = isMillionaire ? "MOE IS A MILLIONAIRE! 🎉" : "Not yet... 😢";
    
    // Update progress
    const progress = (total / GOAL) * 100;
    const progressFill = document.getElementById('progress-fill');
    progressFill.style.width = `${Math.min(progress, 100)}%`;

    // Update remaining
    const remaining = Math.max(GOAL - total, 0);
    document.getElementById('remaining').textContent = valueFormatter.format(remaining);
    
    // Update status text
    const statusText = document.getElementById('status-text');
    statusText.textContent = isMillionaire ? 
        `${valueFormatter.format(total - GOAL)} over goal!` :
        `$${valueFormatter.format(remaining)} to go`;
}

// Animate value changes
function updateValue(newValue) {
    const mainTotal = document.getElementById('main-total');
    const trendArrow = document.getElementById('trend-arrow');
    
    mainTotal.classList.remove('value-up', 'value-down');
    
    if (newValue > previousTotal) {
        mainTotal.classList.add('value-up');
        trendArrow.textContent = '↑';
        trendArrow.className = 'trend-arrow visible up-arrow';
    } else if (newValue < previousTotal) {
        mainTotal.classList.add('value-down');
        trendArrow.textContent = '↓';
        trendArrow.className = 'trend-arrow visible down-arrow';
    }

    gsap.to({value: previousTotal}, {
        value: newValue,
        duration: 1,
        ease: "power2.out",
        onUpdate: function() {
            mainTotal.textContent = valueFormatter.format(this.targets()[0].value);
        }
    });

    setTimeout(() => {
        trendArrow.className = 'trend-arrow';
    }, 1000);

    previousTotal = newValue;
}

// Celebration animation
function celebrateMillionaire() {
    document.body.classList.add('millionaire-celebration');
    createConfetti();
    
    gsap.to('.main-value', {
        scale: 1.2,
        duration: 0.5,
        yoyo: true,
        repeat: 3
    });

    setInterval(createConfetti, 2000);
}

// Initialize Socket.IO connection
const socket = io();

// Handle price updates
socket.on('price_update', (data) => {
    const total = data.total_value;
    const isNewMillionaire = total >= 1000000 && previousTotal < 1000000;
    
    updateValue(total);
    updateTheme(total);

    if (isNewMillionaire) {
        celebrateMillionaire();
    }

    // Update token cards
    Object.entries(data.prices).forEach(([token, tokenData]) => {
        const price = tokenData.price;
        const value = tokenData.value;
        const change = tokenData.priceChange24h;

        document.getElementById(`${token.toLowerCase()}-price`).textContent = formatter.format(price);
        document.getElementById(`${token.toLowerCase()}-value`).textContent = valueFormatter.format(value);
        
        const changeElement = document.getElementById(`${token.toLowerCase()}-change`);
        const changeClass = change >= 0 ? 'token-change-up' : 'token-change-down';
        const changeSign = change >= 0 ? '+' : '';
        changeElement.className = `text-sm ${changeClass}`;
        changeElement.textContent = `${changeSign}${change.toFixed(2)}%`;
    });
});

// Connection status handling
socket.on('connect', () => {
    document.getElementById('connection-status').style.display = 'none';
});

socket.on('disconnect', () => {
    document.getElementById('connection-status').style.display = 'block';
    document.getElementById('connection-status').textContent = 'Reconnecting...';
});
