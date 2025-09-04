/**************************************************************
 * Tic-Tac-Toe (Windows Console)
 * - Human vs Human  (both timed + undo)
 * - Human vs AI     (human timed + undo; AI instant)
 * - AI vs AI        (slow playback)
 *
 * Key features:
 * 1) Human turn has a 10-second timer. If it expires, a random
 *    valid move is placed automatically (and logged as FORCED).
 *
 * 2) After every human move (manual or forced), there is a
 *    5-second window to press 'u' to undo your own last move.
 *    If you undo, the board reprints, and you pick again with
 *    a fresh 10-second timer. Repeat as needed.
 *
 * 3) Every move, undo, forced action, and final result (win /
 *    loss / draw) is logged to the game_N_log.txt file.
 *    N is the game number
 *
 * 4) If you close the program and start the program and play - N will start from 1 and will overwrite the existing game_N_log.txt files
 *
 *
 * 5) Once a game is complete - the program will ask whether you want to play again or not.
 * If you play again - then N will increment by 1 (for game_N_log.txt) file
 *
 * Notes:
 * - This code is Windows-specific because it uses <conio.h>
 *   for non-blocking keyboard reads and Sleep() for delays.
 * - Keep the console focused when playing, so key presses are
 *   detected by _kbhit()/_getch().
 **************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <limits.h>
#include <windows.h>
#include <conio.h>

// ------------------- Constants -------------------

#define EMPTY   ' '   // What an empty cell looks like on the board
#define PLAYER1 'X'   // Player 1 symbol
#define PLAYER2 'O'   // Player 2 symbol

// Human timing controls
#define HUMAN_MOVE_TIME_LIMIT   10   // seconds to make a move
#define HUMAN_UNDO_WINDOW        5   // seconds to press 'u' and undo

// ------------------- Small Structs -------------------

typedef struct {
    int  row;     // 0..2
    int  col;     // 0..2
    char symbol;  // 'X' or 'O'
} Move;

// ------------------- Simple Move Stack (for Undo) -------------------
// We keep a history of moves. Undo only allows removing the very last
// move if it belongs to the player requesting the undo.

#define MAX_MOVES  100

static Move moveStack[MAX_MOVES];
static int  moveTop = -1;  // -1 means empty stack

// Push a move onto the stack when someone makes a move
static void pushMove(int row, int col, char symbol) {
    if (moveTop < MAX_MOVES - 1) {
        moveTop++;
        moveStack[moveTop].row    = row;
        moveStack[moveTop].col    = col;
        moveStack[moveTop].symbol = symbol;
    }
}

// Pop the last move (if any)
static Move popMove(void) {
    Move m = { -1, -1, EMPTY };
    if (moveTop >= 0) {
        m = moveStack[moveTop];
        moveTop--;
    }
    return m;
}

// Peek the last move (without removing)
static Move peekMove(void) {
    Move m = { -1, -1, EMPTY };
    if (moveTop >= 0) {
        m = moveStack[moveTop];
    }
    return m;
}

// ------------------- Score Tracking -------------------

static int humanScoreHvH[2]  = {0, 0}, drawHvH   = 0;
static int humanScoreHvAI[2] = {0, 0}, drawHvAI  = 0;
static int humanScoreAIvAI[2]= {0, 0}, drawAIvAI = 0;

// ------------------- Function Declarations -------------------

// Board management
static void resetBoard(char board[3][3]);
static void printBoard(char board[3][3], int winCells[3][2]);
static int  isMovesLeft(char board[3][3]);

// Game logic
static int  evaluate(char board[3][3], int winCells[3][2],
                     char player1Symbol, char player2Symbol);

static int  minimax(char board[3][3], int depth, int isMax,
                    int alpha, int beta, char aiSymbol, char humanSymbol);

static void findBestMove(char board[3][3], int *bestRow, int *bestCol,
                         char aiSymbol, char humanSymbol);

// Turn helpers (human + AI + undo)
static void getTimedHumanMove(char board[3][3], const char *name,
                              FILE *logFile, char symbol,
                              int timeLimit, int *outRow, int *outCol,
                              int *outForced);

static int  offerUndoWindow(char board[3][3], const char *name,
                            FILE *logFile, char symbol,
                            int seconds, int lastRow, int lastCol);

// Logging and result
static void logMove(FILE *logFile, const char *player,
                    int row, int col, int forced);

static void logUndo(FILE *logFile, const char *player,
                    int row, int col);

static void logResult(FILE *logFile, const char *result,
                      const char *winner);

// Display statistics
static void showStatistics(int mode);

// Utility
static void aiPause(void);

// =================== Main ===================

int main(void) {
    srand((unsigned)time(NULL));  // seed random once

    char playAgain;
    int  mode;
    char playerNames[2][50];      // Names for display + logging

    do {
        // -------- Mode selection --------
        printf("Choose Game Mode:\n");
        printf("  1. Human vs Human\n");
        printf("  2. Human vs AI\n");
        printf("  3. AI vs AI\n");
        printf("Enter 1/2/3: ");
        scanf("%d", &mode);
        while (getchar() != '\n');  // clear leftover newline

        // -------- Setup board + names --------
        char board[3][3];
        resetBoard(board);

        if (mode == 1) { // HvH
            printf("Enter Player 1 name (X): ");
            fgets(playerNames[0], sizeof(playerNames[0]), stdin);
            playerNames[0][strcspn(playerNames[0], "\n")] = '\0';

            printf("Enter Player 2 name (O): ");
            fgets(playerNames[1], sizeof(playerNames[1]), stdin);
            playerNames[1][strcspn(playerNames[1], "\n")] = '\0';
        }
        else if (mode == 2) { // HvAI
            printf("Enter your name: ");
            fgets(playerNames[0], sizeof(playerNames[0]), stdin);
            playerNames[0][strcspn(playerNames[0], "\n")] = '\0';
            strcpy(playerNames[1], "AI");
        }
        else { // AI vs AI
            strcpy(playerNames[0], "AI1");
            strcpy(playerNames[1], "AI2");
        }

        // -------- Who starts? --------
        int turn = rand() % 2;  // 0 = playerNames[0], 1 = playerNames[1]
        int gameOver = 0;
        int winCells[3][2] = { { -1, -1 }, { -1, -1 }, { -1, -1 } };

        // -------- Create a fresh log file --------
        static int gameCount = 0;
        gameCount++;
        char logFileName[64];
        sprintf(logFileName, "game_%d_log.txt", gameCount);
        FILE *logFile = fopen(logFileName, "w");
        if (!logFile) {
            fprintf(stderr, "Failed to open log file. Exiting.\n");
            return 1;
        }
        fprintf(logFile, "Game #%d Log - Mode %d\n\n", gameCount, mode);

        printf("\nTic Tac Toe - Mode %d\n", mode);
        printf("%s goes first!\n\n", turn == 0 ? playerNames[0] : playerNames[1]);

        // Reset move history for this game
        moveTop = -1;

        // =================== Game Loop ===================
        while (!gameOver) {
            printBoard(board, winCells);

            // ---------- Current player's action ----------
            if (mode == 1) {
                // Human vs Human: both sides are human
                const char *currentName = playerNames[turn];
                char currentSymbol      = (turn == 0) ? PLAYER1 : PLAYER2;

                int r, c, forced;
                int undone;

                // Let the current human pick a move, timed.
                do {
                    getTimedHumanMove(board, currentName, logFile,
                                      currentSymbol, HUMAN_MOVE_TIME_LIMIT,
                                      &r, &c, &forced);

                    // After placing, show board + offer 5s undo window.
                    printBoard(board, winCells);

                    undone = offerUndoWindow(board, currentName, logFile,
                                             currentSymbol, HUMAN_UNDO_WINDOW,
                                             r, c);

                    // If undone, we loop and allow them to choose again.
                } while (undone);
            }
            else if (mode == 2) {
                // Human vs AI
                if (turn == 0) {
                    // ----- Human turn (timed + undo window) -----
                    int r, c, forced;
                    int undone;

                    do {
                        getTimedHumanMove(board, playerNames[0], logFile,
                                          PLAYER1, HUMAN_MOVE_TIME_LIMIT,
                                          &r, &c, &forced);

                        printBoard(board, winCells);

                        undone = offerUndoWindow(board, playerNames[0], logFile,
                                                 PLAYER1, HUMAN_UNDO_WINDOW,
                                                 r, c);
                    } while (undone);
                }
                else {
                    // ----- AI turn (no undo) -----
                    int r, c;
                    findBestMove(board, &r, &c, PLAYER2, PLAYER1);
                    board[r][c] = PLAYER2;

                    printf("AI places O at %d,%d\n", r + 1, c + 1);
                    logMove(logFile, "AI", r, c, /*forced=*/0);
                    pushMove(r, c, PLAYER2);

                    aiPause(); // let people watch
                }
            }
            else {
                // AI vs AI (no undo windows, just slow)
                int r, c;
                char aiSymbol = (turn == 0) ? PLAYER1 : PLAYER2;
                char opp      = (turn == 0) ? PLAYER2 : PLAYER1;

                findBestMove(board, &r, &c, aiSymbol, opp);
                board[r][c] = aiSymbol;

                printf("%s places %c at %d,%d\n",
                       playerNames[turn], aiSymbol, r + 1, c + 1);
                logMove(logFile, playerNames[turn], r, c, /*forced=*/0);
                pushMove(r, c, aiSymbol);

                aiPause();
            }

            // ---------- Check for end of game ----------
            int score = evaluate(board, winCells, PLAYER1, PLAYER2);

            if (score == 10) {
                printBoard(board, winCells);
                printf("%s wins!\n\n", playerNames[0]);

                if (mode == 1) humanScoreHvH[0]++;
                if (mode == 2) humanScoreHvAI[0]++;
                if (mode == 3) humanScoreAIvAI[0]++;

                logResult(logFile, "WIN", playerNames[0]);
                gameOver = 1;
            }
            else if (score == -10) {
                printBoard(board, winCells);
                printf("%s wins!\n\n", playerNames[1]);

                if (mode == 1) humanScoreHvH[1]++;
                if (mode == 2) humanScoreHvAI[1]++;
                if (mode == 3) humanScoreAIvAI[1]++;

                logResult(logFile, "WIN", playerNames[1]);
                gameOver = 1;
            }
            else if (!isMovesLeft(board)) {
                printBoard(board, winCells);
                printf("It's a draw!\n\n");

                if (mode == 1) drawHvH++;
                if (mode == 2) drawHvAI++;
                if (mode == 3) drawAIvAI++;

                logResult(logFile, "DRAW", "NONE");
                gameOver = 1;
            }

            // Next player's turn
            turn = 1 - turn;
        }

        fclose(logFile);
        showStatistics(mode);

        // Play another?
        printf("Play again? (y/n): ");
        scanf(" %c", &playAgain);
        while (getchar() != '\n');

    } while (playAgain == 'y' || playAgain == 'Y');

    printf("Thanks for playing!\n");
    return 0;
}

