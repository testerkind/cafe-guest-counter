import os
import cv2
import base64
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from detector import GuestDetector
from history_manager import load_history, add_record, generate_pdf_report, generate_excel_report

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('reports', exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_occupancy_level(percent):
    if percent <= 30:
        return "Низкая"
    elif percent <= 70:
        return "Средняя"
    else:
        return "Высокая"

detector = GuestDetector()

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не выбран'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Пустое имя файла'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Неподдерживаемый формат'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    if not ext:
        ext = 'jpg'

    # Параметр вместимости одного стола (можно сделать настраиваемым через frontend)
    table_capacity = 4  # по умолчанию 4 места за столом

    if ext in ['mp4', 'avi', 'mov']:
        avg_guests, occupancy, annotated_frames = detector.process_video(filepath, table_capacity=table_capacity)
        bike_count = int(round(avg_guests))  # переименуем, но оставим совместимость с фронтом
        annotated_path = None
        if annotated_frames:
            base_name = os.path.splitext(filename)[0]
            out_img_name = base_name + '_annotated.jpg'
            out_img_path = os.path.join(app.config['UPLOAD_FOLDER'], out_img_name)
            cv2.imwrite(out_img_path, annotated_frames[0])
            annotated_path = out_img_path
        add_record(filename, bike_count, occupancy, annotated_path)
        return jsonify({
            'guest_count': bike_count,
            'occupancy': occupancy,
            'is_video': True,
            'message': f'Среднее количество гостей: {bike_count}'
        })
    else:
        total_guests, num_tables, occupancy, annotated_img = detector.process_image(filepath, table_capacity)
        base_name = os.path.splitext(filename)[0]
        out_img_name = base_name + '_annotated.jpg'
        out_img_path = os.path.join(app.config['UPLOAD_FOLDER'], out_img_name)
        cv2.imwrite(out_img_path, annotated_img)
        add_record(filename, total_guests, occupancy, out_img_path)
        annotated_url = '/' + out_img_path.replace('\\', '/')
        return jsonify({
            'guest_count': total_guests,
            'num_tables': num_tables,
            'occupancy': occupancy,
            'annotated_image': annotated_url,
            'is_video': False
        })

@app.route('/camera', methods=['POST'])
def camera_upload():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'error': 'Нет изображения'}), 400
    image_data = data['image'].split(',')[1]
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'cam_capture.jpg')
    with open(filepath, 'wb') as f:
        f.write(base64.b64decode(image_data))

    table_capacity = 4
    total_guests, num_tables, occupancy, annotated_img = detector.process_image(filepath, table_capacity)
    out_img_path = os.path.join(app.config['UPLOAD_FOLDER'], 'cam_capture_annotated.jpg')
    cv2.imwrite(out_img_path, annotated_img)
    add_record('webcam_capture', total_guests, occupancy, out_img_path)
    annotated_url = '/' + out_img_path.replace('\\', '/')
    return jsonify({
        'guest_count': total_guests,
        'num_tables': num_tables,
        'occupancy': occupancy,
        'annotated_image': annotated_url
    })

@app.route('/history', methods=['GET'])
def get_history():
    history = load_history()
    return jsonify(history)

@app.route('/report/pdf', methods=['GET'])
def report_pdf():
    history = load_history()
    output = 'reports/history_report.pdf'
    generate_pdf_report(history, output)
    return send_file(output, as_attachment=True)

@app.route('/report/excel', methods=['GET'])
def report_excel():
    history = load_history()
    output = 'reports/history_report.xlsx'
    generate_excel_report(history, output)
    return send_file(output, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
