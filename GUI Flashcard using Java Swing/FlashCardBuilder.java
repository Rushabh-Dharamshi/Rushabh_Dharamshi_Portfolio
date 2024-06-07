package com.flashcard;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.*;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.Scanner;

public class FlashCardBuilder {
    private JTextArea question; // Text area for entering the question
    private JTextArea answer;   // Text area for entering the answer
    private ArrayList<FlashCard> flashCardList; // List to store flashcards
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
        JMenuItem loadMenuItem = new JMenuItem("LOAD");

        // added menu items to the file menu
        fileMenu.add(newMenuItem);
        fileMenu.add(saveMenuItem);
        fileMenu.add(loadMenuItem);

        // add file menu to the menu bar
        menuBar.add(fileMenu);
        frame.setJMenuBar(menuBar);

        // event listeners
        newMenuItem.addActionListener(new NewMenuItemListener());
        saveMenuItem.addActionListener(new SaveMenuListener());
        loadMenuItem.addActionListener(new LoadMenuItemListener());

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

            System.out.println("Size of arraylist: " + flashCardList.size());
        }
    }

    private void clearFlashCard(){
        question.setText("");
        answer.setText("");
        question.requestFocus();
    }

    private void saveFile(File chosenFile){
        try {
            BufferedWriter writer = new BufferedWriter(new FileWriter(chosenFile));
            for (FlashCard card : flashCardList) {
                writer.write(card.getQuestion() + "/");
                writer.write(card.getAnswer() + "\n");
            }
            writer.close();
        } catch (Exception e) {
            System.out.println("Couldn't write to file");
            e.printStackTrace();
        }
    }

    private void loadFile(File chosenFile){
        try {
            Scanner reader = new Scanner(chosenFile);
            flashCardList.clear();
            while (reader.hasNextLine()) {
                String[] cardData = reader.nextLine().split("/");
                FlashCard card = new FlashCard(cardData[0], cardData[1]);
                flashCardList.add(card);
            }
            reader.close();
        } catch (Exception e) {
            System.out.println("Couldn't read from file");
            e.printStackTrace();
        }
    }

    class NewMenuItemListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            flashCardList.clear();
            clearFlashCard();
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

    class LoadMenuItemListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            JFileChooser fileOpen = new JFileChooser();
            fileOpen.showOpenDialog(frame);
            loadFile(fileOpen.getSelectedFile());

            System.out.println("Load Menu Clicked");
        }
    }
}