// =================== Board Helpers ===================

// Reset the board to empty before starting a new game
static void resetBoard(char board[3][3]) {

    // Iterate through each row
    for (int r = 0; r < 3; r++)

        // Iterate through each column
        for (int c = 0; c < 3; c++)
            board[r][c] = EMPTY; // set cell to EMPTY character
}


// Pretty print the board and optionally highlight a winning line
static void printBoard(char board[3][3], int winCells[3][2]) {
    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);

    printf("\n");

    // loop over each row
    for (int r = 0; r < 3; r++) {

        // draw horizontal separator
        printf("   +---+---+---+\n");

        // print row number
        printf(" %d |", r + 1);

        // loop over each column
        for (int c = 0; c < 3; c++) {
            int highlight = 0; // Flag to indicate if this cell is part of winning line

            // check if this cell is in winCells (winning combination)
            for (int k = 0; k < 3; k++) {
                if (winCells[k][0] == r && winCells[k][1] == c) {
                    highlight = 1;
                }
            }

            // set color for cell based on content or highlight
            if (highlight)
                SetConsoleTextAttribute(hConsole, FOREGROUND_GREEN | FOREGROUND_INTENSITY);
            else if (board[r][c] == PLAYER1)
                SetConsoleTextAttribute(hConsole, FOREGROUND_RED | FOREGROUND_INTENSITY);
            else if (board[r][c] == PLAYER2)
                SetConsoleTextAttribute(hConsole, FOREGROUND_BLUE | FOREGROUND_INTENSITY);
            else
                SetConsoleTextAttribute(hConsole, FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE);

            // print the cell content
            printf(" %c ", board[r][c]);

            // reset color to default
            SetConsoleTextAttribute(hConsole, FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE);
            printf("|"); // column separator
        }
        // end of row
        printf("\n");
    }

    // draw bottom border of the board
    printf("   +---+---+---+\n");
    printf("     1   2   3\n\n"); // column numbers for reference
}


