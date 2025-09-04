# 🎮 Tic-Tac-Toe (C Console Application)

A **Tic-Tac-Toe game** implemented in **C**, demonstrating advanced console programming, AI algorithms, and file logging. Designed for Windows console, this project showcases core C programming skills, recursion, data structures, and file I/O.

---

## 💡 Project Inspiration

During **COMP2208 Intelligent Systems** at the **University of Southampton**, I learned about the **Minimax algorithm and alpha-beta pruning**. Inspired by this, I decided to create my own Tic-Tac-Toe game to apply these concepts practically, including human vs AI gameplay and logging features.

---

## 🛠️ Tech Stack

- 🖥️ **Language:** C (C99 standard)  
- 💻 **Platform:** Windows  
- 📚 **Libraries:** 
  - 📝 `<stdio.h>` – Input/Output  
  - 🔢 `<stdlib.h>` – Memory management & random numbers  
  - 🧵 `<string.h>` – String manipulation  
  - ⏱️ `<time.h>` – Timer functionality  
  - 🎮 `<conio.h>` – Non-blocking keyboard input  
  - 🪟 `<windows.h>` – Sleep & console text attributes  

---

## ⚡ Features

1. 🎭 **Game Modes**
   - 👥 Human vs Human (both timed + undo)
   - 🤖 Human vs AI (human timed + undo; AI instant)
   - 🤖🤖 AI vs AI (slow playback for watching AI play)

2. ⏰ **Human Move Timer**
   - 10-second timer per human turn
   - ⏱️ If time expires, a random valid move is automatically placed

3. 🔄 **Undo Functionality**
   - 5-second window after every human move to press 'u' to undo
   - ✅ Undo works only on the player's last move

4. 🤖 **AI Logic**
   - Uses **Minimax algorithm with alpha-beta pruning** for optimal moves
   - 🧠 AI evaluates board positions recursively and prunes unnecessary branches for efficiency

5. 📝 **Logging**
   - Every move, undo, forced action, and final result is logged in `game_N_log.txt`
   - 🆕 N increments for each game played

6. 📊 **Statistics**
   - Tracks wins, losses, and draws for all game modes
   - 📈 Displays percentage statistics after each game

---

## 📂 Project Structure

- 📝 `main.c` – Contains the complete source code to run the Tic-Tac-Toe game  
- 📂 **Example Game Logs** – Logs generated after playing individual games:
  - 📄 `game_1_log.txt` – Example of Game 1
  - 📄 `game_2_log.txt` – Example of Game 2
  - 📄 `game_8_log.txt` – Example of Game 8

---

This project highlights your ability to code in **C**, implement algorithms like **Minimax with alpha-beta pruning**, handle **timers and undo functionality**, and perform **file I/O for logging game states**.
