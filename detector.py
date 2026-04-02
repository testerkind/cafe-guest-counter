import cv2
from ultralytics import YOLO
from collections import Counter
import numpy as np

class GuestDetector:
    def __init__(self, model_path='yolov8n.pt', conf_threshold=0.5):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.person_class = 0
        self.table_class = 60

    def detect_tables_and_people(self, image_path):
        img = cv2.imread(image_path)
        results = self.model(img, conf=self.conf_threshold)[0]
        boxes = results.boxes
        tables = []
        people = []
        for box in boxes:
            conf = float(box.conf)
            if conf < self.conf_threshold:
                continue
            cls = int(box.cls)
            bbox = box.xyxy[0].tolist()
            if cls == self.table_class:
                tables.append(bbox)
            elif cls == self.person_class:
                people.append(bbox)
        # Удаление дублирующихся bbox людей (слишком похожих)
        people = self._remove_duplicate_boxes(people, iou_threshold=0.5)
        annotated = results.plot()
        return tables, people, annotated

    def _remove_duplicate_boxes(self, boxes, iou_threshold=0.5):
        """Удаляет сильно перекрывающиеся bounding box'ы (оставляет один)."""
        if not boxes:
            return []
        boxes = np.array(boxes)
        keep = []
        indices = np.argsort([(b[2]-b[0])*(b[3]-b[1]) for b in boxes])[::-1]  # по площади (убыв)
        while len(indices) > 0:
            i = indices[0]
            keep.append(i)
            if len(indices) == 1:
                break
            ious = []
            for j in indices[1:]:
                iou = self._compute_iou(boxes[i], boxes[j])
                ious.append(iou)
            indices = indices[1:][np.array(ious) < iou_threshold]
        return [boxes[i].tolist() for i in keep]

    def _compute_iou(self, box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2]-box1[0])*(box1[3]-box1[1])
        area2 = (box2[2]-box2[0])*(box2[3]-box2[1])
        union = area1 + area2 - inter
        return inter / union if union > 0 else 0

    def count_unique_guests(self, tables, people):
        """
        Для каждого стола считает людей, центр которых находится внутри стола.
        Это точнее, чем пересечение bbox.
        """
        guest_counts = []
        assigned_people = set()
        for table in tables:
            tx1, ty1, tx2, ty2 = table
            count = 0
            for i, person in enumerate(people):
                if i in assigned_people:
                    continue
                # Центр человека
                cx = (person[0] + person[2]) / 2
                cy = (person[1] + person[3]) / 2
                if tx1 <= cx <= tx2 and ty1 <= cy <= ty2:
                    count += 1
                    assigned_people.add(i)
            guest_counts.append(count)
        total_unique_guests = len(assigned_people)
        return guest_counts, total_unique_guests

    def process_image(self, image_path, table_capacity=4):
        tables, people, annotated = self.detect_tables_and_people(image_path)
        print(f"[DEBUG] Найдено столов: {len(tables)}, людей: {len(people)}")
        if not tables:
            total_guests = len(people)
            num_tables = 1 if total_guests > 0 else 0
            max_capacity = table_capacity * num_tables if num_tables else table_capacity
            occupancy_percent = (total_guests / max_capacity) * 100 if max_capacity else 0
            occupancy_level = self._get_occupancy_level(occupancy_percent)
            print(f"[DEBUG] Без столов -> гостей: {total_guests}")
            return total_guests, num_tables, occupancy_level, annotated

        guest_counts, total_guests = self.count_unique_guests(tables, people)
        num_tables = len(tables)
        max_capacity = table_capacity * num_tables
        occupancy_percent = (total_guests / max_capacity) * 100 if max_capacity else 0
        occupancy_level = self._get_occupancy_level(occupancy_percent)
        print(f"[DEBUG] Гостей за столами: {total_guests} (людей всего: {len(people)}, не за столами: {len(people)-total_guests})")
        return total_guests, num_tables, occupancy_level, annotated

    def process_video(self, video_path, sample_interval=30, table_capacity=4):
        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        guest_counts = []
        occupancy_levels = []
        annotated_frames = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % sample_interval == 0:
                results = self.model(frame, conf=self.conf_threshold)[0]
                tables = []
                people = []
                for box in results.boxes:
                    cls = int(box.cls)
                    bbox = box.xyxy[0].tolist()
                    if cls == self.table_class:
                        tables.append(bbox)
                    elif cls == self.person_class:
                        people.append(bbox)
                people = self._remove_duplicate_boxes(people)
                if not tables:
                    total_guests = len(people)
                else:
                    _, total_guests = self.count_unique_guests(tables, people)
                guest_counts.append(total_guests)
                max_capacity = table_capacity * len(tables) if tables else table_capacity
                occ_percent = (total_guests / max_capacity) * 100 if max_capacity else 0
                occupancy_levels.append(self._get_occupancy_level(occ_percent))
                if len(annotated_frames) < 5:
                    annotated_frames.append(results.plot())
            frame_count += 1
        cap.release()
        avg_guests = sum(guest_counts) / len(guest_counts) if guest_counts else 0
        common_occupancy = Counter(occupancy_levels).most_common(1)[0][0] if occupancy_levels else "Низкая"
        return avg_guests, common_occupancy, annotated_frames

    def _get_occupancy_level(self, percent):
        if percent <= 30:
            return "Низкая"
        elif percent <= 70:
            return "Средняя"
        else:
            return "Высокая"