// Check if there are any empty cells left on the board
// Returns 1 if at least one empty cell exists, 0 if board is full
static int isMovesLeft(char board[3][3]) {
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < 3; c++)
            if (board[r][c] == EMPTY)
                return 1; // found an empty cell
    return 0; // no empty cell remains
}

// =================== Game Logic ===================

// Evaluate: +10 if PLAYER1 wins, -10 if PLAYER2 wins, 0 otherwise
static int evaluate(char board[3][3], int winCells[3][2],
                    char player1Symbol, char player2Symbol) {

    // check all rows for a winning line
    for (int r = 0; r < 3; r++) {
        if (board[r][0] != EMPTY &&
            board[r][0] == board[r][1] &&
            board[r][1] == board[r][2]) {
            // save winning cell coordinates
            for (int k = 0; k < 3; k++) { winCells[k][0] = r; winCells[k][1] = k; }

            // return +10 or -10 depending on who won
            return (board[r][0] == player1Symbol) ? 10 : -10;
        }
    }

    // Check all columns for a winning line
    for (int c = 0; c < 3; c++) {
        if (board[0][c] != EMPTY &&
            board[0][c] == board[1][c] &&
            board[1][c] == board[2][c]) {
            for (int k = 0; k < 3; k++) { winCells[k][0] = k; winCells[k][1] = c; }
            return (board[0][c] == player1Symbol) ? 10 : -10;
        }
    }

    // Check Main diagonal (top-left to bottom-right)
    if (board[0][0] != EMPTY &&
        board[0][0] == board[1][1] &&
        board[1][1] == board[2][2]) {
        for (int k = 0; k < 3; k++) { winCells[k][0] = k; winCells[k][1] = k; }
        return (board[0][0] == player1Symbol) ? 10 : -10;
    }

    // Check anti-diagonal (top-right to bottom-left)
    if (board[0][2] != EMPTY &&
        board[0][2] == board[1][1] &&
        board[1][1] == board[2][0]) {
        for (int k = 0; k < 3; k++) { winCells[k][0] = k; winCells[k][1] = 2 - k; }
        return (board[0][2] == player1Symbol) ? 10 : -10;
    }

    return 0; // no winner
}


