package com.flashcard;

public class FlashCard {

    private String question;
    private String answer;

    public FlashCard(String qstion, String ans) {
        question = qstion;
        answer = ans;
    }
    public String getQuestion(){
        return this.question;
    }
    public String getAnswer(){
        return this.answer;
    }
    public void setQuestion(String question) {
         this.question = question;
    }
    public void setAnswer(String answer) {
        this.answer = answer;
    }

}
