from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from studyai_web_deployment.app.models.models import Document, Flashcard, Quiz, QuizQuestion, QuizOption
from studyai_web_deployment.app import db
from studyai_web_deployment.app.routes.forms import QueryForm
from studyai_web_deployment.app.utils.document_processor import query_document, generate_flashcards, generate_quiz

study = Blueprint('study', __name__)

@study.route('/document/<int:doc_id>')
@login_required
def view_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    
    # Check if the document belongs to the current user
    if document.user_id != current_user.id:
        flash('You do not have permission to view this document')
        return redirect(url_for('main.dashboard'))
    
    form = QueryForm()
    return render_template('study/document.html', title=document.title, document=document, form=form)

@study.route('/document/<int:doc_id>/query', methods=['POST'])
@login_required
def query(doc_id):
    document = Document.query.get_or_404(doc_id)
    
    # Check if the document belongs to the current user
    if document.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.json
    query_text = data.get('query')
    
    if not query_text:
        return jsonify({'error': 'Missing query'}), 400
    
    try:
        response = query_document(document, query_text)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@study.route('/document/<int:doc_id>/flashcards', methods=['GET', 'POST'])
@login_required
def flashcards(doc_id):
    document = Document.query.get_or_404(doc_id)
    
    # Check if the document belongs to the current user
    if document.user_id != current_user.id:
        flash('You do not have permission to view this document')
        return redirect(url_for('main.dashboard'))
    
    # Check if flashcards already exist for this document
    existing_flashcards = Flashcard.query.filter_by(document_id=doc_id).all()
    
    if request.method == 'POST' or not existing_flashcards:
        try:
            # Delete existing flashcards if regenerating
            if existing_flashcards:
                for card in existing_flashcards:
                    db.session.delete(card)
                db.session.commit()
            
            # Generate new flashcards
            flashcard_data = generate_flashcards(document)
            
            # Save flashcards to database
            for card_data in flashcard_data:
                flashcard = Flashcard(
                    front=card_data['front'],
                    back=card_data['back'],
                    document_id=doc_id
                )
                db.session.add(flashcard)
            
            db.session.commit()
            
            if request.method == 'POST':
                return jsonify({'success': True, 'flashcards': [{'id': card.id, 'front': card.front, 'back': card.back} for card in Flashcard.query.filter_by(document_id=doc_id).all()]})
            
        except Exception as e:
            if request.method == 'POST':
                return jsonify({'error': str(e)}), 500
            flash(f'Error generating flashcards: {str(e)}')
    
    flashcards = Flashcard.query.filter_by(document_id=doc_id).all()
    return render_template('study/flashcards.html', title=f'Flashcards - {document.title}', document=document, flashcards=flashcards)

@study.route('/document/<int:doc_id>/quiz', methods=['GET', 'POST'])
@login_required
def quiz(doc_id):
    document = Document.query.get_or_404(doc_id)
    
    # Check if the document belongs to the current user
    if document.user_id != current_user.id:
        flash('You do not have permission to view this document')
        return redirect(url_for('main.dashboard'))
    
    # Check if a quiz already exists for this document
    existing_quiz = Quiz.query.filter_by(document_id=doc_id).first()
    
    if request.method == 'POST' or not existing_quiz:
        try:
            # Delete existing quiz if regenerating
            if existing_quiz:
                db.session.delete(existing_quiz)
                db.session.commit()
            
            # Generate new quiz
            quiz_data = generate_quiz(document)
            
            # Save quiz to database
            quiz = Quiz(document_id=doc_id)
            db.session.add(quiz)
            db.session.flush()  # Get the quiz ID
            
            for question_data in quiz_data:
                question = QuizQuestion(
                    question_text=question_data['question'],
                    quiz_id=quiz.id
                )
                db.session.add(question)
                db.session.flush()  # Get the question ID
                
                for i, option_text in enumerate(question_data['options']):
                    option = QuizOption(
                        option_text=option_text,
                        is_correct=(i == question_data['correct_answer']),
                        question_id=question.id
                    )
                    db.session.add(option)
            
            db.session.commit()
            
            if request.method == 'POST':
                return jsonify({'success': True})
            
        except Exception as e:
            if request.method == 'POST':
                return jsonify({'error': str(e)}), 500
            flash(f'Error generating quiz: {str(e)}')
    
    quiz = Quiz.query.filter_by(document_id=doc_id).first()
    if quiz:
        questions = []
        for question in quiz.questions:
            questions.append({
                'id': question.id,
                'text': question.question_text,
                'options': [{'id': option.id, 'text': option.option_text} for option in question.options]
            })
        
        return render_template('study/quiz.html', title=f'Quiz - {document.title}', document=document, quiz=quiz, questions=questions)
    else:
        return render_template('study/quiz.html', title=f'Quiz - {document.title}', document=document, quiz=None, questions=None)

@study.route('/document/<int:doc_id>/quiz/submit', methods=['POST'])
@login_required
def submit_quiz(doc_id):
    document = Document.query.get_or_404(doc_id)
    
    # Check if the document belongs to the current user
    if document.user_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.json
    answers = data.get('answers', {})
    
    if not answers:
        return jsonify({'error': 'No answers provided'}), 400
    
    quiz = Quiz.query.filter_by(document_id=doc_id).first()
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    # Calculate score
    total_questions = 0
    correct_answers = 0
    results = {}
    
    for question in quiz.questions:
        total_questions += 1
        question_id = str(question.id)
        
        if question_id in answers:
            selected_option_id = answers[question_id]
            selected_option = QuizOption.query.get(selected_option_id)
            
            if selected_option and selected_option.is_correct:
                correct_answers += 1
                results[question_id] = {'correct': True}
            else:
                results[question_id] = {'correct': False}
                
                # Find the correct option
                for option in question.options:
                    if option.is_correct:
                        results[question_id]['correct_option_id'] = option.id
                        break
        else:
            results[question_id] = {'correct': False, 'not_answered': True}
            
            # Find the correct option
            for option in question.options:
                if option.is_correct:
                    results[question_id]['correct_option_id'] = option.id
                    break
    
    score = correct_answers / total_questions if total_questions > 0 else 0
    percentage = round(score * 100)
    
    return jsonify({
        'score': correct_answers,
        'total': total_questions,
        'percentage': percentage,
        'results': results
    })