// Minimax algorithm with alpha-beta pruning
// - is Max = 1 for maximising (AI), 0 for minimizing (human)
// - alpha, beta are pruning parameters
// returns the best score of the current board state

static int minimax(char board[3][3], int depth, int isMax,
                   int alpha, int beta, char aiSymbol, char humanSymbol) {

    int dummy[3][2] = { { -1, -1 }, { -1, -1 }, { -1, -1 } }; // we ignore actual winning cells here
    int score = evaluate(board, dummy, aiSymbol, humanSymbol);

    // if terminal state reached, return score adjusted by depth
    if (score == 10)  return score - depth; // AI win
    if (score == -10) return score + depth; // Human win
    if (!isMovesLeft(board)) return 0; // Draw

    if (isMax) {
        int best = INT_MIN; // start with worst case for maximiser

        // try all empty cells
        for (int r = 0; r < 3; r++) {
            for (int c = 0; c < 3; c++) {
                if (board[r][c] == EMPTY) {
                    board[r][c] = aiSymbol; // simulate move
                    int val = minimax(board, depth + 1, 0, alpha, beta, aiSymbol, humanSymbol);
                    board[r][c] = EMPTY; // undo move

                    if (val > best) best = val; // update best value
                    if (best > alpha) alpha = best; // update alpha
                    if (beta <= alpha) break; // prune
                }
            }
        }
        return best;
    }
    else {
        int best = INT_MAX; // worst case for minimizer

        // try all empty cells
        for (int r = 0; r < 3; r++) {
            for (int c = 0; c < 3; c++) {
                if (board[r][c] == EMPTY) {
                    board[r][c] = humanSymbol; // simulate human move
                    int val = minimax(board, depth + 1, 1, alpha, beta, aiSymbol, humanSymbol);
                    board[r][c] = EMPTY; // undo move

                    if (val < best) best = val; // update best value
                    if (best < beta) beta = best; // update beta
                    if (beta <= alpha) break; // prune
                }
            }
        }
        return best;
    }
}


