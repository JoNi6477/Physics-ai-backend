import os
import textwrap

try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# Read API key from environment variable
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def generate_simulation_html(question: str) -> str:
    """
    Generates an interactive HTML/JS physics simulation for the given question.
    """
    prompt = f'''
    You are an expert physics engine programmer. 
    The user will provide a physics question. 
    You must write a single HTML file containing an interactive 2D canvas simulation 
    that visualizes the physics concepts in the question.

    Requirements:
    1. Output NOTHING BUT raw HTML code. Do not use markdown blocks like ```html. 
    2. Include inline CSS and JS in the same file.
    3. Use a dark futuristic theme with `#0a0e1a` background, and `#44aaff` accents.
    4. Start the simulation automatically when the page loads.

    Question: "{question}"
    '''

    if HAS_GEMINI and GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.8-flash', 'gemini-3.1-flash-lite']
        
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                html_content = response.text.strip()

                if html_content.startswith("```html"):
                    html_content = html_content[7:]
                elif html_content.startswith("```"):
                    html_content = html_content[3:]
                if html_content.endswith("```"):
                    html_content = html_content[:-3]
                
                html_content = html_content.strip()
                print(f"=== GENERATED HTML WITH {model_name} (Length: {len(html_content)}) ===")
                return html_content
            except Exception as e:
                print(f"=== Model {model_name} failed: {e} ===")
                continue
        
        print("=== All Gemini models failed or unavailable, using fallback simulation ===")

    # Fallback simulation if models are unavailable or API keys missing
    return textwrap.dedent(f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ margin: 0; background: #0a0e1a; color: #e8eaf0; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; overflow: hidden; }}
                canvas {{ background: #0a0e1a; width: 100vw; height: 100vh; }}
                #ui {{ position: absolute; top: 20px; text-align: center; width: 100%; }}
                h2 {{ color: #f7c948; margin: 0; text-shadow: 0px 0px 10px rgba(247, 201, 72, 0.5); }}
                p {{ color: #44aaff; font-size: 1.2rem; }}
            </style>
        </head>
        <body>
            <div id="ui">
                <h2>Projectile Simulation</h2>
                <p>Range R = ½ * g * t₁ * t₂ = 245m</p>
            </div>
            <canvas id="simCanvas"></canvas>
            <script>
                const canvas = document.getElementById('simCanvas');
                const ctx = canvas.getContext('2d');
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
                
                let time = 0;
                const g = 9.8;
                const scale = canvas.width / 300; // Scale 245m to fit screen width
                const startX = 20;
                const startY = canvas.height - 40;
                
                // Physics properties
                const t1 = 5, t2 = 10;
                const R = 0.5 * g * t1 * t2; // 245
                const u = Math.sqrt(g * R / Math.sin(2 * Math.atan(t1/t2)));
                
                // Angles (radians)
                const theta1 = Math.atan((g * t1 * t1) / (2 * R));
                const theta2 = Math.atan((g * t2 * t2) / (2 * R));

                function getPos(u, theta, t) {{
                    return {{
                        x: startX + (u * Math.cos(theta) * t) * scale,
                        y: startY - (u * Math.sin(theta) * t - 0.5 * g * t * t) * scale
                    }};
                }}

                function draw() {{
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    
                    // Draw Ground
                    ctx.fillStyle = '#f7c948';
                    ctx.fillRect(0, startY + 10, canvas.width, 20);
                    
                    // Target indicator
                    ctx.fillStyle = 'white';
                    ctx.fillRect(startX + R * scale - 5, startY, 10, 10);
                    
                    time += 0.05;
                    if (time > 11) time = 0; // Reset loop
                    
                    const p1 = getPos(u, theta1, Math.min(time, t1));
                    const p2 = getPos(u, theta2, Math.min(time, t2));
                    
                    // Draw body 1
                    ctx.beginPath();
                    ctx.arc(p1.x, p1.y, 8, 0, Math.PI*2);
                    ctx.fillStyle = '#44aaff';
                    ctx.fill();
                    
                    // Draw body 2
                    ctx.beginPath();
                    ctx.arc(p2.x, p2.y, 8, 0, Math.PI*2);
                    ctx.fillStyle = '#f7c948';
                    ctx.fill();
                    
                    requestAnimationFrame(draw);
                }}
                draw();
            </script>
        </body>
        </html>
        ''')
