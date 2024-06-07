package com.flashcard;
import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.Iterator;

public class FlashCardBuilder {
    private JTextArea question; // Text area for entering the question
    private JTextArea answer;   // Text area for entering the answer
    private ArrayList<FlashCard> flashCardList; // List to store flashcards (not currently used)
    private JFrame frame;   // Main window frame

    // Constructor
    public FlashCardBuilder() {
        // Create main JFrame
        frame = new JFrame("Flash Card");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE); // Exit application when frame is closed
        frame.setResizable(false); // frame is not resizable

        // Create main JPanel
        JPanel mainPanel = new JPanel();
        mainPanel.setBackground(Color.GREEN); // Set background color to green

        // create a font object
        // font size is 18
        // font is changed from plain to bold
        Font font = new Font("Arial", Font.BOLD, 18);

        // Create JTextArea for entering question
        question = new JTextArea(8, 20);
        question.setLineWrap(true); // Enable line wrapping
        question.setWrapStyleWord(true); // Wrap words
        question.setFont(font); // Set font

        // Create JScrollPane for question JTextArea
        JScrollPane qScrollPane = new JScrollPane(question);
        qScrollPane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_ALWAYS);
        qScrollPane.setHorizontalScrollBarPolicy(ScrollPaneConstants.HORIZONTAL_SCROLLBAR_NEVER);

        // Create JTextArea for entering answer
        answer = new JTextArea(8, 20);
        answer.setLineWrap(true); // Enable line wrapping
        answer.setWrapStyleWord(true); // Wrap words
        answer.setFont(font); // Set font

        // Create JScrollPane for answer JTextArea
        JScrollPane answerScrollPane = new JScrollPane(answer);
        answerScrollPane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_ALWAYS);
        answerScrollPane.setHorizontalScrollBarPolicy(ScrollPaneConstants.HORIZONTAL_SCROLLBAR_NEVER);

        flashCardList = new ArrayList<FlashCard>();

        // Create JButton for moving to the next card
        JButton nextButton = new JButton("Next Card");

        // Create JLabels for "Question" and "Answer"
        JLabel questionJLabel = new JLabel("Question");
        JLabel answerJLabel = new JLabel("Answer");


        // Add components to mainPanel
        mainPanel.add(questionJLabel);
        mainPanel.add(qScrollPane);
        mainPanel.add(answerJLabel);
        mainPanel.add(answerScrollPane);
        mainPanel.add(nextButton);
        nextButton.addActionListener(new NextCardListener());

        JMenuBar menuBar = new JMenuBar();

        JMenu fileMenu = new JMenu("File");
        JMenuItem newMenuItem = new JMenuItem("NEW");
        JMenuItem saveMenuItem = new JMenuItem("SAVE");

        // added menu items to the file menu
        fileMenu.add(newMenuItem);
        fileMenu.add(saveMenuItem);

        // add file menu to the menu bar
        menuBar.add(fileMenu);
        frame.setJMenuBar(menuBar);

        // event listeners
        newMenuItem.addActionListener(new NewMenuItemListener());
        saveMenuItem.addActionListener(new SaveMenuListener());


        // Add mainPanel to the center of the frame
        frame.getContentPane().add(BorderLayout.CENTER, mainPanel);
        frame.setSize(400, 500); // Set frame size
        frame.setVisible(true); // Set frame visible
    }

    // Main method to start the application
    public static void main(String[] args){
        SwingUtilities.invokeLater(new Runnable() {
            @Override
            public void run() {
                new FlashCardBuilder(); // Create an instance of FlashCardBuilder
            }
        });
    }

    class NextCardListener implements ActionListener {

        @Override
        public void actionPerformed(ActionEvent e) {
            System.out.println("Button Clicked");

            FlashCard flashcard = new FlashCard(question.getText(), answer.getText());
            flashCardList.add(flashcard);
            clearFlashCard();

            System.out.println("Size of arraylist" + flashCardList.size());


        }
    }

    private void clearFlashCard(){
        question.setText("Write another Question here");
        answer.setText("Write another answer here");
        question.requestFocus();
    }

    private void saveFile(File chosenFile){
        try {
            BufferedWriter writer = new BufferedWriter(new FileWriter(chosenFile));
            Iterator<FlashCard> cardIterator = flashCardList.iterator();
            while (cardIterator.hasNext()) {
                FlashCard card = cardIterator.next();
                writer.write(card.getQuestion() + "/");
                writer.write(card.getAnswer() + "\n");
            }
            writer.close();



        } catch (Exception e) {
            System.out.println("Couldn't write to file");
            e.printStackTrace();

        }
    }

    class NewMenuItemListener implements ActionListener {

        @Override
        public void actionPerformed(ActionEvent e) {
            System.out.println("New Menu Clicked");
        }
    }
    class SaveMenuListener implements ActionListener {

        @Override
        public void actionPerformed(ActionEvent e) {
            FlashCard card = new FlashCard(question.getText(), answer.getText());
            flashCardList.add(card);

            JFileChooser fileSave = new JFileChooser();
            fileSave.showSaveDialog(frame);
            saveFile(fileSave.getSelectedFile());

            System.out.println("Save Menu Clicked");
        }
    }
}