// Pick the best move for the AI using minimax
static void findBestMove(char board[3][3], int *bestRow, int *bestCol,
                         char aiSymbol, char humanSymbol) {

    int bestVal = INT_MIN; // start with the worst value for AI
    *bestRow = -1; // initialize row
    *bestCol = -1; // initialize column

    // check all empty cells
    for (int r = 0; r < 3; r++) {
        for (int c = 0; c < 3; c++) {
            if (board[r][c] == EMPTY) {
                board[r][c] = aiSymbol; // try AI move here
                int moveVal = minimax(board, 0, 0, INT_MIN, INT_MAX, aiSymbol, humanSymbol);
                board[r][c] = EMPTY; // undo move

                // update best move if this move is better
                if (moveVal > bestVal) {
                    bestVal  = moveVal;
                    *bestRow = r;
                    *bestCol = c;
                }
            }
        }
    }
}

// =================== Human Turn (timed) ===================

/*
 * getTimedHumanMove
 * - Lets a human enter "row col" within 'timeLimit' seconds.
 * - If time expires, chooses a random legal move (forced=1).
 * - On success, updates board, logs, pushes move to stack,
 *   and returns the chosen (row,col) + forced flag.
 *
 * Input is non-blocking: user types digits and presses Enter.
 * If you type nothing and wait, the system will force a move.
 */
