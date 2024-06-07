package com.flashcard;
import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
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

    public FlashCardPlayer() {
        frame = new JFrame("Flash Card Player");
        JPanel mainPanel = new JPanel();
        mainPanel.setLayout(new BoxLayout(mainPanel, BoxLayout.Y_AXIS));
        Font mFont = new Font("Arial", Font.BOLD, 18);
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setResizable(false);

        display = new JTextArea(8, 20);
        display.setLineWrap(true);
        display.setWrapStyleWord(true);
        display.setFont(mFont);

        JScrollPane qJScrollPane = new JScrollPane(display);
        qJScrollPane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_ALWAYS);
        qJScrollPane.setHorizontalScrollBarPolicy(ScrollPaneConstants.HORIZONTAL_SCROLLBAR_NEVER);

        showAnswer = new JButton("Show Answer");
        showAnswer.addActionListener(new NextCardListener());

        userAnswer = new JTextArea(5, 20);
        userAnswer.setLineWrap(true);
        userAnswer.setWrapStyleWord(true);
        userAnswer.setFont(mFont);

        JScrollPane aJScrollPane = new JScrollPane(userAnswer);
        aJScrollPane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_ALWAYS);
        aJScrollPane.setHorizontalScrollBarPolicy(ScrollPaneConstants.HORIZONTAL_SCROLLBAR_NEVER);

        checkAnswer = new JButton("Check Answer");
        checkAnswer.addActionListener(new CheckAnswerListener());

        mainPanel.add(qJScrollPane);
        mainPanel.add(new JLabel("Your Answer:"));
        mainPanel.add(aJScrollPane);
        mainPanel.add(showAnswer);
        mainPanel.add(checkAnswer);

        JMenuBar menuBar = new JMenuBar();
        JMenu fileMenu = new JMenu("File");
        JMenuItem loadMenuItem = new JMenuItem("Load Card Set");
        loadMenuItem.addActionListener(new OpenMenuListener());

        fileMenu.add(loadMenuItem);
        menuBar.add(fileMenu);

        frame.setJMenuBar(menuBar);
        frame.getContentPane().add(BorderLayout.CENTER, mainPanel);
        frame.setSize(640, 600);
        frame.setVisible(true);
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
                }
            }
        }
    }

    class CheckAnswerListener implements ActionListener {
        @Override
        public void actionPerformed(ActionEvent e) {
            String userAnswerText = userAnswer.getText();
            if (userAnswerText.equalsIgnoreCase(currentCard.getAnswer())) {
                JOptionPane.showMessageDialog(frame, "Correct!");
            } else {
                JOptionPane.showMessageDialog(frame, "Incorrect. The correct answer is: " + currentCard.getAnswer());
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
        showAnswer.setText("Show Answer");
        isShowAnswer = true;
    }

    private void makeCard(String line) {
        String[] result = line.split("/");
        FlashCard card = new FlashCard(result[0], result[1]);
        cardList.add(card);
        System.out.println("Made a FlashCard from reading the file");
    }
}
