from flask import Flask, Response, render_template, request, redirect, url_for, flash, session
import cv2
import mediapipe as mp
import numpy as np
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'a17f3e5b6a8c4e2f9d6e7f4a5c8b3d7f'

# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'sanjay@123'
app.config['MYSQL_DB'] = 'vision_therapy'

mysql = MySQL(app)
bcrypt = Bcrypt(app)

# MediaPipe Face Mesh setup
mp_face_mesh = mp.solutions.face_mesh
LEFT_IRIS = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]

def generate_iris_tracking():
    cap = cv2.VideoCapture(0)  # Capture from the webcam
    
    with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as face_mesh:
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv2.flip(frame, 1)  # Flip the frame to provide mirror-like experience
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_h, img_w = frame.shape[:2]
            results = face_mesh.process(rgb_frame)

            if results.multi_face_landmarks:
                mesh_points = np.array([np.multiply([p.x, p.y], [img_w, img_h]).astype(int) 
                                        for p in results.multi_face_landmarks[0].landmark])
                
                (l_cx, l_cy), l_radius = cv2.minEnclosingCircle(mesh_points[LEFT_IRIS])
                (r_cx, r_cy), r_radius = cv2.minEnclosingCircle(mesh_points[RIGHT_IRIS])
                
                center_left = np.array([l_cx, l_cy], dtype=np.int32)
                center_right = np.array([r_cx, r_cy], dtype=np.int32)
                
                cv2.circle(frame, center_left, int(l_radius), (255, 0, 255), 2)
                cv2.circle(frame, center_right, int(r_radius), (255, 0, 255), 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)',
                       (username, email, password_hash))
        mysql.connection.commit()
        cursor.close()

        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  # Corrected key to 'password'

        # Query the database for the user
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.check_password_hash(user[3], password):  # Assuming password_hash is in the 4th column
            session['user_id'] = user[0]  # Assuming id is in the 1st column
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('index.html')
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/exercise/<string:name>')
def exercise(name):
    if 'user_id' not in session:
        flash('Please log in to access exercises.', 'warning')
        return redirect(url_for('login'))
    return render_template(f'{name}.html')

@app.route('/thrataka')
def thrataka():
    return exercise('thrataka')

@app.route('/saccades')
def saccades():
    return exercise('saccades')

@app.route('/balloon')
def balloon():
    return exercise('balloon')

@app.route('/testing')
def testing():
    return render_template('testing.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_iris_tracking(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)