static void getTimedHumanMove(char board[3][3], const char *name,
                              FILE *logFile, char symbol,
                              int timeLimit, int *outRow, int *outCol,
                              int *outForced) {

    int  r = -1, c = -1; // initialize row and column
    int  forced = 0; // flag to indicate if move is forced

    char input[32]; // buffer to store typed input
    int  idx = 0; // current index in input buffer

    clock_t start = clock(); // start timer

    printf("%s (%c), you have %d seconds. Enter row col: ",
           name, symbol, timeLimit);

    fflush(stdout); // ensure prompt is printed immediately

    while (1) {
        // Check elapsed time
        double elapsed = (double)(clock() - start) / CLOCKS_PER_SEC;
        if (elapsed >= timeLimit) {
            // Timer expired -> choose random empty cell
            int empty[9][2], count = 0;
            for (int i = 0; i < 3; i++)
                for (int j = 0; j < 3; j++)
                    if (board[i][j] == EMPTY) {
                        empty[count][0] = i;
                        empty[count][1] = j;
                        count++;
                    }

            if (count > 0) {
                int pick = rand() % count; // pick a random empty cell
                r = empty[pick][0];
                c = empty[pick][1];

                board[r][c] = symbol; // place symbol on board
                pushMove(r, c, symbol); // record move in stack

                printf("\n⏰ Time up! A random move was made for %s at %d,%d.\n",
                       name, r + 1, c + 1);

                logMove(logFile, name, r, c, /*forced=*/1); // log forced move
                forced = 1;
            }
            *outRow = r;
            *outCol = c;
            *outForced = forced;
            return; // exit function after forced move
        }

        // If user typed something
        if (_kbhit()) {
            char ch = _getch(); // get key press without echo

            if (ch == '\r') {
                // ENTER key -> parse input
                input[idx] = '\0'; // null-terminate string

                if (sscanf(input, "%d %d", &r, &c) == 2) {
                    // check if move is valid (within board & empty)
                    if (r >= 1 && r <= 3 && c >= 1 && c <= 3 &&
                        board[r - 1][c - 1] == EMPTY) {

                        board[r - 1][c - 1] = symbol; // place symbol
                        pushMove(r - 1, c - 1, symbol); // record move

                        logMove(logFile, name, r - 1, c - 1, /*forced=*/0); //log
                        *outRow = r - 1;
                        *outCol = c - 1;
                        *outForced = 0;
                        return; // move completed
                    }
                    else {
                        printf("\nInvalid/occupied cell. Try again: ");
                        idx = 0; // reset input buffer
                    }
                }
                else {
                    printf("\nInvalid input. Use 'row col' (e.g., 1 3). Try again: ");
                    idx = 0;
                }
            }
            else if (ch == '\b' && idx > 0) {
                // BACKSPACE: remove last char from buffer
                idx--;
                printf("\b \b"); // erase char visually
            }
            else if (idx < (int)sizeof(input) - 1) {
                // Normal character -> add to buffer
                input[idx++] = ch;
                putchar(ch); // echo character
            }
        }
    }
}

/*
 * offerUndoWindow
 * - After a human places a move at (lastRow,lastCol), wait 'seconds'
 *   listening for 'u' (or 'U') to undo.
 * - You can only undo your own immediate last move.
 * - If undone, clear the cell, log it, reprint the board, and return 1.
 * - If time passes with no 'u', return 0.
 */
static int offerUndoWindow(char board[3][3], const char *name,
                           FILE *logFile, char symbol,
                           int seconds, int lastRow, int lastCol) {
    printf("You have %d seconds to press 'u' to undo your last move...", seconds);
    fflush(stdout);

    clock_t start = clock(); // start undo timer

    while (1) {
        double elapsed = (double)(clock() - start) / CLOCKS_PER_SEC;
        if (elapsed >= seconds) {
            printf(" continuing...\n"); // time is over - no undo
            return 0; // not undone
        }

        // check if user pressed a key
        if (_kbhit()) {
            char ch = _getch();
            if (ch == 'u' || ch == 'U') {
                // Only allow if the last move belongs to this player
                Move last = peekMove(); // get last move

                // only allow undo if last move belongs to this player
                if (last.row == lastRow && last.col == lastCol && last.symbol == symbol) {
                    (void)popMove();                 // remove from move history
                    board[lastRow][lastCol] = EMPTY; // clear the board cell
                    logUndo(logFile, name, lastRow, lastCol); // log undo

                    printf("\n%s undid the move at %d,%d.\n", name, lastRow + 1, lastCol + 1);

                    while (_kbhit()) _getch(); // clear extra key presses


                    int dummy[3][2] = { { -1, -1 }, { -1, -1 }, { -1, -1 } };
                    printBoard(board, dummy); // reprint updated board
                    return 1; // Move undone
                } else {
                    printf("\nYou can only undo your own last move right now.\n");
                    return 0; // cannot undo anything else here
                }
            }
        }

        // Tiny sleep to avoid busy-waiting (keeps CPU cool)
        Sleep(10); // small sleep to reduce CPU usage
    }
}

