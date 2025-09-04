# 🎮 Tic-Tac-Toe (C Console Application)

A **Tic-Tac-Toe game** implemented in **C**, demonstrating advanced console programming, AI algorithms, and file logging. Designed for Windows console, this project showcases core C programming skills, recursion, data structures, and file I/O.

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
