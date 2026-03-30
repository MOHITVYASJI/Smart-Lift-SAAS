import cv2
import os
import json
import numpy as np
from deepface import DeepFace
import faiss

class SpooferEngine:
    def check_liveness(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur_val = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_val < 35: 
            return False, "Spoof Detected (Unnatural Surface Texture)"
        return True, "Live Organism Detected"

class VisionEngine:
    def __init__(self, model_name="Facenet"):
        self.model_name = model_name
        self.spoofer = SpooferEngine()
        # Phase 4 Native QR Decoder Injection
        self.qr_detector = cv2.QRCodeDetector()
        self.index = None
        self.active_users = []

    def extract_vector_and_bbox(self, img_path_or_frame):
        try:
            objs = DeepFace.represent(img_path=img_path_or_frame, model_name=self.model_name, enforce_detection=True)
            if len(objs) > 0:
                vec = np.array(objs[0]["embedding"], dtype='float32')
                faiss.normalize_L2(vec.reshape(1, -1))
                return vec, objs[0]["facial_area"]
        except Exception as e:
            pass
        return None, None
        
    def extract_vector(self, img_path):
        vec, _ = self.extract_vector_and_bbox(img_path)
        return vec

    def build_faiss_index(self, users_list):
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
                    print(f"Error loading vector for User ID {user.user_id}")
                
        if len(vectors) == 0: return False

        dimension = len(vectors[0])
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(np.array(vectors, dtype='float32'))
        return True

    def scan_for_user(self, active_tenant_users):
        if not self.build_faiss_index(active_tenant_users):
            print("[Vision] CRITICAL: No active vectors mathematically mapped for this Tenant.")
            return "ERROR", "NO_DB", "No vectors configured."

        cap = cv2.VideoCapture(0)
        print("\n==================================")
        print("[Vision MULTI-MODAL SCANNER]")
        print("-> Action 1: Show QR Code (Seamless Scan)")
        print("-> Action 2: Trigger 's' (Face Authenticaton)")
        print("-> Action 3: Trigger 'q' (Power Down)")
        print("==================================\n")
        
        while True:
            ret, frame = cap.read()
            if not ret: continue
            
            # Phase 4: Dynamic Seamless QR Polling with Safety Bounds
            try:
                data, bbox, _ = self.qr_detector.detectAndDecode(frame)
                if data:
                    print(f"\n> [QR DETECTED] Token Extracted: {data}")
                    cap.release()
                    cv2.destroyAllWindows()
                    return "QR", data, "Token Discovered"
            except Exception as e:
                pass # Suppress erratic OpenCV camera geometry exceptions
            
            h, w = frame.shape[:2]
            cv2.rectangle(frame, (w//2 - 100, h//2 - 120), (w//2 + 100, h//2 + 120), (56, 189, 248), 2)
            cv2.putText(frame, "SMART LIFT NODE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (56, 189, 248), 2)
            cv2.putText(frame, "[QR/FACE ONLINE]", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (16, 185, 129), 1)
            cv2.imshow("Security Scanner Node", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('s'):
                print("\n> [Vision] Initiating Neural Face Scan...")
                
                is_live, msg = self.spoofer.check_liveness(frame)
                if not is_live:
                    print(f"> [SECURITY ALERT] {msg}")
                    cap.release()
                    cv2.destroyAllWindows()
                    return "ERROR", None, "Spoof Attack Blocked"
                
                live_vector, bbox = self.extract_vector_and_bbox(frame)
                if live_vector is not None:
                    live_vec_np = np.array([live_vector], dtype='float32')
                    faiss.normalize_L2(live_vec_np)
                    distances, indices = self.index.search(live_vec_np, k=1)
                    
                    threshold = 0.40 
                    best_match_dist = distances[0][0]
                    best_match_idx = indices[0][0]
                    
                    if best_match_dist > threshold and best_match_idx != -1:
                        matched_user = self.active_users[best_match_idx]
                        print(f"> [Vision ACCESS GRANTED] Verified Identity: {matched_user.name.upper()} ")
                        print(f"  └─ Confidence Score: {best_match_dist * 100:.1f}% \n")
                        if bbox:
                            x, y, w, h = bbox['x'], bbox['y'], bbox['w'], bbox['h']
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            cv2.putText(frame, f"{matched_user.name} ({matched_user.access_type})", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                            cv2.imshow("Security Scanner Node", frame)
                            cv2.waitKey(1000)
                        cap.release()
                        cv2.destroyAllWindows()
                        return "FACE", matched_user.name, "Verified"
                    else:
                        print(f"> [Vision REJECTED] Access Denied. Fingerprint Mismatch.")
                        if bbox:
                            x, y, w, h = bbox['x'], bbox['y'], bbox['w'], bbox['h']
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                            cv2.putText(frame, "DENIED / UNKNOWN", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                            cv2.imshow("Security Scanner Node", frame)
                            cv2.waitKey(1000)
                        cap.release()
                        cv2.destroyAllWindows()
                        return "ERROR", None, "Face Mismatch"
                else:
                    print("> [Vision WARN] Face not clearly visible. Step back.")

            elif key == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        return "EXIT", None, "Cancelled"
