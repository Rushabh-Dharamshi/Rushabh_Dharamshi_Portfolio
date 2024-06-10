package com.flashcard;

import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.*;
import java.util.ArrayList;
import java.util.Iterator;

public class FlashCardPlayer {
    private JTextArea display;
    private JTextArea userAnswer;
    private ArrayList<FlashCard> cardList;
    private Iterator<FlashCard> cardIterator;
    private FlashCard currentCard;
    private JFrame frame;
    private boolean isShowAnswer;
    private JButton showAnswer;
    private JButton checkAnswer;
    private JLabel scoreLabel;
    private int totalScore;
    private int highScore;
    private ArrayList<FlashCard> incorrectlyAnsweredQuestions;

    public FlashCardPlayer() {
        frame = new JFrame("Flash Card Player");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setResizable(false);

        Font mFont = new Font("Arial", Font.BOLD, 18);

        JPanel mainPanel = new JPanel(new GridBagLayout());
        GridBagConstraints c = new GridBagConstraints();
        c.fill = GridBagConstraints.BOTH;
        c.insets = new Insets(10, 10, 10, 10);

        display = new JTextArea(2, 10);
        display.setLineWrap(true);
        display.setWrapStyleWord(true);
        display.setFont(mFont);
        JScrollPane qJScrollPane = new JScrollPane(display);
        qJScrollPane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_ALWAYS);
        qJScrollPane.setHorizontalScrollBarPolicy(ScrollPaneConstants.HORIZONTAL_SCROLLBAR_NEVER);

