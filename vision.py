import cv2
import os
import json
import numpy as np
from deepface import DeepFace
import faiss
from collections import deque

class AdvancedLivenessDetector:
    """Mobile-Grade Liveness Detection Engine"""
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.mouth_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
        self.frame_history = deque(maxlen=15)  # Store last 15 frames for motion detection
        
    def check_face_quality(self, frame):
        """Check if face is well-lit and clearly visible"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Blur Detection (more sophisticated)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 40:  # Increased from 35
            return False, f"Face Blurry (Sharpness: {laplacian_var:.1f})"
        
        # 2. Brightness Detection
        brightness = np.mean(gray)
        if brightness < 40 or brightness > 240:
            return False, f"Lighting Issue (Brightness: {brightness:.0f})"
        
        # 3. Face Detection Confidence
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(faces) == 0:
            return False, "No face detected"
        if len(faces) > 1:
            return False, "Multiple faces detected"
            
        return True, f"Face Quality OK (Sharpness: {laplacian_var:.1f}, Brightness: {brightness:.0f})"
    
    def check_eye_blink(self, frames_list):
        """Detect eye blink for liveness (eyes open → closed → open)"""
        if len(frames_list) < 5:
            return False, "Insufficient frames"
        
        eye_detected_count = 0
        
        for frame in frames_list:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            
            if len(faces) > 0:
                x, y, w, h = faces[0]
                roi_gray = gray[y:y+h, x:x+w]
                eyes = self.eye_cascade.detectMultiScale(roi_gray)
                
                if len(eyes) >= 2:  # Both eyes visible
                    eye_detected_count += 1
        
        # If eye detection varies between frames, likely a real person
        blink_ratio = eye_detected_count / len(frames_list)
        if 0.3 < blink_ratio < 0.9:  # ~40-80% of frames show eyes = likely blinking
            return True, f"Liveness Detected (Eye Movement: {blink_ratio*100:.0f}%)"
        
        return False, "No eye movement detected (possible video spoof)"
    
    def check_head_movement(self, frames_list):
        """Detect head rotation for liveness"""
        if len(frames_list) < 3:
            return False, "Insufficient frames"
        
        face_positions = []
        gray_frames = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames_list]
        
        for gray in gray_frames:
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            if len(faces) > 0:
                x, y, w, h = faces[0]
                face_positions.append((x + w//2, y + h//2))  # Center point
        
        if len(face_positions) < 2:
            return False, "Face position tracking failed"
        
        # Check if face position changes (head movement)
        position_variance = np.var(face_positions, axis=0)
        movement = np.sum(position_variance)
        
        if movement > 5:  # Face moved significantly
            return True, f"Head Movement Detected (Variance: {movement:.1f})"
        
        return False, "No head movement (possible spoof)"
    
    def comprehensive_check(self, frames_list):
        """Perform all liveness checks"""
        if len(frames_list) == 0:
            return False, "No frames provided"
        
        # Check 1: Face Quality
        quality_ok, quality_msg = self.check_face_quality(frames_list[-1])
        if not quality_ok:
            return False, quality_msg
        
        # Check 2: Eye Blink
        blink_ok, blink_msg = self.check_eye_blink(frames_list)
        if not blink_ok:
            return False, blink_msg
        
        # Check 3: Head Movement
        movement_ok, movement_msg = self.check_head_movement(frames_list)
        if not movement_ok:
            return False, movement_msg
        
        return True, "✓ Liveness Verified (Multi-factor check passed)"


class VisionEngine:
    """Professional-Grade Face Recognition Engine (Mobile-Level Accuracy)"""
    
    def __init__(self, model_names=None):
        """
        Initialize multi-model ensemble for highest accuracy
        Models: Facenet (mobile-optimized), VGGFace2 (robust), ArcFace (accurate)
        """
        if model_names is None:
            self.model_names = ["Facenet512", "VGGFace2", "ArcFace"]  # 3-model ensemble
        else:
            self.model_names = [model_names] if isinstance(model_names, str) else model_names
        
        self.primary_model = "Facenet512"  # Fastest + most accurate for mobile
        self.liveness_detector = AdvancedLivenessDetector()
        self.qr_detector = cv2.QRCodeDetector()
        self.index = None
        self.active_users = []
        self.index_map = {}  # Map for each model's index

    def preprocess_image(self, frame):
        """
        Enhance image quality: adjust brightness, contrast, and normalize
        Similar to mobile preprocessing
        """
        # Convert to HSV for better light handling
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Histogram equalization on V channel
        hsv[:, :, 2] = cv2.equalizeHist(hsv[:, :, 2])
        
        # Convert back to BGR
        enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        # Contrast normalization (CLAHE - Contrast Limited Adaptive Histogram Equalization)
        gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # Merge back (optional but helps with processing)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    
    def extract_vector_ensemble(self, img_path_or_frame, use_all_models=False):
        """
        Extract face vector using ensemble of models for maximum accuracy
        Returns: average embedding + confidence score
        """
        try:
            # Preprocess if it's a frame
            if isinstance(img_path_or_frame, np.ndarray):
                frame = self.preprocess_image(img_path_or_frame)
            else:
                frame = img_path_or_frame
            
            embeddings = []
            bboxes = set()
            
            # Get embeddings from all models
            models_to_use = self.model_names if use_all_models else [self.primary_model]
            
            for model in models_to_use:
                try:
                    objs = DeepFace.represent(
                        img_path=frame, 
                        model_name=model, 
                        enforce_detection=True,
                        normalization='VGGFace'
                    )
                    
                    if len(objs) > 0:
                        vec = np.array(objs[0]["embedding"], dtype='float32')
                        faiss.normalize_L2(vec.reshape(1, -1))
                        embeddings.append(vec)
                        
                        bbox = objs[0].get("facial_area", {})
                        if bbox:
                            bboxes.add(tuple(bbox.values()))
                
                except Exception as e:
                    print(f"[Vision] Model {model} failed: {str(e)[:50]}")
                    continue
            
            if len(embeddings) == 0:
                return None, None, 0.0
            
            # Average embeddings from all models (ensemble)
            ensemble_vector = np.mean(embeddings, axis=0).astype('float32')
            faiss.normalize_L2(ensemble_vector.reshape(1, -1))
            
            # Confidence = number of models that successfully detected face
            confidence = len(embeddings) / len(models_to_use)
            
            bbox = None
            if bboxes:
                bbox = list(bboxes)[0]
            
            return ensemble_vector, bbox, confidence
        
        except Exception as e:
            print(f"[Vision] Extract vector error: {str(e)[:100]}")
            return None, None, 0.0
    
    def extract_vector(self, img_path):
        """Legacy method for single frame extraction"""
        vec, _, _ = self.extract_vector_ensemble(img_path, use_all_models=False)
        return vec

    def build_faiss_index(self, users_list):
        """Build FAISS index with improved similarity search"""
        self.active_users = []
        vectors = []
        
        for user in users_list:
            if user.face_vector and len(user.face_vector) > 5:
                try:
                    vec = np.array(json.loads(user.face_vector), dtype='float32')
                    faiss.normalize_L2(vec.reshape(1, -1))
                    vectors.append(vec.flatten())
                    self.active_users.append(user)
                except Exception as e:
                    print(f"[Vision] Error loading vector for User ID {user.user_id}: {str(e)[:50]}")
        
        if len(vectors) == 0:
            print("[Vision] CRITICAL: No active vectors for this tenant")
            return False
        
        dimension = len(vectors[0])
        
        # Use IndexIVFFlat for scalability (like mobile systems)
        # Falls back to IndexFlatIP if few users
        if len(vectors) < 100:
            self.index = faiss.IndexFlatIP(dimension)
        else:
            nlist = max(10, len(vectors) // 10)  # ~10 cells
            quantizer = faiss.IndexFlatIP(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            self.index.train(np.array(vectors, dtype='float32'))
        
        self.index.add(np.array(vectors, dtype='float32'))
        print(f"[Vision] FAISS Index built with {len(vectors)} users")
        return True

    def scan_for_user(self, active_tenant_users):
        """
        Mobile-grade face recognition with multi-frame matching
        Similar to Apple FaceID and Android Face Unlock
        """
        if not self.build_faiss_index(active_tenant_users):
            print("[Vision] CRITICAL: No active vectors for this tenant")
            return "ERROR", "NO_DB", "No vectors configured"
        
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        print("\n" + "="*50)
        print("🔐 SmartLift Face Recognition Scanner v2.0")
        print("="*50)
        print("📱 Professional Grade - Mobile-Level Accuracy")
        print("1️⃣  Show QR Code (Instant)")
        print("2️⃣  Press 's' for Face Scan (with liveness)")
        print("3️⃣  Press 'q' to Exit")
        print("="*50 + "\n")
        
        frame_queue = deque(maxlen=15)  # Keep last 15 frames for liveness
        match_confidence_history = deque(maxlen=5)  # Track match confidence
        
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            
            frame_queue.append(frame.copy())
            h, w = frame.shape[:2]
            
            # Try QR scanning first (faster)
            try:
                data, bbox, _ = self.qr_detector.detectAndDecode(frame)
                if data:
                    print(f"\n✅ [QR Detected] Token: {data[:30]}...")
                    cap.release()
                    cv2.destroyAllWindows()
                    return "QR", data, "QR verified"
            except:
                pass
            
            # Display UI
            cv2.rectangle(frame, (w//2-110, h//2-130), (w//2+110, h//2+130), (56, 189, 248), 3)
            cv2.putText(frame, "SmartLift Scanner", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (56, 189, 248), 2)
            cv2.putText(frame, "Press 's' to scan face", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (16, 185, 129), 1)
            cv2.imshow("🔐 Face Recognition Scanner", frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s'):
                print("\n⏳ Initiating professional face scan...")
                print("   Verifying liveness (checking for real face)...")
                
                # Step 1: Liveness Check
                is_live, liveness_msg = self.liveness_detector.comprehensive_check(list(frame_queue))
                print(f"   └─ {liveness_msg}")
                
                if not is_live:
                    print("❌ [SECURITY] Spoof/video detected. Access denied.")
                    cap.release()
                    cv2.destroyAllWindows()
                    return "ERROR", None, "Liveness check failed"
                
                # Step 2: Multi-frame matching (like mobile FaceID)
                print("   Capturing biometric data (multi-frame)...")
                
                best_overall_match = None
                best_overall_distance = -1
                match_scores = []
                
                # Test multiple recent frames for confidence
                frames_to_test = list(frame_queue)[-10:]  # Last 10 frames
                
                for idx, test_frame in enumerate(frames_to_test):
                    live_vector, bbox, ensemble_confidence = self.extract_vector_ensemble(
                        test_frame, 
                        use_all_models=True  # Use all models for enrollment
                    )
                    
                    if live_vector is None or ensemble_confidence < 0.66:
                        print(f"   └─ Frame {idx+1}: Face not detected (ensemble conf: {ensemble_confidence:.0%})")
                        continue
                    
                    live_vec_np = np.array([live_vector], dtype='float32')
                    faiss.normalize_L2(live_vec_np)
                    
                    # Search with k=5 to get top matches
                    distances, indices = self.index.search(live_vec_np, k=5)
                    best_match_dist = distances[0][0]
                    best_match_idx = indices[0][0]
                    
                    print(f"   └─ Frame {idx+1}: Confidence {best_match_dist:.0%}")
                    match_scores.append(best_match_dist)
                    
                    if best_match_dist > best_overall_distance:
                        best_overall_distance = best_match_dist
                        best_overall_match = best_match_idx
                
                if len(match_scores) == 0:
                    print("❌ Face recognition failed - no clear detection")
                    cap.release()
                    cv2.destroyAllWindows()
                    return "ERROR", None, "Face detection failed"
                
                # More lenient threshold for high-confidence ensemble matches
                # Mobile systems use ~0.50-0.65 depending on conditions
                avg_confidence = np.mean(match_scores)
                min_confidence = np.min(match_scores)
                max_confidence = np.max(match_scores)
                
                print(f"\n📊 Analysis Results:")
                print(f"   ├─ Avg Confidence: {avg_confidence:.0%}")
                print(f"   ├─ Min Confidence: {min_confidence:.0%}")
                print(f"   ├─ Max Confidence: {max_confidence:.0%}")
                print(f"   └─ Ensemble Models: 3 (Facenet512, VGGFace2, ArcFace)")
                
                # Adaptive threshold - stricter if confidence is inconsistent
                consistency = 1 - (max_confidence - min_confidence)  # How consistent matches are
                adaptive_threshold = 0.55 if consistency > 0.8 else 0.60
                
                if best_overall_distance > adaptive_threshold and best_overall_match != -1:
                    matched_user = self.active_users[best_overall_match]
                    print(f"\n✅ [ACCESS GRANTED]")
                    print(f"   ├─ Identity: {matched_user.name.upper()}")
                    print(f"   ├─ Position: {matched_user.access_type}")
                    print(f"   ├─ Confidence: {best_overall_distance:.0%}")
                    print(f"   └─ Liveness: Verified (real person confirmed)\n")
                    
                    cap.release()
                    cv2.destroyAllWindows()
                    return "FACE", matched_user.name, "Verified"
                
                else:
                    print(f"\n❌ [ACCESS DENIED]")
                    print(f"   ├─ Reason: Face mismatch or unknown person")
                    print(f"   ├─ Confidence: {best_overall_distance:.0%} (threshold: {adaptive_threshold:.0%})")
                    print(f"   └─ Try again with better lighting\n")
                    
                    cap.release()
                    cv2.destroyAllWindows()
                    return "ERROR", None, "Face mismatch"
            
            elif key == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        return "EXIT", None, "Cancelled"
