# Arow: A Top-Down Arena Shooter

<img width="1920" height="620" alt="Untitled594" src="https://github.com/user-attachments/assets/4d435c6f-d6d7-45f9-826d-205542872535" />

A top-down arena shooter built on Pygame. This project serves as a comprehensive template demonstrating complex game mechanics, including procedural waves, diverse enemy types, power-ups, smooth camera controls, and a custom UI.

https://calistainteractive.itch.io/arow-but-better

## Features

*   **Procedural Wave System:** Enemies spawn in increasing numbers and diversity across continuous waves.
*   **Diverse Enemy Types:** Includes **Chargers** (fast, melee), **Shooters** (ranged), and **Snipers** (delayed, high-damage beam attacks), as well as challenging **Boss** enemies.
*   **Boss Fights:** Multi-stage bosses with complex attack patterns (nova, triple laser beams, specialized bullets) that scale difficulty as their health decreases.
*   **Power-Up System:** Collectable items including **Health**, **Dash Charge**, **Rapid Fire** (temporary buff), and the powerful **Plasma Ball** (AOE explosion).
*   **Smooth Camera System:** Implements optional smooth camera following (`smooth_camera_follow`) and visual **Screen Shake** for impactful events (dashing, taking damage, explosions).
*   **Full UI and Menu System:** Includes a main menu with customizable start options, an in-game HUD (Health, Ammo, Dash Charges, Score, Wave Tracker), and a Pause Menu.
*   **Custom Game Settings:** Players can use the menu to start the game at a custom wave and enable specific power-ups from the start for testing.
*   **Splash Screen:** Features an introductory splash screen with fade-in/out effects.

## Getting Started

### Prerequisites

You will need Python 3 and the following libraries. The inclusion of `PIL` (Pillow) suggests possible use of image manipulation features not fully exposed in the current code but part of the setup.

```bash
pip install pygame pillow