        userAnswer = new JTextArea(2, 10);
        userAnswer.setLineWrap(true);
        userAnswer.setWrapStyleWord(true);
        userAnswer.setFont(mFont);
        JScrollPane aJScrollPane = new JScrollPane(userAnswer);
        aJScrollPane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_ALWAYS);
        aJScrollPane.setHorizontalScrollBarPolicy(ScrollPaneConstants.HORIZONTAL_SCROLLBAR_NEVER);

        showAnswer = new JButton("Next");
        showAnswer.addActionListener(new NextCardListener());
        checkAnswer = new JButton("Check Answer");
        checkAnswer.addActionListener(new CheckAnswerListener());

        scoreLabel = new JLabel("Score: 0");
        totalScore = 0;
        highScore = readHighScore();
        updateScoreLabel();

        c.gridx = 0;
        c.gridy = 0;
        c.gridwidth = 2;
        c.weightx = 1;
        c.weighty = 0.5;
        mainPanel.add(qJScrollPane, c);

        c.gridx = 0;
        c.gridy = 1;
        c.gridwidth = 1;
        c.weightx = 0;
        c.weighty = 0;
        c.anchor = GridBagConstraints.WEST;
        mainPanel.add(new JLabel("Your Answer:"), c);

        c.gridx = 1;
        c.gridy = 1;
        c.weightx = 1;
        c.weighty = 0.5;
        c.anchor = GridBagConstraints.CENTER;
        mainPanel.add(aJScrollPane, c);

        JPanel buttonPanel = new JPanel();
        buttonPanel.setLayout(new FlowLayout(FlowLayout.CENTER));
        buttonPanel.add(showAnswer);
        buttonPanel.add(checkAnswer);

        c.gridx = 0;
        c.gridy = 2;
        c.gridwidth = 2;
        c.weightx = 0;
        c.weighty = 0;
        mainPanel.add(buttonPanel, c);

        c.gridx = 0;
        c.gridy = 3;
        c.gridwidth = 2;
        c.anchor = GridBagConstraints.CENTER;
        mainPanel.add(scoreLabel, c);

        JMenuBar menuBar = new JMenuBar();
        JMenu fileMenu = new JMenu("File");
        JMenuItem loadMenuItem = new JMenuItem("Load Card Set");
        loadMenuItem.addActionListener(new OpenMenuListener());
        fileMenu.add(loadMenuItem);
        JMenuItem redoMenuItem = new JMenuItem("Redo Incorrect Answers");
        redoMenuItem.addActionListener(new RedoMenuListener());
        fileMenu.add(redoMenuItem);
        menuBar.add(fileMenu);

        frame.setJMenuBar(menuBar);
        frame.getContentPane().add(mainPanel);
        frame.setSize(640, 400);
        frame.setVisible(true);

        incorrectlyAnsweredQuestions = new ArrayList<>();
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(FlashCardPlayer::new);
    }

    class NextCardListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            if (isShowAnswer) {
                display.setText(currentCard.getAnswer());
                showAnswer.setText("Next Card");
                isShowAnswer = false;
            } else {
                if (cardIterator.hasNext()) {
                    showNextCard();
                } else {
                    display.setText("That was the last card");
                    showAnswer.setEnabled(false);
                    checkHighScore();
                }
            }
        }
    }

    class RedoMenuListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            if (incorrectlyAnsweredQuestions.isEmpty()) {
                JOptionPane.showMessageDialog(frame, "You have not answered any questions incorrectly yet.");
            } else {
                cardList.clear(); // Clear the card list
                cardList.addAll(incorrectlyAnsweredQuestions); // Add incorrectly answered questions back to card list
                cardIterator = cardList.iterator(); // Use iterator over incorrectly answered questions
                showNextCard(); // Show the first incorrect question
            }
        }
    }

    class CheckAnswerListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            String userAnswerText = userAnswer.getText();
            if (userAnswerText.equalsIgnoreCase(currentCard.getAnswer())) {
                if (!incorrectlyAnsweredQuestions.contains(currentCard)) {
                    totalScore++; // Increment the total score only if the question was not previously answered incorrectly
                    updateScoreLabel();
                }
                JOptionPane.showMessageDialog(frame, "Correct!");
            } else {
                if (!incorrectlyAnsweredQuestions.contains(currentCard)) {
                    JOptionPane.showMessageDialog(frame, "Incorrect. The correct answer is: " + currentCard.getAnswer());
                    incorrectlyAnsweredQuestions.add(currentCard); // Add the incorrectly answered question
                }
            }
            showAnswer.setEnabled(true); // Enable the "Next" button after checking the answer
        }
    }
    class RedoNextCardListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            if (cardIterator.hasNext()) {
                showNextCard(); // Show the next incorrect question
            } else {
                JOptionPane.showMessageDialog(frame, "No more incorrect questions to redo.");
                showAnswer.setEnabled(false); // Disable the "Next" button when all incorrect questions are redone
            }
        }
    }


    class OpenMenuListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            JFileChooser fileOpen = new JFileChooser();
            fileOpen.showOpenDialog(frame);
            loadFile(fileOpen.getSelectedFile());
        }
    }

    private void loadFile(File selectedFile) {
        cardList = new ArrayList<>();

        try (BufferedReader reader = new BufferedReader(new FileReader(selectedFile))) {
            String line;
            while ((line = reader.readLine()) != null) {
                makeCard(line);
            }
        } catch (Exception e) {
            System.out.println("Couldn't read file");
            e.printStackTrace();
        }
        cardIterator = cardList.iterator();
        showNextCard();
    }

    private void showNextCard() {
        currentCard = cardIterator.next();
        display.setText(currentCard.getQuestion());
        userAnswer.setText("");
        showAnswer.setText("Next");
        isShowAnswer = true;
    }

    private void makeCard(String line) {
        String[] result = line.split("/");
        FlashCard card = new FlashCard(result[0], result[1]);
        cardList.add(card);
        System.out.println("Made a FlashCard from reading the file");
    }

    private int readHighScore() {
        File file = new File("highscore.txt");
        if (file.exists()) {
            try (BufferedReader reader = new BufferedReader(new FileReader(file))) {
                return Integer.parseInt(reader.readLine());
            } catch (IOException | NumberFormatException e) {
                e.printStackTrace();
            }
        }
        return 0;
    }

    private void writeHighScore(int newHighScore) {
        try (BufferedWriter writer = new BufferedWriter(new FileWriter("highscore.txt"))) {
            writer.write(String.valueOf(newHighScore));
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private void checkHighScore() {
        if (totalScore > highScore) {
            highScore = totalScore;
            writeHighScore(highScore);
            JOptionPane.showMessageDialog(frame, "New high score: " + highScore);
            updateScoreLabel();
        } else {
            JOptionPane.showMessageDialog(frame, "Your score: " + totalScore + ". High score: " + highScore);
        }
    }

    private void updateScoreLabel() {
        scoreLabel.setText("Score: " + totalScore + " | High Score: " + highScore);
    }
}

