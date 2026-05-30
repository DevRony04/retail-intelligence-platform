import uuid
import math

class Track:
    def __init__(self, track_id, bbox, confidence, is_staff=False):
        self.track_id = track_id
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = confidence
        self.is_staff = is_staff
        self.history = [bbox]
        self.frames_since_update = 0
        self.visitor_token = f"VIS_{uuid.uuid4().hex[:6]}"
        self.session_seq = 1
        self.last_zone = None
        self.zone_dwell_start = None

    def update(self, bbox, confidence):
        self.bbox = bbox
        self.confidence = confidence
        self.history.append(bbox)
        self.frames_since_update = 0

    @property
    def centroid(self):
        x = (self.bbox[0] + self.bbox[2]) / 2
        y = (self.bbox[1] + self.bbox[3]) / 2
        return (x, y)

class SimpleByteTracker:
    def __init__(self, max_lost_frames=30, dist_threshold=150):
        self.max_lost_frames = max_lost_frames
        self.dist_threshold = dist_threshold
        self.tracks = {}
        self.next_track_id = 1

    def update(self, detections, is_staff_classifier):
        """
        detections: list of bboxes [x1, y1, x2, y2, confidence]
        is_staff_classifier: callable that takes (bbox, frame) and returns bool
        """
        # Increment lost frames for existing tracks
        for track in self.tracks.values():
            track.frames_since_update += 1

        active_tracks = [t for t in self.tracks.values() if t.frames_since_update <= self.max_lost_frames]
        new_tracks = []

        for det in detections:
            bbox = det[:4]
            conf = det[4]
            det_centroid = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

            # Match with closest active track
            best_track = None
            min_dist = float('inf')

            for track in active_tracks:
                tx, ty = track.centroid
                dist = math.hypot(det_centroid[0] - tx, det_centroid[1] - ty)
                if dist < min_dist and dist < self.dist_threshold:
                    min_dist = dist
                    best_track = track

            if best_track is not None:
                best_track.update(bbox, conf)
                active_tracks.remove(best_track)  # Prevents double assignment
            else:
                # Create a new track
                is_staff = is_staff_classifier(bbox) if is_staff_classifier else False
                new_track = Track(self.next_track_id, bbox, conf, is_staff)
                self.tracks[self.next_track_id] = new_track
                self.next_track_id += 1
                new_tracks.append(new_track)

        # Cleanup very old tracks
        self.tracks = {tid: t for tid, t in self.tracks.items() if t.frames_since_update <= self.max_lost_frames}

        return list(self.tracks.values()), new_tracks
