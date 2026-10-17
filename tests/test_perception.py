"""Synthetic component checks; no dataset images or private observations."""
import tempfile,unittest,subprocess
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from app.tracker.byte_tracker import BYTETracker

class TrackingTests(unittest.TestCase):
    def test_low_confidence_detection_preserves_track(self):
        tracker=BYTETracker(SimpleNamespace(track_thresh=.35,track_buffer=60,match_thresh=.8,mot20=False),frame_rate=2.5)
        first=tracker.update(np.array([[10,10,80,180,.95]]),(200,200),(200,200))
        second=tracker.update(np.array([[12,10,82,180,.2]]),(200,200),(200,200))
        self.assertEqual(len(second),1)
        self.assertEqual(first[0].track_id,second[0].track_id)
    def test_empty_detections_do_not_create_people(self):
        tracker=BYTETracker(SimpleNamespace(track_thresh=.35,track_buffer=60,match_thresh=.8,mot20=False),frame_rate=2.5)
        self.assertEqual(tracker.update(np.empty((0,5)),(200,200),(200,200)),[])

class DecodeTests(unittest.TestCase):
    def test_original_resolution_and_pts_sampling(self):
        from app.perception import decode
        import cv2
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);video=path/'synthetic.mov'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=gray:s=1280x720:r=30:d=1.3','-c:v','mpeg4',str(video)],check=True)
            samples=decode(video,path)
            self.assertEqual(len(samples),4)
            self.assertEqual(cv2.imread(str(samples[0]['path'])).shape[:2],(720,1280))
            for i,sample in enumerate(samples):self.assertAlmostEqual(sample['timestamp_sec'],i*.4,places=2)
    def test_crop_enlarges_only_region(self):
        from app.perception import crop
        image=np.zeros((200,300,3),dtype=np.uint8)
        self.assertEqual(crop(image,[.1,.1,.5,.5]).shape[:2],(160,240))
        self.assertIsNone(crop(image,[.5,.5,.1,.1]))

class EvidenceTests(unittest.TestCase):
    def test_actual_yunet_runtime_and_jpeg_output(self):
        import base64,cv2
        from app.perception import Redactor,MODELS
        if not (MODELS/'yunet.onnx').exists():self.skipTest('Installed auxiliary weights required')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'frame.jpg';cv2.imwrite(str(path),np.full((720,1280,3),128,dtype=np.uint8))
            result=Redactor().evidence({'path':path,'timestamp_sec':1.2})
            decoded=cv2.imdecode(np.frombuffer(base64.b64decode(result['image_base64']),dtype=np.uint8),cv2.IMREAD_COLOR)
            self.assertEqual(decoded.shape[:2],(720,1280));self.assertEqual(result['timestamp_sec'],1.2)
    def test_detected_face_region_is_blurred(self):
        import cv2,base64
        from app.perception import Redactor
        class Detector:
            def setInputSize(self,size):pass
            def detect(self,image):return None,np.array([[40,40,80,80]])
        redactor=Redactor.__new__(Redactor);redactor.net=Detector()
        image=np.zeros((200,200,3),dtype=np.uint8)
        image[40:120:2,40:120]=255
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'frame.png';cv2.imwrite(str(path),image)
            result=redactor.evidence({'path':path,'timestamp_sec':0})
            decoded=cv2.imdecode(np.frombuffer(base64.b64decode(result['image_base64']),dtype=np.uint8),cv2.IMREAD_COLOR)
            self.assertLess(decoded[50:110,50:110].std(),image[50:110,50:110].std()/4)
