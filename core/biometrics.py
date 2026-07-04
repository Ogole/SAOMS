import cv2
import numpy as np
import os
import pickle
import base64
from django.conf import settings
from cryptography.fernet import Fernet


class FaceRecognition:
    """Face recognition for UPF attendance"""

    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.encodings_dir = os.path.join(settings.MEDIA_ROOT, 'face_encodings')
        os.makedirs(self.encodings_dir, exist_ok=True)
        self.key_file = os.path.join(settings.MEDIA_ROOT, 'face_encodings', '.key')
        self.cipher = self._get_cipher()

    def _get_cipher(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
        return Fernet(key)

    def _decode_image(self, image_data):
        if isinstance(image_data, str):
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def _extract_face_encoding(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.05, minNeighbors=3, minSize=(40, 40)
        )
        if len(faces) == 0:
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.01, minNeighbors=2, minSize=(30, 30)
            )
        if len(faces) == 0:
            return None, 0
        if len(faces) > 1:
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        (x, y, w, h) = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        face_roi = cv2.resize(face_roi, (100, 100))
        face_roi = cv2.equalizeHist(face_roi)
        hist = cv2.calcHist([face_roi], [0], None, [256], [0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        return hist.flatten(), 1

    def _compare_faces(self, hist1, hist2):
        return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

    def register_face(self, officer_id, image_data):
        try:
            img = self._decode_image(image_data)
            encoding, face_count = self._extract_face_encoding(img)
            if encoding is None:
                if face_count == 0:
                    return {'success': False, 'error': 'No face detected. Please look directly at the camera.'}
                else:
                    return {'success': False, 'error': 'Multiple faces detected. Only one person should be in frame.'}
            _, buffer = cv2.imencode('.jpg', img)
            face_image = base64.b64encode(buffer).decode()
            encoding_data = {
                'officer_id': officer_id,
                'encoding': encoding.tolist(),
                'face_image': face_image
            }
            encrypted = self.cipher.encrypt(pickle.dumps(encoding_data))
            file_path = os.path.join(self.encodings_dir, f'{officer_id}.enc')
            with open(file_path, 'wb') as f:
                f.write(encrypted)
            return {'success': True, 'message': 'Face registered successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def recognize_face(self, image_data):
        try:
            img = self._decode_image(image_data)
            encoding, face_count = self._extract_face_encoding(img)
            if encoding is None:
                if face_count == 0:
                    return {'success': False, 'error': 'No face detected'}
                else:
                    return {'success': False, 'error': 'Multiple faces detected'}
            best_match = None
            best_score = 0
            for filename in os.listdir(self.encodings_dir):
                if not filename.endswith('.enc'):
                    continue
                file_path = os.path.join(self.encodings_dir, filename)
                try:
                    with open(file_path, 'rb') as f:
                        encrypted = f.read()
                    decrypted = self.cipher.decrypt(encrypted)
                    stored = pickle.loads(decrypted)
                    stored_encoding = np.array(stored['encoding'])
                    score = self._compare_faces(encoding, stored_encoding)
                    if score > best_score and score > 0.85:
                        best_score = score
                        best_match = stored['officer_id']
                except Exception:
                    continue
            if best_match:
                return {
                    'success': True,
                    'match': {
                        'officer_id': best_match,
                        'confidence': round(best_score * 100, 1)
                    }
                }
            return {'success': False, 'error': 'Face not recognized. Please try again.'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def has_face(self, officer_id):
        file_path = os.path.join(self.encodings_dir, f'{officer_id}.enc')
        return os.path.exists(file_path)

    def delete_face(self, officer_id):
        file_path = os.path.join(self.encodings_dir, f'{officer_id}.enc')
        if os.path.exists(file_path):
            os.remove(file_path)
            return {'success': True, 'message': 'Face deleted'}
        return {'success': False, 'error': 'No face found'}

    def get_enrolled_count(self):
        return len([f for f in os.listdir(self.encodings_dir) if f.endswith('.enc')])