package uk.ac.soton.comp1206.game;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import uk.ac.soton.comp1206.component.GameBlock;
import uk.ac.soton.comp1206.component.GameBlockCoordinate;

import java.util.HashSet;
import java.util.Random;
import java.util.Set;

/**
 * The Game class handles the main logic, state and properties of the TetrECS game. Methods to manipulate the game state
 * and to handle actions made by the player should take place inside this class.
 */
public class Game {

    private static final Logger logger = LogManager.getLogger(Game.class);

    /**
     * currentPiece field of type Gamepiece
     * not set to final as it will change
     */

    protected GamePiece currentPiece;

    /**
     * Number of rows
     */
    protected final int rows;

    /**
     * Number of columns
     */
    protected final int cols;

    /**
     * The grid model linked to the game
     */
    protected final Grid grid;

    /**
     * Create a new game with the specified rows and columns. Creates a corresponding grid model.
     * @param cols number of columns
     * @param rows number of rows
     */
    public Game(int cols, int rows) {
        this.cols = cols;
        this.rows = rows;

        //Create a new grid model to represent the game state
        this.grid = new Grid(cols,rows);
    }

    /**
     * Start the game
     */
    public void start() {
        logger.info("Starting game");
        initialiseGame();
    }

    /**
     * Initialise a new game and set up anything that needs to be done at the start
     */
    public void initialiseGame() {
        logger.info("Initialising game");
        setCurrentPiece(spawnPiece());
    }

    /**
     * Handle what should happen when a particular block is clicked
     * @param gameBlock the block that was clicked
     */
    public void blockClicked(GameBlock gameBlock) {
        //Get the position of this block
        int x = gameBlock.getX();
        int y = gameBlock.getY();

        int pieceCentreX = x;
        int pieceCentreY = y;

        grid.playPiece(currentPiece, pieceCentreX, pieceCentreY);

        //Get the new value for this block
        int previousValue = grid.get(x,y);
        int newValue = previousValue + 1;
        if (newValue  > GamePiece.PIECES) {
            newValue = 0;
        }

        //Update the grid with the new value
        grid.set(x,y,newValue);

        afterPiece();

        nextPiece();
    }
    public void afterPiece(){

        Set<GameBlockCoordinate> blocksToBeCleared = new HashSet<>(); // makes use of hashset to store unique values
        // hashset prevents any overlap if a particular block is part of the column and row

        int numRows = grid.getRows();
        int numCols = grid.getCols();

        for (int row = 0; row < numRows; row ++){ // this checks for all the rows
            boolean isRowFull = true; // boolean flag
            for (int col = 0; col < numCols; col++){
                if (grid.get(row, col) == 0){
                    isRowFull = false; // set to false
                    logger.debug("Row is not full");
                    logger.debug("Break from the loop as that row is not fully filled up");
                    break;
                }
            }
            if (isRowFull) { // if row is full
                for (int col = 0; col < numCols; col++)
                    blocksToBeCleared.add(new GameBlockCoordinate(col, row));
            }
        }

        for (int col = 0; col < numCols; col ++){
            boolean isColFull = true;
            for (int row = 0; row < numRows; row ++){
                if (grid.get(col, row) == 0){
                    isColFull = false;
                    break;
                }
            }
            if (isColFull) { // if col is full
                for (int row = 0; row < numRows; row++) {
                    blocksToBeCleared.add(new GameBlockCoordinate(col, row));
                }
            }
        }
        for (GameBlockCoordinate blockCoordinate: blocksToBeCleared) {
            grid.set(blockCoordinate.getX(), blockCoordinate.getY(), 0);
        }
    }

    /**
     * Get the grid model inside this game representing the game state of the board
     * @return game grid model
     */
    public Grid getGrid()   {
        return grid;
    }

    /**
     * Get the number of columns in this game
     * @return number of columns
     */
    public int getCols() {
        return cols;
    }

    /**
     * Get the number of rows in this game
     * @return number of rows
     */
    public int getRows() {
        return rows;
    }

    /**
     * created a random object
     * created a variable to store the random piece to be spawned between 0 and 14 (index for piece starts at 0)
     * @return
     */
    public GamePiece spawnPiece(){
        logger.debug("Spawning a new piece"); // logger to help debug

        Random random = new Random(); // created a random object
        int piece_number = random.nextInt(15); // References: https://www.geeksforgeeks.org/java-util-random-nextint-java/

        GamePiece gamePiece = GamePiece.createPiece(piece_number);
        logger.debug("Spawned piece: {}", gamePiece);

        return gamePiece;
    }

    /**
     * @param currentPiece
     * set method to set piece as the current piece
     */
    public void setCurrentPiece(GamePiece currentPiece) {
        logger.debug("Setting current piece: {}", currentPiece);
        this.currentPiece = currentPiece;
    }

    /**
     * Method that sets the next piece as the current piece
     * replaces the previous current piece
     */
    public void nextPiece(){
        setCurrentPiece(spawnPiece());
    }
}
