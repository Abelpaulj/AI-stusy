from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
import uuid
from app.models.models import Document
from app import db
from app.routes.forms import UploadDocumentForm
from app.utils.document_processor import process_document

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('main/index.html', title='Home')

@main.route('/dashboard')
@login_required
def dashboard():
    documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_at.desc()).all()
    return render_template('main/dashboard.html', title='Dashboard', documents=documents)

@main.route('/about')
def about():
    return render_template('main/about.html', title='About')

@main.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_document():
    form = UploadDocumentForm()
    if form.validate_on_submit():
        if 'document' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['document']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file:
            # Generate a unique ID for this document
            doc_id = str(uuid.uuid4())
            
            # Create a directory for this document if it doesn't exist
            user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(current_user.id))
            doc_dir = os.path.join(user_upload_dir, doc_id)
            os.makedirs(doc_dir, exist_ok=True)
            
            # Save the file
            filename = secure_filename(file.filename)
            file_path = os.path.join(doc_dir, filename)
            file.save(file_path)
            
            # Create document record in database
            document = Document(
                title=form.title.data,
                filename=filename,
                file_path=file_path,
                content_type=file.content_type,
                user_id=current_user.id
            )
            
            db.session.add(document)
            db.session.commit()
            
            # Process the document
            try:
                process_document(document)
                flash('File successfully uploaded and processed')
                return redirect(url_for('study.view_document', doc_id=document.id))
            except Exception as e:
                flash(f'Error processing file: {str(e)}')
                return redirect(url_for('main.dashboard'))
    
    return render_template('main/upload.html', title='Upload Document', form=form)
