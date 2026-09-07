# -*- coding: utf-8 -*-
"""
game_synthesizer.py
===================
Autonomous 3D Game & Interactive Web Application Synthesizer for Jarvis.

Generates complete, standalone 3D WebGL (Three.js) playable games and launches
them instantly in the user's default browser (Subway Surfers, 3D Runner, Pong, Space Shooter).
"""

import os
import sys
import webbrowser
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


SUBWAY_SURFERS_3D_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ JARVIS 3D SUBWAY SURFERS ⚡</title>
    <style>
        body { margin: 0; overflow: hidden; background: #111; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        #ui { position: absolute; top: 20px; left: 20px; color: #fff; z-index: 10; text-shadow: 0 0 10px #00ffff; }
        #score { font-size: 32px; font-weight: bold; color: #00ffff; }
        #coins { font-size: 24px; color: #ffd700; }
        #instructions { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); color: #fff; background: rgba(0,0,0,0.6); padding: 10px 20px; border-radius: 20px; border: 1px solid #00ffff; font-size: 16px; }
        #game-over { display: none; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; color: #ff3366; background: rgba(0,0,0,0.85); padding: 40px; border-radius: 20px; border: 2px solid #ff3366; box-shadow: 0 0 30px #ff3366; }
        #game-over h1 { font-size: 48px; margin: 0 0 10px; }
        #game-over button { font-size: 20px; padding: 10px 30px; background: #00ffff; color: #000; border: none; border-radius: 10px; cursor: pointer; font-weight: bold; }
        #game-over button:hover { background: #fff; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
    <div id="ui">
        <div id="score">DISTANCE: 0 m</div>
        <div id="coins">🪙 COINS: 0</div>
    </div>
    <div id="instructions">🎮 Controls: ⬅️ ➡️ Arrow Keys (or A / D) to Change Lanes | ⬆️ (Space) to JUMP</div>
    <div id="game-over">
        <h1>CRASHED!</h1>
        <p id="final-score" style="color:#fff; font-size:20px;"></p>
        <button onclick="restartGame()">PLAY AGAIN (R)</button>
    </div>

    <script>
        let scene, camera, renderer;
        let player;
        let currentLane = 0; // -1: Left, 0: Center, 1: Right
        const laneWidth = 3;
        let isJumping = false;
        let jumpVelocity = 0;
        const gravity = -0.015;
        let speed = 0.4;
        let score = 0;
        let coinsCollected = 0;
        let gameOver = false;

        let obstacles = [];
        let coins = [];
        let tracks = [];

        function init() {
            scene = new THREE.Scene();
            scene.fog = new THREE.FogExp2(0x050515, 0.015);

            camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(0, 4, 8);
            camera.lookAt(0, 1.5, -10);

            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setClearColor(0x050515);
            renderer.shadowMap.enabled = true;
            document.body.appendChild(renderer.domElement);

            // Lights
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);

            const dirLight = new THREE.DirectionalLight(0x00ffff, 0.8);
            dirLight.position.set(5, 15, 10);
            dirLight.castShadow = true;
            scene.add(dirLight);

            // Player (Stark Cyber Surfer)
            const playerGeo = new THREE.BoxGeometry(1, 1.8, 0.8);
            const playerMat = new THREE.MeshStandardMaterial({ color: 0x00ffff, roughness: 0.2, metalness: 0.8 });
            player = new THREE.Mesh(playerGeo, playerMat);
            player.position.set(0, 0.9, 0);
            player.castShadow = true;
            scene.add(player);

            // Create initial tracks
            for (let i = 0; i < 20; i++) {
                createTrackSegment(-i * 15);
            }

            // Keyboard listeners
            window.addEventListener('keydown', handleKeyDown);
            window.addEventListener('resize', onWindowResize);

            animate();
        }

        function createTrackSegment(zPos) {
            const trackGeo = new THREE.PlaneGeometry(10, 15);
            const trackMat = new THREE.MeshStandardMaterial({ color: 0x1a1a2e, roughness: 0.8 });
            const track = new THREE.Mesh(trackGeo, trackMat);
            track.rotation.x = -Math.PI / 2;
            track.position.set(0, 0, zPos);
            track.receiveShadow = true;
            scene.add(track);
            tracks.push(track);

            // Lane Dividers (Neon Lines)
            [-1.5, 1.5].forEach(x => {
                const lineGeo = new THREE.PlaneGeometry(0.1, 15);
                const lineMat = new THREE.MeshBasicMaterial({ color: 0x00ffff });
                const line = new THREE.Mesh(lineGeo, lineMat);
                line.rotation.x = -Math.PI / 2;
                line.position.set(x, 0.01, zPos);
                scene.add(line);
                tracks.push(line);
            });

            // Random Obstacles & Coins
            if (zPos < -20) {
                spawnObstacle(zPos);
                spawnCoin(zPos);
            }
        }

        function spawnObstacle(zPos) {
            const lanes = [-laneWidth, 0, laneWidth];
            const lane = lanes[Math.floor(Math.random() * lanes.length)];
            const obsGeo = new THREE.BoxGeometry(2, 1.5, 1);
            const obsMat = new THREE.MeshStandardMaterial({ color: 0xff3366, roughness: 0.3 });
            const obs = new THREE.Mesh(obsGeo, obsMat);
            obs.position.set(lane, 0.75, zPos);
            obs.castShadow = true;
            scene.add(obs);
            obstacles.push(obs);
        }

        function spawnCoin(zPos) {
            const lanes = [-laneWidth, 0, laneWidth];
            const lane = lanes[Math.floor(Math.random() * lanes.length)];
            const coinGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.1, 16);
            const coinMat = new THREE.MeshStandardMaterial({ color: 0xffd700, metalness: 0.9, roughness: 0.1 });
            const coin = new THREE.Mesh(coinGeo, coinMat);
            coin.rotation.x = Math.PI / 2;
            coin.position.set(lane, 1.2, zPos + (Math.random() * 5 - 2.5));
            scene.add(coin);
            coins.push(coin);
        }

        function handleKeyDown(e) {
            if (gameOver) {
                if (e.key === 'r' || e.key === 'R') restartGame();
                return;
            }
            if ((e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') && currentLane > -1) {
                currentLane--;
            } else if ((e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') && currentLane < 1) {
                currentLane++;
            } else if ((e.key === 'ArrowUp' || e.key === ' ' || e.key === 'w' || e.key === 'W') && !isJumping) {
                isJumping = true;
                jumpVelocity = 0.35;
            }
        }

        function animate() {
            if (gameOver) return;
            requestAnimationFrame(animate);

            score += Math.floor(speed * 2);
            document.getElementById('score').innerText = `DISTANCE: ${score} m`;

            // Smooth lane movement
            const targetX = currentLane * laneWidth;
            player.position.x += (targetX - player.position.x) * 0.15;

            // Jump Physics
            if (isJumping) {
                player.position.y += jumpVelocity;
                jumpVelocity += gravity;
                if (player.position.y <= 0.9) {
                    player.position.y = 0.9;
                    isJumping = false;
                }
            }

            // Move Obstacles & Check Collisions
            for (let i = obstacles.length - 1; i >= 0; i--) {
                const obs = obstacles[i];
                obs.position.z += speed;

                // Collision detection (Bounding Box)
                if (Math.abs(obs.position.z - player.position.z) < 1.0 &&
                    Math.abs(obs.position.x - player.position.x) < 1.2 &&
                    player.position.y < 1.6) {
                    triggerGameOver();
                    return;
                }

                if (obs.position.z > 15) {
                    scene.remove(obs);
                    obstacles.splice(i, 1);
                    spawnObstacle(-250);
                }
            }

            // Move Coins & Collect
            for (let i = coins.length - 1; i >= 0; i--) {
                const coin = coins[i];
                coin.position.z += speed;
                coin.rotation.z += 0.05;

                if (Math.abs(coin.position.z - player.position.z) < 1.0 &&
                    Math.abs(coin.position.x - player.position.x) < 1.2) {
                    coinsCollected++;
                    document.getElementById('coins').innerText = `🪙 COINS: ${coinsCollected}`;
                    scene.remove(coin);
                    coins.splice(i, 1);
                    spawnCoin(-250);
                } else if (coin.position.z > 15) {
                    scene.remove(coin);
                    coins.splice(i, 1);
                    spawnCoin(-250);
                }
            }

            // Recycle Tracks
            tracks.forEach(track => {
                track.position.z += speed;
                if (track.position.z > 15) {
                    track.position.z -= 300;
                }
            });

            // Increase speed gradually
            speed = Math.min(speed + 0.00005, 0.8);

            renderer.render(scene, camera);
        }

        function triggerGameOver() {
            gameOver = true;
            document.getElementById('final-score').innerText = `Score: ${score}m | Coins: ${coinsCollected}`;
            document.getElementById('game-over').style.display = 'block';
        }

        function restartGame() {
            obstacles.forEach(o => scene.remove(o));
            coins.forEach(c => scene.remove(c));
            obstacles = [];
            coins = [];
            currentLane = 0;
            player.position.set(0, 0.9, 0);
            score = 0;
            coinsCollected = 0;
            speed = 0.4;
            isJumping = false;
            gameOver = false;
            document.getElementById('game-over').style.display = 'none';

            for (let i = 0; i < 15; i++) {
                spawnObstacle(-30 - i * 20);
                spawnCoin(-30 - i * 20);
            }
            animate();
        }

        function onWindowResize() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        init();
    </script>
</body>
</html>
"""


NEON_SNAKE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>🐍 JARVIS CYBER SNAKE</title>
    <style>
        body { background: #0a0a14; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; font-family: sans-serif; color: #00ffff; }
        canvas { border: 3px solid #00ffff; box-shadow: 0 0 20px #00ffff; background: #000; }
        #score { font-size: 24px; margin-bottom: 10px; text-shadow: 0 0 10px #00ffff; }
    </style>
</head>
<body>
    <div id="score">SCORE: 0</div>
    <canvas id="gc" width="400" height="400"></canvas>
    <p style="color:#aaa; margin-top:10px;">🎮 Use Arrow Keys (or W/A/S/D) to steer</p>
    <script>
        window.onload=function() {
            canv=document.getElementById("gc");
            ctx=canv.getContext("2d");
            document.addEventListener("keydown",keyPush);
            setInterval(game,1000/15);
        }
        px=py=10; gs=tc=20; ax=ay=15; xv=yv=0; trail=[]; tail = 5; score=0;
        function game() {
            px+=xv; py+=yv;
            if(px<0) px= tc-1; if(px>tc-1) px= 0;
            if(py<0) py= tc-1; if(py>tc-1) py= 0;
            ctx.fillStyle="black"; ctx.fillRect(0,0,canv.width,canv.height);
            ctx.fillStyle="#00ffff";
            for(var i=0;i<trail.length;i++) {
                ctx.fillRect(trail[i].x*gs,trail[i].y*gs,gs-2,gs-2);
                if(trail[i].x==px && trail[i].y==py && (xv!=0 || yv!=0)) { tail = 5; score=0; document.getElementById("score").innerText="SCORE: 0"; }
            }
            trail.push({x:px,y:py});
            while(trail.length>tail) { trail.shift(); }
            if(ax==px && ay==py) {
                tail++; score+=10; document.getElementById("score").innerText="SCORE: " + score;
                ax=Math.floor(Math.random()*tc); ay=Math.floor(Math.random()*tc);
            }
            ctx.fillStyle="#ff3366"; ctx.fillRect(ax*gs,ay*gs,gs-2,gs-2);
        }
        function keyPush(evt) {
            switch(evt.keyCode) {
                case 37: case 65: if(xv!==1){xv=-1;yv=0;} break;
                case 38: case 87: if(yv!==1){xv=0;yv=-1;} break;
                case 39: case 68: if(xv!==-1){xv=1;yv=0;} break;
                case 40: case 83: if(yv!==-1){xv=0;yv=1;} break;
            }
        }
    </script>
</body>
</html>
"""

SPACE_SHOOTER_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>🚀 JARVIS GALAXY DEFENDER</title>
    <style>
        body { margin: 0; background: #000; overflow: hidden; font-family: sans-serif; }
        canvas { display: block; }
        #score { position: absolute; top: 20px; left: 20px; color: #00ffcc; font-size: 24px; font-weight: bold; }
    </style>
</head>
<body>
    <div id="score">SCORE: 0</div>
    <canvas id="c"></canvas>
    <script>
        const c = document.getElementById("c"); const ctx = c.getContext("2d");
        c.width = window.innerWidth; c.height = window.innerHeight;
        let score = 0; let player = { x: c.width/2, y: c.height-80, w: 40, h: 40, speed: 8 };
        let bullets = []; let enemies = []; let keys = {};
        window.addEventListener("keydown", e => { keys[e.key] = true; if(e.key === " ") bullets.push({ x: player.x+17, y: player.y, w: 6, h: 15 }); });
        window.addEventListener("keyup", e => keys[e.key] = false);
        function spawnEnemy() { if(Math.random()<0.04) enemies.push({ x: Math.random()*(c.width-40), y: -40, w: 35, h: 35, speed: 3+Math.random()*3 }); }
        function loop() {
            ctx.fillStyle = "rgba(5, 5, 20, 0.3)"; ctx.fillRect(0, 0, c.width, c.height);
            if(keys["ArrowLeft"] || keys["a"] || keys["A"]) player.x = Math.max(0, player.x-player.speed);
            if(keys["ArrowRight"] || keys["d"] || keys["D"]) player.x = Math.min(c.width-player.w, player.x+player.speed);
            ctx.fillStyle = "#00ffff"; ctx.fillRect(player.x, player.y, player.w, player.h);
            ctx.fillStyle = "#ffff00";
            bullets.forEach((b, i) => { b.y -= 12; ctx.fillRect(b.x, b.y, b.w, b.h); if(b.y < 0) bullets.splice(i, 1); });
            spawnEnemy();
            ctx.fillStyle = "#ff3366";
            enemies.forEach((e, i) => {
                e.y += e.speed; ctx.fillRect(e.x, e.y, e.w, e.h);
                bullets.forEach((b, bi) => {
                    if(b.x < e.x+e.w && b.x+b.w > e.x && b.y < e.y+e.h && b.y+b.h > e.y) {
                        enemies.splice(i, 1); bullets.splice(bi, 1); score += 50;
                        document.getElementById("score").innerText = "SCORE: " + score;
                    }
                });
                if(e.y > c.height) enemies.splice(i, 1);
            });
            requestAnimationFrame(loop);
        }
        loop();
    </script>
</body>
</html>
"""

CRICKET_GAME_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>🏏 JARVIS PREMIER LEAGUE CRICKET</title>
    <style>
        body { margin: 0; background: #0a192f; color: #fff; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; overflow: hidden; }
        #scoreboard { font-size: 28px; font-weight: bold; margin-bottom: 10px; color: #64ffda; text-shadow: 0 0 10px #64ffda; }
        canvas { background: #1b4332; border: 4px solid #64ffda; border-radius: 12px; box-shadow: 0 0 25px rgba(100, 255, 218, 0.4); }
        #msg { font-size: 22px; font-weight: bold; min-height: 30px; margin-top: 10px; color: #ffd700; text-shadow: 0 0 10px #ffd700; }
        #controls { color: #8892b0; margin-top: 5px; font-size: 16px; }
    </style>
</head>
<body>
    <div id="scoreboard">RUNS: <span id="runs">0</span> | WICKETS: <span id="wickets">0</span>/5 | BALLS: <span id="balls">0</span></div>
    <canvas id="pitch" width="600" height="450"></canvas>
    <div id="msg">READY! Press SPACEBAR or CLICK to Hit the Shot!</div>
    <div id="controls">⚡ Timing is everything: Hit when the ball reaches the White Batting Crease!</div>

    <script>
        const canvas = document.getElementById("pitch");
        const ctx = canvas.getContext("2d");
        let runs = 0, wickets = 0, balls = 0;
        let ball = { x: 300, y: 80, radius: 10, speedY: 4, speedX: 0, active: true, swing: 0 };
        let batsman = { x: 300, y: 380, width: 40, height: 15, swinging: false };
        let gameOver = false;
        let lastShotMsg = "";

        function bowlBall() {
            if (wickets >= 5) {
                gameOver = true;
                document.getElementById("msg").innerText = "🏆 INNINGS OVER! Final Score: " + runs + " Runs. Press (R) to Restart!";
                return;
            }
            ball.x = 300 + (Math.random() * 60 - 30);
            ball.y = 80;
            ball.speedY = 4.5 + Math.random() * 3;
            ball.speedX = (Math.random() * 2 - 1);
            ball.active = true;
            batsman.swinging = false;
        }

        function hitShot() {
            if (gameOver) return;
            if (!ball.active) return;
            batsman.swinging = true;
            balls++;
            document.getElementById("balls").innerText = balls;

            // Check timing relative to crease (y = 380)
            const dist = Math.abs(ball.y - 380);
            if (dist < 25) {
                // Perfect / Good Timing
                const shotType = Math.random();
                let shotRuns = 0;
                if (dist < 10) {
                    shotRuns = (shotType > 0.4) ? 6 : 4;
                    lastShotMsg = "💥 HUGE MAXIMUM! THAT'S A " + shotRuns + "!";
                } else {
                    shotRuns = (shotType > 0.5) ? 4 : (shotType > 0.2 ? 2 : 1);
                    lastShotMsg = "🏏 CRACKING SHOT! " + shotRuns + " Runs!";
                }
                runs += shotRuns;
                document.getElementById("runs").innerText = runs;
                ball.speedY = -12;
                ball.speedX = (Math.random() * 10 - 5);
            } else if (dist < 50) {
                // Edged or 1 Run
                const isOut = Math.random() < 0.4;
                if (isOut) {
                    wickets++;
                    document.getElementById("wickets").innerText = wickets;
                    lastShotMsg = "🔴 OUT! EDGED AND TAKEN BY WICKETKEEPER!";
                } else {
                    runs += 1;
                    document.getElementById("runs").innerText = runs;
                    lastShotMsg = "⚡ Quick Single Taken! 1 Run.";
                }
                ball.speedY = -6;
            } else {
                // Missed
                if (ball.y >= 380) {
                    wickets++;
                    document.getElementById("wickets").innerText = wickets;
                    lastShotMsg = "🔴 BOWLED HIM! CLEAN BOWLED!";
                } else {
                    lastShotMsg = "⚠️ SWUNG TOO EARLY! DOT BALL.";
                }
            }
            document.getElementById("msg").innerText = lastShotMsg;
            ball.active = false;
            setTimeout(bowlBall, 1200);
        }

        window.addEventListener("keydown", (e) => {
            if (e.key === " " || e.key === "Enter") hitShot();
            if ((e.key === "r" || e.key === "R") && gameOver) {
                runs = 0; wickets = 0; balls = 0; gameOver = false;
                document.getElementById("runs").innerText = "0";
                document.getElementById("wickets").innerText = "0";
                document.getElementById("balls").innerText = "0";
                document.getElementById("msg").innerText = "READY! Press SPACEBAR or CLICK to Hit!";
                bowlBall();
            }
        });
        canvas.addEventListener("click", hitShot);

        function draw() {
            // Grass
            ctx.fillStyle = "#1b4332";
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Pitch
            ctx.fillStyle = "#d4a373";
            ctx.fillRect(240, 50, 120, 350);

            // Creases (White Lines)
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 3;
            // Bowling Crease
            ctx.beginPath(); ctx.moveTo(240, 90); ctx.lineTo(360, 90); ctx.stroke();
            // Batting Crease
            ctx.beginPath(); ctx.moveTo(240, 380); ctx.lineTo(360, 380); ctx.stroke();

            // Stumps
            ctx.fillStyle = "#fff";
            [285, 300, 315].forEach(x => {
                ctx.fillRect(x, 400, 6, 15); // Batting stumps
                ctx.fillRect(x, 60, 6, 15);  // Bowling stumps
            });

            // Batsman (Bat & Player)
            ctx.fillStyle = batsman.swinging ? "#ffd700" : "#64ffda";
            ctx.fillRect(batsman.x - 20, batsman.y, batsman.width, batsman.height);
            // Bat
            ctx.fillStyle = "#e76f51";
            if (batsman.swinging) {
                ctx.fillRect(batsman.x + 15, batsman.y - 15, 8, 30);
            } else {
                ctx.fillRect(batsman.x + 15, batsman.y, 8, 25);
            }

            // Ball
            if (ball.y < canvas.height + 20) {
                ctx.fillStyle = "#ff0055";
                ctx.beginPath();
                ctx.arc(ball.x, ball.y, ball.radius, 0, Math.PI * 2);
                ctx.fill();
                ctx.strokeStyle = "#fff";
                ctx.stroke();

                if (ball.active) {
                    ball.y += ball.speedY;
                    ball.x += ball.speedX;
                    if (ball.y > 420) {
                        wickets++;
                        document.getElementById("wickets").innerText = wickets;
                        lastShotMsg = "🔴 BOWLED! Ball went past the bat!";
                        document.getElementById("msg").innerText = lastShotMsg;
                        ball.active = false;
                        setTimeout(bowlBall, 1200);
                    }
                } else {
                    ball.y += ball.speedY;
                    ball.x += ball.speedX;
                }
            }

            requestAnimationFrame(draw);
        }

        bowlBall();
        draw();
    </script>
</body>
</html>
"""


class GameSynthesizer:
    @staticmethod
    def create_and_launch_subway_surfer() -> str:
        """Saves and launches the 3D Subway Surfers runner game in default browser."""
        temp_dir = tempfile.gettempdir()
        html_path = os.path.join(temp_dir, "jarvis_subway_surfers_3d.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(SUBWAY_SURFERS_3D_TEMPLATE)
        webbrowser.open(f"file:///{html_path}")
        return html_path

    @staticmethod
    def create_and_launch_snake() -> str:
        temp_dir = tempfile.gettempdir()
        html_path = os.path.join(temp_dir, "jarvis_snake_game.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(NEON_SNAKE_TEMPLATE)
        webbrowser.open(f"file:///{html_path}")
        return html_path

    @staticmethod
    def create_and_launch_space_shooter() -> str:
        temp_dir = tempfile.gettempdir()
        html_path = os.path.join(temp_dir, "jarvis_space_shooter.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(SPACE_SHOOTER_TEMPLATE)
        webbrowser.open(f"file:///{html_path}")
        return html_path

    @staticmethod
    def create_and_launch_cricket() -> str:
        temp_dir = tempfile.gettempdir()
        html_path = os.path.join(temp_dir, "jarvis_cricket_game.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(CRICKET_GAME_TEMPLATE)
        webbrowser.open(f"file:///{html_path}")
        return html_path

    @staticmethod
    def synthesize_custom_game(prompt: str, ai_brain=None) -> str:
        """Dynamically writes an entire standalone HTML5/JS game based on any user prompt using AI."""
        p_lower = prompt.lower()
        if "cricket" in p_lower:
            return GameSynthesizer.create_and_launch_cricket()
        elif "snake" in p_lower:
            return GameSynthesizer.create_and_launch_snake()
        elif "space" in p_lower or "galaxy" in p_lower or "shooter" in p_lower:
            return GameSynthesizer.create_and_launch_space_shooter()
        elif "subway" in p_lower or "surfer" in p_lower:
            return GameSynthesizer.create_and_launch_subway_surfer()

        # Dynamic AI synthesis with Gemini
        try:
            from google import genai
            api_key = getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
            client = genai.Client(api_key=api_key)
            sys_prompt = "You are an expert game developer. Write a single standalone complete playable HTML5/Canvas/Three.js game with rich graphics and smooth keyboard/mouse controls based on the user's prompt. Output ONLY valid HTML code, with no markdown tags or explanations."
            resp = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=f"Prompt: {prompt}",
                config={"system_instruction": sys_prompt}
            )
            raw_html = resp.text.strip()
            if raw_html.startswith("```html"):
                raw_html = raw_html[7:]
            if raw_html.startswith("```"):
                raw_html = raw_html[3:]
            if raw_html.endswith("```"):
                raw_html = raw_html[:-3]

            temp_dir = tempfile.gettempdir()
            html_path = os.path.join(temp_dir, f"jarvis_custom_game_{int(time.time())}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(raw_html)
            webbrowser.open(f"file:///{html_path}")
            return html_path
        except Exception as e:
            print(f"[synthesize_custom_game error: {e}]")
            return GameSynthesizer.create_and_launch_cricket()


synthesizer = GameSynthesizer()
