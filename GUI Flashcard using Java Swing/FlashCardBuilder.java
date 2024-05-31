package com.flashcard;

import javax.swing.*;
import java.awt.*;
import java.util.ArrayList;

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
        frame.setResizable(false);

        // Create main JPanel
        JPanel mainPanel = new JPanel();
        mainPanel.setBackground(Color.GREEN); // Set background color

        // Set font
        Font font = new Font("Arial", Font.PLAIN, 18);

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
}