// =================== Logging ===================

// log a normal or forced move to the log file
// Log a move; if forced==1, mention it explicitly
static void logMove(FILE *logFile, const char *player,
                    int row, int col, int forced) {
    if (forced)
        fprintf(logFile, "%s -> (%d,%d)  [FORCED by timeout]\n", player, row + 1, col + 1);
    else
        fprintf(logFile, "%s -> (%d,%d)\n", player, row + 1, col + 1);
}

// Log an undo action to the log file
static void logUndo(FILE *logFile, const char *player, int row, int col) {
    fprintf(logFile, "%s UNDID move at (%d,%d)\n", player, row + 1, col + 1);
}

// Log the final result of the game
static void logResult(FILE *logFile, const char *result, const char *winner) {
    if (strcmp(result, "DRAW") == 0) {
        fprintf(logFile, "\nRESULT: DRAW\n");
    } else if (strcmp(result, "WIN") == 0) {
        fprintf(logFile, "\nRESULT: %s WINS\n", winner);
    } else {
        fprintf(logFile, "\nRESULT: %s\n", result);
    }
}

// =================== Stats Display ===================

// Show statistics for all completed games in the current mode
static void showStatistics(int mode) {
    printf("\n=== Game Statistics ===\n");

    if (mode == 1) { // human vs human
        int total = humanScoreHvH[0] + humanScoreHvH[1] + drawHvH;
        printf("Human vs Human:\n");
        printf("  Player 1 Wins: %d (%.1f%%)\n",
               humanScoreHvH[0], total ? 100.0 * humanScoreHvH[0] / total : 0.0);
        printf("  Player 2 Wins: %d (%.1f%%)\n",
               humanScoreHvH[1], total ? 100.0 * humanScoreHvH[1] / total : 0.0);
        printf("  Draws: %d (%.1f%%)\n\n",
               drawHvH,          total ? 100.0 * drawHvH          / total : 0.0);
    }

    if (mode == 2) { // Human vs AI
        int total = humanScoreHvAI[0] + humanScoreHvAI[1] + drawHvAI;
        printf("Human vs AI:\n");
        printf("  Human Wins: %d (%.1f%%)\n",
               humanScoreHvAI[0], total ? 100.0 * humanScoreHvAI[0] / total : 0.0);
        printf("  AI Wins: %d (%.1f%%)\n",
               humanScoreHvAI[1], total ? 100.0 * humanScoreHvAI[1] / total : 0.0);
        printf("  Draws: %d (%.1f%%)\n\n",
               drawHvAI,          total ? 100.0 * drawHvAI          / total : 0.0);
    }

    if (mode == 3) { // AI vs AI
        int total = humanScoreAIvAI[0] + humanScoreAIvAI[1] + drawAIvAI;
        printf("AI vs AI:\n");
        printf("  AI1 Wins: %d (%.1f%%)\n",
               humanScoreAIvAI[0], total ? 100.0 * humanScoreAIvAI[0] / total : 0.0);
        printf("  AI2 Wins: %d (%.1f%%)\n",
               humanScoreAIvAI[1], total ? 100.0 * humanScoreAIvAI[1] / total : 0.0);
        printf("  Draws: %d (%.1f%%)\n\n",
               drawAIvAI,          total ? 100.0 * drawAIvAI          / total : 0.0);
    }
}

// =================== Utility ===================

// Small delay so people can follow AI vs AI
static void aiPause(void) {
    Sleep(800); // milliseconds
}