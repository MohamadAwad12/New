# Is Moe a Millionaire?

A real-time Solana token portfolio tracker with dynamic animations and celebrations.

## Features
- Real-time price tracking using DEX Screener API
- Dynamic theme changes based on portfolio value
- Animated price updates and transitions
- Millionaire celebration effects
- Smooth scroll-snap navigation
- Responsive design

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/is-moe-millionaire.git
cd is-moe-millionaire
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open in browser:
```
http://localhost:5000
```

## Project Structure
```
is-moe-millionaire/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── static/               # Static assets
│   └── js/
│       └── main.js       # JavaScript functions
├── templates/            # HTML templates
│   └── index.html        # Main template
├── .gitignore           # Git ignore file
└── README.md            # Project documentation
```

## Technologies Used
- Flask
- Socket.IO
- GSAP
- TailwindCSS
- DEX Screener API

## Contributing
Feel free to submit issues and enhancement requests!

## License
MIT