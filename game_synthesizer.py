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


synthesizer = GameSynthesizer()
