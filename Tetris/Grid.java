package uk.ac.soton.comp1206.game;

import javafx.beans.property.IntegerProperty;
import javafx.beans.property.SimpleIntegerProperty;
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;


/**
 * The Grid is a model which holds the state of a game board. It is made up of a set of Integer values arranged in a 2D
 * arrow, with rows and columns.
 *
 * Each value inside the Grid is an IntegerProperty can be bound to enable modification and display of the contents of
 * the grid.
 *
 * The Grid contains functions related to modifying the model, for example, placing a piece inside the grid.
 *
 * The Grid should be linked to a GameBoard for it's display.
 */
public class Grid {

    private static final Logger logger = LogManager.getLogger(Grid.class);


    /**
     * The number of columns in this grid
     */
    private final int cols;

    /**
     * The number of rows in this grid
     */
    private final int rows;

    /**
     * The grid is a 2D arrow with rows and columns of SimpleIntegerProperties.
     */
    private final SimpleIntegerProperty[][] grid;

    /**
     * Create a new Grid with the specified number of columns and rows and initialise them
     * @param cols number of columns
     * @param rows number of rows
     */
    public Grid(int cols, int rows) {
        this.cols = cols;
        this.rows = rows;

        //Create the grid itself
        grid = new SimpleIntegerProperty[cols][rows];

        //Add a SimpleIntegerProperty to every block in the grid
        for(var y = 0; y < rows; y++) {
            for(var x = 0; x < cols; x++) {
                grid[x][y] = new SimpleIntegerProperty(0);
            }
        }
    }

    /**
     *
     * @param piece
     * @param x
     * @param y
     * gets the blocks for a particular game piece
     * gets its length and width
     * iterates through both the dimensions of the piece
     * checks if the calculated x and y coordinates are within the grid
     * checks if the coordinates are not occupied by another piece
     * @return a boolean value if the piece can be played or not
     */

    // a game piece consists of blocks each taking 1/25th of the space for a 5 x 5 grid
    public boolean canPlayPiece(GamePiece piece, int x, int y){ // method takes in 3 parameters
        logger.debug("Checking if the piece is playable from its centre");
        int[][] pieceBlocks = piece.getBlocks(); // gets the blocks for that particular piece
        int pieceWidth = pieceBlocks.length; // gets the length of the blocks
        int pieceHeight = pieceBlocks[0].length; // Reference: https://runestone.academy/ns/books/published/csawesome/Unit8-2DArray/a2dSummary.html

        for (int width = 0; width < pieceWidth; width++){ // iterating through the width of the game piece
            for (int height = 0; height < pieceHeight; height++){ // iterating through the height of the game piece
                // x and y are the centre of the piece
                int gridCoordinateX = x - pieceWidth / 2 + width;
                int gridCoordinateY = y - pieceHeight / 2 + height;

                if (gridCoordinateX < 0){ // if the x coordinate is outside the grid
                    return false;
                } else if (gridCoordinateY < 0){ // if the y coordinate is outside the grid
                    return false;
                } else if (gridCoordinateX >= cols){ // indexing starts at 0
                    return false;
                } else if (gridCoordinateY >= rows ){ // indexing starts at 0
                    return false;
                }
                // this code below checks if a block within a piece is occupied and if the grid coordinate is also occupied
                // if they are both occupied, then it should return false as you cannot place a block of the game piece in an occupied space within the grid
                if (pieceBlocks[width][height] == 1 && grid[gridCoordinateX][gridCoordinateY].get() != 0){
                    return false;
                }
            }
        }
        return true; // returns true if the piece can be put in the grid where none of the spaces are occupied
    }

    /**
     *
     * @param piece
     * @param x
     * @param y
     * calls the canPlayPiece method
     * if the piece is playable it iterates through the piece blocks
     * calculates the respective x and y coordinates for each of the game blocks
     * sets the x and y coordinates
     */
    public void playPiece(GamePiece piece, int x, int y) {
        if (canPlayPiece(piece, x, y)) {
            int[][] pieceBlocks = piece.getBlocks();
            int pieceWidth = pieceBlocks.length;
            int pieceHeight = pieceBlocks[0].length;

            for (int width = 0; width < pieceWidth; width++) {
                for (int height = 0; height < pieceHeight; height++) {
                    int gridX = x - pieceWidth / 2 + width;
                    int gridY = y - pieceHeight / 2 + height;
                    set(gridX, gridY, piece.getValue()); // sets the coordinates
                }
            }
        }
    }

    /**
     * Get the Integer property contained inside the grid at a given row and column index. Can be used for binding.
     * @param x column
     * @param y row
     * @return the IntegerProperty at the given x and y in this grid
     */
    public IntegerProperty getGridProperty(int x, int y) {
        return grid[x][y];
    }

    /**
     * Update the value at the given x and y index within the grid
     * @param x column
     * @param y row
     * @param value the new value
     */
    public void set(int x, int y, int value) {
        grid[x][y].set(value);
    }

    /**
     * Get the value represented at the given x and y index within the grid
     * @param x column
     * @param y row
     * @return the value
     */
    public int get(int x, int y) {
        try {
            //Get the value held in the property at the x and y index provided
            return grid[x][y].get();
        } catch (ArrayIndexOutOfBoundsException e) {
            //No such index
            return -1;
        }
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

}
