from flask import Flask, render_template, request, send_file, jsonify, url_for
import os
import uuid
import re
import json
from datetime import datetime
from cv_generator import create_cv_from_dict

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

GENERATED_FOLDER = 'generated'
if not os.path.exists(GENERATED_FOLDER):
    os.makedirs(GENERATED_FOLDER)

extracted_data_store = {}

def parse_cv_text(text):
    """Parse CV text into structured data"""
    lines = text.split('\n')
    lines = [line.strip() for line in lines if line.strip()]
    
    info = {
        'name': 'CURRICULUM VITAE',
        'title': '',
        'email': '',
        'phone': '',
        'summary': '',
        'skills': [],
        'experience': [],
        'education': [],
        'achievements': [],
        'references': []
    }
    
    # Extract Name
    for line in lines[:5]:
        if len(line) < 50 and not any(x in line.lower() for x in ['curriculum', 'vitae', 'cv', 'resume']):
            info['name'] = line
            break
    
    # Extract Email
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if email_match:
        info['email'] = email_match.group()
    
    # Extract Phone
    phone_patterns = [r'\+254\s?\d{9}', r'0\d{9}', r'07\d{8}', r'01\d{8}']
    for pattern in phone_patterns:
        phone_match = re.search(pattern, text)
        if phone_match:
            info['phone'] = phone_match.group()
            break
    
    # Find sections
    sections = {}
    current_section = None
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if 'education' in line_lower and len(line) < 30:
            current_section = 'education'
            sections['education'] = {'start': i, 'lines': []}
        elif 'employment' in line_lower or 'experience' in line_lower:
            current_section = 'experience'
            sections['experience'] = {'start': i, 'lines': []}
        elif 'skill' in line_lower and len(line) < 30:
            current_section = 'skills'
            sections['skills'] = {'start': i, 'lines': []}
        elif 'qualification' in line_lower or 'additional' in line_lower:
            current_section = 'achievements'
            sections['achievements'] = {'start': i, 'lines': []}
        elif 'reference' in line_lower or 'referee' in line_lower:
            current_section = 'references'
            sections['references'] = {'start': i, 'lines': []}
        elif current_section:
            sections[current_section]['lines'].append(line)
    
    # Extract Summary
    summary_lines = []
    edu_start = sections.get('education', {}).get('start', 999)
    for i, line in enumerate(lines):
        if i == 0:
            continue
        if i < edu_start:
            if len(line) > 20 and not any(x in line.lower() for x in ['curriculum', 'vitae', 'cv']):
                summary_lines.append(line)
        else:
            break
    if summary_lines:
        info['summary'] = ' '.join(summary_lines)
    
    # Extract Education
    edu_lines = sections.get('education', {}).get('lines', [])
    if not edu_lines:
        in_edu = False
        for line in lines:
            if 'education' in line.lower():
                in_edu = True
                continue
            if in_edu and line:
                if any(x in line.lower() for x in ['employment', 'skill', 'qualification', 'experience', 'reference']):
                    break
                if len(line) > 3:
                    edu_lines.append(line)
    info['education'] = edu_lines[:10]
    
    # Extract Experience
    exp_lines = sections.get('experience', {}).get('lines', [])
    if not exp_lines:
        in_exp = False
        for line in lines:
            if 'employment' in line.lower() or 'experience' in line.lower():
                in_exp = True
                continue
            if in_exp and line:
                if any(x in line.lower() for x in ['education', 'skill', 'qualification', 'reference']):
                    break
                if len(line) > 3:
                    exp_lines.append(line)
    
    exp_section = []
    current_exp = None
    for line in exp_lines:
        if re.search(r'\d{4}', line):
            if current_exp:
                exp_section.append(current_exp)
            date_match = re.search(r'(\d{4}\s*[–\-]\s*[A-Za-z\s]+)', line)
            date_part = date_match.group(1) if date_match else ''
            
            if ':' in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    date_part = parts[0].strip()
                    rest = parts[1].strip()
                    if '–' in rest or '-' in rest:
                        rest_parts = re.split(r'[–\-]', rest)
                        if len(rest_parts) >= 2:
                            current_exp = {
                                'company': rest_parts[1].strip(),
                                'title': rest_parts[0].strip(),
                                'date': date_part,
                                'bullets': []
                            }
                        else:
                            current_exp = {'company': rest, 'title': '', 'date': date_part, 'bullets': []}
                    else:
                        current_exp = {'company': rest, 'title': '', 'date': date_part, 'bullets': []}
            elif '–' in line or '-' in line:
                parts = re.split(r'[–\-]', line)
                clean_parts = [p.strip() for p in parts if p.strip() and not re.search(r'\d{4}', p)]
                if len(clean_parts) >= 2:
                    current_exp = {
                        'company': clean_parts[1],
                        'title': clean_parts[0],
                        'date': date_part if date_part else '',
                        'bullets': []
                    }
                else:
                    current_exp = {'company': line, 'title': '', 'date': date_part if date_part else '', 'bullets': []}
            else:
                current_exp = {'company': line, 'title': '', 'date': date_part if date_part else '', 'bullets': []}
        elif current_exp and line and len(line) > 3:
            clean_line = re.sub(r'^[•\-]\s*', '', line)
            if clean_line and not any(x in clean_line.lower() for x in ['education', 'skill', 'qualification', 'reference']):
                current_exp['bullets'].append(clean_line)
    if current_exp:
        exp_section.append(current_exp)
    info['experience'] = exp_section
    
    # Extract Skills
    skills_lines = sections.get('skills', {}).get('lines', [])
    skills_found = []
    if skills_lines:
        for line in skills_lines:
            parts = re.split(r'[•,;\n]', line)
            for part in parts:
                part = part.strip()
                if part and len(part) < 60 and len(part) > 2:
                    part = re.sub(r'^[•\-]\s*', '', part)
                    part = re.sub(r'\s+', ' ', part)
                    if part and not any(x in part.lower() for x in ['skills', 'abilities']):
                        skills_found.append(part)
    if not skills_found:
        in_skills = False
        for line in lines:
            if 'skill' in line.lower() and len(line) < 30:
                in_skills = True
                continue
            if in_skills and line:
                if any(x in line.lower() for x in ['education', 'employment', 'experience', 'qualification', 'reference']):
                    break
                parts = re.split(r'[•,;\n]', line)
                for part in parts:
                    part = part.strip()
                    if part and len(part) < 60 and len(part) > 2:
                        part = re.sub(r'^[•\-]\s*', '', part)
                        if part:
                            skills_found.append(part)
    info['skills'] = skills_found[:15]
    
    # Extract Achievements
    ach_lines = sections.get('achievements', {}).get('lines', [])
    achievements_found = []
    for line in ach_lines:
        clean_line = re.sub(r'^[•\-]\s*', '', line)
        if clean_line and len(clean_line) > 3:
            achievements_found.append(clean_line)
    if not achievements_found:
        in_qual = False
        for line in lines:
            if 'qualification' in line.lower() or 'additional' in line.lower():
                in_qual = True
                continue
            if in_qual and line:
                if any(x in line.lower() for x in ['experience', 'education', 'skill', 'employment', 'reference']):
                    break
                if len(line) > 3:
                    clean_line = re.sub(r'^[•\-]\s*', '', line)
                    if clean_line:
                        achievements_found.append(clean_line)
    info['achievements'] = achievements_found[:8]
    
    # Extract References
    ref_lines = sections.get('references', {}).get('lines', [])
    references = []
    if ref_lines:
        current_ref = {}
        for line in ref_lines:
            if line and not any(x in line.lower() for x in ['email:', 'phone:', 'tel:', 'address']):
                if len(line) > 5 and not re.match(r'^[\d\-+]', line):
                    if current_ref and current_ref.get('name'):
                        references.append(current_ref)
                    current_ref = {'name': line, 'position': '', 'email': '', 'phone': ''}
                elif line and current_ref:
                    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line)
                    if email_match:
                        current_ref['email'] = email_match.group()
                        line = line.replace(email_match.group(), '').strip()
                        if line and not current_ref['position']:
                            current_ref['position'] = line
                    phone_match = re.search(r'\+254\s?\d{9}|0\d{9}|07\d{8}|01\d{8}', line)
                    if phone_match:
                        current_ref['phone'] = phone_match.group()
                        line = line.replace(phone_match.group(), '').strip()
                        if line and not current_ref['position']:
                            current_ref['position'] = line
                    elif line and not current_ref['position']:
                        current_ref['position'] = line
        if current_ref and current_ref.get('name'):
            references.append(current_ref)
    info['references'] = references[:5]
    
    # Extract Title
    if info['experience'] and len(info['experience']) > 0:
        first_exp = info['experience'][0]
        if first_exp.get('title'):
            info['title'] = first_exp['title']
    
    return info

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_from_text():
    try:
        cv_text = request.form.get('cv_text', '')
        if not cv_text:
            return render_template('index.html', error='Please paste your CV text.')
        
        cv_data = parse_cv_text(cv_text)
        session_id = uuid.uuid4().hex[:8]
        extracted_data_store[session_id] = cv_data
        
        return render_template('result.html', data=cv_data, session_id=session_id)
    
    except Exception as e:
        return render_template('index.html', error=f'Error: {str(e)}')

@app.route('/generate-pdf/<session_id>')
def generate_pdf(session_id):
    try:
        if session_id not in extracted_data_store:
            return "Session expired. Please paste your CV again.", 404
        
        data = extracted_data_store[session_id]
        pdf_path = create_cv_from_dict(data)
        filename = os.path.basename(pdf_path)
        
        return render_template('download.html', filename=filename, name=data.get('name', 'CV'))
    
    except Exception as e:
        return f"Error generating CV: {str(e)}", 500

@app.route('/download/<filename>')
def download_cv(filename):
    try:
        filepath = os.path.join('generated', filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)