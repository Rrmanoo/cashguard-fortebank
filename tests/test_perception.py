"""CPU-only sampling, accurate timestamps, and evidence regression checks."""
import base64,subprocess,sys,tempfile,unittest
from pathlib import Path
import cv2,numpy as np
from app.perception import decode,evidence

class CPUSamplingTests(unittest.TestCase):
    def test_pts_sampling_and_cpu_downscale(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);video=p/'synthetic.mov'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=gray:s=1280x720:r=30:d=1.3','-c:v','mpeg4',str(video)],check=True)
            samples=decode(video,p,max_edge=1024)
            self.assertEqual(len(samples),4)
            self.assertEqual(cv2.imread(str(samples[0]['path'])).shape[:2],(576,1024))
            for i,sample in enumerate(samples):self.assertAlmostEqual(sample['timestamp_sec'],i*.4,places=2)
    def test_evidence_is_real_jpeg_at_original_timestamp(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'frame.png';cv2.imwrite(str(p),np.full((240,320,3),128,dtype=np.uint8))
            value=evidence({'path':p,'timestamp_sec':1.2})
            self.assertEqual(value['timestamp_sec'],1.2)
            self.assertTrue(base64.b64decode(value['image_base64']).startswith(b'\xff\xd8'))
    def test_runtime_imports_no_local_ml_stack(self):
        process=subprocess.run([sys.executable,'-c',
            'import app.inference,sys; assert not any(m in sys.modules for m in ["torch","transformers","onnxruntime","rtmlib"])'],capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stderr)
